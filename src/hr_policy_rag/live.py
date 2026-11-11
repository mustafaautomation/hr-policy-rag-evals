"""Live RAGAS metrics. This module calls OpenAI and is not used by the offline gate."""

from __future__ import annotations

import os

from hr_policy_rag.models import QuestionScore


class LiveEvalUnavailable(RuntimeError):
    pass


def score_live(
    rows: tuple[QuestionScore, ...],
    *,
    judge_model: str,
    embedding_model: str,
    references: dict[str, str],
) -> dict[str, float]:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise LiveEvalUnavailable("OPENAI_API_KEY is not set")
    from openai import AsyncOpenAI
    from ragas.embeddings.base import BaseRagasEmbedding, embedding_factory
    from ragas.llms import llm_factory
    from ragas.metrics.collections import (
        AnswerRelevancy,
        ContextPrecision,
        ContextRecall,
        Faithfulness,
    )

    client = AsyncOpenAI(api_key=api_key)
    llm = llm_factory(judge_model, client=client)
    embeddings = embedding_factory(
        "openai",
        model=embedding_model,
        client=client,
        interface="modern",
    )
    if not isinstance(embeddings, BaseRagasEmbedding):
        raise TypeError("RAGAS embedding factory did not return the modern interface")
    faithfulness = Faithfulness(llm=llm)
    relevancy = AnswerRelevancy(llm=llm, embeddings=embeddings)
    precision = ContextPrecision(llm=llm)
    recall = ContextRecall(llm=llm)

    faith_scores: list[float] = []
    relevancy_scores: list[float] = []
    precision_scores: list[float] = []
    recall_scores: list[float] = []
    for row in rows:
        contexts = list(row.retrieved_contexts)
        reference = references[row.id]
        faith_scores.append(
            float(
                faithfulness.score(
                    user_input=row.question,
                    response=row.response,
                    retrieved_contexts=contexts,
                ).value
            )
        )
        relevancy_scores.append(
            float(
                relevancy.score(
                    user_input=row.question,
                    response=row.response,
                ).value
            )
        )
        precision_scores.append(
            float(
                precision.score(
                    user_input=row.question,
                    reference=reference,
                    retrieved_contexts=contexts,
                ).value
            )
        )
        recall_scores.append(
            float(
                recall.score(
                    user_input=row.question,
                    reference=reference,
                    retrieved_contexts=contexts,
                ).value
            )
        )
    return {
        "faithfulness": _mean(faith_scores),
        "answer_relevancy": _mean(relevancy_scores),
        "context_precision": _mean(precision_scores),
        "context_recall": _mean(recall_scores),
    }


def _mean(values: list[float]) -> float:
    if not values:
        return float("nan")
    return float(sum(values) / len(values))
