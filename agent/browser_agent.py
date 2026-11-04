import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "evidence"
EVIDENCE.mkdir(parents=True, exist_ok=True)
MAX_ACTIONS = 8


def snapshot(page):
    """Capture observable page content and semantic controls before actions."""
    body = page.locator("body").inner_text(timeout=3000)[:6000]
    buttons, fields, links, images = [], [], [], []

    button_loc = page.get_by_role("button")
    for i in range(min(button_loc.count(), 40)):
        el = button_loc.nth(i)
        try:
            if el.is_visible():
                buttons.append({
                    "name": el.get_attribute("aria-label") or el.inner_text(timeout=700).strip(),
                    "enabled": el.is_enabled(),
                })
        except Exception:
            pass

    field_loc = page.locator("input, textarea, select")
    for i in range(min(field_loc.count(), 30)):
        el = field_loc.nth(i)
        try:
            if el.is_visible():
                fields.append({
                    "type": el.get_attribute("type"),
                    "placeholder": el.get_attribute("placeholder"),
                    "aria_label": el.get_attribute("aria-label"),
                    "name": el.get_attribute("name"),
                    "enabled": el.is_enabled(),
                })
        except Exception:
            pass

    link_loc = page.get_by_role("link")
    for i in range(min(link_loc.count(), 40)):
        el = link_loc.nth(i)
        try:
            if el.is_visible():
                links.append({
                    "name": el.get_attribute("aria-label") or el.inner_text(timeout=700).strip(),
                    "href": el.get_attribute("href"),
                })
        except Exception:
            pass

    image_loc = page.locator("img")
    for i in range(min(image_loc.count(), 50)):
        el = image_loc.nth(i)
        try:
            if el.is_visible():
                images.append({
                    "alt": el.get_attribute("alt") or "",
                    "src": el.get_attribute("src") or "",
                })
        except Exception:
            pass

    return {
        "url": page.url,
        "visible_text": body,
        "buttons": buttons,
        "fields": fields,
        "links": links,
        "images": images,
    }


def _unique_visible_enabled(locator, description):
    found = []
    for i in range(min(locator.count(), 50)):
        item = locator.nth(i)
        try:
            if item.is_visible() and item.is_enabled():
                found.append(item)
        except Exception:
            continue
    if len(found) != 1:
        raise RuntimeError(
            f"Expected one visible enabled {description}; found {len(found)}"
        )
    return found[0]


def _fill_field(page, target, value):
    target = target.strip()
    locators = [
        page.get_by_label(target, exact=True),
        page.get_by_placeholder(target, exact=True),
        page.get_by_role("textbox", name=target, exact=True),
    ]
    errors = []
    for locator in locators:
        try:
            count = locator.count()
            if count == 1:
                item = locator.nth(0)
                if item.is_visible() and item.is_enabled():
                    item.fill(value, timeout=5000)
                    return
        except Exception as exc:
            errors.append(str(exc))
    raise RuntimeError(
        f"Could not identify a unique visible enabled field {target!r}"
    )


