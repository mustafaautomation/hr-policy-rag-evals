from hr_policy_rag.assemble import build_pipeline
from hr_policy_rag.config import load_settings


def test_country_query_retrieves_that_country_chapter() -> None:
    pipeline, _questions = build_pipeline(load_settings(), "standard", force_fake=True)
    hits = pipeline.retriever.search(
        "How many days of paid time off do full-time employees in the United States receive?",
        {"us"},
    )
    assert hits[0].chunk.doc_id == "us-pto"
    assert "uk-leave" not in {hit.chunk.doc_id for hit in hits}
    assert "de-leave" not in {hit.chunk.doc_id for hit in hits}


def test_bad_retriever_misses_the_relevant_chapter() -> None:
    pipeline, _questions = build_pipeline(load_settings(), "bad-retriever", force_fake=True)
    hits = pipeline.retriever.search(
        "How many days of paid time off do full-time employees in the United States receive?",
        {"us"},
    )
    assert hits[0].chunk.doc_id != "us-pto"


def test_numpy_and_faiss_scores_agree_when_faiss_is_present() -> None:
    pipeline, _questions = build_pipeline(load_settings(), "standard", force_fake=True)
    index = pipeline.retriever.index
    if index._faiss is None:
        return
    query = pipeline.retriever._embedder.embed(["paid time off in the United States"])[0]
    faiss_scores = index.scores(query)
    numpy_scores = index.matrix @ (query / max(float((query**2).sum()) ** 0.5, 1e-12))
    assert abs(float(faiss_scores.max()) - float(numpy_scores.max())) < 1e-4
