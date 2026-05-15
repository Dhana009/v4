---
name: playwright-upload
description: Handle all file upload scenarios — standard input, div-based, drag and drop, with custom timeouts.
version: 1.0.0
metadata:
  hermes:
    tags: [upload, file, attach, chooser]
    category: playwright-automation
    triggers: [upload, file, attach, chooser,
               drag and drop file, select file,
               browse file, import file,
               upload document, upload pdf,
               upload image, file input]
---

# Playwright File Upload

## Step 1 — Find the File First
Before any upload action, check file exists:

User provides file path directly:
  "upload ~/Documents/resume.pdf"
  → Use that exact path

User says "use file in uploads folder":
  → Check .hermes/uploads/
  → Use: .hermes/uploads/filename.pdf

User provides no file:
  → Ask user: "Which file do you want to upload?
    Put it in .hermes/uploads/ and tell me
    the filename."

## Step 2 — Identify Upload Element Type
There are two types of upload elements:

TYPE A — Standard file input:
  HTML: <input type="file">
  Visible as a "Choose File" or "Browse" button
  Use set_input_files approach

TYPE B — Custom div/button upload:
  HTML: <div class="upload-area"> or custom button
  No visible file input in DOM
  Use file chooser API approach

How to identify which type:
  Run dom_extract and check elements
  If you see input with type="file" → Type A
  If you see a div/button → Type B
  When unsure → try Type A first, then Type B

## Type A — Standard File Input
Use terminal_tool to run:

  await _page.set_input_files(
    locator_string,
    ".hermes/uploads/filename.pdf"
  )

Multiple files at once:
  await _page.set_input_files(
    locator_string,
    [
      ".hermes/uploads/file1.pdf",
      ".hermes/uploads/file2.pdf"
    ]
  )

## Type B — Custom Div Upload (File Chooser)
IMPORTANT: Set up file chooser listener
BEFORE clicking the upload trigger.

Use terminal_tool to run:

  async with _page.expect_file_chooser() as fc:
    await action_click(
      locator=upload_trigger_locator
    )
  file_chooser = await fc.value
  await file_chooser.set_files(
    ".hermes/uploads/filename.pdf"
  )

## Type C — Drag and Drop File
When user wants to drag file onto drop zone:

  Use terminal_tool to run:
  
  import base64
  with open(".hermes/uploads/filename.pdf",
    "rb") as f:
    file_data = base64.b64encode(
      f.read()).decode()
  
  await _page.evaluate(
    """
    async ({ fileData, fileName, mimeType,
             selector }) => {
      const blob = await fetch(
        `data:${mimeType};base64,${fileData}`
      ).then(r => r.blob())
      const file = new File([blob], fileName,
        { type: mimeType })
      const dt = new DataTransfer()
      dt.items.add(file)
      const el = document.querySelector(selector)
      const event = new DragEvent('drop',
        { dataTransfer: dt, bubbles: true })
      el.dispatchEvent(event)
    }
    """,
    {
      "fileData": file_data,
      "fileName": "filename.pdf",
      "mimeType": "application/pdf",
      "selector": drop_zone_css_selector
    }
  )

## Wait for Upload to Complete
Always wait for confirmation after upload.

User says "wait up to 120 seconds":
  await _page.wait_for_selector(
    confirmation_locator,
    state="visible",
    timeout=120000
  )

Standard upload (no timeout specified):
  await _page.wait_for_selector(
    confirmation_locator,
    state="visible",
    timeout=30000
  )

Confirmation signs to look for:
  - Success message appearing
  - Progress bar completing
  - File name appearing in list
  - Upload button changing state
  - Page navigating after upload

## Generated Code Format
In generated TypeScript test:

Standard input:
  await page.setInputFiles(
    'input[type="file"]',
    path.join(__dirname,
      '../.hermes/uploads/resume.pdf')
  )

File chooser:
  const [fileChooser] = await Promise.all([
    page.waitForEvent('filechooser'),
    uploadButton.click()
  ])
  await fileChooser.setFiles(
    path.join(__dirname,
      '../.hermes/uploads/resume.pdf')
  )

Wait for confirmation:
  await expect(
    page.getByText('Upload successful')
  ).toBeVisible({ timeout: 120000 })

## Signal Mapping
"upload [file]"              → detect type
                               then upload
"attach [file]"              → same as upload
"import [file]"              → same as upload
"drag [file] to [area]"      → drag and drop
"upload and wait [N] secs"   → upload + timeout
"use file in uploads folder" → .hermes/uploads/
"upload the resume"          → find resume in
                               .hermes/uploads/

## Common Problems and Fixes

Upload button not responding:
  → Try file chooser approach instead
  → Check if element is actually a div not input

File not found:
  → Confirm file is in .hermes/uploads/
  → Check exact filename spelling
  → Ask user to add file to uploads folder

Upload seems to work but no confirmation:
  → Increase timeout
  → Look for different confirmation element
  → Check network tab for upload API response


