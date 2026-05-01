---
name: playwright-network
description: Capture network calls, intercept requests, mock API responses, and add API assertions.
version: 1.0.0
metadata:
  hermes:
    tags: [network, API, request, response, mock]
    category: playwright-automation
    triggers: [network, API, request, response,
               observe, intercept, mock, capture,
               API call, network call, endpoint,
               what API, watch network, route]
---

# Playwright Network Handling

## Capture Network Call During Action
Set up listener BEFORE the action.
User says: "click submit — observe the API call"

  Use terminal_tool to run:
  async with _page.expect_response(
    lambda r: "/api/" in r.url
  ) as response_info:
    await action_click(locator=submit_locator)
  response = await response_info.value

  Get details:
  url = response.url
  status = response.status
  request = response.request
  request_body = await request.post_data()
  response_body = await response.json()

  Report to user:
  f"Captured: {request.method} {url}
    Status: {status}
    Request: {request_body}
    Response: {response_body}"

## Filter Noise — Only Capture Relevant Calls
Ignore analytics, tracking, third party:

  async with _page.expect_response(
    lambda r: (
      "/api/" in r.url and
      "analytics" not in r.url and
      "tracking" not in r.url and
      r.request.resource_type == "xhr"
    )
  ) as response_info:
    await action_click(locator=button_locator)

## Mock API Response
Replace real API with fake response for testing:

  await _page.route(
    "**/api/auth/login",
    lambda route: route.fulfill(
      status=200,
      content_type="application/json",
      body='{"token": "fake-token",'
           ' "user_id": 123}'
    )
  )

Mock error response:
  await _page.route(
    "**/api/submit",
    lambda route: route.fulfill(
      status=500,
      body='{"error": "Server error"}'
    )
  )

## Modify Request Headers
Add auth header to all requests:

  async def add_auth(route):
    headers = {
      **route.request.headers,
      "Authorization": "Bearer test-token"
    }
    await route.continue_(headers=headers)

  await _page.route("**/*", add_auth)

## Block Unnecessary Resources
Speed up tests by blocking images/CSS:

  await _page.route(
    "**/*.{png,jpg,jpeg,gif,css,woff}",
    lambda route: route.abort()
  )

## Add Network Assertion in Generated Code
  const [response] = await Promise.all([
    page.waitForResponse(
      r => r.url().includes('/api/login')
        && r.status() === 200
    ),
    loginButton.click()
  ])
  const body = await response.json()
  expect(body.token).toBeDefined()

## Signal Mapping
"observe the API call"       → expect_response
                               BEFORE action
"capture network call"       → same
"what API is called"         → same
"mock the API"               → page.route fulfill
"intercept request"          → page.route
"block images"               → route abort
"add API assertion"          → expect_response
                               in generated code
"check response status"      → response.status()
"check response body"        → response.json()

## When Expected Network Request Never Fires
Sometimes the API call you expect does not
happen. Need to handle this gracefully.

Signs request never fired:
  expect_response times out
  No network activity after action
  Action completed but no API call seen

How to handle:

  Step 1: Set a reasonable timeout
    async with _page.expect_response(
      lambda r: "/api/" in r.url,
      timeout=10000
    ) as response_info:
      await action_click(locator=button_locator)
    
    try:
      response = await response_info.value
    except Exception as e:
      Take screenshot
      Report: "No network request detected
               after this action.
               The action may not trigger
               an API call on this page."

  Step 2: Check if request was already made
    Some apps pre-fetch data before user action.
    Listen from page load not from action:
    
    captured_requests = []
    _page.on(
      "response",
      lambda r: captured_requests.append(r)
        if "/api/" in r.url else None
    )

  Step 3: Tell user clearly
    "No API call was captured after clicking
     [element]. Either:
     1. This action does not trigger a network
        request
     2. The request uses WebSocket instead
        of HTTP
     3. The request fired before we started
        listening
     Want me to monitor all network activity
     from page load instead?"

## Monitor All Network Activity
When user wants to see everything:

  all_requests = []

  async def capture_all(response):
    if not any(x in response.url for x in [
      "analytics", "tracking",
      "hotjar", "facebook", "google-tag"
    ]):
      all_requests.append({
        "method": response.request.method,
        "url": response.url,
        "status": response.status
      })

  _page.on("response", capture_all)

  After user action completes:
  Show summary to user:
  f"Captured {len(all_requests)} API calls:
    {json.dumps(all_requests, indent=2)}"

## WebSocket Monitoring
Some apps use WebSocket instead of HTTP.
Standard expect_response will not capture these.

Detect WebSocket usage:
  ws_messages = []

  _page.on(
    "websocket",
    lambda ws: ws.on(
      "framereceived",
      lambda payload: ws_messages.append(
        payload
      )
    )
  )

  After action:
  If ws_messages:
    Report: "WebSocket messages received:
             [messages summary]"

## Network Request Modification
Change request before it goes to server:

  async def modify_request(route):
    headers = {
      **route.request.headers,
      "X-Test-Header": "playwright-test",
      "Authorization": f"Bearer {test_token}"
    }
    await route.continue_(headers=headers)

  await _page.route("**/api/**",
    modify_request)

## Abort Specific Requests
Block certain requests from completing:

  await _page.route(
    "**/api/analytics/**",
    lambda route: route.abort()
  )

This speeds up tests by blocking
unnecessary tracking calls.

## Generated Code — Network Assertions
In generated TypeScript test:

Wait for request with timeout:
  const response = await page.waitForResponse(
    r => r.url().includes('/api/submit'),
    { timeout: 10000 }
  )
  expect(response.status()).toBe(200)

Handle missing request gracefully:
  try {
    const response = await page.waitForResponse(
      r => r.url().includes('/api/'),
      { timeout: 5000 }
    )
    const body = await response.json()
    expect(body.success).toBeTruthy()
  } catch {
    console.log('No API call detected —
      checking UI state instead')
    await expect(
      page.getByText('Success')
    ).toBeVisible()
  }
