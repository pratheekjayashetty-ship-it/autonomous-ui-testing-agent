import json
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openai import OpenAI

ALLOWED_ACTIONS = {"fill", "click"}
ALLOWED_VERIFICATIONS = {
    "visible_text", "text_absent", "url_contains",
    "validation_message", "distinct_images",
}
MAX_SCENARIOS = 5
MAX_STEPS = 8

SYSTEM = """
You are a general-purpose autonomous UI test planner. Convert the supplied
GitHub issue into a JSON test plan. The target application is not known in
advance. Do not assume a framework, site, selector, credential, page layout,
or application-specific control.

Use only acceptance criteria and test data explicitly supplied in the issue.
Never invent credentials, expected messages, product names, or requirements.
If required test data is missing, do not fabricate it. Keep the acceptance
criterion represented and make its scenario fail closed with a clear explanation.

For every scenario provide: id, criterion, steps, verification.
Allowed actions: fill, click. A fill requires target and exact value.
A click requires target and value=null.
Allowed verification kinds: visible_text, text_absent, url_contains,
validation_message, distinct_images.

Use accessible labels, placeholders, visible text, and roles as targets.
When a repeated control belongs to a particular row/card/section, use
"context text | control label", where context text is visible on that page.
Do not click a row/card title when the criterion is to click its action.
Do not use CSS selectors, XPath, element IDs, or invented selectors.

Scenario independence:
- Every scenario runs in a fresh browser context.
- Include all required setup actions in each scenario (for example, filling
  username and password, submitting login, and adding an item before opening
  a cart).
- For login, include separate fill actions for the exact username and password
  supplied in the issue, followed by a login/sign-in action.
- For add-to-cart criteria, target the product action in its visible context,
  for example "visible product name | Add to cart". Do not use a generic
  "Add to cart" target when multiple products may be present.
- For cart-display criteria, add the requested product and open the cart in
  that same scenario before verifying its visible content.
- Do not rely on state created by a previous scenario.
- Create exactly one separate scenario for every numbered acceptance criterion
  in the issue's Acceptance Criteria section, preserving the original order.
- Do not merge, omit, or silently skip criteria, including negative-login and
  defect-regression criteria.
- Keep each scenario within 8 actions.
- Do not add unnecessary steps.

Verification must check the final observable state:
- Use url_contains for navigation.
- Use visible_text for content that should appear.
- Use validation_message for an application validation/error message.
- Use distinct_images only when the issue explicitly requires comparing
  displayed images for uniqueness/consistency.
- Never claim a pass based only on successful clicks.

Return JSON only with keys summary and scenarios. Generate no more than five
scenarios. Each scenario must have a unique id, non-empty criterion, at least
one step, and one non-empty verification expected value.
"""

PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "scenarios": {
            "type": "array",
            "minItems": 1,
            "maxItems": MAX_SCENARIOS,
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "criterion": {"type": "string"},
                    "steps": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": MAX_STEPS,
                        "items": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string", "enum": ["fill", "click"]},
                                "target": {"type": "string"},
                                "value": {"type": ["string", "null"]},
                            },
                            "required": ["action", "target", "value"],
                            "additionalProperties": False,
                        },
                    },
                    "verification": {
                        "type": "object",
                        "properties": {
                            "kind": {"type": "string", "enum": sorted(ALLOWED_VERIFICATIONS)},
                            "expected": {"type": "string"},
                        },
                        "required": ["kind", "expected"],
                        "additionalProperties": False,
                    },
                },
                "required": ["id", "criterion", "steps", "verification"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["summary", "scenarios"],
    "additionalProperties": False,
}