def _click_button(page, target):
    """Click by accessible name; contextual targets disambiguate repeated actions."""
    target = target.strip()
    context, label = (part.strip() for part in target.split("|", 1)) if "|" in target else ("", target)

    if context:
        text_matches = page.get_by_text(context, exact=True)
        contexts = []
        for i in range(min(text_matches.count(), 30)):
            el = text_matches.nth(i)
            try:
                if el.is_visible():
                    contexts.append(el)
            except Exception:
                pass

        # Walk ancestors from the matching visible text to find the associated action.
        for match in contexts:
            container = match
            for _ in range(12):
                for role in ("button", "link"):
                    try:
                        locator = container.get_by_role(role, name=label, exact=True)
                        if locator.count() == 1:
                            item = locator.nth(0)
                            if item.is_visible() and item.is_enabled():
                                item.click(timeout=5000)
                                return
                    except Exception:
                        pass
                try:
                    container = container.locator("xpath=..")
                except Exception:
                    break
        raise RuntimeError(
            f"Could not find a unique {label!r} control associated with {context!r}"
        )

    for role in ("button", "link"):
        locator = page.get_by_role(role, name=label, exact=True)
        try:
            count = locator.count()
            if count == 1:
                item = locator.nth(0)
                if item.is_visible() and item.is_enabled():
                    item.click(timeout=5000)
                    return
            elif count > 1:
                visible = [
                    locator.nth(i) for i in range(count)
                    if locator.nth(i).is_visible() and locator.nth(i).is_enabled()
                ]
                if len(visible) == 1:
                    visible[0].click(timeout=5000)
                    return
        except Exception:
            pass

    # Generic navigation fallback for icon-only cart/basket controls.
    # Prefer semantic navigation signals and avoid product action buttons such
    # as "Add to cart" or "Remove from cart".
    if any(word in label.casefold() for word in ("cart", "basket", "bag")):
        interactive = page.locator(
            "a, button, [role='link'], [role='button']"
        )
        matches = []
        seen = set()

        for i in range(min(interactive.count(), 80)):
            item = interactive.nth(i)
            try:
                if not item.is_visible() or not item.is_enabled():
                    continue

                aria_label = item.get_attribute("aria-label") or ""
                title = item.get_attribute("title") or ""
                href = item.get_attribute("href") or ""
                css_class = item.get_attribute("class") or ""
                visible_text = item.inner_text(timeout=500).strip()

                # Only explicit semantic attributes/classes may contain a
                # substring signal. Ordinary action text is handled separately.
                semantic_signals = [aria_label, title, href, css_class]

                descendants = item.locator("[aria-label], [title], svg")
                for j in range(min(descendants.count(), 10)):
                    child = descendants.nth(j)
                    semantic_signals.extend([
                        child.get_attribute("aria-label") or "",
                        child.get_attribute("title") or "",
                    ])
                    if child.evaluate(
                        "(el) => el.tagName.toLowerCase() === 'svg'"
                    ):
                        svg_title = child.locator("title").first
                        if svg_title.count():
                            semantic_signals.append(
                                svg_title.inner_text(timeout=300)
                            )

                semantic_text = " ".join(semantic_signals).casefold()
                semantic_text = semantic_text.replace("_", " ").replace("-", " ")
                semantic_match = bool(
                    re.search(r"\b(cart|basket|bag)\b", semantic_text)
                )

                # Visible text is a fallback only when it names the control,
                # not when it describes an action on a product.
                normalized_text = re.sub(
                    r"\s+", " ", visible_text.casefold()
                ).strip()
                text_match = bool(re.fullmatch(
                    r"(?:shopping\s+)?(?:cart|basket|bag)(?:\s+\d+)?",
                    normalized_text,
                ))

                action_text = bool(re.search(
                    r"\b(add|remove|delete)\b.*\b(cart|basket|bag)\b",
                    normalized_text,
                ))
                if action_text:
                    continue

                if semantic_match or text_match:
                    identity = item.evaluate(
                        "(el) => el.tagName + '|' + "
                        "(el.getAttribute('href') || '') + '|' + "
                        "(el.getAttribute('aria-label') || '') + '|' + "
                        "(el.getAttribute('class') || '')"
                    )
                    if identity not in seen:
                        seen.add(identity)
                        matches.append(item)
            except Exception:
                continue

        if len(matches) == 1:
            matches[0].click(timeout=5000)
            return
        if len(matches) > 1:
            raise RuntimeError(
                f"Found {len(matches)} possible visible cart/basket controls "
                f"for {label!r}; refusing an ambiguous click"
            )
        raise RuntimeError(
            f"Could not identify a visible cart/basket control for {label!r}"
        )

    raise RuntimeError(f"No unique visible enabled button or link found for {label!r}")


