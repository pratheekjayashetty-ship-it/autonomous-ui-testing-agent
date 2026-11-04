import json
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
If required test data is missing, do not fabricate it: create a scenario that
fails closed with a clear explanation in its criterion, or omit that scenario.

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
- Include all required setup actions in each scenario (for example, login and
  adding an item before opening a cart).
- Do not rely on state created by a previous scenario.
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


def validate_plan(plan, issue):
    if not isinstance(plan, dict):
        raise ValueError("Generated plan must be a JSON object")
    scenarios = plan.get("scenarios")
    if not isinstance(scenarios, list) or not 1 <= len(scenarios) <= MAX_SCENARIOS:
        raise ValueError(f"Plan must contain between 1 and {MAX_SCENARIOS} scenarios")

    issue_text = (issue.get("title", "") + "\n" + issue.get("body", "")).casefold()
    seen = set()
    for scenario in scenarios:
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

        verification = scenario.get("verification")
        if not isinstance(verification, dict):
            raise ValueError(f"Scenario {sid} requires verification")
        kind, expected = verification.get("kind"), verification.get("expected")
        if kind not in ALLOWED_VERIFICATIONS:
            raise ValueError(f"Unsupported verification kind: {kind!r}")
        if not isinstance(expected, str) or not expected.strip():
            raise ValueError(f"Scenario {sid} has empty verification expected value")

        placeholder_values = {
            "product name",
            "expected result",
            "some text",
            "placeholder",
            "todo",
            "tbd",
        }
        if expected.strip().casefold() in placeholder_values:
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
        "Every scenario must contain id, criterion, steps, and verification.\n"
        "Every step must contain action, target, and value. For click actions, "
        "value must be null. For fill actions, value must be a string copied "
        "exactly from the issue.\n"
        "Every verification must contain kind and expected.\n"
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
