import numpy as np

from hr_policy_rag.embeddings import HashingTfidfEmbedder


def test_embeddings_are_deterministic_and_separated() -> None:
    embedder = HashingTfidfEmbedder(128)
    texts = [
        "Full-time employees in the United States receive 20 days of paid time off.",
        "Full-time employees in Germany receive 30 vacation days per calendar year.",
        "The code of conduct says to treat colleagues with respect.",
    ]
    embedder.fit(texts)
    first = embedder.embed(texts)
    second = embedder.embed(texts)
    assert first.shape == (3, 128)
    assert np.allclose(first, second)
    us_vs_de = float(first[0] @ first[1])
    us_vs_conduct = float(first[0] @ first[2])
    assert us_vs_de > us_vs_conduct
