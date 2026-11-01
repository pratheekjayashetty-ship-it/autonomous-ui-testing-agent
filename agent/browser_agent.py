import json
import re
from pathlib import Path

from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "evidence"
EVIDENCE.mkdir(parents=True, exist_ok=True)

MAX_ACTIONS = 8

SYSTEM = """
You are a bounded autonomous UI testing agent.
Your task is to execute the current test scenario using only the
provided browser interaction tools.
Observe the current page snapshot before choosing an action.
Identify elements using their visible text, accessible labels,
placeholders, roles, and surrounding page context.
Do not assume application-specific selectors, IDs, or element names.
Do not invent elements that are not present in the page snapshot.
When multiple elements have the same label, use the surrounding
visible context to identify the correct element.
Use fill_field only for visible text fields.
Use click_button only for visible, enabled buttons.
Follow the scenario steps and acceptance criteria.
Do not perform unrelated actions or invent additional requirements.
Do not claim that a scenario passed without observable evidence.
Finish with PASSED only when the scenario's expected outcome
has been observed. Otherwise finish with FAILED and explain why.
Stop when the scenario is complete, the action limit is reached,
or no safe progress can be made.
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
            "description": (
                "Click a visible enabled button. If multiple buttons have the "
                "same label, include surrounding context in target, for example "
                "'Sauce Labs Backpack | Add to cart'. Use only context observed "
                "in the current page snapshot."
            ),
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
    """Capture visible page content and semantic interactive elements."""
    body = page.locator("body").inner_text(timeout=3000)[:6000]

    buttons = []
    button_loc = page.get_by_role("button")

    for i in range(min(button_loc.count(), 30)):
        button = button_loc.nth(i)
        try:
            if button.is_visible():
                buttons.append({
                    "text": button.inner_text(timeout=1000).strip(),
                    "aria_label": button.get_attribute("aria-label"),
                    "enabled": button.is_enabled(),
                })
        except Exception:
            continue

    fields = []
    field_loc = page.locator("input, textarea, select")

    for i in range(min(field_loc.count(), 20)):
        field = field_loc.nth(i)
        try:
            if field.is_visible():
                fields.append({
                    "tag": field.evaluate("(el) => el.tagName.toLowerCase()"),
                    "type": field.get_attribute("type"),
                    "name": field.get_attribute("name"),
                    "placeholder": field.get_attribute("placeholder"),
                    "aria_label": field.get_attribute("aria-label"),
                    "label": field.get_attribute("aria-labelledby"),
                    "enabled": field.is_enabled(),
                })
        except Exception:
            continue

    links = []
    link_loc = page.get_by_role("link")

    for i in range(min(link_loc.count(), 15)):
        link = link_loc.nth(i)
        try:
            if link.is_visible():
                links.append({
                    "text": link.inner_text(timeout=1000).strip(),
                    "href": link.get_attribute("href"),
                })
        except Exception:
            continue

    images = []
    image_loc = page.locator("img")
    for i in range(min(image_loc.count(), 30)):
        image = image_loc.nth(i)
        try:
            if image.is_visible():
                images.append({
                    "alt": image.get_attribute("alt"),
                    "src": image.get_attribute("src"),
                })
        except Exception:
            continue

    return {
        "visible_text": body,
        "buttons": buttons,
        "fields": fields,
        "links": links,
        "images": images,
        "url": page.url,
    }



def _fill_field(page, target, value):
    """Fill one uniquely identified, visible, enabled text field."""
    target = target.strip()
    candidates = [
        page.get_by_label(target, exact=True),
        page.get_by_placeholder(target, exact=True),
        page.get_by_role("textbox", name=target, exact=True),
    ]

    for candidate in candidates:
        try:
            matches = [
                candidate.nth(i)
                for i in range(candidate.count())
                if candidate.nth(i).is_visible()
                and candidate.nth(i).is_enabled()
            ]
            if len(matches) == 1:
                matches[0].fill(value, timeout=4000)
                return
        except Exception:
            continue

    raise RuntimeError(
        f"Could not locate a unique visible enabled text field for {target!r}"
    )


def _click_button(page, target):
    """Click a unique visible button, optionally scoped by visible context."""
    target = target.strip()

    if "|" in target:
        context, button_name = (
            part.strip() for part in target.split("|", 1)
        )
    else:
        context, button_name = "", target

    if context:
        context_matches = page.get_by_text(context, exact=True)
        visible_contexts = []

        for index in range(context_matches.count()):
            element = context_matches.nth(index)
            try:
                if element.is_visible():
                    visible_contexts.append(element)
            except Exception:
                continue

        if not visible_contexts:
            raise RuntimeError(
                f"Could not find visible context {context!r}"
            )

        for context_element in visible_contexts:
            container = context_element

            # Search progressively larger ancestors. Stop at the first
            # ancestor that contains exactly one matching enabled button.
            for _ in range(6):
                buttons = container.get_by_role(
                    "button", name=button_name, exact=True
                )
                try:
                    matching = []
                    for index in range(buttons.count()):
                        button = buttons.nth(index)
                        if button.is_visible() and button.is_enabled():
                            matching.append(button)

                    if len(matching) == 1:
                        matching[0].click(timeout=4000)
                        return
                except Exception:
                    pass

                try:
                    container = container.locator("xpath=..")
                except Exception:
                    break

        raise RuntimeError(
            f"Could not find one enabled {button_name!r} button "
            f"associated with visible context {context!r}"
        )

    candidates = [
        page.get_by_role("button", name=button_name, exact=True),
        page.get_by_role("link", name=button_name, exact=True),
    ]

    for candidate in candidates:
        visible_enabled = []
        for index in range(candidate.count()):
            element = candidate.nth(index)
            try:
                if element.is_visible() and element.is_enabled():
                    visible_enabled.append(element)
            except Exception:
                continue

        if len(visible_enabled) == 1:
            visible_enabled[0].click(timeout=4000)
            return
        if len(visible_enabled) > 1:
            raise RuntimeError(
                f"Ambiguous target {button_name!r}: "
                f"{len(visible_enabled)} visible enabled matches"
            )

    raise RuntimeError(
        f"No unique visible enabled button or link found for {button_name!r}"
    )


def _verify(page, scenario, history):
    """Verify scenario outcomes using observable page evidence."""
    verification = scenario.get("verification", {})
    kind = verification.get("kind", "")
    expected = str(verification.get("expected", "")).strip()

    try:
        body = page.locator("body").inner_text(timeout=3000)

        if kind == "visible_text":
            passed = expected.casefold() in body.casefold()
            return passed, (
                f"Expected visible text {expected!r}; "
                f"observed={passed}"
            )

        if kind == "text_absent":
            passed = expected.casefold() not in body.casefold()
            return passed, (
                f"Expected text {expected!r} to be absent; "
                f"observed_absent={passed}"
            )

        if kind == "url_contains":
            passed = expected.casefold() in page.url.casefold()
            return passed, (
                f"Expected URL to contain {expected!r}; "
                f"actual URL={page.url!r}"
            )

        if kind == "distinct_images":
            images = page.locator("img")
            visible_sources = []

            for index in range(min(images.count(), 50)):
                image = images.nth(index)
                try:
                    if not image.is_visible():
                        continue
                    alt = (image.get_attribute("alt") or "").strip()
                    src = (image.get_attribute("src") or "").strip()
                    if alt and src:
                        visible_sources.append({"alt": alt, "src": src})
                except Exception:
                    continue

            if len(visible_sources) < 2:
                return False, (
                    "Could not verify image distinctness: fewer than "
                    "two visible images with alt text and source were found"
                )

            sources = [item["src"] for item in visible_sources]
            duplicates = sorted({
                src for src in sources if sources.count(src) > 1
            })
            passed = not duplicates
            return passed, (
                f"Checked {len(visible_sources)} visible labelled images; "
                f"duplicate image sources found={len(duplicates)}"
            )

        if kind == "validation_message":
            messages = []

            for role in ("alert", "status"):
                locator = page.get_by_role(role)
                for index in range(min(locator.count(), 10)):
                    element = locator.nth(index)
                    if element.is_visible():
                        messages.append(
                            element.inner_text(timeout=1000)
                        )

            actual = " ".join(messages).strip()

            # Some applications display validation text without
            # assigning an alert or status role.
            if not actual:
                actual = body

            passed = bool(expected) and (
                expected.casefold() in actual.casefold()
            )

            return passed, (
                f"Expected validation text {expected!r}; "
                f"observed={actual!r}"
            )

        return False, f"Unsupported verification kind: {kind!r}"

    except Exception as exc:
        return False, f"Independent verification error: {exc}"




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
            ai_status = "FAILED"
            ai_details = f"Browser action failed: {error_text}"
            break

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
