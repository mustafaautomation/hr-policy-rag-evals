"""Command line for asking questions and running the eval gate."""

from __future__ import annotations

import argparse
import sys

from hr_policy_rag.assemble import VARIANTS, build_pipeline, run_variant
from hr_policy_rag.config import load_settings
from hr_policy_rag.corpus import chunk_documents, load_corpus
from hr_policy_rag.embeddings import HashingTfidfEmbedder
from hr_policy_rag.live import LiveEvalUnavailable
from hr_policy_rag.paths import docs_dir, questions_path, snapshot_path
from hr_policy_rag.pgvector_store import PgVectorStore
from hr_policy_rag.questions import write_questions
from hr_policy_rag.report import write_reports
from hr_policy_rag.snapshot import save_snapshot, snapshot_matches


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hr-rag")
    sub = parser.add_subparsers(dest="command", required=True)

    ask = sub.add_parser("ask", help="Answer one handbook question")
    ask.add_argument("question")
    ask.add_argument("--variant", default="standard", choices=VARIANTS)
    ask.add_argument("--embeddings", default="local", choices=("local", "openai"))

    evaluate = sub.add_parser("eval", help="Score the labelled question set and apply thresholds")
    evaluate.add_argument("--mode", default="offline", choices=("offline", "live"))
    evaluate.add_argument("--variant", default="standard", choices=VARIANTS)
    evaluate.add_argument("--update-snapshot", action="store_true")
    evaluate.add_argument("--write-report", action="store_true")

    index_db = sub.add_parser("index-postgres", help="Load the handbook into pgvector")
    index_db.add_argument("--dsn", required=True)

    sub.add_parser(
        "materialize", help="Write reference contexts from the current handbook into the eval set"
    )

    args = parser.parse_args(argv)
    command = str(args.command)
    if command == "ask":
        return _ask(str(args.question), str(args.variant), str(args.embeddings))
    if command == "eval":
        return _eval(
            mode=str(args.mode),
            variant=str(args.variant),
            update_snapshot=bool(args.update_snapshot),
            write_report=bool(args.write_report),
        )
    if command == "index-postgres":
        return _index_postgres(str(args.dsn))
    if command == "materialize":
        return _materialize()
    parser.error(f"Unknown command {command}")
    return 2


def _ask(question: str, variant: str, embeddings: str) -> int:
    settings = load_settings()
    pipeline, _questions = build_pipeline(
        settings, variant, embedder_kind=embeddings, force_fake=False
    )
    result = pipeline.answer_text(question)
    print(result.response)
    if result.hits:
        print("\nSources:")
        for hit in result.hits:
            print(f"- {hit.chunk.title} ({hit.chunk.doc_id}, score {hit.score:.3f})")
    return 0


def _eval(*, mode: str, variant: str, update_snapshot: bool, write_report: bool) -> int:
    try:
        result = run_variant(variant, mode=mode)
    except LiveEvalUnavailable as exc:
        print(str(exc), file=sys.stderr)
        return 2
    _print_metrics(result.metrics, result.passed)
    if mode == "offline" and variant == "standard":
        path = snapshot_path()
        if update_snapshot:
            save_snapshot(result, path)
            print(f"Updated {path}")
        else:
            mismatch = snapshot_matches(result, path)
            if mismatch is not None:
                print(mismatch, file=sys.stderr)
                return 1
        if write_report:
            bad = run_variant("bad-retriever", mode="offline")
            unguarded = run_variant("no-guardrail", mode="offline")
            write_reports(docs_dir(), result, bad, unguarded)
            print(f"Wrote reports under {docs_dir()}")
    if not result.passed:
        print("Gate failed: " + ", ".join(result.failed_metrics), file=sys.stderr)
        return 1
    print("Gate passed.")
    return 0


def _print_metrics(metrics: dict[str, float], passed: bool) -> None:
    del passed
    for name in sorted(metrics):
        print(f"{name}: {metrics[name]:.3f}")


def _index_postgres(dsn: str) -> int:
    settings = load_settings()
    documents = load_corpus()
    chunks = chunk_documents(documents, settings.chunk_size, settings.chunk_overlap)
    embedder = HashingTfidfEmbedder(settings.dimensions)
    embedder.fit([chunk.text for chunk in chunks])
    matrix = embedder.embed([chunk.text for chunk in chunks])
    store = PgVectorStore(dsn, settings.dimensions)
    store.replace_all(chunks, matrix)
    print(f"Indexed {len(chunks)} chunks")
    return 0


def _materialize() -> int:
    settings = load_settings()
    _pipeline, questions = build_pipeline(settings, "standard", force_fake=True)
    write_questions(questions_path(), questions)
    print(f"Wrote {len(questions)} questions to {questions_path()}")
    return 0
