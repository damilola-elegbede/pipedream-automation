# /deploy_to_pd - Deploy Python Scripts to Pipedream Workflows

Deploys Python scripts from `src/steps/` to Pipedream workflows via browser automation.

## Behavior

1. Load workflow IDs from `.env.local`
2. Open browser for Google SSO login (or use cached session)
3. Navigate to each workflow and update Python step code
4. Report results

## Arguments

- `--workflow <name>` - Sync only specified workflow (e.g., `gmail_to_notion`)
- `--dry-run` - Validate configuration without making changes
- `--verbose` - Show detailed debug output

## Implementation

Run the deploy script:

```bash
python -m src.deploy.deploy_to_pipedream $ARGUMENTS
```

## Workflows

| Key | Steps |
|-----|-------|
| `gmail_to_notion` | fetch_gmail_emails, create_notion_task, label_gmail_processed |
| `notion_task_to_gcal` | notion_task_to_gcal |
| `notion_update_to_gcal` | notion_update_to_gcal |
| `gcal_to_notion` | gcal_event_to_notion |

## Prerequisites

- Python dependencies: `pip install playwright && playwright install chromium`
- Configuration: `.env.local` with workflow IDs (copy from `.env.local.example`)
