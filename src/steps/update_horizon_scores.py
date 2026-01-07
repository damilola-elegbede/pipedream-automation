"""
Update Notion Horizon Scores

Scores tasks (0-100) based on alignment with user's "Horizons of Focus"
(Purpose, Values, Vision, Goals, Areas of Focus) using Claude AI.

Usage: Copy-paste into a Pipedream Python step
Required Environment Variables:
  - NOTION_API_TOKEN: Notion internal integration token
  - NOTION_DATABASE_ID: Task database ID
  - NOTION_HORIZONS_PAGE_ID: Horizons of Focus page ID
  - ANTHROPIC_API_KEY: Claude API key
"""
import os
import requests
import time
import json
import random
from concurrent.futures import ThreadPoolExecutor, as_completed


# --- Custom Exceptions ---
class HorizonScoringError(Exception):
    """Raised when horizon scoring fails critically.

    This exception is used to FAIL the Pipedream job loudly instead of
    silently continuing with partial or no results.
    """
    pass


# --- Configuration ---
NOTION_API_VERSION = "2022-06-28"
CLAUDE_MODEL = "claude-opus-4-5-20251101"
BATCH_SIZE = 25  # Increased to reduce number of batches (was 20)
LIST_VALUES = ["Next Actions", "Waiting For", "Someday/Maybe"]

# Parallelization settings - tuned for speed within rate limits
SCORING_WORKERS = 6   # Parallel Claude API calls (was 4)
UPDATE_WORKERS = 8    # Parallel Notion updates (was 5)
FETCH_WORKERS = 3     # Parallel initial data fetches

# --- API Endpoints ---
NOTION_API_BASE = "https://api.notion.com/v1"
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


