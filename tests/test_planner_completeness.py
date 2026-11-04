import copy
import pytest

from agent.planner import validate_plan

ISSUE = {
    "title": "Test login and shopping cart",
    "body": """## Acceptance Criteria

1. Valid login
- Username: standard_user
- Password: secret_sauce
- Verify Products page

2. Invalid login
- Username: invalid_user
- Password: wrong_password
- Exact error: Epic sadface: Username and password do not match any user in this service

3. Add product to cart
- login valid
- Add Sauce Labs Backpack
- cart count 1

4. Cart display
- login valid independent session
- add Backpack
- open cart
- verify Backpack displayed

5. Problem user – Add-to-cart regression
- Username: problem_user
- Password: secret_sauce
- locate Sauce Labs Bolt T-Shirt
- click Add to cart
- verify button label changes to Remove
"""
}


def _scenario(sid, steps, kind, expected):
    return {
        "id": sid,
        "criterion": sid,
        "steps": steps,
        "verification": {"kind": kind, "expected": expected},
    }


def _fill(label, value):
    return {"action": "fill", "target": label, "value": value}


def _click(target):
    return {"action": "click", "target": target, "value": None}


VALID_PLAN = {
    "summary": "Complete five-scenario plan",
    "scenarios": [
        _scenario("TC1", [
            _fill("Username", "standard_user"),
            _fill("Password", "secret_sauce"),
            _click("Login button"),
        ], "visible_text", "Products"),
        _scenario("TC2", [
            _fill("Username", "invalid_user"),
            _fill("Password", "wrong_password"),
            _click("Login button"),
        ], "validation_message", "Epic sadface: Username and password do not match any user in this service"),
        _scenario("TC3", [
            _fill("Username", "standard_user"),
            _fill("Password", "secret_sauce"),
            _click("Login button"),
            _click("Sauce Labs Backpack | Add to cart button"),
        ], "visible_text", "1"),
        _scenario("TC4", [
            _fill("Username", "standard_user"),
            _fill("Password", "secret_sauce"),
            _click("Login button"),
            _click("Backpack | Add to cart button"),
            _click("Cart link"),
        ], "visible_text", "Backpack"),
        _scenario("TC5", [
            _fill("Username", "problem_user"),
            _fill("Password", "secret_sauce"),
            _click("Login button"),
            _click("Sauce Labs Bolt T-Shirt | Add to cart button"),
        ], "visible_text", "Remove"),
    ],
}


def test_accepts_complete_five_criterion_plan():
    assert validate_plan(copy.deepcopy(VALID_PLAN), ISSUE) == VALID_PLAN


def test_rejects_missing_data_placeholder():
    plan = copy.deepcopy(VALID_PLAN)
    plan["scenarios"][0]["verification"]["expected"] = "Cannot verify due to missing data"
    with pytest.raises(ValueError, match="Placeholder verification"):
        validate_plan(plan, ISSUE)


def test_rejects_login_scenario_without_username_fill():
    plan = copy.deepcopy(VALID_PLAN)
    plan["scenarios"][0]["steps"] = plan["scenarios"][0]["steps"][1:]
    with pytest.raises(ValueError, match="username"):
        validate_plan(plan, ISSUE)


def test_rejects_add_to_cart_without_product_context():
    plan = copy.deepcopy(VALID_PLAN)
    plan["scenarios"][2]["steps"][-1] = _click("Add to cart button")
    with pytest.raises(ValueError, match="visible context of product"):
        validate_plan(plan, ISSUE)


def test_rejects_cart_scenario_without_opening_cart():
    plan = copy.deepcopy(VALID_PLAN)
    plan["scenarios"][3]["steps"] = plan["scenarios"][3]["steps"][:-1]
    with pytest.raises(ValueError, match="click on the cart control"):
        validate_plan(plan, ISSUE)


def test_rejects_problem_user_scenario_without_login_setup():
    plan = copy.deepcopy(VALID_PLAN)
    plan["scenarios"][4]["steps"] = plan["scenarios"][4]["steps"][3:]
    with pytest.raises(ValueError, match="username"):
        validate_plan(plan, ISSUE)
