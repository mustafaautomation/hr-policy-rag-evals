"""LLM providers. Offline runs use the deterministic extractive provider."""

from __future__ import annotations

import os
from typing import Protocol

from hr_policy_rag.guardrails import is_hr_report, is_pii_request
from hr_policy_rag.prompts import UNKNOWN, UNSAFE_PII, UNSAFE_REPORT


class LLMProvider(Protocol):
    def complete(self, *, system: str, user: str) -> str: ...


def extract_question(user: str) -> str:
    marker = "Question:\n"
    if marker not in user:
        return user.strip()
    body = user.split(marker, 1)[1]
    if "\n\nContext:\n" in body:
        body = body.split("\n\nContext:\n", 1)[0]
    return body.strip()


def _context_lines(user: str) -> list[str]:
    if "\n\nContext:\n" not in user:
        return []
    context = user.split("\n\nContext:\n", 1)[1]
    lines: list[str] = []
    for line in context.splitlines():
        if line.startswith("- "):
            lines.append(line[2:].strip())
    return [line for line in lines if line]


class FakeProvider:
    """Quotes the supplied handbook sentences. The unsafe mode follows the no-guardrail prompt."""

    def __init__(self, *, obey_guardrails: bool) -> None:
        self.obey_guardrails = obey_guardrails

    def complete(self, *, system: str, user: str) -> str:
        del system
        question = extract_question(user)
        if not self.obey_guardrails and is_hr_report(question):
            return UNSAFE_REPORT
        if not self.obey_guardrails and is_pii_request(question):
            return UNSAFE_PII
        lines = _context_lines(user)
        if not lines:
            return UNKNOWN
        return "According to the Cedarline Studio handbook: " + " ".join(lines)


class OpenAIProvider:
    def __init__(self, model: str, api_key: str) -> None:
        from openai import OpenAI

        self.model = model
        self._client = OpenAI(api_key=api_key)

    def complete(self, *, system: str, user: str) -> str:
        response = self._client.chat.completions.create(
            model=self.model,
            temperature=0,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        content = response.choices[0].message.content
        return content or ""


def provider_for_answer(model: str, *, obey_guardrails: bool, force_fake: bool) -> LLMProvider:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if force_fake or not api_key:
        return FakeProvider(obey_guardrails=obey_guardrails)
    return OpenAIProvider(model, api_key)