def retry_with_backoff(request_func, max_retries=5):
    """
    Execute request with exponential backoff for rate limits.

    Handles HTTP 429 (Too Many Requests) and 503 (Service Unavailable) errors
    by waiting and retrying with exponential backoff. Respects Retry-After header.
    """
    for attempt in range(max_retries):
        try:
            response = request_func()
            response.raise_for_status()
            return response
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code in (429, 503) and attempt < max_retries - 1:
                retry_after = e.response.headers.get('Retry-After')
                if retry_after:
                    try:
                        wait = float(retry_after)
                    except ValueError:
                        wait = (2 ** attempt) + random.uniform(0, 1)
                else:
                    wait = (2 ** attempt) + random.uniform(0, 1)
                print(f"Rate limited. Waiting {wait:.1f}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait)
            else:
                raise
    raise Exception(f"Max retries ({max_retries}) exceeded")


def fetch_page_blocks(page_id, headers):
    """
    Recursively fetch all blocks from a Notion page.

    Returns a list of block objects with their content.
    """
    all_blocks = []
    url = f"{NOTION_API_BASE}/blocks/{page_id}/children"
    start_cursor = None

    while True:
        params = {"page_size": 100}
        if start_cursor:
            params["start_cursor"] = start_cursor

        response = retry_with_backoff(
            lambda u=url, p=params: requests.get(u, headers=headers, params=p, timeout=60)
        )
        data = response.json()
        blocks = data.get("results", [])
        all_blocks.extend(blocks)

        # Recursively fetch children for blocks that have them
        for block in blocks:
            if block.get("has_children"):
                block_id = block.get("id")
                child_blocks = fetch_page_blocks(block_id, headers)
                all_blocks.extend(child_blocks)

        if not data.get("has_more"):
            break
        start_cursor = data.get("next_cursor")

    return all_blocks


def find_inline_databases(blocks):
    """
    Find child_database blocks in a list of blocks and return their IDs.

    Args:
        blocks: List of Notion block objects (from fetch_page_blocks)

    Returns:
        List of dicts with 'id' and 'title' for each inline database
    """
    databases = []
    for block in blocks:
        if block.get("type") == "child_database":
            db_info = block.get("child_database", {})
            databases.append({
                "id": block.get("id"),
                "title": db_info.get("title", "Untitled")
            })
    return databases


def fetch_in_progress_goals(database_id, headers):
    """
    Query goals database for In Progress items with Focus Areas and descriptions.

    Args:
        database_id: The Notion database ID
        headers: Notion API headers

    Returns:
        List of goal dicts with name, description, focus_areas, and focus_count,
        sorted by focus_count descending (higher leverage first)
    """
    url = f"{NOTION_API_BASE}/databases/{database_id}/query"

    # Try with Status filter first, fall back to no filter if it fails
    base_payload = {
        "filter": {
            "property": "Status",
            "status": {"equals": "In Progress"}
        }
    }
    use_filter = True

    # Test if filter works
    try:
        test_response = retry_with_backoff(
            lambda: requests.post(url, headers=headers, json=base_payload, timeout=60)
        )
        test_response.json()  # Validate response
    except Exception as e:
        print(f"    Status filter failed ({e}), fetching all goals...")
        use_filter = False

    goals = []
    start_cursor = None

    while True:
        payload = dict(base_payload) if use_filter else {}
        if start_cursor:
            payload["start_cursor"] = start_cursor

        response = retry_with_backoff(
            lambda p=payload: requests.post(url, headers=headers, json=p, timeout=60)
        )
        data = response.json()

        for page in data.get("results", []):
            props = page.get("properties", {})

            # Extract goal title
            title_prop = props.get("Name", {})
            title = ""
            if title_prop.get("type") == "title":
                title = extract_text_from_rich_text(title_prop.get("title", []))

            # Extract goal description (rich_text property)
            description = ""
            desc_prop = props.get("Description", {})
            if desc_prop.get("type") == "rich_text":
                description = extract_text_from_rich_text(desc_prop.get("rich_text", []))
                # Truncate long descriptions to keep prompts manageable
                if len(description) > 500:
                    description = description[:500] + "..."

            # Extract Focus Areas (multi-select)
            focus_areas = []
            focus_prop = props.get("Focus Area", {})
            if focus_prop.get("type") == "multi_select":
                focus_areas = [opt.get("name") for opt in focus_prop.get("multi_select", [])]

            if title:  # Only include goals with titles
                goals.append({
                    "name": title,
                    "description": description,
                    "focus_areas": focus_areas,
                    "focus_count": len(focus_areas)
                })

        if not data.get("has_more"):
            break
        start_cursor = data.get("next_cursor")

    # Sort by focus_count descending (goals touching more areas = higher priority)
    goals.sort(key=lambda g: g["focus_count"], reverse=True)
    return goals


def extract_text_from_rich_text(rich_text_array):
    """Extract plain text from Notion rich_text array."""
    if not rich_text_array:
        return ""
    return "".join(item.get("plain_text", "") for item in rich_text_array)


def fetch_core_values(database_id, headers):
    """
    Query Core Values database and extract values.

    Args:
        database_id: The Notion database ID for Core Values
        headers: Notion API headers

    Returns:
        List of core value names
    """
    url = f"{NOTION_API_BASE}/databases/{database_id}/query"

    response = retry_with_backoff(
        lambda: requests.post(url, headers=headers, json={}, timeout=60)
    )

    values = []
    for page in response.json().get("results", []):
        props = page.get("properties", {})
        # Extract value name (title property)
        name_prop = props.get("Name", {})
        name = ""
        if name_prop.get("type") == "title":
            name = extract_text_from_rich_text(name_prop.get("title", []))
        if name:
            values.append(name)

    return values


def parse_blocks_to_text(blocks):
    """
    Convert Notion blocks to readable text format.

    Preserves structure with headings and content.
    """
    text_parts = []

    for block in blocks:
        block_type = block.get("type")
        block_data = block.get(block_type, {})

        if block_type in ("heading_1", "heading_2", "heading_3"):
            text = extract_text_from_rich_text(block_data.get("rich_text", []))
            prefix = "#" * int(block_type[-1])
            text_parts.append(f"\n{prefix} {text}\n")

        elif block_type == "paragraph":
            text = extract_text_from_rich_text(block_data.get("rich_text", []))
            if text.strip():
                text_parts.append(text)

        elif block_type == "bulleted_list_item":
            text = extract_text_from_rich_text(block_data.get("rich_text", []))
            text_parts.append(f"• {text}")

        elif block_type == "numbered_list_item":
            text = extract_text_from_rich_text(block_data.get("rich_text", []))
            text_parts.append(f"- {text}")

        elif block_type == "to_do":
            text = extract_text_from_rich_text(block_data.get("rich_text", []))
            checked = block_data.get("checked", False)
            checkbox = "[x]" if checked else "[ ]"
            text_parts.append(f"{checkbox} {text}")

        elif block_type == "toggle":
            text = extract_text_from_rich_text(block_data.get("rich_text", []))
            text_parts.append(f"▸ {text}")

        elif block_type == "quote":
            text = extract_text_from_rich_text(block_data.get("rich_text", []))
            text_parts.append(f"> {text}")

        elif block_type == "callout":
            text = extract_text_from_rich_text(block_data.get("rich_text", []))
            icon = block_data.get("icon", {}).get("emoji", "")
            text_parts.append(f"{icon} {text}")

        elif block_type == "divider":
            text_parts.append("\n---\n")

    return "\n".join(text_parts)


def markdown_to_notion_blocks(markdown_text):
    """
    Convert markdown text to Notion block objects.

    Handles headings, bullet lists, numbered lists, and paragraphs.
    """
    blocks = []
    lines = markdown_text.split('\n')

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Headings
        if stripped.startswith('### '):
            blocks.append({
                "type": "heading_3",
                "heading_3": {"rich_text": [{"type": "text", "text": {"content": stripped[4:]}}]}
            })
        elif stripped.startswith('## '):
            blocks.append({
                "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": stripped[3:]}}]}
            })
        elif stripped.startswith('# '):
            blocks.append({
                "type": "heading_1",
                "heading_1": {"rich_text": [{"type": "text", "text": {"content": stripped[2:]}}]}
            })
        # Bullet lists
        elif stripped.startswith('- ') or stripped.startswith('* '):
            blocks.append({
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": stripped[2:]}}]}
            })
        # Numbered lists (1. 2. etc)
        elif len(stripped) > 2 and stripped[0].isdigit() and '. ' in stripped[:4]:
            content = stripped.split('. ', 1)[1] if '. ' in stripped else stripped
            blocks.append({
                "type": "numbered_list_item",
                "numbered_list_item": {"rich_text": [{"type": "text", "text": {"content": content}}]}
            })
        # Bold headers without # (e.g., **Score Range:**)
        elif stripped.startswith('**') and stripped.endswith('**'):
            blocks.append({
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": stripped}, "annotations": {"bold": True}}]}
            })
        # Regular paragraphs
        else:
            blocks.append({
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": stripped}}]}
            })

    return blocks


