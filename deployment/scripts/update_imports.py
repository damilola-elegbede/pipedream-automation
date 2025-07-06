#!/usr/bin/env python3
"""
Script to update imports in integration files to use the new centralized constants.

This script will:
1. Remove duplicate constant definitions
2. Add imports from src.config.constants
3. Update files to use the centralized constants
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

# Constants to look for and replace
CONSTANTS_TO_REPLACE = [
    ('NOTION_API_BASE_URL = "https://api.notion.com/v1"', 'NOTION_API_BASE_URL'),
    ('NOTION_PAGES_URL = f"{NOTION_API_BASE_URL}/pages"', 'NOTION_PAGES_URL'),
    ('NOTION_BLOCKS_URL = f"{NOTION_API_BASE_URL}/blocks"', 'NOTION_BLOCKS_URL'),
    ('NOTION_DATABASES_URL = f"{NOTION_API_BASE_URL}/databases"', 'NOTION_DATABASES_URL'),
    ('GMAIL_API_BASE_URL = "https://gmail.googleapis.com/gmail/v1/users/me"', 'GMAIL_API_BASE_URL'),
    ('GMAIL_MESSAGES_URL = f"{GMAIL_API_BASE_URL}/messages"', 'GMAIL_MESSAGES_URL'),
]

# Files to update (excluding the one we already updated)
FILES_TO_UPDATE = [
    "src/integrations/update_handler/update_handler.py",
    "src/utils/notion_utils.py",
    "src/integrations/notion_calendar/task_to_event.py",
    "src/integrations/notion_calendar/update_handler.py",
    "src/integrations/create_notion_task/create_notion_task.py",
    "src/integrations/task_to_event/task_to_event.py",
    "src/integrations/calendar_to_notion/calendar_to_notion.py",
]


def update_file(file_path: str) -> bool:
    """Update a single file to use centralized constants."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        original_content = content
        constants_found = []
        
        # Check which constants are defined in this file
        for definition, constant_name in CONSTANTS_TO_REPLACE:
            if definition in content:
                constants_found.append(constant_name)
                # Remove the definition
                content = content.replace(definition + '\n', '')
                content = content.replace(definition, '')
        
        if not constants_found:
            print(f"No constants to replace in {file_path}")
            return False
        
        # Add import if constants were found
        import_statement = f"from src.config.constants import ({', '.join(constants_found)})"
        
        # Find where to insert the import (after other imports)
        import_pattern = r'((?:from\s+[\w.]+\s+import\s+.*?\n|import\s+[\w.]+\n)+)'
        match = re.search(import_pattern, content)
        
        if match:
            # Insert after the last import
            insert_pos = match.end()
            content = content[:insert_pos] + import_statement + '\n' + content[insert_pos:]
        else:
            # No imports found, add at the beginning after docstring
            lines = content.split('\n')
            insert_line = 0
            in_docstring = False
            
            for i, line in enumerate(lines):
                if line.strip().startswith('"""'):
                    in_docstring = not in_docstring
                    if not in_docstring:
                        insert_line = i + 1
                        break
            
            lines.insert(insert_line + 1, import_statement)
            content = '\n'.join(lines)
        
        # Write the updated content
        with open(file_path, 'w') as f:
            f.write(content)
        
        print(f"✓ Updated {file_path}")
        print(f"  - Removed {len(constants_found)} constant definitions")
        print(f"  - Added import for: {', '.join(constants_found)}")
        return True
        
    except Exception as e:
        print(f"✗ Error updating {file_path}: {e}")
        return False


def main():
    """Update all integration files."""
    print("Updating integration files to use centralized constants...\n")
    
    updated_count = 0
    for file_path in FILES_TO_UPDATE:
        if os.path.exists(file_path):
            if update_file(file_path):
                updated_count += 1
        else:
            print(f"✗ File not found: {file_path}")
    
    print(f"\n✓ Updated {updated_count} files successfully")


if __name__ == "__main__":
    main()