def _extract_acceptance_criteria(issue: dict) -> list[dict]:
    """Return top-level numbered acceptance criteria and their supporting text."""
    body = issue.get("body", "") or ""
    in_section = False
    criteria = []
    current = None

    for line in body.splitlines():
        if re.match(r"^\s{0,3}#{1,6}\s+acceptance criteria\b", line, re.IGNORECASE):
            in_section = True
            continue
        if in_section and re.match(r"^\s{0,3}#{1,6}\s+\S", line):
            break
        if not in_section:
            continue

        match = re.match(r"^\s{0,3}\d+[.)]\s+(.+?)\s*$", line)
        if match:
            if current is not None:
                current["body"] = "\n".join(current.pop("lines")).strip()
                criteria.append(current)
            current = {"title": match.group(1).strip(), "lines": []}
        elif current is not None:
            current["lines"].append(line)

    if current is not None:
        current["body"] = "\n".join(current.pop("lines")).strip()
        criteria.append(current)
    return criteria


def _extract_login_credentials(text: str) -> dict[str, str]:
    """Extract explicitly supplied Username/Password values from criterion text."""
    credentials = {}
    for line in text.splitlines():
        match = re.match(
            r"^\s{0,8}(?:[-*+]\s*)?(username|password)\s*(?::|=|\s)\s*(.*?)\s*$",
            line,
            re.IGNORECASE,
        )
        if match:
            value = match.group(2).strip().strip("`'\"")
            if value:
                credentials[match.group(1).casefold()] = value
    return credentials


def _is_login_criterion(text: str) -> bool:
    return bool(re.search(r"\b(log\s*in|login|sign\s*in|authenticate)\b", text, re.IGNORECASE))


def _reference_credentials(criteria: list[dict], invalid: bool) -> dict[str, str]:
    """Find a credential pair from a clearly labelled valid/invalid login criterion."""
    desired = (
        r"\b(invalid|wrong|incorrect|negative)\b"
        if invalid else r"\b(valid|successful|successfully)\b"
    )
    for item in criteria:
        text = item["title"] + "\n" + item["body"]
        if re.search(desired, text, re.IGNORECASE):
            values = _extract_login_credentials(item["body"])
            if {"username", "password"}.issubset(values):
                return values
    return {}


def _extract_product_contexts(criterion_body: str) -> list[str]:
    """Extract product names from simple acceptance-criterion action bullets."""
    products = []
    for line in criterion_body.splitlines():
        clean = re.sub(r"^\s{0,8}[-*+]\s*", "", line).strip()
        match = re.match(r"(?:add|locate|select)\s+(.+?)\s*$", clean, re.IGNORECASE)
        if not match:
            continue
        candidate = re.split(
            r"\s+(?:to\s+(?:the\s+)?cart|and\s+then|then)\b",
            match.group(1), maxsplit=1, flags=re.IGNORECASE,
        )[0].strip(" .:`'\"")
        if candidate.casefold() in {"item", "product", "the item", "the product"}:
            continue
        if candidate and candidate.casefold() not in {p.casefold() for p in products}:
            products.append(candidate)
    return products