def save_rubric_to_notion(rubric_text, page_id, headers):
    """
    Clear existing blocks and save new rubric to a Notion page.

    Args:
        rubric_text: The rubric markdown text
        page_id: The Notion page ID to update
        headers: Notion API headers

    Returns:
        True if successful
    """
    # 1. Fetch existing blocks to delete
    existing_blocks = fetch_page_blocks(page_id, headers)
    print(f"    Clearing {len(existing_blocks)} existing blocks...")

    # 2. Delete existing blocks
    for block in existing_blocks:
        block_id = block.get("id")
        if block_id:
            url = f"{NOTION_API_BASE}/blocks/{block_id}"
            try:
                retry_with_backoff(
                    lambda url=url: requests.delete(url, headers=headers, timeout=60)
                )
            except Exception as e:
                print(f"    Warning: Failed to delete block {block_id}: {e}")
            time.sleep(0.1)  # Rate limit

    # 3. Convert rubric to Notion blocks
    new_blocks = markdown_to_notion_blocks(rubric_text)
    print(f"    Writing {len(new_blocks)} new blocks...")

    # 4. Append new blocks in batches (Notion limit: 100 blocks per request)
    url = f"{NOTION_API_BASE}/blocks/{page_id}/children"
    for i in range(0, len(new_blocks), 100):
        batch = new_blocks[i:i + 100]
        retry_with_backoff(
            lambda batch=batch: requests.patch(url, headers=headers, json={"children": batch}, timeout=60)
        )
        time.sleep(0.3)  # Rate limit between batches

    return True


