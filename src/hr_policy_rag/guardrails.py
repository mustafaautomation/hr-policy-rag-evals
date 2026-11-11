"""Question classes for personal data, HR reports, and country-specific policy."""

from __future__ import annotations

import re
from enum import Enum

from hr_policy_rag.textutil import mentioned_regions

_SENSITIVE = re.compile(
    r"\b(salary|salaries|bonus|bonuses|home address|phone number|personal phone|"
    r"personal email|social security|national insurance number|salary list)\b",
    re.IGNORECASE,
)
_OWN_PAY = re.compile(
    r"\b(my own salary|my salary|my own pay|my pay|check my own salary)\b",
    re.IGNORECASE,
)
_OTHER_PERSON = re.compile(
    r"\b(coworker|colleague|their|his|her|ceo|jordan|priya|another employee|"
    r"other employee|salary list)\b",
    re.IGNORECASE,
)
_REPORT = re.compile(
    r"\b(i am being|i'm being|bullying me|harassed me|touched me|about my body|"
    r"i want to file a grievance|i need to report harassment|i need to report this|"
    r"happened to me)\b",
    re.IGNORECASE,
)
_REGION_TOPICS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(pto|paid time off|annual leave|vacation days?)\b", re.IGNORECASE),
    re.compile(r"\b(sick days|sick pay|sickness)\b", re.IGNORECASE),
    re.compile(r"\b(parental leave|parental pay|maternity|paternity)\b", re.IGNORECASE),
    re.compile(r"\b(health insurance|medical cover|medical plan|hsa)\b", re.IGNORECASE),
    re.compile(r"\b(401k|pension|direktversicherung)\b", re.IGNORECASE),
    re.compile(r"\b(hotel cap|meal allowance)\b", re.IGNORECASE),
    re.compile(r"\b(home-office stipend|home office stipend|learning stipend)\b", re.IGNORECASE),
    re.compile(r"\bprobation\b", re.IGNORECASE),
)


class Action(Enum):
    REFUSE_PII = "refuse_pii"
    ROUTE_HR = "route_hr"
    CLARIFY = "region_clarify"
    ANSWER = "answer"


def is_pii_request(question: str) -> bool:
    if _SENSITIVE.search(question) is None:
        return False
    if _OWN_PAY.search(question) and _OTHER_PERSON.search(question) is None:
        return False
    return True


def is_hr_report(question: str) -> bool:
    return _REPORT.search(question) is not None


def needs_region_clarify(question: str) -> bool:
    if mentioned_regions(question):
        return False
    return any(pattern.search(question) for pattern in _REGION_TOPICS)


def classify(question: str) -> Action:
    if is_pii_request(question):
        return Action.REFUSE_PII
    if is_hr_report(question):
        return Action.ROUTE_HR
    if needs_region_clarify(question):
        return Action.CLARIFY
    return Action.ANSWER
