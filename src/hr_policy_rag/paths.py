"""Repository paths. Commands are meant to be run from a checkout."""

from pathlib import Path


def project_root() -> Path:
    cwd = Path.cwd()
    if (cwd / "pyproject.toml").is_file() and (cwd / "data").is_dir():
        return cwd
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file() and (parent / "data").is_dir():
            return parent
    return cwd


def corpus_dir() -> Path:
    return project_root() / "data" / "corpus"


def questions_path() -> Path:
    return project_root() / "data" / "eval" / "questions.jsonl"


def snapshot_path() -> Path:
    return project_root() / "data" / "snapshots" / "offline_pipeline.jsonl"


def config_path() -> Path:
    return project_root() / "eval_config.yaml"


def docs_dir() -> Path:
    return project_root() / "docs"