def call_claude(prompt, anthropic_key, max_tokens=4096):
    """
    Call Claude API with the given prompt.

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
        return content[0].get("text", "")
    raise Exception(f"Unexpected Claude response format: {data}")


def generate_rubric(horizons_content, anthropic_key):
    """
    Generate a scoring rubric based on the Horizons of Focus content.

    Uses GTD (Getting Things Done) framework for prioritization.
    Returns the rubric as a string.
    """
    prompt = f"""You are helping implement a David Allen GTD (Getting Things Done) prioritization system.

## Context
In GTD, "Horizons of Focus" represent different altitudes of perspective:
- Horizon 5: Purpose/Principles - Life purpose and core values
- Horizon 4: Vision - Long-term vision of ideal life/work
- Horizon 3: Goals - 1-2 year objectives
- Horizon 2: Areas of Focus - Key areas of responsibility (roles, accountabilities)
- Horizon 1: Projects - Multi-step outcomes
- Ground: Next Actions - Individual tasks

## Your Task
Create a scoring rubric (0-100) that evaluates how well a task aligns with the person's stated identity and priorities from their Horizons of Focus document below.

The "Horizon Score" serves as a **priority indicator** - helping the user decide which flexible tasks (no due date) to tackle next based on who they have said they want to be.

## Document Structure
The Horizons document includes:
- Purpose and Core Values
- Vision
- Areas of Focus: Spirituality, Personal Development, Health, Romance, Family, Business & Career, Finances, Fun & Recreation, Social, Humanitarian
- In Progress Goals (each tagged with relevant Focus Areas)

## Scoring Guidelines
Goals spanning MULTIPLE Focus Areas indicate higher strategic leverage.

Score ranges:
- 90-100: Directly advances a high-leverage goal (3+ Focus Areas) - "This IS who I want to be"
- 75-89: Directly advances a focused goal (1-2 Focus Areas) - "This supports my goals"
- 50-74: Supports an Area of Focus with active goals - "This maintains important areas"
- 30-49: Aligns with values but no direct goal connection - "This feels right but isn't urgent"
- 10-29: Maintenance/neutral - "Necessary but not identity-aligned"
- 0-9: Misaligned or distraction - "This pulls me away from who I want to be"

---
HORIZONS OF FOCUS:
{horizons_content}
---

Create a specific rubric based on THIS person's stated horizons that can evaluate their tasks. Be concrete - reference their actual goals, values, and areas."""

    print("Generating scoring rubric from Horizons of Focus...")
    rubric = call_claude(prompt, anthropic_key)
    print(f"Rubric generated ({len(rubric)} characters)")
    return rubric


def query_tasks(database_id, headers):
    """
    Query all tasks with List property in target values and no due date.

    Returns a list of task objects with their properties.
    """
    all_tasks = []
    url = f"{NOTION_API_BASE}/databases/{database_id}/query"
    start_cursor = None

    # Build explicit filter structure for List property AND empty Due date
    # Only score tasks without due dates (flexible tasks needing prioritization)
    or_conditions = [
        {"property": "List", "status": {"equals": "Next Actions"}},
        {"property": "List", "status": {"equals": "Waiting For"}},
        {"property": "List", "status": {"equals": "Someday/Maybe"}}
    ]

    filter_payload = {
        "filter": {
            "and": [
                {"or": or_conditions},
                {"property": "Due", "date": {"is_empty": True}}
            ]
        },
        "page_size": 100
    }

    # Debug: print the filter being sent
    print(f"  Filter: {json.dumps(filter_payload['filter'])}")

    use_fallback = False

    while True:
        if start_cursor:
            filter_payload["start_cursor"] = start_cursor

        try:
            response = retry_with_backoff(
                lambda fp=filter_payload: requests.post(url, headers=headers, json=fp, timeout=60)
            )
            data = response.json()
        except Exception as e:
            if not use_fallback:
                print(f"  Compound filter failed ({e}), trying simpler filter...")
                # Fallback: just filter by List, then filter Due in Python
                filter_payload = {
                    "filter": {"or": or_conditions},
                    "page_size": 100
                }
                use_fallback = True
                continue
            else:
                raise

        tasks = data.get("results", [])

        # If using fallback, filter out tasks with due dates in Python
        if use_fallback:
            original_count = len(tasks)
            tasks = [t for t in tasks
                     if not t.get("properties", {}).get("Due", {}).get("date")]
            print(f"  Fetched {original_count} tasks, {len(tasks)} without due dates (total: {len(all_tasks) + len(tasks)})")
        else:
            print(f"  Fetched {len(tasks)} tasks (total: {len(all_tasks) + len(tasks)})")

        all_tasks.extend(tasks)

        if not data.get("has_more"):
            break
        start_cursor = data.get("next_cursor")
        if start_cursor:
            filter_payload["start_cursor"] = start_cursor
        # Small delay between pagination requests
        time.sleep(0.3)

    return all_tasks


