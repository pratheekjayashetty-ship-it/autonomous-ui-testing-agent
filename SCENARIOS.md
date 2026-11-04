# Test Scenarios

Source: `sample_issue.json` (or a configured GitHub issue labelled `Ready for QA`).

The runtime planner generates scenarios from the issue's acceptance criteria
and explicit test data. Each scenario is executed in a fresh browser context.

Expected coverage from the fixture:

1. **Valid login** — use the supplied standard test account and verify arrival
   at the inventory page.
2. **Invalid login** — use the supplied invalid account and verify the visible
   application error message.
3. **Add product to cart** — log in, add the named product using its contextual
   action, and verify the cart count.
4. **Cart contents** — independently log in, add the named product, open the
   cart, and verify the selected product appears.
5. **Image consistency defect check** — log in with the supplied defect-repro
   account and compare visible labelled product image sources. Report a failure
   only if the observed UI violates the stated criterion.

The exact generated steps, actual outcomes, action logs, and screenshots are
stored under `evidence/`. A planned scenario is not proof of a reproduced
application defect; use the recorded report and screenshot.
