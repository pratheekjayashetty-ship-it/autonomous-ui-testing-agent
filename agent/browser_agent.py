import json
import re
from pathlib import Path

from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "evidence"
EVIDENCE.mkdir(parents=True, exist_ok=True)

MAX_ACTIONS = 8

SYSTEM = """
You are a bounded UI testing agent.
Use the provided tools to interact with the current page.
Use accessible labels, placeholders, and visible buttons.
For task completion, use the button labelled "Mark complete <task name>"
or its stable completeTask-* ID when available.
The app uses a text input labelled "Task name" and placeholder
"Enter a task". The input ID is task-input.
For empty input, click "Add task" and inspect the validation message.
Do not invent results. Do not claim a test passed without evidence.
Finish when you have attempted the scenario or cannot make progress.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "fill_field",
            "description": "Fill a visible text field.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string"},
                    "value": {"type": "string"},
                },
                "required": ["target", "value"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "click_button",
            "description": "Click a visible enabled button.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string"},
                },
                "required": ["target"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": "Finish the scenario with a result explanation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["PASSED", "FAILED"],
                    },
                    "details": {"type": "string"},
                },
                "required": ["status", "details"],
                "additionalProperties": False,
            },
        },
    },
]


def snapshot(page):
    """Return a small snapshot of the visible page for the planner."""
    body = page.locator("body").inner_text(timeout=3000)[:4000]
    buttons = []

    button_loc = page.get_by_role("button")
    for i in range(min(button_loc.count(), 20)):
        button = button_loc.nth(i)
        try:
            if button.is_visible():
                buttons.append({
                    "text": button.inner_text(timeout=1000),
                    "aria_label": button.get_attribute("aria-label"),
                    "id": button.get_attribute("id"),
                    "enabled": button.is_enabled(),
                })
        except Exception:
            continue

    return {
        "visible_text": body,
        "buttons": buttons,
        "url": page.url,
    }


def _fill_field(page, target, value):
    """Resolve common AI-generated names to the real app input."""
    aliases = {
        "taskInput": "task-input",
        "#taskInput": "task-input",
        "Task name": "task-input",
        "Enter a task": "task-input",
    }
    normalized = aliases.get(target, target)

    candidates = []

    if normalized.startswith("#"):
        candidates.append(page.locator(normalized))
    else:
        candidates.append(page.locator(f"#{normalized}"))

    candidates.extend([
        page.get_by_label(target, exact=True),
        page.get_by_placeholder(target, exact=True),
        page.get_by_role("textbox", name=target, exact=True),
        page.get_by_label("Task name", exact=True),
        page.get_by_placeholder("Enter a task", exact=True),
        page.locator("#task-input"),
    ])

    for candidate in candidates:
        try:
            if candidate.count() == 1 and candidate.is_visible():
                candidate.fill(value, timeout=4000)
                return
        except Exception:
            continue

    raise RuntimeError(
        f"Could not locate a unique visible text field for '{target}'"
    )


def _click_button(page, target):
    """Resolve button names and stable task-completion IDs."""
    target = target.strip()
    loc = None

    if target == "Add task":
        loc = page.get_by_role("button", name="Add task", exact=True)

    elif target.startswith("#completeTask-"):
        loc = page.locator(target)

    elif target.startswith("completeTask-"):
        loc = page.locator(f"#{target}")

    elif target in ("Mark as completed", "Mark complete"):
        loc = page.locator("button[id^='completeTask-']:not(:disabled)")

        if loc.count() == 0:
            loc = page.get_by_role(
                "button", name=re.compile(r"^Mark complete\b")
            )

    else:
        loc = page.get_by_role("button", name=target, exact=True)

        if loc.count() == 0 and "complete" in target.casefold():
            loc = page.locator("button[id^='completeTask-']:not(:disabled)")

    visible = []
    for i in range(loc.count()):
        button = loc.nth(i)
        try:
            if button.is_visible() and button.is_enabled():
                visible.append(button)
        except Exception:
            continue

    if not visible:
        raise RuntimeError(
            f"No visible enabled button found for '{target}'"
        )

    # When several tasks have the same button label, prefer a button
    # associated with the task name included in the target.
    if target not in ("Mark complete", "Mark as completed"):
        for button in visible:
            try:
                aria = button.get_attribute("aria-label") or ""
                if target.casefold() in aria.casefold():
                    button.click(timeout=4000)
                    return
            except Exception:
                continue

    visible[0].click(timeout=4000)


def _verify(page, scenario, history):
    """Verify the actual application state independently of the AI."""
    verification = scenario.get("verification", {})
    kind = verification.get("kind", "")
    expected = str(verification.get("expected", ""))

    body = page.locator("body").inner_text(timeout=3000)

    if kind == "visible_text":
        passed = expected.casefold() in body.casefold()
        return passed, f"Expected visible text {expected!r}"

    if kind == "validation_message":
        actual = page.locator("#message").inner_text(timeout=2000)
        accepted_messages = [
            "please enter a task name",
            "task name is required",
            "task name cannot be empty",
        ]
        passed = (
            any(message in actual.casefold() for message in accepted_messages)
            and (
                not expected
                or expected.casefold() in actual.casefold()
                or actual.casefold() in expected.casefold()
                or "empty" in expected.casefold()
                or "required" in expected.casefold()
            )
        )
        return passed, f"Validation message observed: {actual!r}"

    if kind == "completed_task":
        # The original planner may provide expected=True instead of the
        # actual task name. Recover the most recently filled task name.
        task_name = ""
        for entry in reversed(history):
            if entry.get("tool") == "fill_field":
                candidate = str(entry.get("args", {}).get("value", "")).strip()
                if candidate:
                    task_name = candidate
                    break

        if expected.casefold() not in ("true", "completed", "yes") and expected:
            task_name = expected

        if not task_name:
            return False, "Could not determine which task should be completed"

        task = page.locator("#task-list > li").filter(
            has=page.get_by_text(task_name, exact=True)
        )

        try:
            if task.count() != 1:
                return False, (
                    f"Expected one task named {task_name!r}; "
                    f"found {task.count()}"
                )

            classes = task.get_attribute("class") or ""
            passed = "completed" in classes.split()

            # Also confirm the completed state is visible in the UI.
            completed_button = task.get_by_role(
                "button", name=re.compile(r"^Completed\b")
            )
            passed = passed and completed_button.count() == 1

            return passed, (
                f"Task {task_name!r} completed class present={passed}; "
                f"classes={classes!r}"
            )
        except Exception as exc:
            return False, f"Completion verification error: {exc}"

    return False, f"Unsupported verification kind: {kind!r}"


def run_scenario(page, scenario, client: OpenAI, model: str, index: int):
    history = []
    seen = set()
    logs = []
    ai_status = "FAILED"
    ai_details = "Action limit reached."

    for action_number in range(MAX_ACTIONS):
        try:
            current_page = snapshot(page)
            response = client.chat.completions.create(
                model=model,
                temperature=0,
                tools=TOOLS,
                tool_choice="required",
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {
                        "role": "user",
                        "content": json.dumps({
                            "scenario": scenario,
                            "page": current_page,
                            "history": history,
                            "action": action_number + 1,
                            "max_actions": MAX_ACTIONS,
                        }),
                    },
                ],
            )

            message = response.choices[0].message
            if not message.tool_calls:
                ai_details = "The model returned no tool call."
                logs.append(ai_details)
                break

            call = message.tool_calls[0]
            name = call.function.name
            args = json.loads(call.function.arguments)

            if name == "finish":
                ai_status = args["status"]
                ai_details = args["details"]
                logs.append(
                    f"{scenario.get('id')}: finish {ai_status}: {ai_details}"
                )
                break

            signature = (
                name,
                args.get("target"),
                args.get("value"),
            )
            if signature in seen:
                logs.append(f"Stopped repeated action: {signature}")
                break
            seen.add(signature)

            logs.append(f"{scenario.get('id')}: {name} {args}")

            if name == "fill_field":
                _fill_field(page, args["target"], args["value"])
            elif name == "click_button":
                _click_button(page, args["target"])
            else:
                raise RuntimeError(f"Unknown tool: {name}")

            history.append({
                "tool": name,
                "args": args,
                "result": "ok",
            })

        except Exception as exc:
            error_text = str(exc)[:300]
            history.append({
                "tool": name if "name" in locals() else "unknown",
                "args": args if "args" in locals() else {},
                "result": "error",
                "error": error_text,
            })
            logs.append(f"Action error: {error_text}")

    scenario_id = str(scenario.get("id", index))
    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", scenario_id)
    screenshot = EVIDENCE / f"{index:02d}_{safe_id}.png"

    try:
        page.screenshot(path=str(screenshot), full_page=True)
    except Exception as exc:
        logs.append(f"Screenshot failed: {exc}")

    try:
        verified, verification_details = _verify(page, scenario, history)
    except Exception as exc:
        verified = False
        verification_details = f"Independent verification error: {exc}"

    status = "PASSED" if verified else "FAILED"
    details = (
        f"Independent verification: {verification_details}; "
        f"observed pass={verified}. "
        f"AI result={ai_status}: {ai_details}"
    )
    logs.append(f"{scenario_id}: {status}: {details}")

    return {
        "id": scenario_id,
        "criterion": scenario.get("criterion", ""),
        "status": status,
        "details": details,
        "screenshot": str(screenshot.relative_to(ROOT)),
    }, logs