def extract_task_info(task):
    """
    Extract relevant information from a task for scoring.

    Returns a dict with task details.
    """
    properties = task.get("properties", {})
    task_info = {
        "id": task.get("id"),
        "title": "",
        "list": "",
        "project": "",
        "area": "",
        "priority": "",
        "due_date": "",
        "notes": "",
    }

    # Extract title
    title_prop = properties.get("Task name", properties.get("Name", {}))
    if title_prop.get("type") == "title":
        title_array = title_prop.get("title", [])
        task_info["title"] = extract_text_from_rich_text(title_array)

    # Extract List (status type)
    list_prop = properties.get("List", {})
    if list_prop.get("type") == "status":
        status = list_prop.get("status")
        if status:
            task_info["list"] = status.get("name", "")

    # Extract Project (relation or select)
    project_prop = properties.get("Project", properties.get("Projects", {}))
    if project_prop.get("type") == "relation":
        relations = project_prop.get("relation", [])
        if relations:
            task_info["project"] = f"[Related to {len(relations)} project(s)]"
    elif project_prop.get("type") == "select":
        select = project_prop.get("select")
        if select:
            task_info["project"] = select.get("name", "")

    # Extract Area (select or relation)
    area_prop = properties.get("Area", properties.get("Areas", {}))
    if area_prop.get("type") == "select":
        select = area_prop.get("select")
        if select:
            task_info["area"] = select.get("name", "")
    elif area_prop.get("type") == "relation":
        relations = area_prop.get("relation", [])
        if relations:
            task_info["area"] = f"[Related to {len(relations)} area(s)]"

    # Extract Priority (select)
    priority_prop = properties.get("Priority", {})
    if priority_prop.get("type") == "select":
        select = priority_prop.get("select")
        if select:
            task_info["priority"] = select.get("name", "")

    # Extract Due Date
    due_prop = properties.get("Due", properties.get("Due Date", {}))
    if due_prop.get("type") == "date":
        date_obj = due_prop.get("date")
        if date_obj:
            task_info["due_date"] = date_obj.get("start", "")

    # Extract Notes/Description (rich_text)
    notes_prop = properties.get("Notes", properties.get("Description", {}))
    if notes_prop.get("type") == "rich_text":
        notes_array = notes_prop.get("rich_text", [])
        task_info["notes"] = extract_text_from_rich_text(notes_array)[:500]  # Limit length

    return task_info


