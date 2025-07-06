# Pipedream Module Usage Guide

This guide explains how to use the bundled Python modules in your Pipedream workflows.

## Table of Contents
1. [Overview](#overview)
2. [Available Modules](#available-modules)
3. [Installation Steps](#installation-steps)
4. [Module Documentation](#module-documentation)
5. [Example Workflows](#example-workflows)
6. [Troubleshooting](#troubleshooting)

## Overview

The bundled modules in the `pipedream_modules/` directory are self-contained Python files that include all necessary dependencies. They can be directly pasted into Pipedream code steps without requiring additional imports.

### Benefits
- No external dependencies required
- All utility functions included
- Consistent error handling
- Type-safe inputs and outputs

## Available Modules

### 1. Gmail to Notion Task Creator (`gmail_to_notion_bundled.py`)
Creates Notion tasks from Gmail emails with support for HTML content and image extraction.

### 2. Notion to Google Calendar Sync (`notion_to_gcal_bundled.py`)
Synchronizes Notion tasks with due dates to Google Calendar events.

### 3. Calendar to Notion Sync (`calendar_to_notion_bundled.py`)
Updates Notion pages based on Google Calendar event changes.

### 4. Notion Update Handler (`notion_update_handler_bundled.py`)
Handles updates to existing Notion tasks and syncs changes with connected services.

## Installation Steps

### Step 1: Create a New Workflow
1. Log into Pipedream
2. Click "New Workflow"
3. Choose your trigger (e.g., HTTP, Schedule, Gmail, etc.)

### Step 2: Add a Code Step
1. Click "+ Add Step"
2. Select "Code"
3. Choose "Python"

### Step 3: Configure Authentication
1. In the code step, click "Connect Account"
2. Add required accounts:
   - For Notion modules: Connect your Notion account
   - For Gmail modules: Connect your Gmail account
   - For Calendar modules: Connect your Google Calendar account

### Step 4: Paste the Module Code
1. Open the bundled module file (e.g., `pipedream_modules/gmail_to_notion_bundled.py`)
2. Copy the entire contents
3. Paste into the Pipedream code editor
4. At the bottom of the code, add: `return handler(pd)`

### Step 5: Configure Inputs
Add required inputs in the code step configuration:

```javascript
// Example inputs for Gmail to Notion
{
  "database_id": "your-notion-database-id",
  "email": {
    "subject": "Email subject",
    "from": "sender@example.com",
    "body": "Email body content"
  }
}
```

## Module Documentation

### Gmail to Notion Task Creator

**Required Inputs:**
- `database_id` (string): Notion database ID where tasks will be created
- `email` (object): Email data with fields:
  - `subject` (string): Email subject
  - `from` (string): Sender email address
  - `body` or `text` (string): Email body content
  - `html` (string, optional): HTML content for image extraction

**Authentication:**
- Notion OAuth token (automatically provided when you connect your account)

**Returns:**
```json
{
  "success": {
    "task_id": "notion-page-id",
    "task_url": "https://notion.so/...",
    "image_url": "https://..."  // if HTML content was processed
  }
}
```

### Notion to Google Calendar Sync

**Required Inputs:**
- `task` (object): Notion task data from trigger
- `calendar_id` (string): Google Calendar ID
- `calendar_auth` (string): Google Calendar authentication token

**Returns:**
```json
{
  "success": {
    "event_id": "google-event-id",
    "event_url": "https://calendar.google.com/...",
    "task_url": "https://notion.so/..."
  }
}
```

### Calendar to Notion Sync

**Required Inputs:**
- `event` (object): Google Calendar event data
- `notion_auth` (string): Notion authentication token

**Returns:**
```json
{
  "success": {
    "page_id": "notion-page-id",
    "updated_fields": ["title", "date"]
  }
}
```

### Notion Update Handler

**Required Inputs:**
- `page_id` (string): Notion page ID to update
- `updates` (object): Fields to update
- `notion_auth` (string): Notion authentication token

**Returns:**
```json
{
  "success": {
    "page_id": "notion-page-id",
    "updated": true
  }
}
```

## Example Workflows

### Example 1: Gmail to Notion Automation

**Workflow Structure:**
1. **Trigger**: Gmail - New Email Matching Search
2. **Step 1**: Code (Python) - Create Notion Task
3. **Step 2**: Gmail - Add Label to Email

**Code Step Configuration:**
```python
# Copy the entire contents of gmail_to_notion_bundled.py here
# ... (bundled code) ...

# At the bottom, add:
return handler(pd)
```

**Step 1 Inputs:**
```javascript
{
  "database_id": "abc123...",  // Your Notion database ID
  "email": steps.trigger.event  // Email data from trigger
}
```

### Example 2: Bidirectional Notion-Calendar Sync

**Workflow A - Notion to Calendar:**
1. **Trigger**: Notion - Page Updated
2. **Step 1**: Code (Python) - Sync to Calendar

**Workflow B - Calendar to Notion:**
1. **Trigger**: Google Calendar - Event Updated
2. **Step 1**: Code (Python) - Update Notion

### Example 3: Complete Email Processing Pipeline

1. **Trigger**: Schedule (every 15 minutes)
2. **Step 1**: Gmail - Search Emails
3. **Step 2**: Code (Python) - Create Notion Tasks
4. **Step 3**: Gmail - Label Processed Emails

## Troubleshooting

### Common Issues

#### 1. Authentication Errors
**Error**: "Authentication credentials not found"
**Solution**: 
- Reconnect your Notion/Gmail/Google account in Pipedream
- Ensure the account has necessary permissions

#### 2. Missing Required Fields
**Error**: "Required input field 'database_id' is missing"
**Solution**: 
- Add the missing field to your step inputs
- Check the field name matches exactly (case-sensitive)

#### 3. API Rate Limits
**Error**: "Rate limit exceeded"
**Solution**: 
- Add delays between API calls
- Implement exponential backoff
- Check your API plan limits

#### 4. Invalid Database ID
**Error**: "Database not found"
**Solution**: 
- Verify the database ID is correct
- Ensure your Notion integration has access to the database
- Database ID format: remove hyphens from the URL ID

### Debug Mode

To enable detailed logging, modify the logger level in your code:

```python
# Change from:
logger.setLevel(logging.INFO)

# To:
logger.setLevel(logging.DEBUG)
```

### Getting Database IDs

**Notion Database ID:**
1. Open your Notion database
2. Copy the URL: `https://notion.so/workspace/[database-id]?v=...`
3. Extract the ID (32 characters after workspace/)
4. Remove any hyphens

**Google Calendar ID:**
1. Go to Google Calendar settings
2. Find your calendar in the list
3. Copy the Calendar ID (usually ends with @gmail.com or @group.calendar.google.com)

## Best Practices

1. **Error Handling**: The bundled modules include comprehensive error handling. Check the returned object for `error` keys.

2. **Testing**: Test with a single item before running on bulk data.

3. **Rate Limits**: Be mindful of API rate limits:
   - Notion: 3 requests per second
   - Gmail: 250 quota units per user per second
   - Google Calendar: 500 requests per 100 seconds

4. **Logging**: Use Pipedream's built-in logging to debug issues:
   ```python
   print(f"Processing email: {email_data.get('subject')}")
   ```

5. **Secrets**: Never hardcode API keys or tokens. Use Pipedream's account connections.

## Support

For issues or questions:
1. Check the error message details
2. Review the module's expected inputs
3. Verify authentication is properly configured
4. Check Pipedream's execution logs

For module-specific issues, refer to the source code in the `src/integrations/` directory.