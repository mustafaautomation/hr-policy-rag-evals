"""Markdown and HTML eval reports."""

from __future__ import annotations

import html
from pathlib import Path

from hr_policy_rag.models import EvalResult, QuestionScore


def _fmt(value: float) -> str:
    return f"{value:.3f}"


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def render_markdown(standard: EvalResult, bad: EvalResult, unguarded: EvalResult) -> str:
    lines = [
        "# Cedarline Studio handbook eval",
        "",
        "Offline run of the deterministic pipeline. LLM-judge scores are not in this report.",
        "",
        "## Metrics",
        "",
        "| Metric | Score | Threshold | Result |",
        "| --- | ---: | ---: | --- |",
    ]
    for item in standard.metric_values:
        result = "pass" if item.passed else "fail"
        lines.append(
            f"| {_cell(item.name)} | {_fmt(item.value)} | {_fmt(item.threshold)} | {result} |"
        )
    lines.extend(
        [
            "",
            "## Before and after",
            "",
            "The baseline retriever returns the least similar chunks. "
            "The no-guardrail variant answers personal-data questions and adjudicates reports. "
            "The improved column is the standard pipeline.",
            "",
            "| Metric | Bad retriever | No guardrail | Improved |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    names = [item.name for item in standard.metric_values]
    for name in names:
        lines.append(
            "| "
            + " | ".join(
                [
                    _cell(name),
                    _fmt(bad.metrics[name]),
                    _fmt(unguarded.metrics[name]),
                    _fmt(standard.metrics[name]),
                ]
            )
            + " |"
        )
    failures = [row for row in standard.questions if row.failed]
    lines.extend(["", "## Per-question failures", ""])
    if not failures:
        lines.append("No per-question failures in the improved offline run.")
    else:
        lines.extend(_question_table(failures))
    lines.extend(["", "## Improved run, all questions", ""])
    lines.extend(_question_table(standard.questions))
    bad_failures = [row for row in bad.questions if row.failed]
    lines.extend(
        [
            "",
            "## Baseline retriever failures",
            "",
            f"{len(bad_failures)} of {len(bad.questions)} questions failed at least one per-question check.",
            "",
        ]
    )
    lines.extend(_question_table(bad_failures))
    return "\n".join(lines) + "\n"


def _question_table(rows: tuple[QuestionScore, ...] | list[QuestionScore]) -> list[str]:
    lines = [
        "| ID | Behaviour | Hit | String presence | Refusal | Retrieved |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        hit = "" if row.hit is None else _fmt(row.hit)
        retrieved = ", ".join(row.retrieved_doc_ids)
        lines.append(
            "| "
            + " | ".join(
                [
                    _cell(row.id),
                    _cell(row.behaviour),
                    hit,
                    _fmt(row.string_presence),
                    _fmt(row.refusal_correctness),
                    _cell(retrieved),
                ]
            )
            + " |"
        )
    return lines


def render_html(standard: EvalResult, bad: EvalResult, unguarded: EvalResult) -> str:
    metric_rows = []
    for item in standard.metric_values:
        status = "pass" if item.passed else "fail"
        metric_rows.append(
            "<tr>"
            f"<td>{html.escape(item.name)}</td>"
            f"<td>{_fmt(item.value)}</td>"
            f"<td>{_fmt(item.threshold)}</td>"
            f'<td class="{status}">{status}</td>'
            "</tr>"
        )
    compare_rows = []
    for item in standard.metric_values:
        compare_rows.append(
            "<tr>"
            f"<td>{html.escape(item.name)}</td>"
            f"<td>{_fmt(bad.metrics[item.name])}</td>"
            f"<td>{_fmt(unguarded.metrics[item.name])}</td>"
            f"<td>{_fmt(item.value)}</td>"
            "</tr>"
        )
    failures = [row for row in standard.questions if row.failed]
    if failures:
        failure_block = _html_questions(failures)
    else:
        failure_block = "<p>No per-question failures in the improved offline run.</p>"
    bad_failures = [row for row in bad.questions if row.failed]
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Cedarline Studio handbook eval</title>
  <style>
    body {{ margin: 0; background: #f4f1ea; color: #1c1915; font: 16px/1.45 Georgia, "Iowan Old Style", serif; }}
    main {{ max-width: 980px; margin: 0 auto; padding: 32px 24px 64px; }}
    h1 {{ font-size: 32px; margin: 0 0 8px; }}
    h2 {{ font-size: 22px; margin: 32px 0 8px; }}
    p {{ margin: 8px 0 16px; }}
    .note {{ color: #4d463c; max-width: 68ch; }}
    table {{ width: 100%; border-collapse: collapse; background: #fffdf8; margin: 8px 0 16px; }}
    th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid #e4dccb; vertical-align: top; }}
    th {{ font: 600 13px/1.3 ui-sans-serif, sans-serif; letter-spacing: 0.02em; }}
    td {{ font: 14px/1.35 ui-sans-serif, sans-serif; }}
    td:nth-child(n+2), th:nth-child(n+2) {{ text-align: right; }}
    td:first-child, th:first-child {{ text-align: left; }}
    .pass {{ color: #1d6b3a; font-weight: 650; }}
    .fail {{ color: #9d2c2c; font-weight: 650; }}
  </style>
</head>
<body>
<main>
  <h1>Cedarline Studio handbook eval</h1>
  <p class="note">Offline run of the deterministic pipeline on the synthetic employee handbook. This page does not include RAGAS LLM-judge scores.</p>
  <h2>Metrics</h2>
  <table>
    <thead><tr><th>Metric</th><th>Score</th><th>Threshold</th><th>Result</th></tr></thead>
    <tbody>
      {"".join(metric_rows)}
    </tbody>
  </table>
  <h2>Before and after</h2>
  <p class="note">Bad retriever returns the least similar chunks. No guardrail answers personal-data questions and adjudicates reports. Improved is the standard pipeline.</p>
  <table>
    <thead><tr><th>Metric</th><th>Bad retriever</th><th>No guardrail</th><th>Improved</th></tr></thead>
    <tbody>
      {"".join(compare_rows)}
    </tbody>
  </table>
  <h2>Per-question failures</h2>
  {failure_block}
  <h2>Improved run, all questions</h2>
  {_html_questions(list(standard.questions))}
  <h2>Baseline retriever</h2>
  <p class="note">{len(bad_failures)} of {len(bad.questions)} questions failed at least one per-question check under the bad retriever.</p>
  {_html_questions(bad_failures)}
</main>
</body>
</html>
"""


def _html_questions(rows: list[QuestionScore]) -> str:
    body = []
    for row in rows:
        hit = "" if row.hit is None else _fmt(row.hit)
        body.append(
            "<tr>"
            f"<td>{html.escape(row.id)}</td>"
            f"<td>{html.escape(row.behaviour)}</td>"
            f"<td>{hit}</td>"
            f"<td>{_fmt(row.string_presence)}</td>"
            f"<td>{_fmt(row.refusal_correctness)}</td>"
            f"<td>{html.escape(', '.join(row.retrieved_doc_ids))}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>ID</th><th>Behaviour</th><th>Hit</th>"
        "<th>String presence</th><th>Refusal</th><th>Retrieved</th></tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table>"
    )


def write_reports(
    directory: Path, standard: EvalResult, bad: EvalResult, unguarded: EvalResult
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "eval-report.md").write_text(
        render_markdown(standard, bad, unguarded),
        encoding="utf-8",
    )
    (directory / "eval-report.html").write_text(
        render_html(standard, bad, unguarded),
        encoding="utf-8",
    )