def score_tasks_batch(tasks, rubric, anthropic_key):
    """
    Score a batch of tasks using Claude.

    Returns a list of {task_id, score, reasoning} dicts.
    """
    # Format tasks for the prompt
    tasks_text = ""
    for i, task in enumerate(tasks, 1):
        tasks_text += f"""
Task {i}:
- ID: {task['id']}
- Title: {task['title']}
- List: {task['list']}
- Project: {task['project'] or 'None'}
- Area: {task['area'] or 'None'}
- Priority: {task['priority'] or 'None'}
- Due Date: {task['due_date'] or 'None'}
- Notes: {task['notes'] or 'None'}
"""

    prompt = f"""You are scoring tasks based on how well they align with a person's Horizons of Focus.

SCORING RUBRIC:
{rubric}

TASKS TO SCORE:
{tasks_text}

For each task, provide a score from 0-100 based on alignment with the Horizons of Focus.
- 90-100: Directly advances a stated goal or is critical to purpose
- 70-89: Strongly supports an area of focus or contributes to vision
- 50-69: Moderately aligned with values or supports goals indirectly
- 30-49: Neutral maintenance task or loosely connected
- 0-29: Misaligned, distraction, or contrary to stated priorities

Return your response as a JSON array with this exact format:
[
  {{"task_id": "xxx", "score": 85, "reasoning": "Brief explanation"}},
  ...
]

IMPORTANT: Return ONLY the JSON array, no other text."""

    response_text = call_claude(prompt, anthropic_key)

    # Parse JSON response - FAIL LOUDLY on parse errors
    try:
        # Find JSON array in response
        start_idx = response_text.find('[')
        end_idx = response_text.rfind(']') + 1
        if start_idx == -1 or end_idx == 0:
            raise HorizonScoringError(
                f"No JSON array found in Claude response. "
                f"Response was: {response_text[:500]}..."
            )
        json_str = response_text[start_idx:end_idx]
        scores = json.loads(json_str)
        return scores
    except json.JSONDecodeError as e:
        raise HorizonScoringError(
            f"Failed to parse Claude response as JSON: {e}. "
            f"Response was: {response_text[:500]}..."
        )


def update_horizon_score(task_id, score, headers):
    """
    Update a task's Horizon Score property in Notion.

    Returns True on success, False on failure.
    """
    url = f"{NOTION_API_BASE}/pages/{task_id}"
    payload = {
        "properties": {
            "Horizon Score": {"number": score}
        }
    }

    try:
        retry_with_backoff(
            lambda: requests.patch(url, headers=headers, json=payload, timeout=60)
        )
        return True
    except Exception as e:
        print(f"  Error updating task {task_id}: {e}")
        return False


def score_all_batches_parallel(task_batches, rubric, anthropic_key):
    """
    Score multiple batches of tasks in parallel using ThreadPoolExecutor.

    Args:
        task_batches: List of task info lists (each batch is a list of task dicts)
        rubric: The scoring rubric string
        anthropic_key: Anthropic API key

    Returns:
        List of score dicts with task_id, score, and reasoning

    Raises:
        HorizonScoringError: If ANY batch fails to score (fail loudly)
    """
    all_scores = []
    failed_batches = []
    total_batches = len(task_batches)

    print(f"  Scoring {total_batches} batches with {SCORING_WORKERS} parallel workers...")

    with ThreadPoolExecutor(max_workers=SCORING_WORKERS) as executor:
        # Submit all batches for parallel execution
        future_to_batch = {
            executor.submit(score_tasks_batch, batch, rubric, anthropic_key): i
            for i, batch in enumerate(task_batches)
        }

        # Collect results as they complete
        for future in as_completed(future_to_batch):
            batch_num = future_to_batch[future]
            try:
                scores = future.result()
                all_scores.extend(scores)
                print(f"  Batch {batch_num + 1}/{total_batches} complete ({len(scores)} scores)")
            except Exception as e:
                print(f"  Batch {batch_num + 1}/{total_batches} failed: {e}")
                failed_batches.append((batch_num + 1, str(e)))

    # FAIL LOUDLY if ANY batch failed
    if failed_batches:
        failed_info = ", ".join([f"Batch {num}: {err}" for num, err in failed_batches])
        raise HorizonScoringError(
            f"{len(failed_batches)}/{total_batches} batches failed to score. "
            f"Failures: {failed_info}"
        )

    return all_scores


