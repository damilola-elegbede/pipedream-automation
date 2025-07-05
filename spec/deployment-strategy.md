# Pipedream Automation Deployment Strategy & Execution Plan

## Document Information
- **Version**: 2.0.0
- **Date**: 2025-07-05
- **Purpose**: Actionable plan for improving and deploying code to Pipedream
- **Status**: Execution Ready

## Table of Contents
1. [Current State Assessment](#1-current-state-assessment)
2. [Code Improvements Plan](#2-code-improvements-plan)
3. [Pipedream Deployment Approach](#3-pipedream-deployment-approach)
4. [Execution Steps](#4-execution-steps)
5. [Testing & Validation](#5-testing--validation)

---

## 1. Current State Assessment

### 1.1 What We Have
- **8 integration modules** with duplicated code and constants
- **Working Python code** that follows Pipedream's handler pattern
- **78% test coverage** with pytest
- **Basic error handling** that needs improvement
- **No deployment automation** for Pipedream

### 1.2 What We Need
- **Consolidated codebase** with shared utilities
- **Single-file modules** for Pipedream deployment
- **Improved error handling** and validation
- **Deployment scripts** to automate Pipedream updates
- **Documentation** on how to use in Pipedream workflows

---

## 2. Code Improvements Plan

### 2.1 Phase 1: Code Consolidation (IMMEDIATE)

#### Step 1.1: Create Constants Module
**File**: `src/config/constants.py`
```python
# API URLs
NOTION_API_BASE_URL = "https://api.notion.com/v1"
NOTION_API_VERSION = "2022-06-28"
GMAIL_API_BASE_URL = "https://gmail.googleapis.com/gmail/v1/users/me"

# Timeouts and Limits
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
BATCH_SIZE = 100

# Error Messages
ERROR_MISSING_AUTH = "Authentication credentials not found"
ERROR_INVALID_INPUT = "Required input field '{}' is missing"
```

#### Step 1.2: Consolidate Duplicate Functions
**Action**: Move these duplicated functions to appropriate utils:
- `build_notion_properties()` → `notion_utils.py`
- `format_error_message()` → `common_utils.py`
- `validate_required_fields()` → `validation.py`

#### Step 1.3: Update All Integration Files
**Action**: Replace local definitions with imports:
```python
# Before (in 8 files):
NOTION_API_BASE_URL = "https://api.notion.com/v1"

# After:
from src.config.constants import NOTION_API_BASE_URL
```

### 2.2 Phase 2: Create Bundler for Pipedream

#### Step 2.1: Build Module Bundler
**File**: `scripts/bundle_for_pipedream.py`
```python
#!/usr/bin/env python3
"""
Bundle Python modules with their dependencies for Pipedream deployment.
This creates self-contained Python files that can be pasted into Pipedream.
"""

import ast
import os
from pathlib import Path

def bundle_module(module_name, output_dir="pipedream_modules"):
    """
    Bundle a module with all its dependencies into a single file.
    
    Args:
        module_name: Name of the module (e.g., 'notion_gcal_sync')
        output_dir: Directory to save bundled modules
    """
    # Implementation steps:
    # 1. Read the main module file
    # 2. Parse imports and identify internal dependencies
    # 3. Inline all internal dependencies
    # 4. Add Pipedream-specific wrapper
    # 5. Write bundled file
```

#### Step 2.2: Create Bundle Configuration
**File**: `bundle.config.json`
```json
{
  "modules": {
    "notion_to_gcal": {
      "entry": "src/integrations/notion_gcal/task_to_event.py",
      "dependencies": [
        "src/utils/common_utils.py",
        "src/utils/notion_utils.py",
        "src/config/constants.py"
      ],
      "output": "notion_to_gcal_bundled.py"
    },
    "gmail_to_notion": {
      "entry": "src/integrations/gmail_notion/create_notion_task.py",
      "dependencies": [
        "src/utils/common_utils.py",
        "src/config/constants.py"
      ],
      "output": "gmail_to_notion_bundled.py"
    }
  }
}
```

### 2.3 Phase 3: Improve Error Handling

#### Step 3.1: Create Error Handler Decorator
**File**: `src/utils/error_handling.py`
```python
import functools
import logging
from typing import Dict, Any

def pipedream_error_handler(func):
    """Decorator for consistent error handling in Pipedream"""
    @functools.wraps(func)
    def wrapper(pd):
        try:
            # Validate basic structure
            if not hasattr(pd, 'inputs') and not isinstance(pd, dict):
                return {"error": "Invalid Pipedream context"}
                
            # Run the actual function
            return func(pd)
            
        except KeyError as e:
            return {"error": f"Missing required field: {str(e)}"}
        except ValueError as e:
            return {"error": f"Invalid value: {str(e)}"}
        except Exception as e:
            logging.error(f"Unexpected error in {func.__name__}: {str(e)}")
            return {"error": f"Internal error: {str(e)}"}
    return wrapper
```

#### Step 3.2: Add Input Validation
**File**: `src/utils/validation.py`
```python
from typing import List, Dict, Any

def validate_pipedream_inputs(pd, required_fields: List[str]) -> Dict[str, Any]:
    """
    Validate and extract required fields from Pipedream context.
    
    Args:
        pd: Pipedream context
        required_fields: List of required field paths (e.g., ['notion.auth', 'task_id'])
        
    Returns:
        Dict with validated inputs
        
    Raises:
        ValueError: If required fields are missing
    """
    # Implementation
```

---

## 3. Pipedream Deployment Approach

### 3.1 Module Structure for Pipedream

Each module will be bundled into a single file that includes:

```python
"""
Module: Notion to Google Calendar Sync
Version: 1.0.0
Generated: 2025-07-05
"""

# === EMBEDDED DEPENDENCIES START ===
# From src/utils/common_utils.py
def safe_get(data, keys):
    # ... function code ...

# From src/config/constants.py
NOTION_API_BASE_URL = "https://api.notion.com/v1"
# ... other constants ...

# === EMBEDDED DEPENDENCIES END ===

# === MAIN MODULE START ===
def handler(pd):
    """
    Main Pipedream handler function.
    
    Expected inputs:
    - pd.inputs.notion_auth: Notion authentication
    - pd.inputs.task_data: Task information
    - pd.inputs.calendar_id: Target calendar
    """
    # ... main logic ...
    
# === MAIN MODULE END ===

# Pipedream execution
return handler(pd)
```

### 3.2 Deployment Methods

#### Method 1: Manual Copy-Paste (Immediate)
1. Run bundler script
2. Copy bundled code
3. Paste into Pipedream code step
4. Configure authentication

#### Method 2: Pipedream CLI (Automated)
```bash
# Deploy using Pipedream CLI
pd deploy notion_to_gcal_bundled.py --workspace production
```

#### Method 3: API Deployment (Future)
```python
# Deploy via API
deploy_to_pipedream(
    module="notion_to_gcal_bundled.py",
    workflow_id="wf_abc123",
    step_name="sync_to_calendar"
)
```

---

## 4. Execution Steps

### 4.1 Week 1: Foundation

#### Day 1-2: Code Consolidation
- [ ] Create `src/config/constants.py` with all API URLs
- [ ] Create `src/utils/validation.py` for input validation  
- [ ] Create `src/utils/error_handling.py` for error management
- [ ] Update 8 files to use shared constants
- [ ] Run tests to ensure nothing breaks

#### Day 3-4: Build Bundler
- [ ] Create `scripts/bundle_for_pipedream.py`
- [ ] Test bundler with one module
- [ ] Create bundled versions of all modules
- [ ] Manually test one bundled module in Pipedream

#### Day 5: Documentation
- [ ] Create `docs/pipedream-usage.md`
- [ ] Document each module's inputs/outputs
- [ ] Create example Pipedream workflows
- [ ] Update CLAUDE.md with new structure

### 4.2 Week 2: Enhancement

#### Day 6-7: Improve Error Handling
- [ ] Add error handler decorator to all modules
- [ ] Implement input validation in all handlers
- [ ] Add request timeouts
- [ ] Test error scenarios

#### Day 8-9: Security Improvements
- [ ] Add credential validation
- [ ] Implement request signing where needed
- [ ] Sanitize error messages
- [ ] Add rate limiting logic

#### Day 10: Testing
- [ ] Create test suite for bundled modules
- [ ] Test in Pipedream sandbox
- [ ] Document test results

### 4.3 Week 3: Deployment

#### Day 11-12: Create Deployment Scripts
- [ ] Create `scripts/deploy_to_pipedream.py`
- [ ] Add workflow templates
- [ ] Create environment configuration

#### Day 13-14: Production Preparation
- [ ] Deploy to Pipedream staging
- [ ] Run parallel tests
- [ ] Create rollback procedures
- [ ] Final documentation

#### Day 15: Go Live
- [ ] Deploy to production
- [ ] Monitor for 24 hours
- [ ] Address any issues
- [ ] Document lessons learned

---

## 5. Testing & Validation

### 5.1 Local Testing Before Bundling
```bash
# Run existing tests
make test

# Test specific module
pytest tests/integrations/test_notion_gcal.py
```

### 5.2 Testing Bundled Modules
```python
# test_bundled_modules.py
import subprocess
import json

def test_bundled_module(module_path, test_input):
    """Test a bundled module locally"""
    # Create mock Pipedream context
    pd_context = {
        "inputs": test_input,
        "steps": {},
        "workflow": {"id": "test"}
    }
    
    # Run module
    result = subprocess.run([
        "python", "-c", 
        f"pd = {json.dumps(pd_context)}; exec(open('{module_path}').read())"
    ], capture_output=True, text=True)
    
    return json.loads(result.stdout)
```

### 5.3 Pipedream Testing Checklist
- [ ] Module loads without errors
- [ ] Authentication works correctly
- [ ] All required inputs are validated
- [ ] Error responses are properly formatted
- [ ] Success responses include expected data
- [ ] Performance is acceptable (<30s execution)

---

## 6. Success Criteria

### 6.1 Code Quality
- [ ] Zero code duplication across modules
- [ ] All functions have error handling
- [ ] 90%+ test coverage achieved
- [ ] All modules follow consistent patterns

### 6.2 Deployment
- [ ] All modules bundled successfully
- [ ] Deployment script works reliably
- [ ] Documentation is complete
- [ ] Team can deploy updates independently

### 6.3 Production
- [ ] All workflows running successfully
- [ ] Error rate < 1%
- [ ] Average execution time < 10s
- [ ] No security vulnerabilities

---

## 7. Quick Reference

### 7.1 Commands
```bash
# Bundle all modules
python scripts/bundle_for_pipedream.py --all

# Bundle specific module
python scripts/bundle_for_pipedream.py --module notion_gcal

# Test bundled module
python scripts/test_bundled.py pipedream_modules/notion_gcal.py

# Deploy to Pipedream (future)
python scripts/deploy_to_pipedream.py --env production
```

### 7.2 File Locations
- **Source code**: `src/integrations/`
- **Shared utilities**: `src/utils/`
- **Bundled modules**: `pipedream_modules/`
- **Deployment scripts**: `scripts/`
- **Documentation**: `docs/`

### 7.3 Module Naming Convention
- **Source**: `src/integrations/notion_gcal/task_to_event.py`
- **Bundled**: `pipedream_modules/notion_gcal_task_to_event.py`
- **In Pipedream**: `Notion GCal - Task to Event`

---

## Next Immediate Actions

1. **Start with Step 1.1**: Create the constants file
2. **Then Step 1.2**: Move one duplicate function as a test
3. **Verify tests pass**: Run `make test`
4. **Continue with consolidation**: Update all 8 files

This plan is now executable - each step has clear actions and expected outcomes.