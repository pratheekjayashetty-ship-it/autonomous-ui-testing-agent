import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from playwright.sync_api import sync_playwright

from agent.issue_source import load_issue
from agent.planner import make_plan
from agent.browser_agent import run_scenario
from agent.reporting import write_report, EVIDENCE

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


def main():
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key or api_key == "replace_me":
        raise SystemExit("Set OPENAI_API_KEY in .env")

    model = os.getenv("OPENAI_MODEL", "openai/gpt-oss-20b")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.groq.com/openai/v1")
    app_url = os.getenv("APP_URL", "https://www.saucedemo.com/").strip()
    headless = os.getenv("HEADLESS", "false").casefold() == "true"

    client = OpenAI(api_key=api_key, base_url=base_url)
    issue = load_issue()
    print(f"Loaded issue #{issue.get('number')}: {issue.get('title')}")
    print(f"Target application: {app_url}")
    print("Browser: installed Google Chrome (Playwright channel=chrome)")

    plan = make_plan(issue, client, model)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "generated_plan.json").write_text(
        json.dumps(plan, indent=2), encoding="utf-8"
    )

    results, logs = [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=headless)
        try:
            for index, scenario in enumerate(plan["scenarios"], start=1):
                scenario_id = scenario.get("id", f"scenario_{index}")
                print(f"\nRunning {scenario_id}: {scenario.get('criterion', '')}")
                context = browser.new_context(
                    viewport={"width": 1365, "height": 900}
                )
                page = context.new_page()
                page.set_default_timeout(
                    int(os.getenv("PLAYWRIGHT_TIMEOUT_MS", "7000"))
                )
                try:
                    page.goto(
                        app_url,
                        wait_until="domcontentloaded",
                        timeout=int(os.getenv("PAGE_LOAD_TIMEOUT_MS", "30000")),
                    )
                    result, entries = run_scenario(
                        page, scenario, client, model, index
                    )
                    results.append(result)
                    logs.extend(entries)
                    print(f"  {result['status']}: {result['details']}")
                except Exception as exc:
                    result = {
                        "id": scenario_id,
                        "criterion": scenario.get("criterion", ""),
                        "status": "FAILED",
                        "details": f"Scenario setup error: {type(exc).__name__}: {exc}",
                        "screenshot": "",
                    }
                    results.append(result)
                    logs.append(f"{scenario_id}: {result['details']}")
                    print(f"  FAILED: {result['details']}")
                finally:
                    context.close()
        finally:
            browser.close()

    report = write_report(issue, plan, results, logs)
    print("\nRun summary:", report["summary"])
    print(f"Evidence directory: {EVIDENCE}")
    print(f"Markdown report: {EVIDENCE / 'report.md'}")
    print(f"JSON report: {EVIDENCE / 'report.json'}")
    if report["summary"]["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
