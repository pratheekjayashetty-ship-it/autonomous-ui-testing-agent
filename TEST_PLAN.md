# Test Plan & Strategy

## Objective
Demonstrate an issue-driven UI test agent that plans from acceptance criteria,
executes bounded semantic browser actions against a public web application,
and reports outcomes based on independent browser observations.

## Architecture
1. `agent/issue_source.py` loads a GitHub issue labelled `Ready for QA`, or the
   local `sample_issue.json` fixture.
2. `agent/planner.py` asks an OpenAI-compatible model for a structured JSON plan.
   It rejects unsupported actions, malformed plans, and fill values not present
   in the issue text.
3. `agent/browser_agent.py` observes visible page state and executes only the
   validated plan using Playwright semantic locators.
4. Every scenario gets a fresh browser context and must establish its own state.
5. Independent verification checks the final rendered UI, URL, validation text,
   or image-source uniqueness.
6. `agent/reporting.py` saves a JSON report, Markdown report, action log, and
   scenario screenshots.

## Guardrails
- Up to five scenarios and eight actions per scenario.
- Fresh browser context per scenario; no state leakage.
- No arbitrary code execution or model-selected browser tools at runtime.
- Only `fill` and `click` actions are supported.
- Ambiguous or missing controls fail closed.
- A scenario passes only if all actions execute and independent verification
  succeeds.
- API, network, browser, and locator errors are execution failures, not product
  defects.

## Public target and defect demonstration
The sample issue targets the public SauceDemo storefront. It includes standard
and invalid login test data, a cart workflow for Sauce Labs Backpack, and an
image-consistency check using the `problem_user` demo account. The image scenario
is considered a defect only if the live page observation shows duplicate image
sources for distinct labelled products. A test run must capture its screenshot
and report before a defect claim is made.

## Unit tests
`pytest` tests validate planner input constraints, rejection of invented
credentials, fixture loading, and report aggregation. Browser integration tests
are separate because they require Chrome, network access, and the model API.

## Limitations
- This is a bounded take-home prototype, not a general-purpose commercial test
  framework.
- The plan remains model-generated and should be reviewed for relevance.
- `Ready for QA` is implemented as a GitHub issue label; a Projects webhook is
  not included.
- Dynamic interfaces, CAPTCHA, MFA, and non-semantic controls may require
  additional adapters.
