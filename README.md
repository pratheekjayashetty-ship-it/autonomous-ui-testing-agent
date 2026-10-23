# Autonomous UI Testing Agent

A bounded AI-powered QA agent that reads a GitHub issue, generates test scenarios from acceptance criteria, controls a browser with Playwright, and saves evidence-backed results.

## Quick start
Requires Python 3.11+ and an OpenAI API key.

```bash
python -m venv .venv
source .venv/bin/activate
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
```

Add `OPENAI_API_KEY` to `.env`. Start the demo app in terminal 1:

```bash
python app.py
```

In terminal 2:

```bash
python run_agent.py
```

Open `evidence/report.md` for the summary. Screenshots and structured logs are also saved in `evidence/`.

## Use a real GitHub issue (optional)
Create an issue with acceptance criteria and add the `Ready for QA` label. Configure `GITHUB_TOKEN`, `GITHUB_REPOSITORY=owner/repo`, and `GITHUB_ISSUE_NUMBER` in `.env`. The token needs repository issue read access. If these settings are blank, the sample issue is used.

## Files
- `app.py`: local Task Manager demo app
- `agent/issue_source.py`: issue ingestion
- `agent/planner.py`: LLM planning
- `agent/browser_agent.py`: bounded browser actions and verification
- `agent/reporting.py`: reports and evidence
- `TEST_PLAN.md`, `SCENARIOS.md`: assignment documentation

## Guardrails
The agent has a fixed action limit, repeated-action detection, semantic locators, operation timeouts, and independent verification. It cannot run arbitrary shell or Python code. This is a demonstration project; review generated plans before adapting it to sensitive applications.
