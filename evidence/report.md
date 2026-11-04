# Autonomous UI Test Report

Issue: #2 — Test SauceDemo login and shopping cart

**Result: FAILED** — 4/5 scenarios passed

## TC1: PASSED
- Criterion: Valid login - Username: standard_user - Password: secret_sauce - Verify that the Products page is displayed.
- Details: Executed 3/3 planned steps. Independent verification: Expected visible text 'Products'; observed=True. Execution error: none
- Screenshot: evidence\01_TC1.png

## TC2: PASSED
- Criterion: Invalid login - Username: invalid_user - Password: wrong_password - Verify that this exact error message is displayed: Epic sadface: Username and password do not match any user in this service
- Details: Executed 3/3 planned steps. Independent verification: Expected validation message 'Epic sadface: Username and password do not match any user in this service'; observed='Epic sadface: Username and password do not match any user in this service'. Execution error: none
- Screenshot: evidence\02_TC2.png

## TC3: PASSED
- Criterion: Add product to cart - Log in using valid credentials. - Add Sauce Labs Backpack to the cart. - Verify that the cart count becomes 1.
- Details: Executed 4/4 planned steps. Independent verification: Expected visible text '1'; observed=True. Execution error: none
- Screenshot: evidence\03_TC3.png

## TC4: PASSED
- Criterion: Cart display - Log in using valid credentials in an independent browser session. - Add Sauce Labs Backpack to the cart. - Open the cart. - Verify that Sauce Labs Backpack is displayed.
- Details: Executed 5/5 planned steps. Independent verification: Expected visible text 'Sauce Labs Backpack'; observed=True. Execution error: none
- Screenshot: evidence\04_TC4.png

## TC5: FAILED
- Criterion: Problem user – Add-to-cart regression - Username: problem_user - Password: secret_sauce - Log in using the supplied credentials. - Locate Sauce Labs Bolt T-Shirt. - Click its associated Add to cart button. - Verify that its button label changes to Remove. - Report FAILED if the action completes but Remove is not visible.
- Details: Executed 4/4 planned steps. Independent verification: Expected visible text 'Remove'; observed=False. Execution error: none
- Screenshot: evidence\05_TC5.png

## Action log

- TC1: step 1: observed_url=https://www.saucedemo.com/; fill 'Username'
- TC1: step 2: observed_url=https://www.saucedemo.com/; fill 'Password'
- TC1: step 3: observed_url=https://www.saucedemo.com/; click 'Login'
- TC1: PASSED: Executed 3/3 planned steps. Independent verification: Expected visible text 'Products'; observed=True. Execution error: none
- TC2: step 1: observed_url=https://www.saucedemo.com/; fill 'Username'
- TC2: step 2: observed_url=https://www.saucedemo.com/; fill 'Password'
- TC2: step 3: observed_url=https://www.saucedemo.com/; click 'Login'
- TC2: PASSED: Executed 3/3 planned steps. Independent verification: Expected validation message 'Epic sadface: Username and password do not match any user in this service'; observed='Epic sadface: Username and password do not match any user in this service'. Execution error: none
- TC3: step 1: observed_url=https://www.saucedemo.com/; fill 'Username'
- TC3: step 2: observed_url=https://www.saucedemo.com/; fill 'Password'
- TC3: step 3: observed_url=https://www.saucedemo.com/; click 'Login'
- TC3: step 4: observed_url=https://www.saucedemo.com/inventory.html; click 'Sauce Labs Backpack | Add to cart'
- TC3: PASSED: Executed 4/4 planned steps. Independent verification: Expected visible text '1'; observed=True. Execution error: none
- TC4: step 1: observed_url=https://www.saucedemo.com/; fill 'Username'
- TC4: step 2: observed_url=https://www.saucedemo.com/; fill 'Password'
- TC4: step 3: observed_url=https://www.saucedemo.com/; click 'Login'
- TC4: step 4: observed_url=https://www.saucedemo.com/inventory.html; click 'Sauce Labs Backpack | Add to cart'
- TC4: step 5: observed_url=https://www.saucedemo.com/inventory.html; click 'Cart'
- TC4: PASSED: Executed 5/5 planned steps. Independent verification: Expected visible text 'Sauce Labs Backpack'; observed=True. Execution error: none
- TC5: step 1: observed_url=https://www.saucedemo.com/; fill 'Username'
- TC5: step 2: observed_url=https://www.saucedemo.com/; fill 'Password'
- TC5: step 3: observed_url=https://www.saucedemo.com/; click 'Login'
- TC5: step 4: observed_url=https://www.saucedemo.com/inventory.html; click 'Sauce Labs Bolt T-Shirt | Add to cart'
- TC5: FAILED: Executed 4/4 planned steps. Independent verification: Expected visible text 'Remove'; observed=False. Execution error: none