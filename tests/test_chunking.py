from hr_policy_rag.config import load_settings
from hr_policy_rag.corpus import chunk_documents, load_corpus, split_text


def test_short_text_stays_one_chunk() -> None:
    assert split_text("abcdef", chunk_size=10, overlap=2) == ["abcdef"]


def test_overlap_is_applied() -> None:
    pieces = split_text("abcdefghijklmnopqrstuvwxyz", chunk_size=10, overlap=4)
    assert pieces[0] == "abcdefghij"
    assert pieces[1].startswith("ghij")
    assert pieces[-1].endswith("z")


def test_handbook_documents_are_one_chunk_each() -> None:
    settings = load_settings()
    documents = load_corpus()
    chunks = chunk_documents(documents, settings.chunk_size, settings.chunk_overlap)
    assert 15 <= len(documents) <= 30
    assert len(chunks) == len(documents)
    assert {chunk.doc_id for chunk in chunks} == {document.id for document in documents}