def _verify(page, scenario, history=None):
    """Verify the scenario's final observable state.

    ``history`` is accepted for backward compatibility with earlier callers
    and tests. Verification is deliberately based on the current browser state.
    """
    verification = scenario.get("verification", {})
    kind = verification.get("kind")
    expected = str(verification.get("expected", "")).strip()
    body = page.locator("body").inner_text(timeout=3000)

    if kind == "visible_text":
        ok = expected.casefold() in body.casefold()
        return ok, f"Expected visible text {expected!r}; observed={ok}"

    if kind == "text_absent":
        ok = expected.casefold() not in body.casefold()
        return ok, f"Expected text {expected!r} absent; observed_absent={ok}"

    if kind == "url_contains":
        ok = expected.casefold() in page.url.casefold()
        return ok, f"Expected URL to contain {expected!r}; actual={page.url!r}"

    if kind == "validation_message":
        messages = []
        for role in ("alert", "status"):
            locator = page.get_by_role(role)
            for i in range(min(locator.count(), 10)):
                item = locator.nth(i)
                if item.is_visible():
                    messages.append(item.inner_text(timeout=1000))
        actual = " ".join(messages).strip() or body
        ok = bool(expected) and expected.casefold() in actual.casefold()
        return ok, f"Expected validation message {expected!r}; observed={actual!r}"

    if kind == "distinct_images":
        locator = page.locator("img")
        labelled = []
        for i in range(min(locator.count(), 60)):
            item = locator.nth(i)
            try:
                alt = (item.get_attribute("alt") or "").strip()
                src = (item.get_attribute("src") or "").strip()
                if item.is_visible() and alt and src:
                    labelled.append((alt, src))
            except Exception:
                pass
        product_like = [(alt, src) for alt, src in labelled if alt.casefold() not in {"logo", "company logo"}]
        sources = [src for _, src in product_like]
        duplicates = sorted({src for src in sources if sources.count(src) > 1})
        ok = len(product_like) >= 2 and not duplicates
        return ok, (
            f"Checked {len(product_like)} visible labelled images; "
            f"duplicate sources={len(duplicates)}"
        )

    return False, f"Unsupported verification kind: {kind!r}"


def run_scenario(page, scenario, client=None, model=None, index=1):
    """Execute a validated plan deterministically and independently verify it."""
    logs = []
    steps = scenario.get("steps", [])
    completed = 0
    failure = None

    if not isinstance(steps, list) or not steps or len(steps) > MAX_ACTIONS:
        failure = f"Invalid action count; expected 1-{MAX_ACTIONS} steps"
    else:
        for number, step in enumerate(steps, start=1):
            try:
                if not isinstance(step, dict):
                    raise RuntimeError("Step is not an object")
                action, target = step.get("action"), step.get("target")
                if action == "fill":
                    value = step.get("value")
                    if not isinstance(value, str):
                        raise RuntimeError("Fill action requires a string value")
                elif action == "click":
                    value = None
                else:
                    raise RuntimeError(f"Unsupported action {action!r}")

                observed = snapshot(page)
                logs.append(
                    f"{scenario.get('id')}: step {number}: "
                    f"observed_url={observed['url']}; {action} {target!r}"
                )
                if action == "fill":
                    _fill_field(page, target, value)
                else:
                    _click_button(page, target)
                completed += 1
            except Exception as exc:
                failure = f"Step {number} failed: {type(exc).__name__}: {exc}"
                logs.append(f"{scenario.get('id')}: {failure}")
                break

    scenario_id = str(scenario.get("id", index))
    safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", scenario_id)
    screenshot = EVIDENCE / f"{index:02d}_{safe_id}.png"
    try:
        page.screenshot(path=str(screenshot), full_page=True)
    except Exception as exc:
        logs.append(f"Screenshot failed: {exc}")

    complete = bool(steps) and completed == len(steps) and failure is None
    if complete:
        try:
            verified, verification_details = _verify(page, scenario)
        except Exception as exc:
            verified, verification_details = False, f"Verification error: {exc}"
    else:
        verified = False
        verification_details = "Not run because one or more planned actions failed."

    passed = complete and verified
    status = "PASSED" if passed else "FAILED"
    details = (
        f"Executed {completed}/{len(steps)} planned steps. "
        f"Independent verification: {verification_details}. "
        f"Execution error: {failure or 'none'}"
    )
    logs.append(f"{scenario_id}: {status}: {details}")
    return {
        "id": scenario_id,
        "criterion": scenario.get("criterion", ""),
        "status": status,
        "details": details,
        "screenshot": str(screenshot.relative_to(ROOT)),
    }, logs
