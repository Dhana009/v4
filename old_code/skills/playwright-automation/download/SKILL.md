---
name: playwright-download
description: Handle file downloads triggered by button clicks, links, or API responses.
version: 1.0.0
metadata:
  hermes:
    tags: [download, save, export, file]
    category: playwright-automation
    triggers: [download, save, export, save as,
               download file, export report,
               download pdf, download csv,
               save document, export data]
---

# Playwright File Downloads

## Critical Rule — Set Up Listener BEFORE Click
Always set up download listener BEFORE
clicking the button that triggers download.

WRONG order:
  1. Click download button
  2. Try to capture download  ← TOO LATE

CORRECT order:
  1. Set up download listener  ← FIRST
  2. Click download button     ← THEN click

## Standard Download
Use terminal_tool to run:

  async with _page.expect_download() as dl_info:
    await action_click(
      locator=download_button_locator
    )
  download = await dl_info.value

  Save to .hermes/downloads/:
  import os
  os.makedirs(".hermes/downloads", exist_ok=True)
  await download.save_as(
    f".hermes/downloads/{download.suggested_filename}"
  )

## Download with Custom Filename
  await download.save_as(
    ".hermes/downloads/my-report.pdf"
  )

## Get Download Info
After download completes:

  filename = download.suggested_filename
  url = download.url
  failure = await download.failure()

  If failure is not None:
    Download failed — report error to user

## Download Triggered by Link
Some downloads are triggered by clicking
an anchor tag with href pointing to file:

  async with _page.expect_download() as dl_info:
    await action_click(locator=link_locator)
  download = await dl_info.value
  await download.save_as(
    f".hermes/downloads/{download.suggested_filename}"
  )

## Download with Timeout
For large files that take time:

  async with _page.expect_download(
    timeout=120000
  ) as dl_info:
    await action_click(
      locator=download_button_locator
    )
  download = await dl_info.value

## Verify Download Completed
After saving the file:

  import os
  file_path = f".hermes/downloads/{filename}"
  
  Check file exists and has content:
  if os.path.exists(file_path):
    size = os.path.getsize(file_path)
    if size > 0:
      print(f"Download successful: {filename}
              ({size} bytes)")
    else:
      print("File downloaded but empty")
  else:
    print("Download failed — file not found")

## Generated Code Format
In generated TypeScript test:

Standard download:
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    downloadButton.click()
  ])
  await download.saveAs(
    path.join(__dirname,
      '../.hermes/downloads/',
      download.suggestedFilename())
  )

Verify file downloaded:
  const filePath = path.join(__dirname,
    '../.hermes/downloads/',
    download.suggestedFilename())
  expect(fs.existsSync(filePath)).toBeTruthy()

Download with timeout:
  const [download] = await Promise.all([
    page.waitForEvent('download',
      { timeout: 120000 }),
    exportButton.click()
  ])

## Folder Structure
All downloads saved to:
  .hermes/downloads/

Create this folder if it does not exist:
  os.makedirs(".hermes/downloads", exist_ok=True)

## Signal Mapping
"download [file]"             → expect_download
                                BEFORE click
"export report"               → expect_download
                                BEFORE click
"save as [filename]"          → download +
                                custom filename
"download and verify"         → download +
                                check file exists
"download takes long"         → timeout=120000
"download [file] to [folder]" → save_as with
                                custom path

## Common Problems and Fixes

Download not captured:
  → Listener was set up after click
  → Move listener setup BEFORE click

Download file is empty:
  → Check network tab for errors
  → Verify user has permission to download
  → Check if auth is required

Download fails silently:
  → Check download.failure() result
  → Take screenshot to see current state
  → Check if page shows error message

Cannot find downloaded file:
  → Check .hermes/downloads/ folder
  → Verify save_as path is correct
  → Check file permissions

After confirming, run:
  .venv/bin/python start.py "say hello"

Confirm clean boot.
