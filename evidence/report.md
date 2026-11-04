# Autonomous UI Test Report

Issue: #2 — Test SauceDemo login and shopping cart

**Result: FAILED** — 3/4 scenarios passed

## TC1: PASSED
- Criterion: Valid login with standard_user and secret_sauce should display Products page
- Details: Executed 3/3 planned steps. Independent verification: Expected visible text 'Products'; observed=True. Execution error: none
- Screenshot: evidence\01_TC1.png

## TC2: PASSED
- Criterion: Add Sauce Labs Backpack to cart after valid login; cart count becomes 1
- Details: Executed 4/4 planned steps. Independent verification: Expected visible text '1'; observed=True. Execution error: none
- Screenshot: evidence\02_TC2.png

## TC3: PASSED
- Criterion: After adding Sauce Labs Backpack to cart, opening cart displays the product
- Details: Executed 5/5 planned steps. Independent verification: Expected visible text 'Sauce Labs Backpack'; observed=True. Execution error: none
- Screenshot: evidence\03_TC3.png

## TC4: FAILED
- Criterion: Problem user can add Sauce Labs Bolt T-Shirt to cart; button changes to Remove
- Details: Executed 4/4 planned steps. Independent verification: Expected visible text 'Remove'; observed=False. Execution error: none
- Screenshot: evidence\04_TC4.png

## Action log

- TC1: step 1: observed_url=https://www.saucedemo.com/; fill 'Username'
- TC1: step 2: observed_url=https://www.saucedemo.com/; fill 'Password'
- TC1: step 3: observed_url=https://www.saucedemo.com/; click 'Login'
- TC1: PASSED: Executed 3/3 planned steps. Independent verification: Expected visible text 'Products'; observed=True. Execution error: none
- TC2: step 1: observed_url=https://www.saucedemo.com/; fill 'Username'
- TC2: step 2: observed_url=https://www.saucedemo.com/; fill 'Password'
- TC2: step 3: observed_url=https://www.saucedemo.com/; click 'Login'
- TC2: step 4: observed_url=https://www.saucedemo.com/inventory.html; click 'Sauce Labs Backpack | Add to cart'
- TC2: PASSED: Executed 4/4 planned steps. Independent verification: Expected visible text '1'; observed=True. Execution error: none
- TC3: step 1: observed_url=https://www.saucedemo.com/; fill 'Username'
- TC3: step 2: observed_url=https://www.saucedemo.com/; fill 'Password'
- TC3: step 3: observed_url=https://www.saucedemo.com/; click 'Login'
- TC3: step 4: observed_url=https://www.saucedemo.com/inventory.html; click 'Sauce Labs Backpack | Add to cart'
- TC3: step 5: observed_url=https://www.saucedemo.com/inventory.html; click 'Cart'
- TC3: PASSED: Executed 5/5 planned steps. Independent verification: Expected visible text 'Sauce Labs Backpack'; observed=True. Execution error: none
- TC4: step 1: observed_url=https://www.saucedemo.com/; fill 'Username'
- TC4: step 2: observed_url=https://www.saucedemo.com/; fill 'Password'
- TC4: step 3: observed_url=https://www.saucedemo.com/; click 'Login'
- TC4: step 4: observed_url=https://www.saucedemo.com/inventory.html; click 'Sauce Labs Bolt T-Shirt | Add to cart'
- TC4: FAILED: Executed 4/4 planned steps. Independent verification: Expected visible text 'Remove'; observed=False. Execution error: none