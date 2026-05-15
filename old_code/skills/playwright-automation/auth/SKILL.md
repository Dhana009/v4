---
name: playwright-auth
description: Handle authentication, storage state, session management. User controls auth completely.
version: 1.0.0
metadata:
  hermes:
    tags: [auth, login, session, storageState]
    category: playwright-automation
    triggers: [login, auth, session, credentials,
               storage state, save auth, load auth,
               logged in, authentication,
               save session, reuse login]
---

# Authentication and Session Management

## Core Rule — User Controls Auth Completely
NEVER touch authentication unless user
explicitly asks.
NEVER auto-login.
NEVER auto-save storage state.
NEVER assume app needs authentication.
NEVER store credentials in plain text.

## Storage State — The Right Way to Handle Auth
Save login state once.
Reuse it in every subsequent session.
This avoids logging in every time.

## Flow 1 — First Time Setup
User launches session.
User logs in manually.
User says: "save storage state"

  Use terminal_tool to run:
  await _context.storage_state(
    path=".hermes/auth/storageState.json"
  )
  print("Storage state saved to:"
    " .hermes/auth/storageState.json")

Confirm to user:
  "Storage state saved ✅
   Next session: say 'load auth' to skip login"

## Flow 2 — Load Saved Auth
User says: "load storage state" or "use saved auth"
Must do this BEFORE browser_launch.

  Use terminal_tool to run:
  import json
  import os

  auth_path = ".hermes/auth/storageState.json"
  if os.path.exists(auth_path):
    _context = await _browser.new_context(
      storage_state=auth_path
    )
    _page = await _context.new_page()
    print("Auth loaded — already logged in")
  else:
    print("No saved auth found at:", auth_path)
    print("Please login manually first")

## Flow 3 — Auth Expires or Fails
Signs auth has expired:
  Page redirects to login page
  API returns 401 response
  "Session expired" message appears

When detected:
  Tell user: "Auth state expired.
              Please login again.
              I will save new state when done."
  User logs in.
  Save new storage state.
  Continue session.

## Flow 4 — No Auth Needed
User never mentions auth.
Agent never touches it.
Continue with test recording as normal.

## Multiple Users
Save separate state per user role:

  Admin user:
  await _context.storage_state(
    path=".hermes/auth/admin-storageState.json"
  )

  Regular user:
  await _context.storage_state(
    path=".hermes/auth/user-storageState.json"
  )

  User specifies which to load:
  "load admin auth" → admin-storageState.json
  "load user auth"  → user-storageState.json

## Credentials from .env
Never type credentials in chat.
Store in .hermes/.env:

  TEST_EMAIL=user@company.com
  TEST_PASSWORD=secret123
  ADMIN_EMAIL=admin@company.com
  ADMIN_PASSWORD=admin-secret

Use in fill actions:
  action_fill(
    locator=email_locator,
    value="process.env.TEST_EMAIL"
  )

Generated code uses:
  await emailInput.fill(
    process.env.TEST_EMAIL ?? '')

NEVER show actual values in chat or output.

## Generated Code Format

Load storage state at test start:
  test.use({
    storageState: '.hermes/auth/storageState.json'
  })

Or in beforeAll:
  test.beforeAll(async ({ browser }) => {
    const context = await browser
      .newContext()
    const page = await context.newPage()
    await page.goto(process.env.BASE_URL)
    await page.getByLabel('Email').fill(
      process.env.TEST_EMAIL)
    await page.getByLabel('Password').fill(
      process.env.TEST_PASSWORD)
    await page.getByRole('button',
      { name: 'Login' }).click()
    await context.storageState({
      path: '.hermes/auth/storageState.json'
    })
    await context.close()
  })

## Signal Mapping
"save storage state"        → storage_state save
"save auth"                 → same
"load storage state"        → new_context with
                              storage_state path
"load auth"                 → same
"use saved session"         → same
"auth expired"              → delete old state
                              prompt user login
                              save new state
"login as admin"            → load admin state
"login as user"             → load user state

