from hr_policy_rag.config import load_settings
from hr_policy_rag.corpus import chunk_documents, load_corpus
from hr_policy_rag.paths import questions_path
from hr_policy_rag.questions import load_questions


def test_eval_set_shape_and_contexts() -> None:
    settings = load_settings()
    chunks = chunk_documents(
        load_corpus(),
        settings.chunk_size,
        settings.chunk_overlap,
    )
    questions = load_questions(questions_path(), chunks, require_stored_contexts=True)
    assert 30 <= len(questions) <= 50
    behaviours = {item.behaviour for item in questions}
    assert {"answer", "region_clarify", "unknown", "refuse_pii", "route_hr"} <= behaviours
    for item in questions:
        assert item.must_include
        blob = "\n".join(item.reference_contexts)
        for phrase in item.must_include:
            assert phrase in item.reference_answer
        if item.behaviour == "answer":
            for phrase in item.must_include:
                assert phrase in blob, item.id
            assert item.reference_doc_ids
