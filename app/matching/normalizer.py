"""Title normalization.

Deliberately minimal and predictable rather than aggressive — the goal is
to remove *formatting* noise (punctuation, casing, whitespace) so
"AirPods Pro (2nd Generation)" and "AirPods Pro 2nd Gen" compare fairly,
without rewriting words in ways that could accidentally merge two actually
different products (e.g. we never strip model numbers or capacities).
"""

from __future__ import annotations

import re

_PUNCTUATION_RE = re.compile(r"[^\w\s]", re.UNICODE)
_WHITESPACE_RE = re.compile(r"\s+")

# Common marketing/formatting synonyms that don't change product identity.
_SYNONYM_MAP = {
    "generation": "gen",
    "2nd": "2",
    "3rd": "3",
    "4th": "4",
    "5th": "5",
    "1st": "1",
}


def normalize_title(title: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace, apply a small
    synonym map. Does not touch word order or remove any words — that is
    fuzzy matching's job (see ``matching/matcher.py``), not normalization's.
    """
    text = title.strip().lower()
    # Delete punctuation entirely rather than replacing it with a space --
    # replacing "WH-1000XM5" with "WH 1000XM5" would tokenize it differently
    # from the equally-common unhyphenated "WH1000XM5" spelling, which
    # defeats fuzzy matching on exactly the kind of formatting variance this
    # function exists to neutralize. Deleting is safe here because product
    # titles almost always also have real whitespace between distinct words;
    # punctuation is rarely a title's *only* word separator.
    text = _PUNCTUATION_RE.sub("", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()

    words = text.split(" ")
    words = [_SYNONYM_MAP.get(word, word) for word in words]
    return " ".join(words)
