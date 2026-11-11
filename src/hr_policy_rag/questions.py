"""Load the labelled eval set and keep reference contexts tied to the corpus."""

from __future__ import annotations

import json
from pathlib import Path

from hr_policy_rag.models import Chunk, Question

_BEHAVIOURS = {"answer", "region_clarify", "unknown", "refuse_pii", "route_hr"}
_REQUIRED = {
    "id",
    "question",
    "reference_answer",
    "reference_doc_ids",
    "must_include",
    "behaviour",
    "category",
}


def load_questions(
    path: Path, chunks: list[Chunk], *, require_stored_contexts: bool
) -> list[Question]:
    by_doc: dict[str, list[Chunk]] = {}
    for chunk in chunks:
        by_doc.setdefault(chunk.doc_id, []).append(chunk)
    questions: list[Question] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        raw = json.loads(line)
        if not isinstance(raw, dict):
            raise ValueError(f"{path}:{line_number} is not an object")
        missing = _REQUIRED - set(raw)
        if missing:
            raise ValueError(f"{path}:{line_number} missing {sorted(missing)}")
        behaviour = str(raw["behaviour"])
        if behaviour not in _BEHAVIOURS:
            raise ValueError(f"{path}:{line_number} has unknown behaviour {behaviour}")
        doc_ids = tuple(str(item) for item in raw["reference_doc_ids"])
        contexts: list[str] = []
        for doc_id in doc_ids:
            if doc_id not in by_doc:
                raise KeyError(f"Question {raw['id']} references unknown document {doc_id}")
            contexts.extend(chunk.text for chunk in by_doc[doc_id])
        stored = raw.get("reference_contexts")
        if stored is None:
            if require_stored_contexts:
                raise ValueError(f"Question {raw['id']} is missing reference_contexts")
        else:
            if list(stored) != contexts:
                raise ValueError(
                    f"Question {raw['id']} reference_contexts do not match the handbook chunks"
                )
        must_not = raw.get("must_not_include", [])
        questions.append(
            Question(
                id=str(raw["id"]),
                question=str(raw["question"]),
                reference_answer=str(raw["reference_answer"]),
                reference_doc_ids=doc_ids,
                reference_contexts=tuple(contexts),
                must_include=tuple(str(item) for item in raw["must_include"]),
                must_not_include=tuple(str(item) for item in must_not),
                behaviour=behaviour,
                category=str(raw["category"]),
            )
        )
    return questions


def write_questions(path: Path, questions: list[Question]) -> None:
    lines = []
    for item in questions:
        payload = {
            "id": item.id,
            "question": item.question,
            "reference_answer": item.reference_answer,
            "reference_doc_ids": list(item.reference_doc_ids),
            "reference_contexts": list(item.reference_contexts),
            "must_include": list(item.must_include),
            "must_not_include": list(item.must_not_include),
            "behaviour": item.behaviour,
            "category": item.category,
        }
        lines.append(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
