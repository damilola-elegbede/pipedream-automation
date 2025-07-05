#!/usr/bin/env python3
"""
Bundle Python modules with their dependencies for Pipedream deployment.
Version 2: Improved dependency resolution and cleaner output.
"""

import ast
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

# Load bundle configuration
BUNDLE_CONFIG_PATH = "bundle.config.json"


class DependencyResolver:
    """Resolve and extract dependencies from Python modules."""
    
    def __init__(self):
        self.resolved_functions = {}
        self.resolved_constants = {}
        self.resolved_classes = {}
        
    def get_function_source(self, file_path: str, func_name: str) -> Optional[str]:
        """Extract a function's source code from a file."""
        with open(file_path, 'r') as f:
            lines = f.readlines()
            content = ''.join(lines)
            tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == func_name:
                # Get the complete function including decorators
                start = node.lineno - 1
                # Check for decorators
                if node.decorator_list:
                    start = min(d.lineno - 1 for d in node.decorator_list)
                end = node.end_lineno
                
                return ''.join(lines[start:end]).rstrip() + '\n'
        return None
    
    def get_constant_value(self, file_path: str, const_name: str) -> Optional[str]:
        """Extract a constant's definition from a file."""
        with open(file_path, 'r') as f:
            lines = f.readlines()
            
        # Find the constant definition
        for i, line in enumerate(lines):
            if line.strip().startswith(f"{const_name} ="):
                # Check if it's a multiline definition
                if line.strip().endswith('{'):
                    # Find the closing brace
                    result = [line.rstrip()]
                    j = i + 1
                    while j < len(lines):
                        result.append(lines[j].rstrip())
                        if lines[j].strip().endswith('}'):
                            break
                        j += 1
                    return '\n'.join(result)
                else:
                    return line.rstrip()
        return None
    
    def resolve_dependencies(self, file_path: str) -> Dict[str, Set[str]]:
        """Find all internal dependencies in a file."""
        with open(file_path, 'r') as f:
            tree = ast.parse(f.read())
        
        dependencies = {
            'functions': set(),
            'constants': set(),
            'modules': set()
        }
        
        # Track what's imported
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith('src.'):
                    dependencies['modules'].add(node.module)
                    for alias in node.names:
                        if alias.name == '*':
                            # Import all from module
                            dependencies['modules'].add(node.module)
                        else:
                            # Track specific imports
                            if node.module.endswith('constants'):
                                dependencies['constants'].add(alias.name)
                            elif node.module.endswith('utils'):
                                dependencies['functions'].add(alias.name)
        
        # Find used functions and constants in the code
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                # Check if it's a known constant pattern
                if node.id.isupper() and '_' in node.id:
                    dependencies['constants'].add(node.id)
                    
        return dependencies


