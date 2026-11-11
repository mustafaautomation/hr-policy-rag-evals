from hr_policy_rag.pgvector_store import schema_statements, vector_literal


def test_schema_uses_the_configured_dimension() -> None:
    _extension, table = schema_statements(768)
    assert "vector(768)" in table
    assert "CREATE EXTENSION IF NOT EXISTS vector" in schema_statements(768)[0]


def test_vector_literal_is_a_pgvector_array() -> None:
    assert vector_literal([0.1, 0.25]) == "[0.10000000,0.25000000]"