def _validate_scenario_actions(scenario: dict, criterion: dict, criteria: list[dict]) -> None:
    """Reject plans that omit explicit login, product, or cart setup actions."""
    sid = scenario["id"]
    text = criterion["title"] + "\n" + criterion["body"]
    steps = scenario["steps"]
    fills = [step for step in steps if step["action"] == "fill"]
    clicks = [step for step in steps if step["action"] == "click"]

    explicit_credentials = _extract_login_credentials(criterion["body"])
    if _is_login_criterion(text) or {"username", "password"}.issubset(explicit_credentials):
        credentials = explicit_credentials
        if not {"username", "password"}.issubset(credentials):
            invalid = bool(re.search(r"\b(invalid|wrong|incorrect|negative)\b", text, re.IGNORECASE))
            credentials = _reference_credentials(criteria, invalid)
        if not {"username", "password"}.issubset(credentials):
            raise ValueError(
                f"Scenario {sid} requires login, but the issue does not provide "
                "a complete username/password pair to use"
            )

        for field in ("username", "password"):
            expected_value = credentials[field].casefold()
            matching = [step for step in fills if step["value"].casefold() == expected_value]
            if not matching:
                raise ValueError(
                    f"Scenario {sid} is missing a fill action for the supplied {field}"
                )
            label_terms = (
                ("username", "user name", "user id", "email")
                if field == "username" else ("password",)
            )
            if not any(
                any(term in step["target"].casefold() for term in label_terms)
                for step in matching
            ):
                raise ValueError(
                    f"Scenario {sid} must fill the {field} value using a matching "
                    "accessible field label"
                )
        if not any(
            re.search(r"\b(login|log in|sign in|submit)\b", step["target"], re.IGNORECASE)
            for step in clicks
        ):
            raise ValueError(
                f"Scenario {sid} requires a login/sign-in button click after filling credentials"
            )

    products = _extract_product_contexts(criterion["body"])
    # Any explicit product action in the criterion needs a product-context target.
    add_to_cart_required = bool(products) and bool(
        re.search(r"\b(cart|basket)\b", text, re.IGNORECASE)
        or re.search(r"\b(add|adding|locate|select)\b", text, re.IGNORECASE)
    )
    if add_to_cart_required and products:
        for product in products:
            matched = any(
                product.casefold() in step["target"].casefold()
                and re.search(r"\badd\b", step["target"], re.IGNORECASE)
                and re.search(r"\b(cart|basket)\b", step["target"], re.IGNORECASE)
                for step in clicks
            )
            if not matched:
                raise ValueError(
                    f"Scenario {sid} must target the add-to-cart action in the "
                    f"visible context of product {product!r}"
                )

    opens_cart = bool(re.search(
        r"\b(open|view|go to|navigate to)\s+(?:the\s+)?(?:shopping\s+)?cart\b",
        text, re.IGNORECASE,
    ))
    if opens_cart and not any(
        re.search(r"\b(cart|basket)\b", step["target"], re.IGNORECASE)
        and not re.search(r"\badd\b", step["target"], re.IGNORECASE)
        for step in clicks
    ):
        raise ValueError(f"Scenario {sid} must include a click on the cart control")


def _count_numbered_acceptance_criteria(issue: dict) -> int:
    return len(_extract_acceptance_criteria(issue))


