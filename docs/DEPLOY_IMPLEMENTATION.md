# Pipedream Deploy Implementation Details

This document explains how the `/deploy_to_pd` command works to deploy Python scripts to Pipedream workflows via browser automation.

## Why Browser Automation?

Pipedream's REST API does **not** support updating step code. The only way to modify Python action code is through the web UI. This script automates that process using Playwright.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Local Scripts  │────▶│   Playwright    │────▶│   Pipedream     │
│  src/steps/*.py │     │   Browser       │     │   Web Editor    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Key Technical Details

### Editor Type: CodeMirror (NOT Monaco)

Pipedream uses **CodeMirror** for their code editor, not Monaco Editor.

**How we discovered this:**
```python
# Debug output from update_code():
Editor elements found: {
    '.monaco-editor': 0,  # Not present
    '.cm-editor': 1,      # CodeMirror!
    '.cm-content': 1
}
```

**Selector priority:**
1. `.cm-editor` (CodeMirror 6)
2. `.cm-content`
3. `.CodeMirror` (CodeMirror 5 fallback)
4. `[class*='editor']` (generic fallback)

### Code Replacement Strategy

The code uses a click → select all → paste approach:

```python
# Step 1: Click inside the editor to focus
editor = page.locator(".cm-editor").first
await editor.click()

# Step 2: Select all existing code
await page.keyboard.press("ControlOrMeta+KeyA")

# Step 3: Paste new code from clipboard (replaces selection)
await page.evaluate(f"navigator.clipboard.writeText({repr(new_code)})")
await page.keyboard.press("ControlOrMeta+KeyV")
```

**Why clipboard paste instead of typing?**
- Faster for large code files
- Avoids CodeMirror's autocomplete/autoindent interference
- More reliable than `keyboard.type()` which can miss characters

### Deploy Button

The Deploy button is a `<SPAN>` element, not a `<button>`:

```html
<span class="whitespace-nowrap">Deploy</span>
```

**Solution:** Use Playwright's text locator:
```python
deploy_button = page.get_by_text("Deploy", exact=True).first
await deploy_button.click()
```

## Authentication

### Google SSO Flow

1. Browser opens with persistent profile (`.tmp/browser_profile/`)
2. User manually completes Google SSO login
3. Cookies are cached to `.env.local` as base64-encoded JSON
4. Subsequent runs use cached cookies if valid

### Cookie Expiration

| Cookie | Purpose | Expiration |
|--------|---------|------------|
| `pdsid` | **Session ID** | ~14 days |
| `pdhs` | User hash | ~1 year |
| `pdli` | Login indicator | ~1 year |

**The `pdsid` cookie is the critical one** - it expires in ~14 days. Users need to re-authenticate before it expires to maintain access.

### Extending Session

You cannot directly extend the cookie expiration (it's set by Pipedream's server). However:

1. **Automatic refresh**: Each successful login refreshes all cookies
2. **Persistent browser profile**: The profile at `.tmp/browser_profile/` maintains the session
3. **Best practice**: Run sync at least once every 2 weeks to keep session fresh

## Browser Permissions

The script grants clipboard permissions for the paste operation:

```python
context = await playwright.chromium.launch_persistent_context(
    user_data_dir=str(BROWSER_PROFILE_DIR),
    permissions=["clipboard-read", "clipboard-write"],
)
await context.grant_permissions(["clipboard-read", "clipboard-write"])
```

## Workflow URL Format

Pipedream uses this URL structure:
```
https://pipedream.com/@{username}/projects/{project_id}/{workflow-slug}/build
```

Example:
```
https://pipedream.com/@damilolaelegbede/projects/proj_qzsZPn/gmail-to-notion-p_6lCxdAp/build
```

## Troubleshooting

### "Could not find any editor element"
- The CODE section may not have expanded
- Check if step panel is open
- Verify the step was clicked successfully

### "Deploy button not found"
- Press Escape may not have closed the step panel
- Try clicking outside the panel first
- Check screenshot at `.tmp/screenshots/deploy-button-not-found.png`

### Code not replacing (appending instead)
- Select all (`Cmd+A`) may not be working
- Ensure editor is focused before keyboard commands
- Check if clipboard permissions are granted

### Session expired
- Delete `.env.local` and run sync again to re-authenticate
- Or manually log in to Pipedream in the browser window

## Files Modified

| File | Purpose |
|------|---------|
| `src/deploy/deploy_to_pipedream.py` | Main deploy orchestration |
| `src/deploy/selectors.py` | DOM selectors for Pipedream UI |
| `src/deploy/config.py` | Workflow configuration loading |
| `src/deploy/utils.py` | Cookie handling, file operations |
| `src/deploy/exceptions.py` | Custom error types |

## API Support Check

At the end of each sync, the script automatically checks if Pipedream's API now supports updating workflow step code. This is important because:

1. **Current limitation**: As of December 2024, Pipedream's REST API only supports updating a workflow's activation status, NOT step code
2. **Future opportunity**: If Pipedream adds code update support, we can switch from browser automation to direct API calls

The check fetches the Pipedream API docs and looks for:
- **Negative indicators** (checked first): "activation status", "consider making a new workflow"
- **Positive indicators**: "update step code", "modify step code", etc.

Output example:
```
API Support Check:
  Supports code update: False
  Message: Pipedream API still does NOT support updating step code. Browser automation remains required.
```

If the API ever adds support, you'll see:
```
API Support Check:
  Supports code update: True
  Message: Pipedream API may NOW support updating step code! Check docs: [URL]
```

## Testing

Run tests with:
```bash
python -m pytest tests/test_deploy/ -v
```

Coverage requirement: 70% (currently ~72%)

## References

- [Playwright + Monaco/CodeMirror guide](https://giacomocerquone.com/notes/monaco-playwright/)
- [Playwright clipboard permissions](https://journeyofquality.wordpress.com/2024/07/28/grant-browser-permission-in-playwright/)
- [Pipedream workflow docs](https://pipedream.com/docs/workflows/quickstart)
