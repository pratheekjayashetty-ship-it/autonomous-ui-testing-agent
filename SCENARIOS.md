# Test Scenarios

Source: `sample_issue.json` (or a configured GitHub issue labelled `Ready for QA`).

The runtime planner generates scenarios from the issue's acceptance criteria
and explicit test data. Each scenario is executed in a fresh browser context.

Expected coverage from the fixture:
1. **Valid login** — use the supplied standard account and verify the Products
   page is displayed.
2. **Invalid login** — use the supplied invalid account and verify the exact
   application error message is displayed.
3. **Add product to cart** — add Sauce Labs Backpack and verify the cart count.
4. **Cart contents** — independently log in, add Sauce Labs Backpack, open the
   cart, and verify the product appears.
5. **Problem-user cart regression** — log in as `problem_user`, add the Sauce
   Labs Bolt T-Shirt, and verify the button changes to `Remove`. Report a defect
   only if the action completes but `Remove` is not visible.
The exact generated steps, actual outcomes, action logs, and screenshots are
stored under `evidence/`. A planned scenario is not proof of a reproduced
application defect; use the recorded report and screenshot.