def update_scores_parallel(scores, headers):
    """
    Update Notion pages with scores in parallel using ThreadPoolExecutor.

    Args:
        scores: List of score dicts with task_id, score, reasoning
        headers: Notion API headers

    Returns:
        Tuple of (successful_updates, errors)
    """
    successful = []
    errors = []
    total = len(scores)

    def update_single(score_data):
        """Update a single task and return result."""
        task_id = score_data.get("task_id")
        raw_score = score_data.get("score")
        reasoning = score_data.get("reasoning", "")

        if not task_id or raw_score is None:
            return None, None, False, "Missing task_id or score", score_data

        try:
            score = max(0, min(100, int(raw_score)))
        except (ValueError, TypeError):
            return task_id, None, False, f"Invalid score value: {raw_score}", score_data

        success = update_horizon_score(task_id, score, headers)
        return task_id, score, success, reasoning, None

    print(f"  Updating {total} tasks with {UPDATE_WORKERS} parallel workers...")

    with ThreadPoolExecutor(max_workers=UPDATE_WORKERS) as executor:
        futures = [executor.submit(update_single, s) for s in scores]

        completed = 0
        for future in as_completed(futures):
            task_id, score, success, reasoning, error_data = future.result()
            completed += 1

            if error_data:
                errors.append({
                    "task_id": task_id,
                    "error": reasoning,
                    "data": error_data
                })
            elif success:
                successful.append({
                    "task_id": task_id,
                    "score": score,
                    "reasoning": reasoning
                })
                if completed % 25 == 0 or completed == total:
                    print(f"  Progress: {completed}/{total} updates complete")
            else:
                errors.append({
                    "task_id": task_id,
                    "score": score,
                    "error": "Failed to update Notion"
                })

    # FAIL LOUDLY if error rate exceeds 20%
    if total > 0:
        error_rate = len(errors) / total
        if error_rate > 0.20:
            raise HorizonScoringError(
                f"Update failure rate too high: {len(errors)}/{total} ({error_rate:.0%}) failed. "
                f"Threshold is 20%. First few errors: {errors[:3]}"
            )

    return successful, errors