class ModuleBundler:
    """Bundle Python modules with their dependencies."""
    
    def __init__(self):
        self.resolver = DependencyResolver()
        self.embedded_items = set()  # Track what's already embedded
        
    def create_bundled_module(self, config: Dict[str, any]) -> str:
        """Create a complete bundled module."""
        entry_file = config['entry']
        module_name = config.get('name', 'Bundled Module')
        
        # Read main module content
        with open(entry_file, 'r') as f:
            main_content = f.read()
        
        # Process the content
        main_content = self.clean_imports(main_content)
        dependencies = self.resolver.resolve_dependencies(entry_file)
        
        # Collect all embedded code
        embedded_code = []
        
        # Add constants first
        const_code = self.collect_constants(dependencies['constants'])
        if const_code:
            embedded_code.append("# === CONSTANTS ===")
            embedded_code.extend(const_code)
            embedded_code.append("")
        
        # Add utility functions
        func_code = self.collect_functions(dependencies['functions'])
        if func_code:
            embedded_code.append("# === UTILITY FUNCTIONS ===")
            embedded_code.extend(func_code)
            embedded_code.append("")
        
        # Build the final module
        template = f'''"""
{module_name}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Bundled for Pipedream deployment
"""

import logging
import json
import requests
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from requests.exceptions import HTTPError, RequestException

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# === EMBEDDED DEPENDENCIES ===
{chr(10).join(embedded_code)}

# === MAIN MODULE ===
{main_content}

# === PIPEDREAM HANDLER ===
# The handler function is the entry point for Pipedream
# Usage: return handler(pd)
'''
        return template
    
    def clean_imports(self, content: str) -> str:
        """Remove internal imports from module content."""
        lines = content.split('\n')
        cleaned_lines = []
        in_type_checking = False
        
        for line in lines:
            # Skip TYPE_CHECKING blocks
            if 'TYPE_CHECKING:' in line:
                in_type_checking = True
                continue
            if in_type_checking and line.strip() == '':
                in_type_checking = False
                continue
                
            # Skip internal imports
            if line.strip().startswith('from src.'):
                continue
            if line.strip().startswith('import src.'):
                continue
                
            # Skip if we're in TYPE_CHECKING block
            if not in_type_checking:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()
    
    def collect_constants(self, constants: Set[str]) -> List[str]:
        """Collect all required constants."""
        const_file = "src/config/constants.py"
        collected = []
        
        if not os.path.exists(const_file):
            return collected
            
        with open(const_file, 'r') as f:
            content = f.read()
            
        # Define the constants we need with their dependencies
        const_deps = {
            'NOTION_HEADERS': ['DEFAULT_HEADERS', 'NOTION_API_VERSION'],
            'NOTION_PAGES_URL': ['NOTION_API_BASE_URL'],
            'NOTION_BLOCKS_URL': ['NOTION_API_BASE_URL'],
            'NOTION_DATABASES_URL': ['NOTION_API_BASE_URL'],
            'GMAIL_MESSAGES_URL': ['GMAIL_API_BASE_URL'],
        }
        
        # Expand constants to include dependencies
        expanded_constants = set(constants)
        for const in list(constants):
            if const in const_deps:
                expanded_constants.update(const_deps[const])
        
        # Extract constants in order
        for const in ['NOTION_API_VERSION', 'NOTION_API_BASE_URL', 'GMAIL_API_BASE_URL', 
                      'DEFAULT_HEADERS', 'NOTION_HEADERS', 'NOTION_PAGES_URL', 
                      'NOTION_BLOCKS_URL', 'NOTION_DATABASES_URL', 'GMAIL_MESSAGES_URL',
                      'ERROR_INVALID_INPUT', 'ERROR_MISSING_AUTH', 'SUCCESS_CREATED']:
            if const in expanded_constants and const not in self.embedded_items:
                value = self.resolver.get_constant_value(const_file, const)
                if value:
                    collected.append(value)
                    self.embedded_items.add(const)
        
        return collected
    
    def collect_functions(self, functions: Set[str]) -> List[str]:
        """Collect all required utility functions."""
        collected = []
        
        # Check each utils file
        utils_files = [
            "src/utils/common_utils.py",
            "src/utils/validation.py",
            "src/utils/error_handling.py",
            "src/utils/notion_utils.py"
        ]
        
        for utils_file in utils_files:
            if not os.path.exists(utils_file):
                continue
                
            for func_name in functions:
                if func_name not in self.embedded_items:
                    source = self.resolver.get_function_source(utils_file, func_name)
                    if source:
                        collected.append(f"# From {utils_file}")
                        collected.append(source)
                        collected.append("")
                        self.embedded_items.add(func_name)
        
        return collected


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Bundle Python modules for Pipedream")
    parser.add_argument('--module', help='Bundle a specific module')
    parser.add_argument('--all', action='store_true', help='Bundle all modules')
    parser.add_argument('--output-dir', default='pipedream_modules', help='Output directory')
    
    args = parser.parse_args()
    
    # Load configuration
    if not os.path.exists(BUNDLE_CONFIG_PATH):
        print(f"Error: {BUNDLE_CONFIG_PATH} not found. Run with --create-config first.")
        return
    
    with open(BUNDLE_CONFIG_PATH, 'r') as f:
        config = json.load(f)
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    bundler = ModuleBundler()
    
    if args.all:
        # Bundle all modules
        for module_key, module_config in config['modules'].items():
            output_path = os.path.join(args.output_dir, module_config['output'])
            bundled = bundler.create_bundled_module(module_config)
            
            with open(output_path, 'w') as f:
                f.write(bundled)
            
            print(f"✓ Bundled {module_config['entry']} -> {output_path}")
            bundler.embedded_items.clear()  # Reset for next module
            
    elif args.module:
        # Bundle specific module
        if args.module in config['modules']:
            module_config = config['modules'][args.module]
            output_path = os.path.join(args.output_dir, module_config['output'])
            bundled = bundler.create_bundled_module(module_config)
            
            with open(output_path, 'w') as f:
                f.write(bundled)
            
            print(f"✓ Bundled {module_config['entry']} -> {output_path}")
        else:
            print(f"Module '{args.module}' not found in configuration")
            print(f"Available modules: {', '.join(config['modules'].keys())}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()