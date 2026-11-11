"""Shared records for documents, retrieval hits, and labelled questions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Document:
    id: str
    title: str
    region: str
    topic: str
    body: str


@dataclass(frozen=True)
class Chunk:
    id: str
    doc_id: str
    title: str
    region: str
    topic: str
    text: str


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float


@dataclass(frozen=True)
class Question:
    id: str
    question: str
    reference_answer: str
    reference_doc_ids: tuple[str, ...]
    reference_contexts: tuple[str, ...]
    must_include: tuple[str, ...]
    must_not_include: tuple[str, ...]
    behaviour: str
    category: str


@dataclass(frozen=True)
class Answer:
    question_id: str
    question: str
    response: str
    hits: tuple[Hit, ...]
    behaviour_expected: str
    category: str


@dataclass(frozen=True)
class QuestionScore:
    id: str
    category: str
    behaviour: str
    question: str
    response: str
    retrieved_doc_ids: tuple[str, ...]
    retrieved_contexts: tuple[str, ...]
    hit: float | None
    reciprocal_rank: float | None
    string_presence: float
    refusal_correctness: float
    non_llm_context_recall: float | None

    @property
    def failed(self) -> bool:
        if self.string_presence < 1.0 or self.refusal_correctness < 1.0:
            return True
        if self.hit is not None and self.hit < 1.0:
            return True
        return self.non_llm_context_recall is not None and self.non_llm_context_recall < 1.0


@dataclass(frozen=True)
class MetricValue:
    name: str
    value: float
    threshold: float

    @property
    def passed(self) -> bool:
        return self.value >= self.threshold


@dataclass(frozen=True)
class EvalResult:
    variant: str
    mode: str
    metrics: dict[str, float]
    metric_values: tuple[MetricValue, ...]
    questions: tuple[QuestionScore, ...]

    @property
    def passed(self) -> bool:
        return all(item.passed for item in self.metric_values)

    @property
    def failed_metrics(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.metric_values if not item.passed)
