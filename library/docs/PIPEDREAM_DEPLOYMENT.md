# Pipedream Deployment Guide

This guide walks you through deploying the automation integrations to Pipedream, a serverless integration platform that enables you to connect APIs and automate workflows.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Deployment Steps](#deployment-steps)
- [Workflow Configuration](#workflow-configuration)
- [Monitoring & Debugging](#monitoring--debugging)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

This repository contains several automation integrations designed to run on Pipedream:

### Available Integrations

1. **Gmail → Notion Task Creator**: Automatically creates Notion tasks from Gmail emails
2. **Notion ↔ Google Calendar Sync**: Bidirectional synchronization between Notion tasks and Google Calendar events
3. **AI Content Processor**: Processes and enriches content using AI services
4. **Email Fetcher**: Advanced Gmail email fetching with filtering
5. **Task Management**: Comprehensive task lifecycle management

### Key Features

- **Robust retry logic** with exponential backoff
- **Structured logging** for easy debugging
- **Error enrichment** with user-friendly messages
- **Request correlation** across function calls
- **Service-specific optimizations** for different APIs

## Prerequisites

### 1. Pipedream Account
- Sign up at [pipedream.com](https://pipedream.com)
- Verify your email and complete account setup

### 2. API Access & Authentication

You'll need API credentials for the services you want to integrate:

#### Gmail Integration
- Google Cloud Project with Gmail API enabled
- OAuth 2.0 credentials or service account
- Required scopes: `https://www.googleapis.com/auth/gmail.modify`

#### Notion Integration
- Notion integration with appropriate permissions
- Integration token (starts with `secret_`)
- Database IDs for target databases

#### Google Calendar Integration
- Google Cloud Project with Calendar API enabled
- OAuth 2.0 credentials
- Required scopes: `https://www.googleapis.com/auth/calendar`

#### OpenAI Integration (for AI features)
- OpenAI API key
- Appropriate usage limits and billing setup

### 3. Development Tools
- Git for version control
- Python 3.8+ for local testing
- Code editor (VS Code recommended)

## Deployment Steps

### Step 1: Create a New Workflow

1. Log into your Pipedream dashboard
2. Click "Create Workflow"
3. Choose your trigger source (Gmail, HTTP webhook, Schedule, etc.)

### Step 2: Add Integration Steps

For each integration module, create a new step:

1. Click "+" to add a new step
2. Choose "Custom Code" or "Python"
3. Copy the integration code from the respective module
4. Configure the step name and description

#### Example: Gmail → Notion Integration

```python
# Step 1: Gmail Trigger (built-in Pipedream component)
# Configure Gmail trigger to watch for new emails

# Step 2: Fetch Email Details
def handler(pd: "pipedream"):
    # Copy code from src/integrations/gmail_notion/fetch_emails.py
    from src.integrations.gmail_notion.fetch_emails import handler
    return handler(pd)

# Step 3: Create Notion Task
def handler(pd: "pipedream"):
    # Copy code from src/integrations/gmail_notion/create_notion_task.py
    from src.integrations.gmail_notion.create_notion_task import handler
    return handler(pd)

# Step 4: Label Processed Email
def handler(pd: "pipedream"):
    # Copy code from src/integrations.gmail_notion.label_processed import handler
    from src.integrations.gmail_notion.label_processed import handler
    return handler(pd)
```

### Step 3: Configure Environment Variables

In your workflow settings, add the following environment variables:

```bash
# Notion Configuration
NOTION_TOKEN=secret_your_notion_integration_token
NOTION_DATABASE_ID=your_database_id

# Gmail Configuration
GMAIL_CLIENT_ID=your_gmail_client_id
GMAIL_CLIENT_SECRET=your_gmail_client_secret
GMAIL_REFRESH_TOKEN=your_refresh_token

# Google Calendar Configuration
GCAL_CLIENT_ID=your_calendar_client_id
GCAL_CLIENT_SECRET=your_calendar_client_secret
GCAL_REFRESH_TOKEN=your_calendar_refresh_token

# OpenAI Configuration (if using AI features)
OPENAI_API_KEY=your_openai_api_key

# Optional: Logging Configuration
LOG_LEVEL=INFO
ENABLE_DEBUG_LOGGING=false
```

### Step 4: Deploy Utility Dependencies

Since Pipedream runs in a serverless environment, you need to include the utility modules in each step:

#### Option A: Inline Dependencies (Recommended for small utilities)

Copy the utility code directly into your step:

```python
def handler(pd: "pipedream"):
    # Inline retry manager utility
    import time
    import random
    from functools import wraps
    
    def with_retry(service='default', max_retries=3):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                for attempt in range(max_retries):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        if attempt == max_retries - 1:
                            raise
                        delay = (2 ** attempt) + random.uniform(0, 1)
                        time.sleep(delay)
            return wrapper
        return decorator
    
    # Your integration code here
    @with_retry(service='notion')
    def create_notion_task():
        # Implementation
        pass
```

#### Option B: Package Dependencies (For complex utilities)

Create a custom npm package or use Pipedream's file system:

```python
# At the top of your step
import sys
sys.path.append('/opt/pipedream/src')

# Import your utilities
from utils.retry_manager import with_retry
from utils.error_enrichment import enrich_error
from utils.structured_logger import get_pipedream_logger
```

### Step 5: Test Your Workflow

1. Click "Test" in the Pipedream workflow editor
2. Provide sample input data
3. Check the execution logs for errors
4. Verify the output matches expectations

## Workflow Configuration

### Gmail → Notion Task Creator

#### Trigger Configuration
```yaml
trigger:
  type: gmail
  events: ["new_email"]
  filters:
    - label: "inbox"
    - is_unread: true
```

#### Step Configuration
```python
# Step 1: Email Processing
def handler(pd: "pipedream"):
    from src.utils.structured_logger import get_pipedream_logger
    
    logger = get_pipedream_logger('gmail_notion_processor')
    
    with logger.request_context() as request_id:
        logger.info("Processing email", email_id=pd.steps.trigger.event.id)
        
        # Process email content
        email_data = {
            'subject': pd.steps.trigger.event.payload.subject,
            'body': pd.steps.trigger.event.payload.body,
            'from': pd.steps.trigger.event.payload.from_email,
            'date': pd.steps.trigger.event.payload.date
        }
        
        return {'email': email_data, 'request_id': request_id}
```

### Notion ↔ Google Calendar Sync

#### Bidirectional Sync Configuration
```python
# Notion → Calendar (triggered by Notion changes)
def handler(pd: "pipedream"):
    notion_data = pd.steps.trigger.event.payload
    
    if notion_data.get('type') == 'page_update':
        # Process task updates
        from src.integrations.notion_gcal.task_to_event import handler
        return handler(pd)

# Calendar → Notion (triggered by Calendar changes)  
def handler(pd: "pipedream"):
    calendar_data = pd.steps.trigger.event.payload
    
    if calendar_data.get('type') == 'event_update':
        # Process calendar updates
        from src.integrations.notion_gcal.calendar_to_notion import handler
        return handler(pd)
```

## Monitoring & Debugging

### Structured Logging

All integrations use structured JSON logging for easy monitoring:

```python
# Example log output
{
  "level": "INFO",
  "message": "API call to notion",
  "timestamp": "2024-01-01T10:00:00Z",
  "request_id": "req_123456",
  "service": "notion",
  "endpoint": "/v1/pages",
  "method": "POST",
  "duration_seconds": 0.245
}
```

### Error Tracking

Errors are enriched with context and user-friendly messages:

```python
# Example error log
{
  "level": "ERROR", 
  "message": "Notion API error",
  "error_type": "NotionAPIError",
  "user_message": "Database not found. Please check your database ID.",
  "technical_details": "404 Not Found: database_id abc123 not found",
  "request_id": "req_123456",
  "service": "notion"
}
```

### Monitoring Dashboard

Monitor your workflows using:

1. **Pipedream Dashboard**: Built-in execution logs and metrics
2. **External Logging**: Ship logs to services like Datadog, New Relic
3. **Custom Alerts**: Set up notifications for failures

## Best Practices

### 1. Error Handling

Always wrap API calls with proper error handling:

```python
def handler(pd: "pipedream"):
    from src.utils.retry_manager import with_retry
    from src.utils.error_enrichment import enrich_error
    
    @with_retry(service='notion', max_retries=5)
    def create_notion_page(data):
        try:
            response = requests.post(url, json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            enriched = enrich_error(e, 'notion', {'operation': 'create_page'})
            pd.flow.exit(enriched.user_message)
```

### 2. Request Correlation

Use request IDs to track operations across steps:

```python
def handler(pd: "pipedream"):
    from src.utils.structured_logger import get_pipedream_logger
    
    logger = get_pipedream_logger('workflow_name')
    
    # Get request ID from previous step or create new one
    request_id = pd.steps.previous_step.get('request_id') or str(uuid.uuid4())
    
    with logger.request_context(request_id=request_id):
        # All operations in this context are correlated
        result = process_data()
        return {'result': result, 'request_id': request_id}
```

### 3. Resource Management

Be mindful of Pipedream's resource limits:

- **Execution time**: 30 seconds per step
- **Memory**: 256MB per step  
- **Network requests**: Rate limited by destination service
- **Storage**: Temporary files only

### 4. Security

- Store sensitive data in environment variables
- Use Pipedream's built-in secret management
- Validate all input data
- Never log sensitive information

```python
def handler(pd: "pipedream"):
    # ✅ Good: Use environment variables
    api_key = os.environ.get('NOTION_TOKEN')
    
    # ❌ Bad: Hard-coded secrets
    api_key = "secret_abc123"
    
    # ✅ Good: Validate inputs
    if not pd.steps.trigger.event.get('subject'):
        pd.flow.exit("Missing required field: subject")
```

## Troubleshooting

### Common Issues

#### 1. Import Errors
```
ModuleNotFoundError: No module named 'src.utils'
```

**Solution**: Use inline code or verify file structure:
```python
# Inline the required utilities instead of importing
# Or use absolute imports with sys.path
```

#### 2. Timeout Errors
```
TimeoutError: Step execution exceeded 30 seconds
```

**Solution**: Optimize your code or split into multiple steps:
```python
# Break large operations into smaller steps
# Use async operations where possible
# Implement pagination for large datasets
```

#### 3. Authentication Failures
```
401 Unauthorized: Invalid authentication credentials
```

**Solution**: Verify your environment variables and credentials:
```python
# Check environment variables are set
assert os.environ.get('NOTION_TOKEN'), "NOTION_TOKEN not set"

# Test authentication separately
def test_auth():
    response = requests.get(auth_test_endpoint, headers=headers)
    assert response.status_code == 200, f"Auth failed: {response.text}"
```

#### 4. Rate Limiting
```
429 Too Many Requests: Rate limit exceeded
```

**Solution**: The retry manager handles this automatically:
```python
# The retry manager includes exponential backoff
@with_retry(service='notion', max_retries=5)
def api_call():
    # Automatically retries with backoff on 429 errors
    pass
```

### Debugging Tips

1. **Use structured logging**: Enable debug logging to see detailed execution flow
2. **Test locally first**: Run integration code locally before deploying
3. **Start simple**: Begin with basic functionality and add features incrementally
4. **Monitor step outputs**: Check the data flow between steps
5. **Use Pipedream's testing tools**: Test individual steps with sample data

### Getting Help

- **Pipedream Community**: [community.pipedream.com](https://community.pipedream.com)
- **Pipedream Docs**: [docs.pipedream.com](https://docs.pipedream.com)
- **Integration Issues**: Create an issue in this repository
- **API Documentation**: Refer to service-specific API docs (Notion, Gmail, etc.)

## Performance Optimization

### 1. Minimize Cold Starts
- Keep step code concise
- Avoid unnecessary imports
- Cache authentication tokens

### 2. Batch Operations
```python
# ✅ Good: Batch API calls
def process_multiple_items(items):
    # Process items in batches of 10
    for batch in chunks(items, 10):
        process_batch(batch)

# ❌ Bad: Individual API calls
def process_items_individually(items):
    for item in items:
        process_single_item(item)  # Makes N API calls
```

### 3. Efficient Data Transfer
```python
# ✅ Good: Pass only necessary data between steps
return {
    'task_id': result.get('id'),
    'status': 'completed',
    'url': result.get('url')
}

# ❌ Bad: Pass entire response objects
return {
    'full_response': response.json(),  # May be very large
    'metadata': additional_data        # Unnecessary data
}
```

This deployment guide provides everything needed to successfully deploy and monitor your Pipedream automation integrations. Start with simple workflows and gradually add complexity as you become more familiar with the platform.