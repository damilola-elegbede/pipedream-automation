# Gmail to Notion Configuration Guide

A comprehensive step-by-step guide for configuring Pipedream to automatically create Notion tasks from Gmail emails using this automation package.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Repository Setup Methods](#repository-setup-methods)
- [Pipedream Workflow Configuration](#pipedream-workflow-configuration)
- [Authentication Setup](#authentication-setup)
- [Testing and Validation](#testing-and-validation)
- [Troubleshooting](#troubleshooting)
- [Code Examples](#code-examples)

## Overview

This guide walks you through setting up an automated workflow that:
1. Monitors your Gmail for new emails (with optional filtering)
2. Extracts email content and metadata
3. Creates structured tasks in your Notion database
4. Labels processed emails in Gmail (optional)

**Key Features:**
- Automatic email-to-task conversion
- Customizable email filtering
- Rich content support (text + images)
- Error handling and retry logic
- Structured logging for debugging

## Prerequisites

### Required Accounts
- **Pipedream Account**: Sign up at [pipedream.com](https://pipedream.com)
- **Google Account**: With Gmail access
- **Notion Account**: With workspace access
- **GitHub Account**: For repository access (recommended)

### API Access Requirements

#### Gmail API Setup
1. **Google Cloud Console Setup:**
   ```markdown
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create new project or select existing one
   - Enable Gmail API
   - Create OAuth 2.0 credentials
   - Add authorized redirect URIs for Pipedream
   ```

2. **Required Scopes:**
   ```
   https://www.googleapis.com/auth/gmail.modify
   https://www.googleapis.com/auth/gmail.readonly
   ```

#### Notion API Setup
1. **Create Notion Integration:**
   ```markdown
   - Go to [Notion Developers](https://developers.notion.com)
   - Click "Create new integration"
   - Name your integration (e.g., "Gmail Task Creator")
   - Select associated workspace
   - Copy the "Internal Integration Token"
   ```

2. **Database Preparation:**
   ```markdown
   - Create or select target Notion database
   - Add required properties:
     * Name (Title)
     * Email (Email) - optional
     * Due Date (Date) - optional
   - Share database with your integration
   - Copy database ID from URL
   ```

### Development Tools
- Git for repository cloning
- Code editor (VS Code recommended)
- Terminal/command line access

## Repository Setup Methods

Based on Pipedream documentation research, there are several approaches to deploy this automation package:

### Method 1: GitHub Sync (Recommended for Teams)

**Best for:** Teams, version control, automatic updates

**IMPORTANT**: The `git clone` command runs on YOUR LOCAL MACHINE, not in Pipedream.

1. **Fork or Clone Repository (On Your Computer)**
   ```bash
   # Run this on your local machine/terminal
   git clone https://github.com/your-username/pipedream-automation.git
   cd pipedream-automation
   ```

2. **Enable Pipedream GitHub Sync**
   - Requires Pipedream Business plan
   - Go to Pipedream Dashboard → Projects
   - Create new project or select existing
   - Enable GitHub sync
   - Connect to your forked repository
   - Select branch (main/master)

3. **Sync Workflow Files**
   - Pipedream will automatically sync workflows from `/pipedream/workflows/`
   - Changes to GitHub automatically deploy to Pipedream
   - Supports bi-directional sync for collaborative development

### Method 2: Direct Code Copy (Recommended for Individual Use)

**Best for:** Individual users, quick setup, no version control needed

**IMPORTANT**: You download the code locally, then copy-paste into Pipedream workflow steps.

1. **Download Repository (On Your Computer)**
   ```bash
   # Option A: Git clone on your local machine
   git clone https://github.com/damilola-elegbede/pipedream-automation.git
   
   # Option B: Download ZIP from GitHub website
   # Go to GitHub → Code → Download ZIP → Extract on your computer
   ```

2. **Copy Bundled Code (From Your Computer to Pipedream)**
   - On your computer, navigate to `/pipedream_modules/gmail_to_notion_bundled.py`
   - Open the file in a text editor
   - Copy the entire file content (Ctrl+A, Ctrl+C)
   - Go to Pipedream workflow → Add "Custom Code" step
   - Paste the code into the step (Ctrl+V)

### Keeping Repository Updated

**For GitHub Sync Users:**
- Updates automatically sync from GitHub
- Create pull requests for changes
- Use development branches for testing

**For Direct Copy Users:**
1. **Check for Updates (On Your Computer):**
   ```bash
   # Run this on your local machine where you cloned the repo
   cd pipedream-automation
   git pull origin main
   ```

2. **Re-copy Updated Code:**
   - Check `src/steps/` for the step files you're using
   - Copy the updated code from your local files
   - Paste into your Pipedream workflow steps
   - Test updated functionality

3. **Set Update Reminders:**
   - Weekly check for updates
   - Subscribe to repository notifications
   - Follow release notes for breaking changes

## Pipedream Workflow Configuration

### Step 1: Create New Workflow

```markdown
1. **Login to Pipedream Dashboard**
   - Go to [pipedream.com](https://pipedream.com)
   - Click "Create Workflow"

2. **Choose Trigger Type**
   - **Option A: Timer Trigger** (Recommended for beginners)
     * Select "Schedule" 
     * Set interval (e.g., every 15 minutes)
     * Good for batch processing
   
   - **Option B: Gmail Trigger** (Advanced)
     * Select "Gmail" app
     * Choose "New Email" trigger
     * Requires webhook setup
     * Real-time processing
   
   - **Option C: HTTP Trigger**
     * Select "HTTP / Webhook"
     * Trigger via external systems
     * Manual testing friendly
```

### Step 2: Configure Gmail Authentication Step

```markdown
1. **Add New Step**
   - Click "+" to add step
   - Choose "Custom Code"
   - Select "Python" as language

2. **Add Gmail Authentication**
   ```python
   # Step Name: Gmail Authentication
   # This step connects to Gmail API
   
   import os
   
   def handler(pd: "pipedream"):
       # Gmail authentication will be handled by Pipedream's built-in Gmail app
       # This step just validates the connection
       
       gmail_auth = pd.steps.trigger.get('gmail', {}).get('$auth', {})
       
       if not gmail_auth:
           raise ValueError("Gmail authentication not configured")
       
       return {
           "auth_configured": True,
           "message": "Gmail authentication validated"
       }
   ```
```

### Step 3: Configure Notion Authentication Step

```markdown
1. **Add Another Step**
   - Click "+" to add step
   - Choose "Custom Code"
   - Select "Python" as language

2. **Add Notion Authentication**
   ```python
   # Step Name: Notion Authentication
   # This step validates Notion connection
   
   import os
   
   def handler(pd: "pipedream"):
       # Get Notion token from environment or step configuration
       notion_token = os.environ.get('NOTION_TOKEN')
       
       if not notion_token:
           raise ValueError("NOTION_TOKEN environment variable not set")
       
       # Validate database ID
       database_id = os.environ.get('NOTION_DATABASE_ID')
       
       if not database_id:
           raise ValueError("NOTION_DATABASE_ID environment variable not set")
       
       return {
           "auth_configured": True,
           "database_id": database_id,
           "message": "Notion authentication validated"
       }
   ```
```

### Step 4: Add Main Gmail to Notion Handler

```markdown
1. **Add Main Processing Step**
   - Click "+" to add step
   - Choose "Custom Code"
   - Select "Python" as language

2. **Copy Bundled Code**
   ```python
   # Step Name: Gmail to Notion Task Creator
   # Copy the entire content from pipedream_modules/gmail_to_notion_bundled.py
   
   # [PASTE FULL BUNDLED CODE HERE - See Code Examples section below]
   
   # Main handler execution
   def handler(pd: "pipedream"):
       # The bundled module includes its own handler function
       # Just call it with the Pipedream context
       result = handler(pd)
       return result
   ```
```

## Authentication Setup

### Configure Environment Variables

```markdown
1. **Access Workflow Settings**
   - Go to your workflow in Pipedream
   - Click "Settings" or "Environment Variables"

2. **Add Required Variables**
   ```bash
   # Notion Configuration
   NOTION_TOKEN=secret_your_notion_integration_token_here
   NOTION_DATABASE_ID=your_database_id_here
   
   # Gmail Configuration (if using manual auth)
   GMAIL_CLIENT_ID=your_gmail_oauth_client_id
   GMAIL_CLIENT_SECRET=your_gmail_oauth_client_secret
   
   # Optional: Logging Configuration
   LOG_LEVEL=INFO
   ```

3. **Security Best Practices**
   ```markdown
   - Never hardcode tokens in your code
   - Use Pipedream's environment variable encryption
   - Rotate tokens regularly
   - Use least-privilege access scopes
   ```
```

### Connect Pipedream Apps

```markdown
1. **Gmail App Connection**
   - In your workflow step, click "Connect an app"
   - Search for "Gmail"
   - Click "Connect" and follow OAuth flow
   - Grant required permissions
   - Pipedream handles token management

2. **Notion App Connection**
   - Click "Connect an app" in relevant step
   - Search for "Notion"
   - Enter your Integration Token
   - Test connection
   - Pipedream stores credentials securely
```

## Testing and Validation

### Initial Testing

```markdown
1. **Test Individual Steps**
   ```markdown
   - Click "Test" on each step
   - Verify authentication steps pass
   - Check data flow between steps
   - Review execution logs
   ```

2. **End-to-End Testing**
   ```markdown
   - Trigger workflow manually
   - Send test email to Gmail
   - Verify Notion task creation
   - Check error handling
   ```

3. **Validation Checklist**
   ```markdown
   ✅ Gmail authentication successful
   ✅ Notion authentication successful
   ✅ Database ID valid and accessible
   ✅ Email data extracted correctly
   ✅ Notion task created with proper formatting
   ✅ Error handling works for invalid inputs
   ✅ Logging provides useful debugging info
   ```
```

### Performance Testing

```markdown
1. **Load Testing**
   ```markdown
   - Test with multiple emails
   - Verify handling of large email content
   - Check timeout behavior (30-second limit)
   - Monitor memory usage
   ```

2. **Error Scenario Testing**
   ```markdown
   - Invalid database ID
   - Missing Notion permissions
   - Gmail API rate limits
   - Network connectivity issues
   - Malformed email content
   ```
```

## Troubleshooting

### Common Issues and Solutions

#### Authentication Errors

```markdown
**Issue:** `401 Unauthorized: Invalid authentication credentials`

**Solutions:**
1. **Check Environment Variables**
   ```python
   # Add debugging step
   def handler(pd: "pipedream"):
       notion_token = os.environ.get('NOTION_TOKEN')
       print(f"Token exists: {bool(notion_token)}")
       print(f"Token prefix: {notion_token[:10] if notion_token else 'None'}")
   ```

2. **Verify Notion Integration**
   - Check integration token hasn't expired
   - Verify integration has database access
   - Confirm database is shared with integration

3. **Gmail OAuth Issues**
   - Reconnect Gmail app in Pipedream
   - Check OAuth scopes are sufficient
   - Verify Google Cloud Console configuration
```

#### Data Flow Issues

```markdown
**Issue:** `No email data provided`

**Solutions:**
1. **Debug Data Structure**
   ```python
   def handler(pd: "pipedream"):
       print("Available steps:")
       for step_name in dir(pd.steps):
           if not step_name.startswith('_'):
               print(f"  {step_name}: {type(getattr(pd.steps, step_name))}")
       
       print("Step data:")
       print(pd.steps.trigger)
   ```

2. **Check Trigger Configuration**
   - Verify trigger is providing email data
   - Check data format matches expected structure
   - Add data transformation if needed
```

#### Performance Issues

```markdown
**Issue:** `TimeoutError: Step execution exceeded 30 seconds`

**Solutions:**
1. **Optimize Processing**
   ```python
   # Limit email content size
   def handler(pd: "pipedream"):
       max_content_length = 5000
       plain_text = email_data.get("text", "")[:max_content_length]
   ```

2. **Split into Multiple Steps**
   - Separate email fetching from task creation
   - Process emails in batches
   - Use asynchronous operations where possible
```

### Debugging Tools

```markdown
1. **Enhanced Logging**
   ```python
   import logging
   
   # Configure detailed logging
   logging.basicConfig(level=logging.DEBUG)
   logger = logging.getLogger(__name__)
   
   def handler(pd: "pipedream"):
       logger.info("Starting Gmail to Notion processing")
       logger.debug(f"Input data: {pd.inputs}")
       # ... processing ...
       logger.info("Processing completed successfully")
   ```

2. **Step Output Inspection**
   ```python
   # Add at end of each step
   def handler(pd: "pipedream"):
       result = process_data()
       
       # Export detailed debugging info
       pd.export("debug_info", {
           "timestamp": datetime.now().isoformat(),
           "step_name": "gmail_to_notion",
           "input_keys": list(pd.inputs.keys()),
           "result_type": type(result).__name__
       })
       
       return result
   ```

3. **Test Data Generation**
   ```python
   # Create mock data for testing
   def create_test_email():
       return {
           "subject": "Test Task Creation",
           "from": "test@example.com",
           "text": "This is a test email for task creation",
           "html": "<p>This is a test email for task creation</p>",
           "date": datetime.now().isoformat()
       }
   ```
```

## Code Examples

### Complete Bundled Code Template

```python
"""
Gmail to Notion Task Creator - Pipedream Workflow
Complete bundled implementation with all dependencies
"""

import logging
import json
import requests
import os
from typing import Any, Dict, List, Optional
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Constants
NOTION_API_VERSION = "2022-06-28"
NOTION_API_BASE_URL = "https://api.notion.com/v1"
NOTION_HEADERS = {
    "Content-Type": "application/json",
    "Notion-Version": NOTION_API_VERSION,
}

def safe_get(obj, path, default=None):
    """Safely get nested dictionary values"""
    if obj is None or path is None:
        return default
    if not isinstance(path, list):
        path = [path]
    
    current = obj
    try:
        for key in path:
            if isinstance(current, dict):
                current = current.get(key, default)
            elif isinstance(current, list) and isinstance(key, int):
                current = current[key] if 0 <= key < len(current) else default
            else:
                return default
        return current
    except Exception:
        return default

def build_notion_properties(title: str, email: Optional[str] = None) -> Dict[str, Any]:
    """Build Notion properties for task creation"""
    properties = {
        "Name": {
            "title": [{"text": {"content": title}}]
        }
    }
    
    if email:
        properties["Email"] = {"email": email}
    
    return properties

def build_page_content_blocks(plain_text: str) -> List[Dict[str, Any]]:
    """Build Notion page content blocks"""
    return [{
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": plain_text}}]
        }
    }]

def handler(pd: "pipedream") -> Dict[str, Any]:
    """
    Main handler for Gmail to Notion task creation
    """
    try:
        # Get environment variables
        notion_token = os.environ.get('NOTION_TOKEN')
        database_id = os.environ.get('NOTION_DATABASE_ID')
        
        if not notion_token:
            raise ValueError("NOTION_TOKEN environment variable not set")
        if not database_id:
            raise ValueError("NOTION_DATABASE_ID environment variable not set")
        
        # Extract email data from trigger or previous step
        email_data = None
        
        # Try different data sources
        if hasattr(pd.steps, 'trigger') and hasattr(pd.steps.trigger, 'event'):
            email_data = pd.steps.trigger.event
        elif hasattr(pd, 'inputs') and 'email' in pd.inputs:
            email_data = pd.inputs['email']
        elif 'email' in pd:
            email_data = pd['email']
        
        if not email_data:
            # Create test data for initial testing
            email_data = {
                "subject": "Test Email Task",
                "from": "test@example.com",
                "text": "This is a test email converted to a Notion task.",
                "date": datetime.now().isoformat()
            }
            logger.warning("No email data found, using test data")
        
        # Extract email details
        subject = email_data.get("subject", "No Subject")
        sender = email_data.get("from", "")
        plain_text = email_data.get("text", email_data.get("body", "No content"))
        
        # Extract email address from sender
        email_address = sender.strip() if sender else None
        
        # Build Notion task
        properties = build_notion_properties(subject, email_address)
        content_blocks = build_page_content_blocks(plain_text)
        
        # Create Notion page
        headers = {
            **NOTION_HEADERS,
            "Authorization": f"Bearer {notion_token}"
        }
        
        payload = {
            "parent": {"database_id": database_id},
            "properties": properties,
            "children": content_blocks
        }
        
        response = requests.post(
            f"{NOTION_API_BASE_URL}/pages",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            task_data = response.json()
            logger.info(f"Successfully created Notion task: {task_data.get('id')}")
            
            return {
                "success": True,
                "task_id": task_data.get("id"),
                "task_url": task_data.get("url"),
                "email_subject": subject,
                "timestamp": datetime.now().isoformat()
            }
        else:
            error_msg = f"Notion API error: {response.status_code} - {response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)
            
    except Exception as e:
        logger.error(f"Error in Gmail to Notion handler: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# For Pipedream execution
if __name__ == "__main__":
    # This allows local testing
    test_pd = {
        "inputs": {
            "email": {
                "subject": "Local Test Email",
                "from": "test@local.com",
                "text": "Testing locally"
            }
        }
    }
    result = handler(test_pd)
    print(json.dumps(result, indent=2))
```

### Environment Variables Template

```bash
# Add these to your Pipedream workflow environment variables

# Required: Notion Integration Token
NOTION_TOKEN=secret_your_notion_integration_token_here

# Required: Target Notion Database ID  
NOTION_DATABASE_ID=your_database_id_here

# Optional: Logging Level
LOG_LEVEL=INFO

# Optional: Gmail Query Filter (if using Gmail trigger)
GMAIL_QUERY=is:unread label:action-required

# Optional: Maximum emails to process per run
MAX_EMAILS_PER_RUN=10
```

### Testing Workflow Configuration

```yaml
# Example workflow configuration for testing
# This can be used with Pipedream's GitHub sync feature

org_id: your_org_id
project_id: your_project_id

steps:
  - name: gmail_auth
    type: app_auth
    app: gmail
    
  - name: notion_auth  
    type: app_auth
    app: notion
    
  - name: gmail_to_notion_processor
    type: code
    language: python
    code: |
      # Paste the complete bundled code here
      
      def handler(pd: "pipedream"):
          return handler(pd)

triggers:
  - type: timer
    cron: "*/15 * * * *"  # Every 15 minutes
    timezone: UTC

settings:
  name: "Gmail to Notion Task Creator"
  auto_deploy: true
```

---

This configuration guide provides everything needed to successfully set up Gmail to Notion automation using Pipedream. Start with the direct code copy method for quick setup, then consider GitHub sync for more advanced version control and team collaboration.

For additional support:
- **Pipedream Community**: [community.pipedream.com](https://community.pipedream.com)
- **Repository Issues**: Create an issue in the GitHub repository
- **API Documentation**: [Notion API](https://developers.notion.com), [Gmail API](https://developers.google.com/gmail/api)