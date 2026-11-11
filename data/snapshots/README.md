# Offline snapshot

`offline_pipeline.jsonl` stores outputs from the deterministic offline pipeline.

`llm_judge_scores` is null on every row. This file does not contain RAGAS faithfulness, answer relevancy, context precision, or context recall. Those metrics run only in live mode when `OPENAI_API_KEY` is set. The scores here were not produced by an LLM judge, and they are not example judge scores.
