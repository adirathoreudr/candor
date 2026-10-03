"""What the memory can see at a moment: the hard rules live here and nowhere else.

- A unit exists from its delivery time on; nothing after `as_of` is visible.
- A deleted message is gone from its deletion time on.
- An edit replaces the message text from the edit time on.
- Deletion events are bookkeeping, not content, so they are never visible as units.
"""
from dataclasses import replace
from datetime import datetime

from candor.ingest import Corpus, Unit


class Memory:
    def __init__(self, corpus: Corpus):
        self.corpus = corpus
        self.by_id = {u.id: u for u in corpus.units}

    def is_visible(self, unit_id: str, as_of: datetime) -> bool:
        u = self.by_id.get(unit_id)
        if u is None or u.time > as_of or u.meta.get("event") == "deleted":
            return False
        gone = self.corpus.deleted.get(unit_id)
        return not (gone and gone <= as_of)

    def unit_at(self, unit_id: str, as_of: datetime) -> Unit:
        """The unit as it read at `as_of`, latest edit applied. Caller checks visibility."""
        u = self.by_id[unit_id]
        newer = [text for t, text in self.corpus.edits.get(u.id, []) if t <= as_of]
        return replace(u, text=newer[-1], meta={**u.meta, "edited": True}) if newer else u

    def visible(self, as_of: datetime) -> list[Unit]:
        return [self.unit_at(u.id, as_of) for u in self.corpus.units if self.is_visible(u.id, as_of)]

    def assert_visible(self, ids: list[str], as_of: datetime) -> None:
        """Last line of defence before anything is written out."""
        bad = [i for i in ids if not self.is_visible(i, as_of)]
        if bad:
            raise AssertionError(f"non-visible ids at {as_of.isoformat()}: {bad}")
