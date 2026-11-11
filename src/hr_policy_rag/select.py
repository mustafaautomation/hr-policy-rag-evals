"""Choose handbook sentences the answer is allowed to quote."""

from __future__ import annotations

from hr_policy_rag.models import Hit
from hr_policy_rag.textutil import content_tokens, regions_in, split_sentences


def select_sentences(
    hits: list[Hit],
    question: str,
    regions: set[str],
    *,
    limit: int,
) -> list[str]:
    question_words = set(content_tokens(question))
    ranked: list[tuple[int, int, str]] = []
    order = 0
    for hit in hits:
        for sentence in split_sentences(hit.chunk.text):
            mentioned = regions_in(sentence)
            if regions and mentioned and not mentioned <= regions:
                continue
            overlap = len(question_words & set(content_tokens(sentence)))
            if overlap <= 0:
                continue
            ranked.append((overlap, order, sentence))
            order += 1
    ranked.sort(key=lambda item: (-item[0], item[1]))
    chosen: list[tuple[int, str]] = []
    seen: set[str] = set()
    for _overlap, position, sentence in ranked:
        if sentence in seen:
            continue
        seen.add(sentence)
        chosen.append((position, sentence))
        if len(chosen) >= limit:
            break
    chosen.sort(key=lambda item: item[0])
    return [sentence for _position, sentence in chosen]
