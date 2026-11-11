"""In-memory retrieval. FAISS is used when the package is installed; numpy is the fallback."""

from __future__ import annotations

from typing import Any

import numpy as np

from hr_policy_rag.config import Settings
from hr_policy_rag.embeddings import Embedder
from hr_policy_rag.models import Chunk, Hit


class VectorIndex:
    def __init__(self, matrix: np.ndarray) -> None:
        if matrix.ndim != 2:
            raise ValueError("Embedding matrix must be two-dimensional")
        self.matrix = np.asarray(matrix, dtype=np.float64)
        self._faiss: Any = None
        faiss_module: Any
        try:
            import faiss as faiss_module
        except ImportError:
            faiss_module = None
        if faiss_module is not None and len(self.matrix) > 0:
            index = faiss_module.IndexFlatIP(self.matrix.shape[1])
            index.add(np.ascontiguousarray(self.matrix, dtype=np.float32))
            self._faiss = index

    def scores(self, query: np.ndarray) -> np.ndarray:
        vector = np.asarray(query, dtype=np.float64).reshape(-1)
        norm = float(np.linalg.norm(vector))
        if norm > 0.0:
            vector = vector / norm
        if self._faiss is not None:
            packed = np.ascontiguousarray(vector.reshape(1, -1), dtype=np.float32)
            distances, ids = self._faiss.search(packed, len(self.matrix))
            found = np.zeros(len(self.matrix), dtype=np.float64)
            for score, row_id in zip(distances[0], ids[0], strict=True):
                if int(row_id) >= 0:
                    found[int(row_id)] = float(score)
            return found
        return self.matrix @ vector


class Retriever:
    def __init__(
        self,
        chunks: list[Chunk],
        embedder: Embedder,
        settings: Settings,
        *,
        mode: str = "standard",
    ) -> None:
        if mode not in {"standard", "worst"}:
            raise ValueError(f"Unknown retriever mode {mode}")
        self.chunks = chunks
        self.settings = settings
        self.mode = mode
        matrix = embedder.embed([chunk.text for chunk in chunks])
        self.index = VectorIndex(matrix)
        self._embedder = embedder

    def search(self, question: str, regions: set[str]) -> list[Hit]:
        query = self._embedder.embed([question])[0]
        raw_scores = self.index.scores(query)
        ranked = list(range(len(self.chunks)))
        if self.mode == "worst":
            ranked.sort(
                key=lambda row: (self._rank_score(float(raw_scores[row])), self.chunks[row].id)
            )
        else:
            if regions:
                filtered = [
                    row
                    for row in ranked
                    if self.chunks[row].region in regions or self.chunks[row].region == "global"
                ]
                if filtered:
                    ranked = filtered
            ranked.sort(
                key=lambda row: (
                    -self._rank_score(
                        self._boost(self.chunks[row], regions, float(raw_scores[row]))
                    ),
                    self.chunks[row].id,
                )
            )
        hits: list[Hit] = []
        for row in ranked[: self.settings.top_k]:
            hits.append(Hit(chunk=self.chunks[row], score=float(raw_scores[row])))
        return hits

    def _rank_score(self, score: float) -> float:
        # Collapse float32 noise from FAISS so tied chunks sort by id on every CPU.
        return round(score, 4)

    def _boost(self, chunk: Chunk, regions: set[str], score: float) -> float:
        if not regions:
            return score
        if chunk.region == "global":
            return score * self.settings.global_factor
        if chunk.region in regions:
            return score
        return score * self.settings.other_region_factor
