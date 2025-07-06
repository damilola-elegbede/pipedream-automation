# Deployment Guide for Unified Pipedream Repository

This guide explains how to deploy and manage the unified Pipedream automation repository structure.

## Repository Structure

```
pipedream-automation/
├── pipedream/                    # Pipedream-specific configurations
│   ├── workflows/               # Workflow definitions (.js files)
│   ├── components/              # Reusable components
│   │   ├── actions/            # Action components
│   │   ├── sources/            # Source components
│   │   └── common/             # Shared utilities
│   ├── sources/                # Event sources
│   └── actions/                # Custom actions
├── library/                     # Python library code
│   ├── src/                    # Source code
│   │   ├── config/             # Configuration files
│   │   ├── integrations/       # Integration modules
│   │   └── utils/              # Utility functions
│   ├── tests/                  # Test files
│   └── docs/                   # Library documentation
├── deployment/                  # Deployment scripts and configs
│   ├── scripts/                # Bundling and deployment scripts
│   └── templates/              # Template files
└── docs/                       # General documentation
```

## Deployment Process

### 1. Bundle Python Modules

The bundler script creates self-contained Python modules for Pipedream deployment:

```bash
# Bundle all modules
cd deployment/scripts
python bundle_for_pipedream_v2.py --all

# Bundle specific module
python bundle_for_pipedream_v2.py --module gmail_to_notion
```

### 2. Deploy to Pipedream

#### Option A: Using Pipedream CLI

```bash
# Deploy a workflow
pd deploy pipedream/workflows/gmail-to-notion.js

# Deploy a component
pd deploy pipedream/components/actions/notion-task-creator.js
```

#### Option B: Using Pipedream Web Interface

1. Copy the bundled module content from `deployment/scripts/pipedream_modules/`
2. Paste into a new Python code step in your workflow
3. Configure the workflow inputs and triggers

### 3. Update Workflow References

When deploying bundled modules, update your workflow files to reference the correct bundled modules:

```javascript
// In your workflow file
const { handler } = await import('./bundled/gmail_to_notion_bundled.js');
```

## Configuration Management

### Bundle Configuration

The `bundle.config.json` file defines which modules to bundle:

```json
{
  "modules": {
    "gmail_to_notion": {
      "name": "Gmail to Notion Task Creator",
      "entry": "../../library/src/integrations/gmail_notion/create_notion_task.py",
      "dependencies": [
        "../../library/src/utils/common_utils.py",
        "../../library/src/utils/validation.py",
        "../../library/src/utils/error_handling.py",
        "../../library/src/utils/retry_manager.py",
        "../../library/src/utils/error_enrichment.py",
        "../../library/src/utils/structured_logger.py",
        "../../library/src/config/constants.py"
      ],
      "output": "gmail_to_notion_bundled.py"
    }
  }
}
```

### Environment Variables

Configure these environment variables in your Pipedream workflows:

- `NOTION_API_KEY` - Your Notion integration token
- `GMAIL_API_KEY` - Gmail API credentials
- `GOOGLE_CALENDAR_API_KEY` - Google Calendar API credentials

## Development Workflow

### 1. Local Development

```bash
# Set up development environment
cd library
pip install -r requirements.txt

# Run tests
pytest

# Run linting
flake8 src/
```

### 2. Testing Changes

```bash
# Run specific test
pytest tests/test_gmail_notion/test_create_notion_task.py

# Run with coverage
pytest --cov=src --cov-report=html
```

### 3. Update and Deploy

```bash
# 1. Make changes to library code
# 2. Update tests
# 3. Bundle modules
cd deployment/scripts
python bundle_for_pipedream_v2.py --all

# 4. Deploy to Pipedream
pd deploy pipedream/workflows/gmail-to-notion.js
```

## Directory Migration

If you're migrating from the old structure:

1. **Python modules**: Moved from `src/` to `library/src/`
2. **Tests**: Moved from `tests/` to `library/tests/`
3. **Scripts**: Moved from `scripts/` to `deployment/scripts/`
4. **Documentation**: Moved from `docs/` to `library/docs/`

## Best Practices

### 1. Module Organization

- Keep integration logic in `library/src/integrations/`
- Place utility functions in `library/src/utils/`
- Store configuration in `library/src/config/`

### 2. Workflow Organization

- Use descriptive names for workflow files
- Group related workflows in subdirectories
- Include version information in workflow metadata

### 3. Component Reuse

- Create reusable components in `pipedream/components/`
- Use common utilities in `pipedream/components/common/`
- Document component interfaces clearly

### 4. Testing

- Write tests for all integration modules
- Use mocking for external API calls
- Maintain test coverage above 80%

### 5. Documentation

- Update README files when adding new features
- Document deployment procedures
- Include troubleshooting guides

## Troubleshooting

### Common Issues

1. **Module not found errors**: Check bundle.config.json paths
2. **Import errors**: Ensure all dependencies are included
3. **API authentication**: Verify environment variables are set
4. **Path resolution**: Check relative paths in bundled modules

### Debugging

```bash
# Check bundled module contents
cat deployment/scripts/pipedream_modules/gmail_to_notion_bundled.py

# Validate configuration
python -c "import json; print(json.load(open('bundle.config.json')))"

# Test module import
python -c "from deployment.scripts.pipedream_modules.gmail_to_notion_bundled import handler"
```

## Support

- Check the `docs/` directory for additional documentation
- Review test files for usage examples
- Refer to Pipedream documentation for platform-specific issues