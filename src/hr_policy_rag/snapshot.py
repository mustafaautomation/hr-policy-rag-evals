"""Committed offline pipeline outputs. This file does not store LLM-judge scores."""

from __future__ import annotations

import json
from pathlib import Path

from hr_policy_rag.models import EvalResult, QuestionScore

META_NOTE = (
    "Offline pipeline outputs from the deterministic fake provider. "
    "llm_judge_scores is null because no live judge was run for this file. "
    "These are not RAGAS faithfulness, answer relevancy, context precision, "
    "or context recall scores."
)


def _row_payload(row: QuestionScore) -> dict[str, object]:
    return {
        "behaviour": row.behaviour,
        "category": row.category,
        "hit": row.hit,
        "id": row.id,
        "llm_judge_scores": None,
        "non_llm_context_recall": row.non_llm_context_recall,
        "question": row.question,
        "reciprocal_rank": row.reciprocal_rank,
        "refusal_correctness": row.refusal_correctness,
        "response": row.response,
        "retrieved_doc_ids": list(row.retrieved_doc_ids),
        "string_presence": row.string_presence,
    }


def dump_snapshot(result: EvalResult) -> str:
    meta = {
        "_meta": True,
        "illustrative_judge_scores": False,
        "kind": "offline-pipeline-snapshot",
        "llm_judge_scores": None,
        "mode": result.mode,
        "note": META_NOTE,
        "variant": result.variant,
    }
    lines = [json.dumps(meta, ensure_ascii=False, sort_keys=True)]
    for row in result.questions:
        lines.append(json.dumps(_row_payload(row), ensure_ascii=False, sort_keys=True))
    return "\n".join(lines) + "\n"


def save_snapshot(result: EvalResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_snapshot(result), encoding="utf-8")


def snapshot_matches(result: EvalResult, path: Path) -> str | None:
    if not path.is_file():
        return f"Missing snapshot {path}. Run hr-rag eval --mode offline --update-snapshot."
    expected = dump_snapshot(result)
    actual = path.read_text(encoding="utf-8")
    if actual == expected:
        return None
    return "Committed offline snapshot does not match a fresh offline run."
