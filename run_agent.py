import os
import json
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
    key = os.getenv("OPENAI_API_KEY", "").strip()

    if not key or key == "replace_me":
        raise SystemExit("Set OPENAI_API_KEY in .env")

    model = os.getenv("OPENAI_MODEL", "openai/gpt-oss-20b")
    url = os.getenv("APP_URL", "http://127.0.0.1:5000")

    client = OpenAI(
        api_key=key,
        base_url="https://api.groq.com/openai/v1"
    )

    issue = load_issue()

    print(
        f"Loaded issue #{issue.get('number')}: "
        f"{issue.get('title')}"
    )

    plan = make_plan(issue, client, model)

    (EVIDENCE / "generated_plan.json").write_text(
        json.dumps(plan, indent=2),
        encoding="utf-8"
    )

    results = []
    logs = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            headless=False
        )

        page = browser.new_page(
            viewport={"width": 1365, "height": 900}
        )

        page.set_default_timeout(4000)

        try:
            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=10000
            )

            for i, s in enumerate(plan["scenarios"], 1):
                print(
                    f"Running {s.get('id')}: "
                    f"{s.get('criterion')}"
                )

                result, entries = run_scenario(
                    page,
                    s,
                    client,
                    model,
                    i
                )

                results.append(result)
                logs.extend(entries)

                print(
                    f"  {result['status']}: "
                    f"{result['details']}"
                )

                page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=10000
                )

        finally:
            browser.close()

    report = write_report(
        issue,
        plan,
        results,
        logs
    )

    print("Summary:", report["summary"])
    print("Evidence:", EVIDENCE)

    if report["summary"]["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()