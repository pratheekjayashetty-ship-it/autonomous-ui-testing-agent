# Test Scenarios

Source issue: `sample_issue.json`, labeled `Ready for QA`.

1. **AC1 — Add a non-empty task**
   - Given the Task Manager page is open
   - When a non-empty task name is entered and Add task is clicked
   - Then the task is visible and a confirmation appears.

2. **AC2 — Task visibility**
   - When a uniquely named task is added
   - Then the exact task name appears in the list.

3. **AC3 — Mark completed**
   - Given a task exists
   - When its Mark complete button is clicked
   - Then the task has completed styling and the button label changes.

4. **AC4 — Reject empty task**
   - When Add task is clicked with an empty field
   - Then `Please enter a task name.` appears and no task is added.

The runtime plan is generated from the issue body. Actual generated scenarios and results are stored in `evidence/`.
