# Test Plan & Strategy

## Architecture
1. `issue_source.py` loads a local issue fixture or fetches a GitHub issue using the REST API. GitHub issues must have the `Ready for QA` label.
2. `planner.py` uses an OpenAI model to map issue acceptance criteria to structured scenarios.
3. `browser_agent.py` provides a bounded LLM action loop and Playwright semantic locators.
4. Deterministic verification checks rendered UI state after the agent acts.
5. `reporting.py` saves JSON/Markdown results and scenario screenshots in `evidence/`.

## Loop prevention
- Maximum 4 scenarios and 5 planner steps per scenario.
- Maximum 8 browser action rounds per scenario.
- Repeated action signatures are blocked.
- Browser operations have timeouts.
- Only allow-listed tools are exposed; arbitrary code execution is unavailable.
- The model cannot independently mark a test as passed; the final observable verification decides.

## Element identification and assertions
Use accessible labels, placeholders, button roles and names. If a locator is ambiguous or absent, record an error rather than guessing a CSS selector. Final verification inspects rendered text or completed styling. Unsupported verification kinds fail closed.

## Error handling and evidence
Action errors are retained in the log. Screenshots are captured at scenario end. `report.json` contains structured results; `report.md` provides a readable summary.

## Limitations
This is a bounded take-home demo. `Ready for QA` is represented by a GitHub issue label; a GitHub Projects webhook is not included. The sample app and verification rules are intentionally small and should be adapted before testing other applications.
