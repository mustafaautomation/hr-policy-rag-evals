from pathlib import Path

from hr_policy_rag.assemble import run_variant
from hr_policy_rag.paths import project_root
from hr_policy_rag.report import render_html, render_markdown
from hr_policy_rag.snapshot import snapshot_matches


def _explain(result: object) -> str:
    lines = []
    metrics = result.metrics
    for name, value in metrics.items():
        lines.append(f"{name}={value:.3f}")
    for row in result.questions:
        if row.string_presence < 1 or row.refusal_correctness < 1 or row.hit == 0:
            lines.append(
                f"{row.id} hit={row.hit} presence={row.string_presence:.3f} "
                f"refusal={row.refusal_correctness:.3f} docs={row.retrieved_doc_ids} "
                f"response={row.response[:240]}"
            )
    return "\n".join(lines)


def test_standard_pipeline_passes_the_offline_gate() -> None:
    result = run_variant("standard")
    assert result.passed, _explain(result)


def test_bad_retriever_fails_the_gate() -> None:
    result = run_variant("bad-retriever")
    assert not result.passed
    assert "hit_rate" in result.failed_metrics or "non_llm_context_recall" in result.failed_metrics


def test_no_guardrail_fails_refusal_correctness() -> None:
    result = run_variant("no-guardrail")
    assert not result.passed
    assert "refusal_correctness" in result.failed_metrics


def test_snapshot_matches_fresh_offline_run() -> None:
    result = run_variant("standard")
    mismatch = snapshot_matches(
        result, project_root() / "data" / "snapshots" / "offline_pipeline.jsonl"
    )
    assert mismatch is None, mismatch


def test_committed_report_matches_fresh_run() -> None:
    standard = run_variant("standard")
    bad = run_variant("bad-retriever")
    unguarded = run_variant("no-guardrail")
    docs = project_root() / "docs"
    assert (docs / "eval-report.md").read_text(encoding="utf-8") == render_markdown(
        standard, bad, unguarded
    )
    assert (docs / "eval-report.html").read_text(encoding="utf-8") == render_html(
        standard, bad, unguarded
    )


def test_readme_reports_measured_scores() -> None:
    standard = run_variant("standard")
    bad = run_variant("bad-retriever")
    readme = Path(project_root() / "README.md").read_text(encoding="utf-8")
    lowered = readme.lower()
    assert "synthetic" in lowered
    assert "cedarline studio" in lowered
    assert "respond.io" not in lowered
    for banned in ("production-ready", "enterprise-grade", "blazing"):
        assert banned not in lowered
    assert "llm-judge" in lowered or "llm judge" in lowered
    for value in list(standard.metrics.values()) + list(bad.metrics.values()):
        assert f"{value:.3f}" in readme
