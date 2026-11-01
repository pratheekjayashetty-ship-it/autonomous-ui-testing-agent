
import json
from openai import OpenAI


SYSTEM = """
You are an autonomous UI test planning assistant.

Convert the supplied GitHub issue into a structured JSON test plan.

Generate scenarios strictly from the acceptance criteria.
Do not assume a particular application or website.

Each scenario must contain:
- id
- criterion
- steps
- verification

Each step must contain:
- action
- target
- optional value

Allowed actions:
- fill
- click

Allowed verification kinds:
- visible_text
- text_absent
- url_contains
- validation_message
- distinct_images

Verification must describe an observable expected outcome.

For duplicate buttons, include surrounding context in the target.
Example: "Sauce Labs Backpack | Add to cart".

For image consistency requirements, use distinct_images.

Do not invent application defects or acceptance criteria.
Do not generate scenarios that require unsupported browser actions.

Limits:
- Maximum 4 scenarios.
- Maximum 5 steps per scenario.
- Maximum 8 browser actions per scenario.

Return a valid JSON object with keys summary and scenarios.
Do not include Markdown or explanations outside the JSON.
"""


ALLOWED_ACTIONS = {"fill", "click"}

ALLOWED_VERIFICATIONS = {
    "visible_text",
    "text_absent",
    "url_contains",
    "validation_message",
    "distinct_images",
}


def make_plan(issue, client: OpenAI, model: str):
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": json.dumps({
                    "title": issue.get("title"),
                    "body": issue.get("body"),
                }),
            },
        ],
    )

    plan = json.loads(response.choices[0].message.content)

    scenarios = plan.get("scenarios")

    if not isinstance(scenarios, list) or not scenarios or len(scenarios) > 4:
        raise ValueError("Invalid plan scenario count")

    for scenario in scenarios:
        if not isinstance(scenario, dict):
            raise ValueError("Each scenario must be an object")

        if not scenario.get("id") or not scenario.get("criterion"):
            raise ValueError("Scenario requires id and criterion")

        steps = scenario.get("steps")

        if not isinstance(steps, list) or len(steps) > 5:
            raise ValueError("Invalid scenario steps")

        for step in steps:
            if step.get("action") not in ALLOWED_ACTIONS:
                raise ValueError("Unsupported action")

            if not step.get("target"):
                raise ValueError("Step target is required")

            if step["action"] == "fill" and "value" not in step:
                raise ValueError("Fill action requires a value")

        verification = scenario.get("verification", {})

        if verification.get("kind") not in ALLOWED_VERIFICATIONS:
            raise ValueError(
                f"Unsupported verification kind: "
                f"{verification.get('kind')!r}"
            )

        if "expected" not in verification:
            raise ValueError("Verification expected value is required")

    return plan
