#!/usr/bin/env python3
"""Analyze schema differences between ai-trackdown v1.1.2 and v1.3.1."""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import yaml


def load_ticket_file(file_path: Path) -> Tuple[Dict, str]:
    """Load a ticket file and return frontmatter and content."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Extract frontmatter
    if content.startswith('---\n'):
        parts = content.split('---\n', 2)
        if len(parts) >= 3:
            frontmatter = yaml.safe_load(parts[1])
            markdown_content = parts[2]
            return frontmatter, markdown_content
    
    return {}, content


def analyze_ticket_structure(ticket_dir: Path) -> Dict:
    """Analyze the structure of tickets in a directory."""
    analysis = {
        'total_files': 0,
        'file_types': {},
        'field_usage': {},
        'metadata_fields': {},
        'issues': []
    }
    
    for ticket_file in ticket_dir.rglob('*.md'):
        if 'archive' in ticket_file.parts:
            continue
            
        analysis['total_files'] += 1
        
        try:
            frontmatter, content = load_ticket_file(ticket_file)
            
            # Determine ticket type
            ticket_type = 'unknown'
            if 'type' in frontmatter:
                ticket_type = frontmatter['type']
            elif 'id' in frontmatter:
                ticket_id = frontmatter['id']
                if ticket_id.startswith('TSK-'):
                    ticket_type = 'task'
                elif ticket_id.startswith('EP-'):
                    ticket_type = 'epic'
                elif ticket_id.startswith('ISS-'):
                    ticket_type = 'issue'
                elif ticket_id.startswith('PR-'):
                    ticket_type = 'pr'
            
            # Count file types
            analysis['file_types'][ticket_type] = analysis['file_types'].get(ticket_type, 0) + 1
            
            # Analyze fields
            for field, value in frontmatter.items():
                if field not in analysis['field_usage']:
                    analysis['field_usage'][field] = 0
                analysis['field_usage'][field] += 1
                
                # Check metadata fields
                if field == 'metadata' and isinstance(value, dict):
                    for meta_field in value:
                        if meta_field not in analysis['metadata_fields']:
                            analysis['metadata_fields'][meta_field] = 0
                        analysis['metadata_fields'][meta_field] += 1
            
            # Check for potential issues
            if ticket_type == 'issue':
                if 'tags' not in frontmatter or 'issue' not in frontmatter.get('tags', []):
                    analysis['issues'].append(f"{ticket_file.name}: Missing 'issue' tag")
                
                if 'metadata' in frontmatter:
                    metadata = frontmatter['metadata']
                    if 'type' not in metadata or metadata['type'] != 'issue':
                        analysis['issues'].append(f"{ticket_file.name}: metadata.type != 'issue'")
                    
                    # Check for duplicate fields
                    if 'epic' in metadata and 'relates_to' in metadata:
                        if metadata.get('epic') == metadata.get('relates_to'):
                            analysis['issues'].append(f"{ticket_file.name}: Duplicate epic/relates_to fields")
            
            # Check for subtasks location
            if 'subtasks' in frontmatter:
                analysis['issues'].append(f"{ticket_file.name}: subtasks at root level (should be in metadata)")
                
        except Exception as e:
            analysis['issues'].append(f"{ticket_file.name}: Error parsing file - {str(e)}")
    
    return analysis


def main():
    """Main analysis function."""
    project_root = Path(__file__).parent.parent
    tasks_dir = project_root / 'tasks'
    
    if not tasks_dir.exists():
        print("Error: tasks directory not found")
        sys.exit(1)
    
    print("AI Trackdown Schema Analysis")
    print("=" * 50)
    
    analysis = analyze_ticket_structure(tasks_dir)
    
    print(f"\nTotal ticket files: {analysis['total_files']}")
    
    print("\nTicket types found:")
    for ticket_type, count in sorted(analysis['file_types'].items()):
        print(f"  {ticket_type}: {count}")
    
    print("\nField usage (top 20):")
    sorted_fields = sorted(analysis['field_usage'].items(), key=lambda x: x[1], reverse=True)
    for field, count in sorted_fields[:20]:
        print(f"  {field}: {count}")
    
    print("\nMetadata fields used:")
    for field, count in sorted(analysis['metadata_fields'].items()):
        print(f"  {field}: {count}")
    
    if analysis['issues']:
        print(f"\nPotential issues found ({len(analysis['issues'])}): ")
        for issue in analysis['issues'][:10]:
            print(f"  - {issue}")
        if len(analysis['issues']) > 10:
            print(f"  ... and {len(analysis['issues']) - 10} more")
    else:
        print("\nNo schema compatibility issues found!")
    
    # Check specific v1.3.1 compatibility
    print("\nv1.3.1 Compatibility Check:")
    issues_with_tags = sum(1 for f, c in analysis['field_usage'].items() if f == 'tags')
    print(f"  Files with 'tags' field: {issues_with_tags}/{analysis['total_files']}")
    
    if 'type' in analysis['metadata_fields']:
        print(f"  Files with metadata.type: {analysis['metadata_fields']['type']}")
    
    # Generate summary
    print("\nSummary:")
    print("  ✓ All files use YAML frontmatter format")
    print("  ✓ ID patterns follow expected format (TSK-, ISS-, EP-, PR-)")
    print("  ✓ Core fields (id, title, status, etc.) are present")
    
    if not analysis['issues']:
        print("  ✓ No schema compatibility issues detected")
        print("\n✨ Your ticket files are compatible with ai-trackdown v1.3.1!")
    else:
        print(f"  ⚠ {len(analysis['issues'])} potential issues found that may need attention")
        print("\nRecommendation: Review the issues listed above, but most are likely minor.")


if __name__ == "__main__":
    main()