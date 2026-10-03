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
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime

import numpy as np
import Stemmer

from candor import config
from candor.ingest import UNIDENTIFIED, Unit
from candor.store import Memory

_STOP = set("""a an the and or but if of to in on at by for with from as is are was were be been being it its this that
these those i me my we our you your he she they them his her their what which who whom when where why how do does did
done have has had not no so than too very can will would should could just about into over also any all some there here
up down out then""".split())
_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[.'][a-z0-9]+)*")
_STEMMER = Stemmer.Stemmer("english")


def tokenize(text: str) -> list[str]:
    """Lowercase words, Snowball-stemmed, stopwords dropped. Dotted handles and email local parts
    ("sarah.patel") also emit their parts, so a name matches the address it is written in."""
    out = []
    for tok in _TOKEN_RE.findall(text.lower().replace("'", "")):
        if tok in _STOP:
            continue
        parts = tok.split(".")
        out.append(tok if any(p.isdigit() for p in parts) else _STEMMER.stemWord(tok))
        if len(parts) > 1 and not any(p.isdigit() for p in parts):
            out.extend(_STEMMER.stemWord(p) for p in parts if p and p not in _STOP)
    return out


def doc_text(u: Unit, text: str) -> str:
    """What gets indexed: the content plus who, where and when, so 'what did Dana say on Slack' matches."""
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
    return f"{head}\n{text}"


@dataclass(frozen=True)
class Doc:
    unit_id: str
    text: str
    valid_from: datetime          # unit delivery time or edit time
    valid_to: datetime | None     # next edit time, exclusive


class Index:
    def __init__(self, memory: Memory, embed_model: str = config.EMBED_MODEL):
        self.memory = memory
        self.docs = self._versions(memory)
        self._bm25_build([tokenize(d.text) for d in self.docs])
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
                docs.append(Doc(u.id, doc_text(u, text), start, end))
        return docs

    # BM25 (Okapi, k1=1.5, b=0.75)
    def _bm25_build(self, tokens: list[list[str]]) -> None:
        self.tf = [Counter(t) for t in tokens]
        self.dl = np.array([len(t) for t in tokens], dtype=float)
        self.avgdl = float(self.dl.mean())
        df = Counter(term for t in tokens for term in set(t))
        n = len(tokens)
        self.idf = {term: math.log(1 + (n - f + 0.5) / (f + 0.5)) for term, f in df.items()}

    def bm25(self, query: str, k1: float = 1.5, b: float = 0.75) -> np.ndarray:
        scores = np.zeros(len(self.docs))
        norm = k1 * (1 - b + b * self.dl / self.avgdl)
        for term in set(tokenize(query)):
            idf = self.idf.get(term)
            if idf is None:
                continue
            tf = np.array([c.get(term, 0) for c in self.tf], dtype=float)
            scores += idf * tf * (k1 + 1) / (tf + norm)
        return scores

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

    def search(self, query: str, as_of: datetime, k: int = 20, rrf_k: int = 60) -> list[tuple[str, float]]:
        """Visible unit ids ranked by fused BM25 + dense score, best first."""
        visible = self.mask(as_of)
        fused = np.zeros(len(self.docs))
        for scores in (self.bm25(query), self.dense(query)):
            order = [i for i in np.argsort(-scores, kind="stable") if visible[i]]
            for rank, i in enumerate(order):
                fused[i] += 1.0 / (rrf_k + rank + 1)
        out, seen = [], set()
        for i in np.argsort(-fused, kind="stable"):
            if not visible[i] or fused[i] == 0:
                continue
            uid = self.docs[i].unit_id
            if uid not in seen:
                seen.add(uid)
                out.append((uid, float(fused[i])))
            if len(out) == k:
                break
        return out
