"""Retrieve handbook chunks, apply guardrails, and call the generator."""

from __future__ import annotations

from hr_policy_rag.config import Settings
from hr_policy_rag.embeddings import Embedder, document_frequencies
from hr_policy_rag.guardrails import Action, classify
from hr_policy_rag.index import Retriever
from hr_policy_rag.models import Answer, Hit, Question
from hr_policy_rag.prompts import (
    CLARIFY_REGION,
    REFUSE_PII,
    ROUTE_HR,
    UNKNOWN,
    render_user,
    system_prompt,
)
from hr_policy_rag.providers import LLMProvider
from hr_policy_rag.select import select_sentences
from hr_policy_rag.textutil import content_tokens, mentioned_regions


class Pipeline:
    def __init__(
        self,
        retriever: Retriever,
        provider: LLMProvider,
        settings: Settings,
        *,
        guardrails_enabled: bool,
        document_frequency: dict[str, int],
    ) -> None:
        self.retriever = retriever
        self.provider = provider
        self.settings = settings
        self.guardrails_enabled = guardrails_enabled
        self.document_frequency = document_frequency

    def answer_text(self, question: str) -> Answer:
        regions = mentioned_regions(question)
        hits = tuple(self.retriever.search(question, regions))
        action = classify(question)
        response = self._respond(question, list(hits), regions, action)
        return Answer(
            question_id="",
            question=question,
            response=response,
            hits=hits,
            behaviour_expected=action.value,
            category="",
        )

    def answer_question(self, item: Question) -> Answer:
        regions = mentioned_regions(item.question)
        hits = tuple(self.retriever.search(item.question, regions))
        action = classify(item.question)
        response = self._respond(item.question, list(hits), regions, action)
        return Answer(
            question_id=item.id,
            question=item.question,
            response=response,
            hits=hits,
            behaviour_expected=item.behaviour,
            category=item.category,
        )

    def _respond(
        self,
        question: str,
        hits: list[Hit],
        regions: set[str],
        action: Action,
    ) -> str:
        if action is Action.CLARIFY:
            return CLARIFY_REGION
        if self.guardrails_enabled and action is Action.REFUSE_PII:
            return REFUSE_PII
        if self.guardrails_enabled and action is Action.ROUTE_HR:
            return ROUTE_HR
        if action in {Action.REFUSE_PII, Action.ROUTE_HR}:
            return self.provider.complete(
                system=system_prompt(guardrails=False),
                user=render_user(question, []),
            )
        if self._missing_from_handbook(question):
            return UNKNOWN
        sentences = select_sentences(
            hits,
            question,
            regions,
            limit=self.settings.max_sentences,
        )
        if not sentences:
            return UNKNOWN
        return self.provider.complete(
            system=system_prompt(guardrails=self.guardrails_enabled),
            user=render_user(question, sentences),
        )

    def _missing_from_handbook(self, question: str) -> bool:
        tokens = content_tokens(question)
        if not tokens:
            return True
        return any(self.document_frequency.get(token, 0) == 0 for token in tokens)


def frequencies_for(embedder: Embedder, texts: list[str]) -> dict[str, int]:
    del embedder
    return document_frequencies(texts)
