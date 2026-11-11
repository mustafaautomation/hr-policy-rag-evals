"""Optional pgvector index. Unit tests do not need Postgres."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import psycopg

from hr_policy_rag.models import Chunk


def schema_statements(dimensions: int) -> tuple[str, str]:
    if not isinstance(dimensions, int) or dimensions < 8:
        raise ValueError("dimensions must be an integer >= 8")
    extension = "CREATE EXTENSION IF NOT EXISTS vector"
    table = f"""
        CREATE TABLE IF NOT EXISTS handbook_chunks (
            id TEXT PRIMARY KEY,
            doc_id TEXT NOT NULL,
            title TEXT NOT NULL,
            region TEXT NOT NULL,
            topic TEXT NOT NULL,
            content TEXT NOT NULL,
            embedding vector({dimensions})
        )
        """
    return extension, table


def vector_literal(values: Sequence[float]) -> str:
    return "[" + ",".join(f"{float(value):.8f}" for value in values) + "]"


class PgVectorStore:
    def __init__(self, dsn: str, dimensions: int) -> None:
        self.dsn = dsn
        self.dimensions = dimensions

    def ensure_schema(self) -> None:
        extension, table = schema_statements(self.dimensions)
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(extension)
                cur.execute(table)
            conn.commit()

    def replace_all(self, chunks: list[Chunk], matrix: np.ndarray) -> None:
        if len(chunks) != len(matrix):
            raise ValueError("chunks and embeddings must have the same length")
        self.ensure_schema()
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM handbook_chunks")
                for chunk, vector in zip(chunks, matrix, strict=True):
                    if len(vector) != self.dimensions:
                        raise ValueError("Embedding dimension does not match the table")
                    cur.execute(
                        """
                        INSERT INTO handbook_chunks
                            (id, doc_id, title, region, topic, content, embedding)
                        VALUES (%s, %s, %s, %s, %s, %s, %s::vector)
                        """,
                        (
                            chunk.id,
                            chunk.doc_id,
                            chunk.title,
                            chunk.region,
                            chunk.topic,
                            chunk.text,
                            vector_literal(vector.tolist()),
                        ),
                    )
            conn.commit()

    def search(self, vector: np.ndarray, limit: int) -> list[tuple[str, str, float]]:
        if len(vector) != self.dimensions:
            raise ValueError("Query dimension does not match the table")
        literal = vector_literal(vector.tolist())
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, content, 1 - (embedding <=> %s::vector) AS score
                    FROM handbook_chunks
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (literal, literal, limit),
                )
                rows = cur.fetchall()
        return [(str(row[0]), str(row[1]), float(row[2])) for row in rows]
