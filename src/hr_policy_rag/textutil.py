"""Token and sentence helpers shared by retrieval and guardrails."""

from __future__ import annotations

import re

STOPWORDS: frozenset[str] = frozenset(
    {
        "a",
        "about",
        "after",
        "all",
        "also",
        "am",
        "an",
        "and",
        "any",
        "are",
        "as",
        "at",
        "be",
        "before",
        "bring",
        "by",
        "can",
        "cannot",
        "cant",
        "check",
        "company",
        "could",
        "cover",
        "covers",
        "decide",
        "did",
        "do",
        "does",
        "dont",
        "each",
        "for",
        "from",
        "get",
        "gets",
        "had",
        "handbook",
        "has",
        "have",
        "how",
        "i",
        "if",
        "ignore",
        "im",
        "in",
        "into",
        "is",
        "it",
        "its",
        "just",
        "long",
        "many",
        "me",
        "much",
        "my",
        "no",
        "not",
        "of",
        "offer",
        "offers",
        "on",
        "only",
        "or",
        "our",
        "out",
        "over",
        "part",
        "per",
        "percent",
        "percentage",
        "please",
        "print",
        "right",
        "rule",
        "rules",
        "same",
        "send",
        "share",
        "should",
        "so",
        "tell",
        "than",
        "that",
        "the",
        "their",
        "them",
        "then",
        "there",
        "they",
        "this",
        "to",
        "too",
        "toward",
        "towards",
        "under",
        "up",
        "us",
        "was",
        "we",
        "were",
        "what",
        "whats",
        "when",
        "where",
        "which",
        "who",
        "why",
        "will",
        "with",
        "would",
        "you",
        "your",
    }
)

_TOKEN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_SENTENCE = re.compile(r"(?<=[.!?])\s+")

REGION_PATTERNS: dict[str, re.Pattern[str]] = {
    "us": re.compile(r"\b(united states|u\.s\.a\.|u\.s\.|usa|austin)\b", re.IGNORECASE),
    "uk": re.compile(r"\b(united kingdom|u\.k\.|uk|london|britain)\b", re.IGNORECASE),
    "de": re.compile(r"\b(germany|german|berlin|deutschland)\b", re.IGNORECASE),
}

_SELF_REGION = re.compile(
    r"\b(?:i am|i'm|i work|i live|i am based|i'm based)\s+in\s+(?:the\s+)?"
    r"(united states|united kingdom|germany|berlin|london|austin|uk|usa)\b",
    re.IGNORECASE,
)

_PLACE_TO_REGION = {
    "united states": "us",
    "usa": "us",
    "austin": "us",
    "united kingdom": "uk",
    "uk": "uk",
    "london": "uk",
    "britain": "uk",
    "germany": "de",
    "berlin": "de",
}


def normalize(text: str) -> str:
    lowered = text.lower().replace("401(k)", "401k")
    lowered = lowered.replace("'", "").replace("’", "")
    return lowered


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(normalize(text))


def content_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    for token in tokenize(text):
        if token in STOPWORDS:
            continue
        if len(token) <= 2 and not token.isdigit():
            continue
        tokens.append(token)
    return tokens


def split_sentences(text: str) -> list[str]:
    parts = _SENTENCE.split(text.strip())
    return [part.strip() for part in parts if part.strip()]


def regions_in(text: str) -> set[str]:
    found: set[str] = set()
    for region, pattern in REGION_PATTERNS.items():
        if pattern.search(text):
            found.add(region)
    return found


def self_region(question: str) -> str | None:
    match = _SELF_REGION.search(question)
    if match is None:
        return None
    return _PLACE_TO_REGION[match.group(1).lower()]


def mentioned_regions(question: str) -> set[str]:
    personal = self_region(question)
    if personal is not None:
        return {personal}
    return regions_in(question)
