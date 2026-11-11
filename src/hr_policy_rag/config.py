"""Load eval_config.yaml into a typed settings object."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from hr_policy_rag.paths import config_path


@dataclass(frozen=True)
class Settings:
    top_k: int
    other_region_factor: float
    global_factor: float
    max_sentences: int
    dimensions: int
    chunk_size: int
    chunk_overlap: int
    answer_model: str
    judge_model: str
    embedding_model: str
    thresholds: dict[str, float]
    offline_metrics: tuple[str, ...]
    live_metrics: tuple[str, ...]

    def threshold(self, name: str) -> float:
        if name not in self.thresholds:
            raise KeyError(f"No threshold configured for {name}")
        return self.thresholds[name]


def load_settings(path: Path | None = None) -> Settings:
    config_file = path or config_path()
    raw = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{config_file} must contain a mapping")
    retrieval = _mapping(raw, "retrieval")
    embeddings = _mapping(raw, "embeddings")
    chunking = _mapping(raw, "chunking")
    llm = _mapping(raw, "llm")
    thresholds_raw = _mapping(raw, "thresholds")
    thresholds = {str(key): _as_float(value) for key, value in thresholds_raw.items()}
    offline = tuple(str(item) for item in _list(raw, "offline_metrics"))
    live = tuple(str(item) for item in _list(raw, "live_metrics"))
    dimensions = _as_int(embeddings["dimensions"])
    if dimensions < 8:
        raise ValueError("embeddings.dimensions must be at least 8")
    return Settings(
        top_k=_as_int(retrieval["top_k"]),
        other_region_factor=_as_float(retrieval["other_region_factor"]),
        global_factor=_as_float(retrieval["global_factor"]),
        max_sentences=_as_int(retrieval["max_sentences"]),
        dimensions=dimensions,
        chunk_size=_as_int(chunking["chunk_size"]),
        chunk_overlap=_as_int(chunking["chunk_overlap"]),
        answer_model=str(llm["answer_model"]),
        judge_model=str(llm["judge_model"]),
        embedding_model=str(llm["embedding_model"]),
        thresholds=thresholds,
        offline_metrics=offline,
        live_metrics=live,
    )


def _mapping(raw: dict[str, object], key: str) -> dict[str, object]:
    value = raw.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be a mapping")
    return value


def _list(raw: dict[str, object], key: str) -> list[object]:
    value = raw.get(key)
    if not isinstance(value, list):
        raise ValueError(f"{key} must be a list")
    return value


def _as_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise TypeError(f"Expected an integer, got {value!r}")
    return int(value)


def _as_float(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise TypeError(f"Expected a number, got {value!r}")
    return float(value)
