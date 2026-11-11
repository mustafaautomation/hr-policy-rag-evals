"""Build a pipeline for a named variant and run the eval set."""

from __future__ import annotations

from hr_policy_rag.config import Settings, load_settings
from hr_policy_rag.corpus import chunk_documents, load_corpus
from hr_policy_rag.embeddings import build_embedder, document_frequencies
from hr_policy_rag.index import Retriever
from hr_policy_rag.models import EvalResult, Question
from hr_policy_rag.paths import questions_path
from hr_policy_rag.pipeline import Pipeline
from hr_policy_rag.providers import FakeProvider, LLMProvider, provider_for_answer
from hr_policy_rag.questions import load_questions
from hr_policy_rag.scoring import make_result, score_answers

VARIANTS = ("standard", "bad-retriever", "no-guardrail")


def build_pipeline(
    settings: Settings,
    variant: str = "standard",
    *,
    embedder_kind: str = "local",
    force_fake: bool = False,
) -> tuple[Pipeline, list[Question]]:
    if variant not in VARIANTS:
        raise ValueError(f"Unknown variant {variant}")
    documents = load_corpus()
    chunks = chunk_documents(documents, settings.chunk_size, settings.chunk_overlap)
    embedder = build_embedder(embedder_kind, settings.dimensions, settings.embedding_model)
    fit = getattr(embedder, "fit", None)
    texts = [chunk.text for chunk in chunks]
    if callable(fit):
        fit(texts)
    mode = "worst" if variant == "bad-retriever" else "standard"
    retriever = Retriever(chunks, embedder, settings, mode=mode)
    guardrails = variant != "no-guardrail"
    provider: LLMProvider
    if force_fake:
        provider = FakeProvider(obey_guardrails=guardrails)
    else:
        provider = provider_for_answer(
            settings.answer_model,
            obey_guardrails=guardrails,
            force_fake=False,
        )
    pipeline = Pipeline(
        retriever,
        provider,
        settings,
        guardrails_enabled=guardrails,
        document_frequency=document_frequencies(texts),
    )
    questions = load_questions(questions_path(), chunks, require_stored_contexts=False)
    return pipeline, questions


def run_variant(
    variant: str,
    *,
    mode: str = "offline",
    settings: Settings | None = None,
) -> EvalResult:
    active = settings or load_settings()
    if mode not in {"offline", "live"}:
        raise ValueError(f"Unknown mode {mode}")
    force_fake = mode == "offline"
    pipeline, questions = build_pipeline(active, variant, force_fake=force_fake)
    answers = [pipeline.answer_question(item) for item in questions]
    scores = score_answers(questions, answers)
    metric_names: tuple[str, ...] = active.offline_metrics
    extra: dict[str, float] | None = None
    if mode == "live":
        from hr_policy_rag.live import score_live

        extra = score_live(
            scores,
            judge_model=active.judge_model,
            embedding_model=active.embedding_model,
            references={item.id: item.reference_answer for item in questions},
        )
        metric_names = active.offline_metrics + active.live_metrics
    return make_result(
        variant=variant,
        mode=mode,
        scores=scores,
        thresholds=active.thresholds,
        metric_names=metric_names,
        extra_metrics=extra,
    )
