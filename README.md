# Autonomous UI Testing Agent

An issue-driven UI testing prototype. It reads acceptance criteria and explicit
test data from a GitHub issue (or local fixture), asks an OpenAI-compatible model
to generate a bounded test plan, executes the validated plan with Playwright,
independently verifies observable outcomes, and saves reports and screenshots.

## Recruiter feedback addressed

- **Public app:** defaults to `https://www.saucedemo.com/`; `APP_URL` is configurable.
- **Generic planning/execution:** planner instructions contain no app-specific
  selectors or credentials. Test data must come from the issue. Browser actions
  use accessible names, labels, visible context, and observed link destinations.
- **Failure reporting:** the fixture includes a `problem_user` add-to-cart
  regression for the Sauce Labs Bolt T-Shirt. A defect is reported only when
  the click completes but the expected `Remove` label is not visible.
- **Unit tests:** pytest tests cover plan validation, issue fixture loading, and
  report aggregation.

## Requirements

- Python 3.11+
- Google Chrome installed (the runner uses Playwright `channel="chrome"`)
- Groq or another OpenAI-compatible chat-completions API key/model
- Network access to the public application and API

## Setup (Windows Git Bash)

```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install -r requirements.txt
```

The runner uses your installed Google Chrome, so a Playwright Chromium download
is not required. Playwright's Python package is still required.

Copy and configure environment:

```bash
cp .env.example .env
```

Set `OPENAI_API_KEY` in `.env`. Keep `.env` private and never commit it.

Default API settings use Groq's OpenAI-compatible endpoint:

```dotenv
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_MODEL=openai/gpt-oss-20b
APP_URL=https://www.saucedemo.com/
HEADLESS=false
```

## Run

```bash
./.venv/Scripts/python.exe -m pytest -q
./.venv/Scripts/python.exe run_agent.py
```

The runner uses a fresh browser context for each scenario. Each scenario must
contain its own login and setup actions. The planner validates that every
credential/value entered by a fill action is explicitly present in the issue
text; invented credentials are rejected before browser execution.

## Issue source

If `GITHUB_TOKEN`, `GITHUB_REPOSITORY`, and `GITHUB_ISSUE_NUMBER` are all set,
the agent fetches that GitHub issue and requires the `Ready for QA` label.
Otherwise, it loads `sample_issue.json`.

The sample fixture specifies:
- standard account for successful login
- invalid account and exact expected error message for negative login
- Sauce Labs Backpack for add-to-cart and cart-content checks
- `problem_user` credentials for the Bolt T-Shirt add-to-cart regression
The issue must state all test values and expected outcomes. The agent does not
guess passwords, error messages, or product names. The planner requires one
scenario for each numbered acceptance criterion and rejects incomplete plans.

## Execution and guardrails

- Maximum five scenarios and eight actions per scenario.
- Each scenario runs in a fresh browser context.
- No model tool-selection call is made for every browser action. The planner
  returns a structured plan; the executor runs only those validated actions.
- Semantic Playwright locators are used; ambiguous/missing controls fail closed.
- Each scenario is independently verified from rendered text, URL, validation
  text, or image sources.
- Browser/API/locator errors are reported as execution errors, not application
  defects.
- A failed defect assertion is a candidate app defect; retain its screenshot
  and verify it manually before reporting it to the recruiter.

## Evidence

Generated files are saved under `evidence/`:
- `generated_plan.json`
- `report.json`
- `report.md`
- one screenshot per scenario

Do not claim a defect was reproduced unless the corresponding run's report and
screenshot show it.

## Git hygiene and suggested commits

```bash
git add agent/planner.py agent/browser_agent.py
git commit -m "refactor: make planning and browser execution application-agnostic"

git add run_agent.py agent/issue_source.py
git commit -m "feat: run isolated scenarios against configurable public applications"

git add tests requirements.txt
git commit -m "test: add planner issue-loader and reporting unit tests"

git add sample_issue.json README.md TEST_PLAN.md SCENARIOS.md .env.example
git commit -m "docs: add public app and reproducible defect test fixture"
```

Keep `.env`, `.venv/`, `__pycache__/`, `.pytest_cache/`, and compiled Python
files out of version control. Keep evidence reports and screenshots only after
reviewing them for secrets or personal data.
