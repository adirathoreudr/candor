"""Text normalization shared by search and record linking."""
import re

import Stemmer

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