def validate_plan(plan, issue):
    if not isinstance(plan, dict):
        raise ValueError("Generated plan must be a JSON object")
    scenarios = plan.get("scenarios")
    if not isinstance(scenarios, list) or not 1 <= len(scenarios) <= MAX_SCENARIOS:
        raise ValueError(f"Plan must contain between 1 and {MAX_SCENARIOS} scenarios")

    acceptance_criteria = _extract_acceptance_criteria(issue)
    required_criteria_count = len(acceptance_criteria)
    if required_criteria_count:
        if required_criteria_count > MAX_SCENARIOS:
            raise ValueError(
                f"Issue has {required_criteria_count} numbered acceptance criteria, "
                f"but the planner limit is {MAX_SCENARIOS} scenarios"
            )
        if len(scenarios) != required_criteria_count:
            raise ValueError(
                "Plan must include exactly one scenario per numbered acceptance "
                f"criterion: found {len(scenarios)} scenarios for "
                f"{required_criteria_count} criteria"
            )

    issue_text = (issue.get("title", "") + "\n" + issue.get("body", "")).casefold()
    seen = set()
    for scenario_index, scenario in enumerate(scenarios):
        if not isinstance(scenario, dict):
            raise ValueError("Each scenario must be an object")
        sid = scenario.get("id")
        criterion = scenario.get("criterion")
        if not isinstance(sid, str) or not sid.strip() or sid in seen:
            raise ValueError(f"Invalid or duplicate scenario id: {sid!r}")
        seen.add(sid)
        if not isinstance(criterion, str) or not criterion.strip():
            raise ValueError(f"Scenario {sid} requires a criterion")

        steps = scenario.get("steps")
        if not isinstance(steps, list) or not 1 <= len(steps) <= MAX_STEPS:
            raise ValueError(f"Scenario {sid} must contain 1-{MAX_STEPS} steps")
        for step in steps:
            if not isinstance(step, dict):
                raise ValueError(f"Invalid step in {sid}")
            action, target, value = step.get("action"), step.get("target"), step.get("value")
            if action not in ALLOWED_ACTIONS:
                raise ValueError(f"Unsupported action in {sid}: {action!r}")
            if not isinstance(target, str) or not target.strip():
                raise ValueError(f"Missing target in {sid}")
            if action == "fill":
                if not isinstance(value, str) or not value:
                    raise ValueError(f"Fill step in {sid} requires a value")
                # Prevent the planner from inventing passwords/test data.
                if value.casefold() not in issue_text:
                    raise ValueError(
                        f"Fill value {value!r} in {sid} is not present in issue test data"
                    )
            elif value is not None:
                raise ValueError(f"Click step in {sid} must have value=null")

        if acceptance_criteria:
            _validate_scenario_actions(
                scenario, acceptance_criteria[scenario_index], acceptance_criteria
            )

        verification = scenario.get("verification")
        if not isinstance(verification, dict):
            raise ValueError(f"Scenario {sid} requires verification")
        kind, expected = verification.get("kind"), verification.get("expected")
        if kind not in ALLOWED_VERIFICATIONS:
            raise ValueError(f"Unsupported verification kind: {kind!r}")
        if not isinstance(expected, str) or not expected.strip():
            raise ValueError(f"Scenario {sid} has empty verification expected value")

        normalized_expected = re.sub(r"[^a-z0-9]+", " ", expected.casefold()).strip()
        placeholder_phrases = (
            "product name", "expected result", "some text", "placeholder",
            "todo", "tbd", "cannot verify due to missing data", "cannot verify",
            "missing data", "not specified", "unknown", "n a",
        )
        if any(phrase in normalized_expected for phrase in placeholder_phrases):
            raise ValueError(
                f"Placeholder verification expected value "
                f"for scenario {sid}: {expected!r}"
            )

    return plan


def _extract_json_object(content: str) -> str:
    """Extract the first complete JSON object from a model response.

    Handles Markdown fences and short explanatory text around the object.
    Braces inside quoted strings do not affect object-boundary detection.
    """
    if not content or not content.strip():
        raise ValueError("The planning model returned an empty response")

    cleaned = content.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].lstrip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    start = cleaned.find("{")
    if start < 0:
        raise ValueError("Planner response did not contain a JSON object")

    depth = 0
    in_string = False
    escaped = False

    for index in range(start, len(cleaned)):
        char = cleaned[index]

        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return cleaned[start:index + 1]

    raise ValueError("Planner response contained an incomplete JSON object")


def _loads_with_limited_repair(candidate: str):
    """Load JSON, repairing only unambiguous missing-comma syntax errors.

    A comma is inserted only at the exact position where Python's JSON parser
    reports that a comma or closing delimiter was expected. All parsed data
    is still subjected to validate_plan() before browser execution.
    """
    repaired = candidate
    repair_count = 0
    max_repairs = 12

    while True:
        try:
            return json.loads(repaired)
        except json.JSONDecodeError as exc:
            can_insert_comma = (
                exc.msg == "Expecting ',' delimiter"
                and 0 < exc.pos < len(repaired)
                and repair_count < max_repairs
            )
            if not can_insert_comma:
                raise

            # The parser is positioned at the next token, where a separator
            # is missing (commonly between adjacent object properties).
            repaired = repaired[:exc.pos] + "," + repaired[exc.pos:]
            repair_count += 1


