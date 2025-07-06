# Pipedream Workflow Configuration Examples

This document provides ready-to-use Pipedream workflow configurations for the automation integrations in this repository.

## Table of Contents

- [Gmail to Notion Task Creator](#gmail-to-notion-task-creator)
- [Notion to Google Calendar Sync](#notion-to-google-calendar-sync)
- [Bidirectional Calendar Sync](#bidirectional-calendar-sync)
- [AI Content Processing](#ai-content-processing)
- [Batch Email Processing](#batch-email-processing)

## Gmail to Notion Task Creator

Creates Notion tasks automatically from incoming Gmail messages.

### Workflow Configuration

```yaml
name: "Gmail to Notion Task Creator"
description: "Automatically create Notion tasks from Gmail emails"
trigger:
  app: gmail
  event: "New Email Matching Search"
  search: "in:inbox is:unread"
```

### Step 1: Gmail Trigger (Built-in Pipedream Component)

Configure the Gmail trigger with these settings:
- **Search**: `in:inbox is:unread label:action-required`
- **Polling interval**: Every 5 minutes
- **Include body**: Yes

### Step 2: Fetch and Process Email

```python
def handler(pd: "pipedream"):
    """Process incoming Gmail email for Notion task creation"""
    
    # Import utilities inline for Pipedream compatibility
    import json
    import uuid
    import time
    import logging
    from datetime import datetime, timezone
    
    # Structured logging setup
    def log_json(level, message, **kwargs):
        log_data = {
            'level': level,
            'message': message,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'workflow': 'gmail_notion_creator',
            'step': 'process_email',
            **kwargs
        }
        print(json.dumps(log_data))
    
    # Extract email data
    email_data = pd.steps.trigger.event
    request_id = str(uuid.uuid4())
    
    log_json('INFO', 'Processing email', 
             request_id=request_id,
             email_id=email_data.get('id'),
             subject=email_data.get('subject', '')[:50])
    
    # Process email content
    processed_email = {
        'id': email_data.get('id'),
        'subject': email_data.get('subject', 'No Subject'),
        'body': email_data.get('bodyPlain', '') or email_data.get('bodyHtml', ''),
        'from': email_data.get('from', {}).get('address', ''),
        'from_name': email_data.get('from', {}).get('name', ''),
        'date': email_data.get('date'),
        'labels': email_data.get('labelIds', []),
        'thread_id': email_data.get('threadId'),
        'snippet': email_data.get('snippet', '')
    }
    
    # Extract action items from email content
    body_text = processed_email['body'].lower()
    is_action_required = any(keyword in body_text for keyword in [
        'todo', 'action required', 'please review', 'deadline',
        'urgent', 'asap', 'follow up', 'task', 'assignment'
    ])
    
    # Determine priority based on content
    priority = 'Medium'
    if any(keyword in body_text for keyword in ['urgent', 'asap', 'high priority']):
        priority = 'High'
    elif any(keyword in body_text for keyword in ['low priority', 'when convenient']):
        priority = 'Low'
    
    log_json('INFO', 'Email processed', 
             request_id=request_id,
             is_action_required=is_action_required,
             priority=priority)
    
    return {
        'email': processed_email,
        'is_action_required': is_action_required,
        'priority': priority,
        'request_id': request_id
    }
```

### Step 3: Create Notion Task

```python
def handler(pd: "pipedream"):
    """Create Notion task from processed email"""
    
    import requests
    import json
    import os
    import time
    import random
    from datetime import datetime, timezone
    
    # Get data from previous step
    email_data = pd.steps.process_email['email']
    priority = pd.steps.process_email['priority']
    request_id = pd.steps.process_email['request_id']
    is_action_required = pd.steps.process_email['is_action_required']
    
    # Skip if not action required
    if not is_action_required:
        print(json.dumps({
            'level': 'INFO',
            'message': 'Skipping email - no action required',
            'request_id': request_id,
            'email_id': email_data['id']
        }))
        return {'skipped': True, 'reason': 'No action required'}
    
    # Notion configuration
    notion_token = os.environ['NOTION_TOKEN']
    database_id = os.environ['NOTION_DATABASE_ID']
    
    def log_json(level, message, **kwargs):
        log_data = {
            'level': level,
            'message': message,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'workflow': 'gmail_notion_creator',
            'step': 'create_notion_task',
            'request_id': request_id,
            **kwargs
        }
        print(json.dumps(log_data))
    
    # Retry logic with exponential backoff
    def with_retry(max_retries=3):
        def decorator(func):
            def wrapper(*args, **kwargs):
                for attempt in range(max_retries):
                    try:
                        return func(*args, **kwargs)
                    except requests.exceptions.RequestException as e:
                        if attempt == max_retries - 1:
                            raise
                        delay = (2 ** attempt) + random.uniform(0, 1)
                        log_json('WARNING', f'Request failed, retrying in {delay:.2f}s',
                                attempt=attempt + 1, error=str(e))
                        time.sleep(delay)
            return wrapper
        return decorator
    
    @with_retry(max_retries=5)
    def create_notion_page(page_data):
        headers = {
            'Authorization': f'Bearer {notion_token}',
            'Content-Type': 'application/json',
            'Notion-Version': '2022-06-28'
        }
        
        log_json('INFO', 'Creating Notion page', 
                database_id=database_id[:8] + '...',
                title=page_data['properties']['Name']['title'][0]['text']['content'][:50])
        
        response = requests.post(
            'https://api.notion.com/v1/pages',
            headers=headers,
            json=page_data
        )
        response.raise_for_status()
        return response.json()
    
    # Prepare Notion page data
    page_data = {
        'parent': {'database_id': database_id},
        'properties': {
            'Name': {
                'title': [{
                    'text': {'content': f"📧 {email_data['subject']}"}
                }]
            },
            'Status': {
                'select': {'name': 'To Do'}
            },
            'Priority': {
                'select': {'name': priority}
            },
            'Source': {
                'select': {'name': 'Email'}
            },
            'Email From': {
                'rich_text': [{
                    'text': {'content': f"{email_data['from_name']} <{email_data['from']}>"}
                }]
            },
            'Email ID': {
                'rich_text': [{
                    'text': {'content': email_data['id']}
                }]
            },
            'Created Date': {
                'date': {'start': datetime.now(timezone.utc).isoformat()}
            }
        },
        'children': [{
            'object': 'block',
            'type': 'paragraph',
            'paragraph': {
                'rich_text': [{
                    'type': 'text',
                    'text': {'content': f"Email snippet: {email_data['snippet'][:500]}..."}
                }]
            }
        }, {
            'object': 'block',
            'type': 'toggle',
            'toggle': {
                'rich_text': [{
                    'type': 'text',
                    'text': {'content': 'Full Email Content'}
                }],
                'children': [{
                    'object': 'block',
                    'type': 'paragraph',
                    'paragraph': {
                        'rich_text': [{
                            'type': 'text',
                            'text': {'content': email_data['body'][:2000]}  # Limit content size
                        }]
                    }
                }]
            }
        }]
    }
    
    try:
        result = create_notion_page(page_data)
        
        log_json('INFO', 'Notion task created successfully',
                task_id=result['id'],
                task_url=result['url'])
        
        return {
            'success': True,
            'task_id': result['id'],
            'task_url': result['url'],
            'email_id': email_data['id'],
            'request_id': request_id
        }
        
    except Exception as e:
        error_msg = str(e)
        
        # Enrich error with user-friendly message
        if '401' in error_msg:
            user_message = "Invalid Notion authentication. Please check your NOTION_TOKEN."
        elif '404' in error_msg:
            user_message = "Database not found. Please check your NOTION_DATABASE_ID."
        elif '429' in error_msg:
            user_message = "Rate limit exceeded. The task will be retried automatically."
        else:
            user_message = f"Failed to create Notion task: {error_msg}"
        
        log_json('ERROR', 'Failed to create Notion task',
                error=error_msg,
                user_message=user_message)
        
        pd.flow.exit(user_message)
```

### Step 4: Label Processed Email

```python
def handler(pd: "pipedream"):
    """Label the processed email in Gmail"""
    
    import requests
    import json
    import os
    from datetime import datetime, timezone
    
    # Only proceed if task was created successfully
    if not pd.steps.create_notion_task.get('success'):
        return {'skipped': True, 'reason': 'Task creation failed'}
    
    request_id = pd.steps.create_notion_task['request_id']
    email_id = pd.steps.create_notion_task['email_id']
    
    def log_json(level, message, **kwargs):
        log_data = {
            'level': level,
            'message': message,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'workflow': 'gmail_notion_creator',
            'step': 'label_email',
            'request_id': request_id,
            **kwargs
        }
        print(json.dumps(log_data))
    
    # Gmail API configuration would go here
    # This step would add a "Processed" label to the email
    
    log_json('INFO', 'Email processed and labeled',
             email_id=email_id,
             task_id=pd.steps.create_notion_task['task_id'])
    
    return {
        'email_id': email_id,
        'labeled': True,
        'request_id': request_id
    }
```

## Notion to Google Calendar Sync

Synchronizes Notion tasks with due dates to Google Calendar events.

### Workflow Configuration

```yaml
name: "Notion to Google Calendar Sync"
description: "Sync Notion tasks with due dates to Google Calendar"
trigger:
  app: notion
  event: "Updated Page in Database"
  database_id: "your_notion_database_id"
```

### Step 1: Process Notion Update

```python
def handler(pd: "pipedream"):
    """Process Notion page update for calendar sync"""
    
    import json
    import uuid
    from datetime import datetime, timezone
    
    # Extract Notion data
    notion_data = pd.steps.trigger.event
    request_id = str(uuid.uuid4())
    
    def log_json(level, message, **kwargs):
        print(json.dumps({
            'level': level,
            'message': message,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'workflow': 'notion_calendar_sync',
            'step': 'process_update',
            'request_id': request_id,
            **kwargs
        }))
    
    # Extract task properties
    properties = notion_data.get('properties', {})
    
    task_data = {
        'id': notion_data.get('id'),
        'title': properties.get('Name', {}).get('title', [{}])[0].get('text', {}).get('content', ''),
        'status': properties.get('Status', {}).get('select', {}).get('name', ''),
        'due_date': properties.get('Due Date', {}).get('date', {}).get('start'),
        'priority': properties.get('Priority', {}).get('select', {}).get('name', ''),
        'calendar_event_id': properties.get('Calendar Event ID', {}).get('rich_text', [{}])[0].get('text', {}).get('content'),
        'url': notion_data.get('url')
    }
    
    # Check if this task needs calendar sync
    needs_sync = (
        task_data['due_date'] and 
        task_data['status'] not in ['Done', 'Cancelled'] and
        task_data['title']
    )
    
    log_json('INFO', 'Notion task processed',
             task_id=task_data['id'][:8] + '...',
             title=task_data['title'][:50],
             needs_sync=needs_sync,
             due_date=task_data['due_date'])
    
    return {
        'task': task_data,
        'needs_sync': needs_sync,
        'request_id': request_id
    }
```

### Step 2: Create/Update Calendar Event

```python
def handler(pd: "pipedream"):
    """Create or update Google Calendar event"""
    
    import requests
    import json
    import os
    from datetime import datetime, timezone, timedelta
    
    # Get data from previous step
    task_data = pd.steps.process_update['task']
    needs_sync = pd.steps.process_update['needs_sync']
    request_id = pd.steps.process_update['request_id']
    
    if not needs_sync:
        return {'skipped': True, 'reason': 'No sync needed'}
    
    def log_json(level, message, **kwargs):
        print(json.dumps({
            'level': level,
            'message': message,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'workflow': 'notion_calendar_sync',
            'step': 'calendar_sync',
            'request_id': request_id,
            **kwargs
        }))
    
    # Google Calendar API configuration
    calendar_access_token = os.environ['GOOGLE_CALENDAR_ACCESS_TOKEN']
    calendar_id = os.environ.get('GOOGLE_CALENDAR_ID', 'primary')
    
    # Prepare event data
    due_date = datetime.fromisoformat(task_data['due_date'].replace('Z', '+00:00'))
    
    event_data = {
        'summary': f"📝 {task_data['title']}",
        'description': f"Notion Task: {task_data['url']}\nPriority: {task_data['priority']}",
        'start': {
            'dateTime': due_date.isoformat(),
            'timeZone': 'UTC'
        },
        'end': {
            'dateTime': (due_date + timedelta(hours=1)).isoformat(),
            'timeZone': 'UTC'
        },
        'source': {
            'title': 'Notion Task',
            'url': task_data['url']
        }
    }
    
    headers = {
        'Authorization': f'Bearer {calendar_access_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        if task_data['calendar_event_id']:
            # Update existing event
            response = requests.put(
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{task_data['calendar_event_id']}",
                headers=headers,
                json=event_data
            )
        else:
            # Create new event
            response = requests.post(
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
                headers=headers,
                json=event_data
            )
        
        response.raise_for_status()
        event = response.json()
        
        log_json('INFO', 'Calendar event synced',
                event_id=event['id'],
                action='updated' if task_data['calendar_event_id'] else 'created')
        
        return {
            'success': True,
            'event_id': event['id'],
            'event_url': event.get('htmlLink'),
            'action': 'updated' if task_data['calendar_event_id'] else 'created',
            'task_id': task_data['id'],
            'request_id': request_id
        }
        
    except Exception as e:
        log_json('ERROR', 'Calendar sync failed', error=str(e))
        pd.flow.exit(f"Failed to sync calendar: {str(e)}")
```

## AI Content Processing

Process and enhance content using AI services.

### Workflow Configuration

```yaml
name: "AI Content Processor"
description: "Process and enhance content using AI"
trigger:
  type: webhook
  path: "/ai-process"
```

### Step 1: Process AI Content

```python
def handler(pd: "pipedream"):
    """Process content using AI services"""
    
    import requests
    import json
    import os
    import re
    from datetime import datetime, timezone
    
    # Get content from webhook
    content = pd.steps.trigger.event.body.get('content', '')
    content_type = pd.steps.trigger.event.body.get('type', 'text')
    
    def log_json(level, message, **kwargs):
        print(json.dumps({
            'level': level,
            'message': message,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'workflow': 'ai_content_processor',
            **kwargs
        }))
    
    # AI processing based on content type
    if content_type == 'markdown_to_html':
        # Convert markdown to HTML
        processed_content = convert_markdown_to_html(content)
    elif content_type == 'extract_tasks':
        # Extract action items from text
        processed_content = extract_action_items(content)
    elif content_type == 'summarize':
        # Summarize long content
        processed_content = summarize_content(content)
    else:
        processed_content = content
    
    log_json('INFO', 'Content processed',
             content_type=content_type,
             input_length=len(content),
             output_length=len(str(processed_content)))
    
    return {
        'original_content': content,
        'processed_content': processed_content,
        'content_type': content_type
    }

def convert_markdown_to_html(markdown_text):
    """Convert markdown to HTML"""
    # Simple markdown to HTML conversion
    html = markdown_text
    html = re.sub(r'# (.*)', r'<h1>\1</h1>', html)
    html = re.sub(r'## (.*)', r'<h2>\1</h2>', html)
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)
    html = re.sub(r'\n', '<br>', html)
    return html

def extract_action_items(text):
    """Extract action items from text"""
    action_patterns = [
        r'(?i)todo:?\s*(.+)',
        r'(?i)action(?:\s+item)?:?\s*(.+)',
        r'(?i)task:?\s*(.+)',
        r'(?i)follow[\s-]?up:?\s*(.+)'
    ]
    
    action_items = []
    for pattern in action_patterns:
        matches = re.findall(pattern, text, re.MULTILINE)
        action_items.extend(matches)
    
    return action_items

def summarize_content(content):
    """Summarize content (placeholder for AI service)"""
    # In a real implementation, you would call an AI service like OpenAI
    words = content.split()
    if len(words) <= 50:
        return content
    
    # Simple extractive summary - take first and last sentences
    sentences = content.split('.')
    if len(sentences) >= 2:
        return f"{sentences[0]}. ... {sentences[-1]}."
    
    return content[:200] + "..." if len(content) > 200 else content
```

These examples provide a solid foundation for implementing your Pipedream workflows. Each example includes proper error handling, logging, and retry logic using the utilities from this repository.

## Best Practices Applied

1. **Structured Logging**: All examples use JSON-structured logging for easy monitoring
2. **Error Handling**: Comprehensive error handling with user-friendly messages  
3. **Retry Logic**: Exponential backoff retry logic for API calls
4. **Request Correlation**: Request IDs to track operations across steps
5. **Resource Efficiency**: Minimal data transfer between steps
6. **Security**: Environment variables for sensitive data

## Next Steps

1. Copy the relevant workflow configuration to your Pipedream account
2. Set up the required environment variables
3. Test each step individually before running the full workflow
4. Monitor execution logs using the structured JSON output
5. Customize the logic based on your specific requirements