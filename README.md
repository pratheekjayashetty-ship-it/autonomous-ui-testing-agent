# Autonomous UI Testing Agent

An AI-powered QA agent that reads a GitHub issue, generates test scenarios from its acceptance criteria, executes bounded browser actions using Playwright, validates the UI, and saves structured test reports and screenshot evidence.

## Project Overview

This project demonstrates an autonomous UI testing workflow:

1. Read an issue and its acceptance criteria from GitHub.
2. Generate a structured test plan.
3. Execute UI actions against a demo Task Manager application using Playwright.
4. Validate the observed UI against expected behavior.
5. Save test results, logs, generated plans, and screenshots for review.

## Test Results

The latest local test run completed with:

- Total scenarios: 3
- Passed: 3
- Failed: 0

The scenarios cover task creation, task completion, and validation of empty task names.

These results are from the local demo application; they have not been independently reproduced by a reviewer.

See the Markdown report, JSON report, and generated test plan:
- `evidence/report.md`
- `evidence/report.json`
- `evidence/generated_plan.json`

## Prerequisites

- Python 3.11 or later
- An OpenAI API key, if using the configured OpenAI model
- GitHub access and a personal access token with read access to repository issues when testing against a private repository
- Internet access to install dependencies and retrieve GitHub issues

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/pratheekjayashetty-ship-it/autonomous-ui-testing-agent.git
cd autonomous-ui-testing-agent
```

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
playwright install chromium
```

### 4. Configure environment variables

Copy `.env.example` to `.env` in the project root.

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS/Linux:

```bash
cp .env.example .env
```

Open `.env` and fill in the values required by the implementation. For example:

```dotenv
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini
APP_URL=http://127.0.0.1:5000
GITHUB_TOKEN=your_github_token
GITHUB_REPOSITORY=pratheekjayashetty-ship-it/autonomous-ui-testing-agent
GITHUB_ISSUE_NUMBER=1
```

Use your own credentials. Never commit `.env`, API keys, or access tokens to GitHub.

The GitHub token needs permission to read issues in the selected repository. If using a fine-grained personal access token, grant access to the target repository and the Issues: Read-only permission; metadata read access is also required.

### 5. Start the demo application

Open a terminal in the project directory, activate the virtual environment, and run:

```bash
python app.py
```

Keep this terminal running. The demo application should be available at:

`http://127.0.0.1:5000`

### 6. Run the agent

Open a second terminal in the project directory, activate the same virtual environment, and run:

```bash
python run_agent.py
```

The agent loads the configured GitHub issue when the required GitHub environment variables are set. Otherwise, it uses the sample issue if supported by the current configuration.

Review the generated output in the `evidence/` directory.

## GitHub Issue Configuration

The sample issue is provided for local testing. To test with a real GitHub issue:

1. Create or select an issue containing clear acceptance criteria.
2. Configure `GITHUB_REPOSITORY`, `GITHUB_ISSUE_NUMBER`, and `GITHUB_TOKEN` in `.env`.
3. If the implementation requires the `Ready for QA` label, apply that exact label to the issue.
4. Run the agent and inspect the generated plan, execution results, and evidence.

For private repositories, the token must have access to the target repository.

## Project Structure

```text
autonomous-ui-testing-agent/
├── agent/
│   ├── browser_agent.py
│   ├── issue_source.py
│   ├── planner.py
│   └── reporting.py
├── evidence/
│   ├── generated_plan.json
│   ├── report.json
│   ├── report.md
│   └── [test screenshots]
├── .env.example
├── .gitignore
├── app.py
├── requirements.txt
├── run_agent.py
├── sample_issue.json
├── SCENARIOS.md
└── TEST_PLAN.md
```

The exact screenshot filenames may vary by run.

## Evidence and Reports

- Test report (Markdown): `evidence/report.md`
- Test report (JSON): `evidence/report.json`
- Generated test plan: `evidence/generated_plan.json`
- Screenshot evidence: `evidence/`

The reports capture the test outcomes and observations from the recorded run.

## Guardrails and Limitations

- Browser actions are intentionally bounded to the demo application's supported interactions.
- Test outcomes depend on the issue acceptance criteria, generated plan, and actual UI behavior.
- AI-generated plans should be reviewed for correctness and coverage.
- A passing demo run does not establish production readiness or guarantee that every possible UI behavior has been tested.
- API quotas, credentials, network access, or browser setup can affect execution.

## Security

- Keep `.env` out of version control.
- Do not upload `.venv`, API keys, or personal access tokens.
- Use least-privilege GitHub credentials.
- Use a dedicated test environment for browser automation.
- Review screenshots and reports before sharing them to ensure they contain no sensitive information.

## Assignment Documentation

- Test Plan: `TEST_PLAN.md`
- Test Scenarios: `SCENARIOS.md`

## Author

Developed as a demonstration of AI-assisted QA automation, issue-driven test planning, Playwright UI execution, and evidence-based reporting.
