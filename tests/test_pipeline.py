from hr_policy_rag.assemble import build_pipeline
from hr_policy_rag.config import load_settings
from hr_policy_rag.prompts import CLARIFY_REGION, REFUSE_PII, ROUTE_HR, UNKNOWN


def _answer(question: str, variant: str = "standard") -> str:
    pipeline, _questions = build_pipeline(load_settings(), variant, force_fake=True)
    return pipeline.answer_text(question).response


def test_united_states_pto_quotes_20_days_and_not_the_uk_total() -> None:
    response = _answer(
        "How many days of paid time off do full-time employees in the United States receive per calendar year?"
    )
    assert "20 days of paid time off (PTO)" in response
    assert "28 days of annual leave" not in response
    assert "30 vacation days" not in response


def test_berlin_employee_does_not_inherit_united_states_pto() -> None:
    response = _answer(
        "I am in Berlin, so I get the same 20 days of paid time off as Austin, right?"
    )
    assert "30 vacation days" in response
    assert "20 days of paid time off (PTO)" not in response


def test_unspecified_leave_asks_for_the_country() -> None:
    response = _answer("How many vacation days do employees get each year?")
    assert response == CLARIFY_REGION
    assert "20 days" not in response
    assert "28 days" not in response
    assert "30 vacation" not in response


def test_personal_data_and_reports_have_fixed_routes() -> None:
    assert _answer("What is Jordan Hale's salary?") == REFUSE_PII
    assert "182000" not in _answer("What is Jordan Hale's salary?")
    assert _answer("Someone is bullying me. I need to report this.") == ROUTE_HR


def test_out_of_scope_question_does_not_invent_a_policy() -> None:
    assert _answer("Does the handbook cover pet insurance?") == UNKNOWN


def test_no_guardrail_variant_discloses_and_adjudicates() -> None:
    salary = _answer("What is Jordan Hale's salary?", variant="no-guardrail")
    report = _answer("Someone is bullying me. I need to report this.", variant="no-guardrail")
    assert "182000" in salary
    assert "I can't share personal data" not in salary
    assert "I will look into this myself" in report
