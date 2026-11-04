import pytest

from agent.planner import validate_plan


ISSUE = {
    "title": "Login",
    "body": "Valid username: standard_user\nValid password: secret_sauce",
}


def valid_plan():
    return {
        "summary": "login test",
        "scenarios": [{
            "id": "login",
            "criterion": "User can log in",
            "steps": [
                {"action": "fill", "target": "Username", "value": "standard_user"},
                {"action": "fill", "target": "Password", "value": "secret_sauce"},
                {"action": "click", "target": "Login", "value": None},
            ],
            "verification": {"kind": "url_contains", "expected": "inventory"},
        }],
    }


def test_accepts_valid_plan():
    assert validate_plan(valid_plan(), ISSUE)["scenarios"][0]["id"] == "login"


def test_rejects_invented_credentials():
    plan = valid_plan()
    plan["scenarios"][0]["steps"][0]["value"] = "made_up_user"
    with pytest.raises(ValueError, match="not present in issue test data"):
        validate_plan(plan, ISSUE)


def test_rejects_duplicate_scenario_ids():
    plan = valid_plan()
    plan["scenarios"].append(dict(plan["scenarios"][0]))
    with pytest.raises(ValueError, match="duplicate scenario id"):
        validate_plan(plan, ISSUE)


def test_rejects_unsupported_verification():
    plan = valid_plan()
    plan["scenarios"][0]["verification"]["kind"] = "guess"
    with pytest.raises(ValueError, match="Unsupported verification"):
        validate_plan(plan, ISSUE)


def test_rejects_plan_that_omits_an_acceptance_criterion():
    issue_with_two_criteria = {
        "title": "Login coverage",
        "body": (
            "## Acceptance Criteria\n"
            "1. Valid credentials allow login.\n"
            "2. Invalid credentials show an error.\n"
        ),
    }

    with pytest.raises(
        ValueError, match="exactly one scenario per numbered acceptance criterion"
    ):
        validate_plan(valid_plan(), issue_with_two_criteria)
