# hr-policy-rag-evals

[![CI](https://github.com/mustafaautomation/hr-policy-rag-evals/actions/workflows/ci.yml/badge.svg)](https://github.com/mustafaautomation/hr-policy-rag-evals/actions/workflows/ci.yml)

Personal open-source demo for a RAG assistant over an employee handbook, with a RAGAS evaluation gate. The company, Cedarline Studio, is made up. The 29 handbook chapters in `data/corpus/` are synthetic text written for this repository. They are not a real employer's policy and they do not contain real employee records.

The assistant answers questions about leave, benefits, expenses, remote work, and the code of conduct. It refuses requests for another employee's salary or personal data, sends harassment and grievance reports to the People team, and keeps United States, United Kingdom, and Germany rules separate.

## Architecture

```mermaid
flowchart TD
  Q[Question] --> C[Classifier]
  C -->|another person's pay or personal data| P[Refusal]
  C -->|harassment or grievance report| H[Route to the People team]
  C -->|country-specific rule, no country named| R[Ask which country]
  C -->|in the handbook| E[Hashing TF-IDF embedder]
  E --> V[Retriever]
  V --> F[FAISS in memory]
  V --> D[pgvector, optional]
  F --> S[Keep sentences for the named country]
  D --> S
  S --> L[LLM provider]
  L --> A[Answer]
  A --> M[Metrics]
  M --> G[Threshold gate]
```

Offline runs use a deterministic provider that quotes the selected handbook sentences. Live runs use OpenAI for the answer and for the RAGAS judge. Retrieval stays on the local embedder in both modes, so the offline and live paths see the same chunks.

## Run it

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --group dev
uv run hr-rag ask "How many days of paid time off do full-time employees in the United States receive per calendar year?"
uv run hr-rag eval --mode offline
```

`hr-rag eval --mode offline` needs no API key. It scores the 50 labelled questions, compares the result with `data/snapshots/offline_pipeline.jsonl`, and exits non-zero if any offline metric is below its threshold.

These two variants are expected to fail the gate:

```bash
uv run hr-rag eval --mode offline --variant bad-retriever
uv run hr-rag eval --mode offline --variant no-guardrail
```

`bad-retriever` returns the least similar chunks. `no-guardrail` answers personal-data questions and adjudicates reports.

### Live RAGAS judge

```bash
export OPENAI_API_KEY=...
uv run hr-rag eval --mode live
uv run hr-rag ask "How many vacation days do full-time employees in Germany receive per calendar year?"
```

Live mode adds faithfulness, answer relevancy, context precision, and context recall. The judge model and the answer model both default to `gpt-4o-mini` in `eval_config.yaml`. If `OPENAI_API_KEY` is unset, the live command exits 2 and does not write judge scores.

GitHub Actions runs the offline gate on every push and pull request. `.github/workflows/live-eval.yml` is `workflow_dispatch` only, and it skips when the `OPENAI_API_KEY` secret is absent.

### Postgres

```bash
docker compose up -d
uv run hr-rag index-postgres --dsn postgresql://cedarline:cedarline@localhost:5432/handbook
```

The compose password is for this local database only. Tests and CI use the FAISS index and do not start Postgres. If FAISS is not installed, retrieval falls back to a numpy inner product.

## Metrics

| Metric | What a reader should take from it |
| --- | --- |
| Faithfulness | Whether the answer sticks to the retrieved handbook text. Live RAGAS judge only. |
| Answer relevancy | Whether the answer addresses the question. RAGAS also calls this response relevancy. Live only. |
| Context precision | Whether useful chunks are ranked above unrelated ones. Live only. |
| Context recall | Whether the retrieved text covers the reference answer. Live only. |
| Non-LLM context recall | Whether each labelled source chapter was retrieved. RAGAS `NonLLMContextRecall` compares strings and does not call a model. |
| Answer string presence | Whether the required handbook phrases are in the answer. RAGAS `StringPresence`. A forbidden phrase from the wrong country scores 0. |
| Refusal correctness | Whether pay and personal-data questions are refused, reports go to the People team, missing policies get "I don't know", and a missing country is not answered with one global number. |
| Hit rate | Share of questions whose labelled chapter appears in the top results. |
| MRR | How high that labelled chapter ranks. 1 means it was first. |

The offline generator quotes handbook sentences, so the offline scores measure retrieval, sentence choice, and the guardrails. They are not a chat model's faithfulness. LLM-judge scores are not in the snapshot or the sample report. This repository has not run the live judge, so it does not publish faithfulness, answer relevancy, context precision, or context recall figures.

## Thresholds

From `eval_config.yaml`. Offline bars are what CI enforces. Live bars are the configured pass line for a future live run. They are not measurements from this repo.

| Metric | Bar | Mode |
| --- | ---: | --- |
| non_llm_context_recall | 0.850 | offline |
| answer_string_presence | 0.900 | offline |
| refusal_correctness | 0.950 | offline |
| hit_rate | 0.850 | offline |
| mrr | 0.700 | offline |
| faithfulness | 0.700 | live |
| answer_relevancy | 0.700 | live |
| context_precision | 0.600 | live |
| context_recall | 0.700 | live |

## Offline scores from this run

| Metric | Bad retriever | No guardrail | Improved |
| --- | ---: | ---: | ---: |
| non_llm_context_recall | 0.000 | 1.000 | 1.000 |
| answer_string_presence | 0.340 | 0.840 | 1.000 |
| refusal_correctness | 0.820 | 0.840 | 1.000 |
| hit_rate | 0.000 | 1.000 | 1.000 |
| mrr | 0.000 | 0.960 | 0.960 |

The improved column is the standard pipeline. Its MRR is 0.960, so the labelled chapter is usually first and not always first. The bad retriever is below every offline bar. The no-guardrail variant keeps retrieval and drops string presence to 0.840 and refusal correctness to 0.840.

## Sample report

![Offline eval report](docs/eval-report.png)

Full write-up: [docs/eval-report.md](docs/eval-report.md) and [docs/eval-report.html](docs/eval-report.html). Regenerate with:

```bash
uv run hr-rag eval --mode offline --write-report
```

`data/snapshots/offline_pipeline.jsonl` stores the offline answers and per-question scores. `llm_judge_scores` is null. See [data/snapshots/README.md](data/snapshots/README.md).

## Using it on another handbook

1. Replace the markdown files in `data/corpus/`. Each file needs `id`, `title`, `region` (`us`, `uk`, `de`, or `global`), and `topic` in the front matter.
2. Replace `data/eval/questions.jsonl` with labelled questions, reference answers, source document ids, phrases that must appear, and a behaviour: `answer`, `region_clarify`, `unknown`, `refuse_pii`, or `route_hr`.
3. Run `uv run hr-rag materialize` so the stored reference contexts match the current chunks.
4. Run `uv run hr-rag eval --mode offline --update-snapshot --write-report`.
5. Change the bars in `eval_config.yaml` after you have seen a real run.
6. To call another generator, implement `LLMProvider.complete` and pass it into the pipeline. `OpenAIProvider` and `FakeProvider` are the two included.

## Development

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv run hr-rag eval --mode offline
```

CI runs those four checks. None of them use `continue-on-error`.

## License

MIT. Copyright 2026 Muhammad Mustafa.
