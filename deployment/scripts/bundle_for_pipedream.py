#!/usr/bin/env python3
"""
Bundle Python modules with their dependencies for Pipedream deployment.

This creates self-contained Python files that can be pasted into Pipedream
code steps without requiring external imports.
"""

import ast
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Load bundle configuration
BUNDLE_CONFIG_PATH = "bundle.config.json"


class ModuleBundler:
    """Bundle Python modules with their dependencies."""
    
    def __init__(self):
        self.imported_modules = set()
        self.module_contents = {}
        self.constants_used = set()
        
    def extract_imports(self, file_path: str) -> Set[str]:
        """Extract all internal imports from a Python file."""
        with open(file_path, 'r') as f:
            tree = ast.parse(f.read())
        
        imports = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith('src.'):
                    # Track which names are imported
                    for alias in node.names:
                        imports.add((node.module, alias.name))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith('src.'):
                        imports.add((alias.name, None))
        
        return imports
    
    def read_module_content(self, module_path: str) -> str:
        """Read and process module content."""
        with open(module_path, 'r') as f:
            content = f.read()
        
        # Remove module-level imports of internal modules
        lines = content.split('\n')
        filtered_lines = []
        skip_next = False
        
        for line in lines:
            # Skip internal imports
            if line.strip().startswith('from src.') or line.strip().startswith('import src.'):
                continue
            # Skip TYPE_CHECKING blocks
            if 'TYPE_CHECKING' in line:
                skip_next = True
                continue
            if skip_next and line.strip() == '':
                skip_next = False
                continue
            if not skip_next:
                filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
    
    def extract_functions_and_constants(self, module_path: str, names: List[str]) -> str:
        """Extract specific functions and constants from a module."""
        with open(module_path, 'r') as f:
            content = f.read()
            tree = ast.parse(content)
        
        extracted = []
        
        for node in tree.body:
            # Extract functions
            if isinstance(node, ast.FunctionDef) and node.name in names:
                # Get the source code for this function
                start_line = node.lineno - 1
                end_line = node.end_lineno
                with open(module_path, 'r') as f:
                    lines = f.readlines()
                function_code = ''.join(lines[start_line:end_line])
                extracted.append(function_code)
            
            # Extract constants
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in names:
                        start_line = node.lineno - 1
                        end_line = node.end_lineno or node.lineno
                        with open(module_path, 'r') as f:
                            lines = f.readlines()
                        const_code = ''.join(lines[start_line:end_line])
                        extracted.append(const_code)
        
        return '\n'.join(extracted)
    
    def bundle_module(self, module_config: Dict[str, any], output_dir: str = "pipedream_modules") -> str:
        """Bundle a module with all its dependencies."""
        entry_file = module_config['entry']
        dependencies = module_config.get('dependencies', [])
        output_file = module_config['output']
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, output_file)
        
        # Read the main module
        main_content = self.read_module_content(entry_file)
        
        # Extract imports from main module
        imports = self.extract_imports(entry_file)
        
        # Collect all required functions and constants
        embedded_code = []
        
        # Process each import
        for module_name, import_name in imports:
            module_path = module_name.replace('.', '/') + '.py'
            
            if os.path.exists(module_path):
                if import_name:
                    # Extract specific function/constant
                    code = self.extract_functions_and_constants(module_path, [import_name])
                    if code:
                        embedded_code.append(f"# From {module_path}")
                        embedded_code.append(code)
        
        # Also include explicitly listed dependencies
        for dep_path in dependencies:
            if os.path.exists(dep_path):
                # Extract all exports from dependency
                imports_from_dep = set()
                for module_name, import_name in imports:
                    if module_name.replace('.', '/') + '.py' == dep_path:
                        imports_from_dep.add(import_name)
                
                if imports_from_dep:
                    code = self.extract_functions_and_constants(dep_path, list(imports_from_dep))
                    if code:
                        embedded_code.append(f"# From {dep_path}")
                        embedded_code.append(code)
        
        # Build the bundled module
        bundled_content = f'''"""
Module: {module_config.get('name', 'Unknown')}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Description: Bundled module for Pipedream deployment
"""

# === STANDARD IMPORTS ===
import logging
import requests
from typing import Any, Dict, Optional, List
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# === EMBEDDED DEPENDENCIES START ===
{chr(10).join(embedded_code)}
# === EMBEDDED DEPENDENCIES END ===

# === MAIN MODULE START ===
{main_content}
# === MAIN MODULE END ===
'''
        
        # Write the bundled file
        with open(output_path, 'w') as f:
            f.write(bundled_content)
        
        print(f"✓ Bundled {entry_file} -> {output_path}")
        return output_path


def create_default_config():
    """Create a default bundle configuration file."""
    config = {
        "modules": {
            "notion_to_gcal": {
                "name": "Notion to Google Calendar Sync",
                "entry": "src/integrations/notion_gcal/task_to_event.py",
                "dependencies": [
                    "src/utils/common_utils.py",
                    "src/utils/notion_utils.py",
                    "src/config/constants.py"
                ],
                "output": "notion_to_gcal_bundled.py"
            },
            "gmail_to_notion": {
                "name": "Gmail to Notion Task Creator",
                "entry": "src/integrations/gmail_notion/create_notion_task.py",
                "dependencies": [
                    "src/utils/common_utils.py",
                    "src/utils/validation.py",
                    "src/utils/error_handling.py",
                    "src/config/constants.py"
                ],
                "output": "gmail_to_notion_bundled.py"
            },
            "calendar_to_notion": {
                "name": "Google Calendar to Notion Sync",
                "entry": "src/integrations/calendar_to_notion/calendar_to_notion.py",
                "dependencies": [
                    "src/utils/common_utils.py",
                    "src/config/constants.py"
                ],
                "output": "calendar_to_notion_bundled.py"
            },
            "notion_update_handler": {
                "name": "Notion Update Handler",
                "entry": "src/integrations/update_handler/update_handler.py",
                "dependencies": [
                    "src/utils/common_utils.py",
                    "src/config/constants.py"
                ],
                "output": "notion_update_handler_bundled.py"
            }
        }
    }
    
    with open(BUNDLE_CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✓ Created default configuration: {BUNDLE_CONFIG_PATH}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Bundle Python modules for Pipedream")
    parser.add_argument('--module', help='Bundle a specific module')
    parser.add_argument('--all', action='store_true', help='Bundle all modules')
    parser.add_argument('--create-config', action='store_true', help='Create default config')
    parser.add_argument('--output-dir', default='pipedream_modules', help='Output directory')
    
    args = parser.parse_args()
    
    if args.create_config:
        create_default_config()
        return
    
    # Load configuration
    if not os.path.exists(BUNDLE_CONFIG_PATH):
        print(f"Configuration file not found. Creating default config...")
        create_default_config()
    
    with open(BUNDLE_CONFIG_PATH, 'r') as f:
        config = json.load(f)
    
    bundler = ModuleBundler()
    
    if args.all:
        # Bundle all modules
        for module_name, module_config in config['modules'].items():
            module_config['name'] = module_config.get('name', module_name)
            bundler.bundle_module(module_config, args.output_dir)
    elif args.module:
        # Bundle specific module
        if args.module in config['modules']:
            module_config = config['modules'][args.module]
            module_config['name'] = module_config.get('name', args.module)
            bundler.bundle_module(module_config, args.output_dir)
        else:
            print(f"Module '{args.module}' not found in configuration")
            print(f"Available modules: {', '.join(config['modules'].keys())}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()