def _parse_plan_response(content: str, issue: dict):
    """Extract, parse, normalize, and strictly validate a planner response."""
    candidate = _extract_json_object(content)

    try:
        plan = _loads_with_limited_repair(candidate)
    except json.JSONDecodeError as exc:
        start = max(0, exc.pos - 80)
        end = min(len(candidate), exc.pos + 80)
        excerpt = candidate[start:end].replace("\n", "\\n")
        raise ValueError(
            f"Planner returned invalid JSON: {exc}; near {excerpt!r}"
        ) from exc

    # Normalize only the unambiguous singleton-array formatting mistake
    # sometimes returned by compatible chat-completion models.
    if isinstance(plan, dict) and isinstance(plan.get("scenarios"), list):
        for scenario in plan["scenarios"]:
            if not isinstance(scenario, dict):
                continue
            verification = scenario.get("verification")
            if (
                isinstance(verification, list)
                and len(verification) == 1
                and isinstance(verification[0], dict)
            ):
                scenario["verification"] = verification[0]

    return validate_plan(plan, issue)

def make_plan(issue, client, model: str):
    """Generate a JSON plan, retrying malformed output and validating locally.

    Provider-specific JSON response modes are intentionally not required:
    compatible endpoints can differ in their support for structured output.
    """
    issue_payload = {
        "title": issue.get("title"),
        "body": issue.get("body"),
    }
    user_content = (
        "Create an independent UI test plan from this GitHub issue.\n"
        "Return exactly one complete JSON object, with no Markdown fences "
        "and no text before or after it.\n"
        "Required top-level keys: summary and scenarios.\n"
        "Generate exactly one separate scenario for every numbered acceptance "
        "criterion in the Acceptance Criteria section, preserving order. Do "
        "not omit or combine criteria; include negative-login and defect tests.\n"
        "Every scenario must contain id, criterion, steps, and verification.\n"
        "Every step must contain action, target, and value. For click actions, "
        "value must be null. For fill actions, value must be a string copied "
        "exactly from the issue.\n"
        "Every verification must contain kind and expected. Expected must be "
        "a concrete observable value explicitly stated in the issue, never a "
        "placeholder or an explanation that data is missing.\n"
        "For every login scenario, fill the exact username and password "
        "provided by the issue, then click the login/sign-in control. When a "
        "scenario says valid login but omits the values locally, reuse the "
        "valid credential pair explicitly provided by another acceptance "
        "criterion. For invalid login, use the invalid pair.\n"
        "For add-to-cart criteria, include the product name as visible context "
        "in the add-to-cart target. For cart display, add the item and open "
        "the cart within the same scenario.\n"
        "Use double quotes for all JSON keys and string values. Escape any "
        "double quote that appears inside a string. Include commas between "
        "every property and array item. Do not use trailing commas.\n"
        "Do not invent credentials, test data, expected messages, or "
        "acceptance criteria. Keep the JSON concise and complete.\n\n"
        "GitHub issue:\n"
        + json.dumps(issue_payload, ensure_ascii=False)
    )

    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user_content},
    ]

    last_error = None
    previous_content = ""

    # A third attempt gives the model one chance to regenerate after a
    # formatting repair or validation failure, without looping indefinitely.
    for attempt in range(3):
        if attempt > 0:
            messages.append({
                "role": "assistant",
                "content": previous_content[:12000],
            })
            messages.append({
                "role": "user",
                "content": (
                    "The previous response was rejected by the local parser "
                    f"or validator: {last_error}\n\n"
                    "Regenerate the plan from the GitHub issue already supplied. "
                    "Do not copy the malformed JSON. Return a fresh, complete, "
                    "syntactically valid JSON object only. Check every comma, "
                    "quote, bracket, required field, action, and verification "
                    "before responding. Keep the plan concise and do not invent "
                    "requirements or test data."
                ),
            })

        response = client.chat.completions.create(
            model=model,
            temperature=0,
            messages=messages,
        )
        content = response.choices[0].message.content
        previous_content = content or ""

        try:
            return _parse_plan_response(content, issue)
        except ValueError as exc:
            last_error = str(exc)

    raise ValueError(
        f"Planner failed after three attempts: {last_error}"
    )
