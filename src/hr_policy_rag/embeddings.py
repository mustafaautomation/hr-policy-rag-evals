"""Local hashing TF-IDF embeddings, plus an optional OpenAI embedder."""

from __future__ import annotations

import hashlib
import math
import os
from typing import Protocol

import numpy as np

from hr_policy_rag.textutil import content_tokens


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> np.ndarray: ...


def document_frequencies(texts: list[str]) -> dict[str, int]:
    frequencies: dict[str, int] = {}
    for text in texts:
        for token in set(content_tokens(text)):
            frequencies[token] = frequencies.get(token, 0) + 1
    return frequencies


def _feature(token: str, dimensions: int) -> tuple[int, float]:
    digest = hashlib.md5(token.encode("utf-8")).digest()
    index = int.from_bytes(digest[:4], "little") % dimensions
    sign = 1.0 if digest[4] % 2 == 0 else -1.0
    return index, sign


class HashingTfidfEmbedder:
    """Deterministic hashed TF-IDF. No model download and no API key."""

    def __init__(self, dimensions: int) -> None:
        self.dimensions = dimensions
        self.idf: dict[str, float] = {}
        self._fitted = False

    def fit(self, texts: list[str]) -> None:
        frequencies = document_frequencies(texts)
        total = len(texts)
        idf: dict[str, float] = {}
        for token, freq in frequencies.items():
            idf[token] = math.log((total + 1) / (freq + 1)) + 1.0
        # Bigram idf is computed from the same documents.
        bigram_df: dict[str, int] = {}
        for text in texts:
            tokens = content_tokens(text)
            bigrams = {f"{tokens[i]}_{tokens[i + 1]}" for i in range(len(tokens) - 1)}
            for bigram in bigrams:
                bigram_df[bigram] = bigram_df.get(bigram, 0) + 1
        for token, freq in bigram_df.items():
            idf[token] = math.log((total + 1) / (freq + 1)) + 1.0
        self.idf = idf
        self._fitted = True

    def embed(self, texts: list[str]) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("Fit the hashing embedder on the handbook before embedding")
        matrix = np.zeros((len(texts), self.dimensions), dtype=np.float64)
        for row, text in enumerate(texts):
            tokens = content_tokens(text)
            counts: dict[str, int] = {}
            for token in tokens:
                counts[token] = counts.get(token, 0) + 1
            for index in range(len(tokens) - 1):
                bigram = f"{tokens[index]}_{tokens[index + 1]}"
                counts[bigram] = counts.get(bigram, 0) + 1
            for token, count in counts.items():
                weight = (1.0 + math.log(count)) * self.idf.get(token, 1.0)
                feature, sign = _feature(token, self.dimensions)
                matrix[row, feature] += sign * weight
            norm = float(np.linalg.norm(matrix[row]))
            if norm > 0.0:
                matrix[row] /= norm
        return matrix


class OpenAIEmbedder:
    """Optional hosted embeddings for a client deployment. Not used by the offline gate."""

    def __init__(self, model: str, api_key: str) -> None:
        from openai import OpenAI

        self.model = model
        self._client = OpenAI(api_key=api_key)

    def embed(self, texts: list[str]) -> np.ndarray:
        response = self._client.embeddings.create(model=self.model, input=texts)
        ordered = sorted(response.data, key=lambda item: item.index)
        matrix = np.asarray([item.embedding for item in ordered], dtype=np.float64)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0.0] = 1.0
        return matrix / norms


def build_embedder(kind: str, dimensions: int, embedding_model: str) -> Embedder:
    if kind == "local":
        return HashingTfidfEmbedder(dimensions)
    if kind == "openai":
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        return OpenAIEmbedder(embedding_model, api_key)
    raise ValueError(f"Unknown embedder {kind}")
