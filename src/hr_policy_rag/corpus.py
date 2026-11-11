"""Load the synthetic handbook and split it into chunks."""

from __future__ import annotations

from pathlib import Path

from hr_policy_rag.models import Chunk, Document
from hr_policy_rag.paths import corpus_dir

_REGIONS = {"us", "uk", "de", "global"}


def load_corpus(directory: Path | None = None) -> list[Document]:
    folder = directory or corpus_dir()
    documents: list[Document] = []
    for path in sorted(folder.glob("*.md")):
        documents.append(parse_document(path))
    if not documents:
        raise FileNotFoundError(f"No handbook documents in {folder}")
    return documents


def parse_document(path: Path) -> Document:
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---\n"):
        raise ValueError(f"{path} is missing front matter")
    parts = raw.split("---\n", 2)
    if len(parts) < 3:
        raise ValueError(f"{path} front matter is not closed")
    meta: dict[str, str] = {}
    for line in parts[1].splitlines():
        if not line.strip():
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()
    region = meta["region"]
    if region not in _REGIONS:
        raise ValueError(f"{path} has unsupported region {region}")
    return Document(
        id=meta["id"],
        title=meta["title"],
        region=region,
        topic=meta["topic"],
        body=parts[2].strip(),
    )


def chunk_documents(documents: list[Document], chunk_size: int, overlap: int) -> list[Chunk]:
    chunks: list[Chunk] = []
    for document in documents:
        rendered = f"{document.title}.\n\n{document.body.strip()}\n"
        parts = split_text(rendered, chunk_size, overlap)
        for index, part in enumerate(parts, start=1):
            suffix = "" if len(parts) == 1 else f"-{index}"
            text = part if part.endswith("\n") else f"{part}\n"
            chunks.append(
                Chunk(
                    id=f"{document.id}{suffix}",
                    doc_id=document.id,
                    title=document.title,
                    region=document.region,
                    topic=document.topic,
                    text=text,
                )
            )
    return chunks


def split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than chunk_overlap")
    if len(text) <= chunk_size:
        return [text]
    pieces: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        pieces.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return pieces
