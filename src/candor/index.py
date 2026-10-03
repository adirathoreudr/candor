"""Search index over every version of every unit.

A unit's text can change (Slack edits), so the index holds one document per text version, each
valid over a time window. A search at `as_of` only scores documents that are visible then, so an
edit is found by its new wording from the edit time on, and never before.

Two scorers, fused with reciprocal rank fusion:
- BM25 over a light normalization of the text (exact names, numbers, ids)
- dense cosine similarity from a local embedding model (paraphrase)
Corpus embeddings are cached in artifacts/ keyed by model and text, so no model call repeats.
"""
import hashlib
import math
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime

import numpy as np

from candor import config, links
from candor.ingest import UNIDENTIFIED, Unit
from candor.store import Memory
from candor.text import tokenize


def doc_head(u: Unit) -> str:
    """Who, where and when, so 'what did Dana say on Slack' matches. Indexed as its own field."""
    who = u.speaker or ("unidentified speaker" if u.author_kind == UNIDENTIFIED else "")
    when = u.time.strftime("%a %b %d %Y")
    head = f"{u.context}. {who}. {when}."
    m = u.meta
    if u.source == "gmail":
        head += f" From {m['from']} to {', '.join(m['to'])}{' cc ' + ', '.join(m['cc']) if m['cc'] else ''}."
    elif u.source == "calendar":
        head += (f" {m['summary']}, {m['start']} to {m['end']}, {m['status']}, location {m.get('location') or 'none'}, "
                 f"attendees {', '.join(a['email'] for a in m['attendees'])}.")
    elif u.source == "dictation":
        head += f" Delivery: {m['delivery_state']}."
    return head


@dataclass(frozen=True)
class Doc:
    unit_id: str
    head: str                     # who / where / when
    body: str                     # what was said
    valid_from: datetime          # unit delivery time or edit time
    valid_to: datetime | None     # next edit time, exclusive

    @property
    def text(self) -> str:
        return f"{self.head}\n{self.body}"


