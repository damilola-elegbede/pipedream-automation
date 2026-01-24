"""
Analyze Email with Claude

Extracts structured information from email content using Claude AI.
Returns JSON with summary, action items, key dates, links, contacts,
urgency, and category.

Usage: Import and call analyze_email() from create_notion_task.py
"""
import json
import requests

# Import shared retry utility - handles both Pipedream and test environments
try:
    from utils.retry import retry_with_backoff
except ImportError:
    from steps.utils.retry import retry_with_backoff


# --- Configuration ---
CLAUDE_MODEL = "claude-sonnet-4-20250514"
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


def call_claude(prompt, anthropic_key, max_tokens=2048):
    """
    Call Claude API with the given prompt.

    Args:
        prompt: The prompt to send to Claude
        anthropic_key: Anthropic API key
        max_tokens: Maximum tokens in response

    Returns the response text or raises an exception.
    """
    headers = {
        "x-api-key": anthropic_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    response = retry_with_backoff(
        lambda: requests.post(ANTHROPIC_API_URL, headers=headers, json=payload, timeout=60)
    )

    data = response.json()
    content = data.get("content", [])
    if content and len(content) > 0:
        # Concatenate all text blocks (API may return multiple content blocks)
        return "".join(part.get("text", "") for part in content if part.get("type") == "text")
    raise ValueError("Unexpected Claude response format: missing text content block(s)")


def parse_claude_response(response_text):
    """
    Parse Claude's JSON response, handling potential formatting issues.

    Args:
        response_text: Raw response text from Claude

    Returns:
        Parsed dict with analysis results, or empty defaults on failure
    """
    default_result = {
        "summary": "",
        "action_items": [],
        "key_dates": [],
        "important_links": [],
        "key_contacts": [],
        "urgency": "medium",
        "category": "other"
    }

    try:
        # Find JSON object in response (Claude may include markdown formatting)
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1

        if start_idx == -1 or end_idx == 0:
            print("    Warning: No JSON object found in Claude response")
            return default_result

        json_str = response_text[start_idx:end_idx]
        result = json.loads(json_str)

        # Validate and normalize fields
        validated = {}
        validated["summary"] = str(result.get("summary", ""))[:2000]

        # Action items - ensure list of strings
        action_items = result.get("action_items", [])
        if isinstance(action_items, list):
            validated["action_items"] = [str(item)[:500] for item in action_items[:10]]
        else:
            validated["action_items"] = []

        # Key dates - ensure list of dicts with date and context
        key_dates = result.get("key_dates", [])
        if isinstance(key_dates, list):
            validated["key_dates"] = []
            for item in key_dates[:10]:
                if isinstance(item, dict):
                    validated["key_dates"].append({
                        "date": str(item.get("date", ""))[:50],
                        "context": str(item.get("context", ""))[:200]
                    })
        else:
            validated["key_dates"] = []

        # Important links - ensure list of dicts with url and description
        links = result.get("important_links", [])
        if isinstance(links, list):
            validated["important_links"] = []
            for item in links[:10]:
                if isinstance(item, dict):
                    validated["important_links"].append({
                        "url": str(item.get("url", ""))[:500],
                        "description": str(item.get("description", ""))[:200]
                    })
        else:
            validated["important_links"] = []

        # Key contacts - ensure list of dicts with name, email, role
        contacts = result.get("key_contacts", [])
        if isinstance(contacts, list):
            validated["key_contacts"] = []
            for item in contacts[:10]:
                if isinstance(item, dict):
                    validated["key_contacts"].append({
                        "name": str(item.get("name", ""))[:100],
                        "email": str(item.get("email", ""))[:200],
                        "role": str(item.get("role", ""))[:100]
                    })
        else:
            validated["key_contacts"] = []

        # Urgency - normalize to allowed values
        urgency = str(result.get("urgency", "medium")).lower()
        if urgency not in ("high", "medium", "low"):
            urgency = "medium"
        validated["urgency"] = urgency

        # Category - normalize to allowed values
        category = str(result.get("category", "other")).lower()
        allowed_categories = ("meeting", "request", "info", "followup", "approval", "other")
        if category not in allowed_categories:
            category = "other"
        validated["category"] = category

        return validated

    except json.JSONDecodeError as e:
        print(f"    Warning: Failed to parse Claude JSON response: {e}")
        return default_result
    except Exception as e:
        print(f"    Warning: Error processing Claude response: {e}")
        return default_result


def analyze_email(subject, sender, date, body, anthropic_key):
    """
    Analyze an email using Claude and extract structured information.

    Args:
        subject: Email subject line
        sender: Email sender
        date: Email date
        body: Plain text email body
        anthropic_key: Anthropic API key

    Returns:
        Dict with analysis results:
        {
            "summary": "Brief 2-3 sentence summary",
            "action_items": ["Task 1", "Task 2"],
            "key_dates": [{"date": "2024-01-15", "context": "Meeting deadline"}],
            "important_links": [{"url": "...", "description": "..."}],
            "key_contacts": [{"name": "...", "email": "...", "role": "..."}],
            "urgency": "high|medium|low",
            "category": "meeting|request|info|followup|approval|other"
        }

    Returns empty/default values on API failure (fallback behavior).
    """
    if not anthropic_key:
        print("    Warning: ANTHROPIC_API_KEY not provided. Skipping email analysis.")
        return None

    # Truncate body if too long to keep costs reasonable
    max_body_length = 10000
    truncated_body = body[:max_body_length] if body else ""
    if body and len(body) > max_body_length:
        truncated_body += "\n\n[Email truncated for analysis]"

    prompt = f"""Analyze this email and extract structured information for task management.

Subject: {subject}
From: {sender}
Date: {date}
Body:
{truncated_body}

Return a JSON object with these fields:
- summary: 2-3 sentence summary of the email's main point and any required action
- action_items: array of specific tasks/actions required (empty array if none)
- key_dates: array of objects with "date" (ISO format or descriptive) and "context" fields
- important_links: array of objects with "url" and "description" fields
- key_contacts: array of objects with "name", "email", and "role" (e.g., "Requestor", "Stakeholder") fields
- urgency: "high", "medium", or "low" based on time sensitivity and importance
- category: one of "meeting", "request", "info", "followup", "approval", or "other"

Rules:
- Be concise but complete in the summary
- Only include action items that are explicitly requested or clearly implied
- Extract ALL dates mentioned, with context about what they refer to
- Include all URLs/links found in the email
- For contacts, include anyone mentioned who might be relevant to the task
- Base urgency on deadlines, language ("urgent", "ASAP"), and business impact
- Choose the category that best fits the email's primary purpose

Return ONLY the JSON object, no other text."""

    try:
        print("    Calling Claude to analyze email...")
        response = call_claude(prompt, anthropic_key)
        result = parse_claude_response(response)
        print(f"    Analysis complete. Summary length: {len(result['summary'])} chars, "
              f"{len(result['action_items'])} action items, urgency: {result['urgency']}")
        return result
    except Exception as e:
        print(f"    Error calling Claude API: {e}")
        return None