def handler(pd: "pipedream"):
    """Main entry point for Pipedream step."""

    # --- 1. Get Credentials from Environment ---
    notion_token = os.environ.get("NOTION_API_TOKEN")
    if not notion_token:
        raise Exception("NOTION_API_TOKEN environment variable not set")

    database_id = os.environ.get("NOTION_DATABASE_ID")
    if not database_id:
        raise Exception("NOTION_DATABASE_ID environment variable not set")

    horizons_page_id = os.environ.get("NOTION_HORIZONS_PAGE_ID")
    if not horizons_page_id:
        raise Exception("NOTION_HORIZONS_PAGE_ID environment variable not set")

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if not anthropic_key:
        raise Exception("ANTHROPIC_API_KEY environment variable not set")

    # Optional: page to save the rubric for review
    rubric_page_id = os.environ.get("NOTION_RUBRIC_PAGE_ID")

    # Optional: inline database IDs for Goals and Core Values
    goals_db_id = os.environ.get("NOTION_GOALS_DB_ID")
    core_values_db_id = os.environ.get("NOTION_CORE_VALUES_DB_ID")

    # --- 2. Set up headers ---
    notion_headers = {
        "Authorization": f"Bearer {notion_token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_API_VERSION,
    }

    successful_updates = []
    errors = []

    try:
        # --- 3. Fetch all data in PARALLEL for speed ---
        print("Step 1: Fetching Horizons, Core Values, and Goals in parallel...")

        # Helper functions for parallel execution
        def fetch_horizons():
            blocks = fetch_page_blocks(horizons_page_id, notion_headers)
            content = parse_blocks_to_text(blocks)
            return blocks, content

        def fetch_values_safe():
            if not core_values_db_id:
                return None
            try:
                return fetch_core_values(core_values_db_id, notion_headers)
            except Exception as e:
                print(f"  Warning: Could not fetch Core Values: {e}")
                return None

        def fetch_goals_safe():
            if not goals_db_id:
                return None
            try:
                return fetch_in_progress_goals(goals_db_id, notion_headers)
            except Exception as e:
                print(f"  Warning: Could not fetch Goals: {e}")
                return None

        # Execute all fetches in parallel
        with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as executor:
            horizons_future = executor.submit(fetch_horizons)
            values_future = executor.submit(fetch_values_safe)
            goals_future = executor.submit(fetch_goals_safe)

            # Wait for all results
            blocks, horizons_content = horizons_future.result()
            core_values = values_future.result()
            goals = goals_future.result()

        print(f"  Fetched {len(blocks)} blocks, {len(horizons_content)} characters of content")

        if not horizons_content.strip():
            raise HorizonScoringError("Horizons of Focus page is empty or has no readable content")

        # --- 3b. Append Core Values to horizons content ---
        if core_values:
            horizons_content += "\n\n## Core Values\n"
            for value in core_values:
                horizons_content += f"• {value}\n"
            print(f"  Added {len(core_values)} core values")
        elif core_values_db_id:
            print("  No core values found")
        else:
            print("  NOTION_CORE_VALUES_DB_ID not set, skipping Core Values")

        # --- 3c. Append In Progress Goals to horizons content ---
        if goals:
            horizons_content += "\n\n## In Progress Goals (ordered by cross-area impact)\n"
            for goal in goals:
                areas_str = ", ".join(goal["focus_areas"]) if goal["focus_areas"] else "No specific area"
                # Include description if available
                desc = goal.get("description", "")
                if desc:
                    horizons_content += f"• {goal['name']} [Focus Areas: {areas_str}]\n  Description: {desc}\n"
                else:
                    horizons_content += f"• {goal['name']} [Focus Areas: {areas_str}]\n"
            print(f"  Added {len(goals)} in-progress goals")
        elif goals_db_id:
            print("  No in-progress goals found")
        else:
            print("  NOTION_GOALS_DB_ID not set, skipping Goals")

        # --- 4. Generate scoring rubric ---
        print("\nStep 2: Generating scoring rubric with Claude...")
        rubric = generate_rubric(horizons_content, anthropic_key)

        # --- 4b. Save rubric to Notion page (if configured) ---
        if rubric_page_id:
            print("  Saving rubric to Notion page...")
            try:
                save_rubric_to_notion(rubric, rubric_page_id, notion_headers)
                print(f"  Rubric saved: https://notion.so/{rubric_page_id.replace('-', '')}")
            except Exception as e:
                print(f"  Warning: Failed to save rubric to Notion: {e}")

        # --- 5. Query tasks ---
        print(f"\nStep 3: Querying tasks with List in {LIST_VALUES}...")
        tasks = query_tasks(database_id, notion_headers)
        print(f"  Found {len(tasks)} tasks to score")

        if not tasks:
            return {
                "status": "Completed",
                "message": "No tasks found matching filter criteria",
                "tasks_scored": 0,
                "successful_updates": [],
                "errors": []
            }

        # --- 6. Extract task info for scoring ---
        print("\nStep 4: Extracting task information...")
        task_infos = [extract_task_info(task) for task in tasks]

        # --- 7. Score tasks in parallel batches ---
        print(f"\nStep 5: Scoring tasks in parallel batches of {BATCH_SIZE}...")
        task_batches = [
            task_infos[i:i + BATCH_SIZE]
            for i in range(0, len(task_infos), BATCH_SIZE)
        ]
        all_scores = score_all_batches_parallel(task_batches, rubric, anthropic_key)
        print(f"  Received {len(all_scores)} scores from Claude")

        # --- 8. Update Notion with scores in parallel ---
        print("\nStep 6: Updating Horizon Scores in Notion (parallel)...")
        successful_updates, errors = update_scores_parallel(all_scores, notion_headers)

    except HorizonScoringError:
        # FAIL LOUDLY - re-raise scoring errors to fail the Pipedream job
        raise
    except Exception as e:
        # FAIL LOUDLY - wrap unexpected errors and re-raise
        raise HorizonScoringError(f"Unexpected error during execution: {e}") from e

    # --- 9. Return summary ---
    status = "Completed" if not errors else "Partial"
    print("\n--- Processing Complete ---")
    print(f"Successfully updated: {len(successful_updates)}")
    print(f"Errors: {len(errors)}")

    return {
        "status": status,
        "tasks_scored": len(successful_updates),
        "successful_updates": successful_updates,
        "errors": errors,
        "rubric_preview": rubric[:500] if 'rubric' in dir() else None
    }
