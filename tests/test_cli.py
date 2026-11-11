import pytest

from hr_policy_rag.cli import main


def test_offline_eval_command_passes() -> None:
    assert main(["eval", "--mode", "offline"]) == 0


def test_bad_retriever_command_fails_the_gate() -> None:
    assert main(["eval", "--mode", "offline", "--variant", "bad-retriever"]) == 1


def test_live_eval_without_a_key_does_not_invent_scores(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert main(["eval", "--mode", "live"]) == 2