class BM25:
    """Okapi BM25 over pre-tokenized documents."""

    def __init__(self, tokens: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.tf = [Counter(t) for t in tokens]
        dl = np.array([len(t) for t in tokens], dtype=float)
        self.norm = k1 * (1 - b + b * dl / max(dl.mean(), 1e-9))
        self.k1 = k1
        df = Counter(term for t in tokens for term in set(t))
        self.idf = {term: math.log(1 + (len(tokens) - f + 0.5) / (f + 0.5)) for term, f in df.items()}

    def scores(self, query_terms: set[str]) -> np.ndarray:
        out = np.zeros(len(self.tf))
        for term in query_terms:
            idf = self.idf.get(term)
            if idf is None:
                continue
            tf = np.array([c.get(term, 0) for c in self.tf], dtype=float)
            out += idf * tf * (self.k1 + 1) / (tf + self.norm)
        return out


class Index:
    # The header (title, speaker, recipients) matches every record in a meeting or thread, so it
    # counts for less than the content: otherwise "Yeah." outranks the decision because of its title.
    HEAD_WEIGHT = 0.3
    # Records with fewer content words than this ("Yeah.", "Chris?", "Thanks, guys.") cannot be
    # evidence for anything; they rank after every record that has content.
    MIN_CONTENT_TERMS = 3
    # Each of the top LINK_TOP records lifts its linked partners by LINK_WEIGHT x its own score (max,
    # not sum). Only "same communication" links rank: an email thread, a dictation and what it became.
    # Measured on train: meeting -> calendar links flood the ranking (one event per 100+ segments)
    # and Slack thread links drift off topic in long threads; both lowered the score.
    LINK_TOP = 10
    LINK_WEIGHT = 0.3
    RANKING_LINKS = {links.EMAIL_THREAD, links.DICTATION_SENT}

    def __init__(self, memory: Memory, embed_model: str = config.EMBED_MODEL):
        self.memory = memory
        self.links = links.build(memory.corpus)
        self.docs = self._versions(memory)
        body_tokens = [tokenize(d.body) for d in self.docs]
        self.contentful = np.array([len(set(t)) >= self.MIN_CONTENT_TERMS for t in body_tokens])
        self.body_bm25 = BM25(body_tokens)
        self.head_bm25 = BM25([tokenize(d.head) for d in self.docs])
        self.embed_model = embed_model
        self._embedder = None
        self.vectors = self._corpus_vectors()

    @staticmethod
    def _versions(memory: Memory) -> list[Doc]:
        docs = []
        for u in memory.corpus.units:
            if u.meta.get("event") == "deleted":
                continue
            history = memory.corpus.edits.get(u.id, [])
            starts = [u.time] + [t for t, _ in history]
            texts = [u.text] + [t for _, t in history]
            for i, (start, text) in enumerate(zip(starts, texts)):
                end = starts[i + 1] if i + 1 < len(starts) else None
                docs.append(Doc(u.id, doc_head(u), text, start, end))
        return docs

    def bm25(self, query: str) -> np.ndarray:
        terms = set(tokenize(query))
        return self.body_bm25.scores(terms) + self.HEAD_WEIGHT * self.head_bm25.scores(terms)

    # Dense
    def _embedder_model(self):
        if self._embedder is None:
            from fastembed import TextEmbedding
            self._embedder = TextEmbedding(self.embed_model, cache_dir=str(config.MODEL_CACHE),
                                           threads=config.EMBED_THREADS)
        return self._embedder

    def _corpus_vectors(self, chunk: int = 64) -> np.ndarray:
        """Embed in checkpointed chunks: memory stays flat and an interrupted run resumes where it stopped."""
        texts = [d.text[:config.EMBED_MAX_CHARS] for d in self.docs]
        digest = hashlib.sha256(("\x00".join(texts) + self.embed_model).encode()).hexdigest()[:16]
        out_dir = config.ARTIFACTS / "embeddings"
        path = out_dir / f"{self.embed_model.replace('/', '__')}-{digest}.npy"
        if path.exists():
            return np.load(path).astype(np.float32)
        parts_dir = out_dir / f".parts-{digest}"
        parts_dir.mkdir(parents=True, exist_ok=True)
        parts = []
        for n, start in enumerate(range(0, len(texts), chunk)):
            part = parts_dir / f"{n:04d}.npy"
            if not part.exists():
                vecs = np.array(list(self._embedder_model().passage_embed(texts[start:start + chunk],
                                                                          batch_size=config.EMBED_BATCH)),
                                dtype=np.float32)
                np.save(part, vecs)
                print(f"embedded {min(start + chunk, len(texts))}/{len(texts)}", file=sys.stderr)
            parts.append(np.load(part))
        vecs = np.concatenate(parts)
        vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
        np.save(path, vecs.astype(np.float16))
        for p in parts_dir.iterdir():
            p.unlink()
        parts_dir.rmdir()
        return vecs

    def dense(self, query: str) -> np.ndarray:
        q = np.array(next(iter(self._embedder_model().query_embed([query]))), dtype=np.float32)
        return self.vectors @ (q / np.linalg.norm(q))

    def mask(self, as_of: datetime) -> np.ndarray:
        return np.array([self.memory.is_visible(d.unit_id, as_of) and d.valid_from <= as_of
                         and (d.valid_to is None or as_of < d.valid_to) for d in self.docs])

    def _link_bonus(self, fused: np.ndarray, visible: np.ndarray) -> np.ndarray:
        bonus = np.zeros(len(self.docs))
        if not self.LINK_WEIGHT:
            return bonus
        doc_of = {self.docs[i].unit_id: i for i in np.flatnonzero(visible)}   # one visible version per unit
        ranked = [i for i in np.lexsort((-fused, ~self.contentful)) if visible[i] and fused[i] > 0]
        for i in ranked[:self.LINK_TOP]:
            for partner, kind in self.links.get(self.docs[i].unit_id, {}).items():
                j = doc_of.get(partner) if kind in self.RANKING_LINKS else None
                if j is not None:
                    bonus[j] = max(bonus[j], self.LINK_WEIGHT * fused[i])
        return bonus

    def search(self, query: str, as_of: datetime, k: int = 20, rrf_k: int = 60) -> list[tuple[str, float]]:
        """Visible unit ids ranked by fused BM25 + dense score, best first."""
        visible = self.mask(as_of)
        fused = np.zeros(len(self.docs))
        for scores in (self.bm25(query), self.dense(query)):
            order = [i for i in np.argsort(-scores, kind="stable") if visible[i]]
            for rank, i in enumerate(order):
                fused[i] += 1.0 / (rrf_k + rank + 1)
        fused = fused + self._link_bonus(fused, visible)
        out, seen = [], set()
        for i in np.lexsort((-fused, ~self.contentful)):   # contentful first, then by fused score
            if not visible[i] or fused[i] == 0:
                continue
            uid = self.docs[i].unit_id
            if uid not in seen:
                seen.add(uid)
                out.append((uid, float(fused[i])))
            if len(out) == k:
                break
        return out
