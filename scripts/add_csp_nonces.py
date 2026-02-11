#!/usr/bin/env python3
"""
Add nonce attribute to all inline script tags in templates for CSP compliance.
"""

import re
from pathlib import Path

def add_nonce_to_scripts(file_path: Path) -> bool:
    """Add nonce="{{ csp_nonce }}" to inline script tags without src attribute."""
    content = file_path.read_text(encoding='utf-8')
    original = content
    
    # Simple approach: find all <script> tags and check if they need nonce
    lines = content.split('\n')
    modified = False
    
    for i, line in enumerate(lines):
        # Skip if line doesn't contain <script
        if '<script' not in line.lower():
            continue
        
        # Skip external scripts (with src=)
        if 'src=' in line:
            continue
        
        # Skip if already has nonce
        if 'nonce=' in line:
            continue
        
        # Add nonce to inline script tag
        # Match: <script> or <script type="text/javascript">
        if '<script>' in line:
            lines[i] = line.replace('<script>', '<script nonce="{{ csp_nonce }}">')
            modified = True
        elif '<script ' in line and '>' in line:
            # Insert nonce before closing >
            lines[i] = line.replace('<script ', '<script nonce="{{ csp_nonce }}" ')
            modified = True
    
    if modified:
        file_path.write_text('\n'.join(lines), encoding='utf-8')
        return True
    return False

def main():
    templates_dir = Path('templates')
    updated_files = []
    
    for html_file in templates_dir.rglob('*.html'):
        if add_nonce_to_scripts(html_file):
            updated_files.append(html_file)
    
    print(f"✅ Updated {len(updated_files)} template files:")
    for f in sorted(updated_files):
        print(f"   - {f}")

if __name__ == '__main__':
    main()
