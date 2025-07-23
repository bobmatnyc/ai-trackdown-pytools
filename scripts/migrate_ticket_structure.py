#!/usr/bin/env python3
"""Migrate existing tickets to the correct directory structure.

This script migrates tickets from the old structure (tasks/tsk/) to the new structure
following the ai-trackdown schema:
- tasks/epics/ for EP-XXXX files
- tasks/issues/ for ISS-XXXX files  
- tasks/tasks/ for TSK-XXXX files
- tasks/prs/ for PR-XXXX files
"""

import os
import re
import shutil
import sys
from pathlib import Path
from typing import List, Tuple, Optional

import yaml


def parse_ticket_file(file_path: Path) -> Optional[dict]:
    """Parse a ticket file and extract frontmatter."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract frontmatter
        pattern = r'^---\s*\n(.*?)\n---\s*\n'
        match = re.match(pattern, content, re.DOTALL)
        
        if match:
            return yaml.safe_load(match.group(1))
        return None
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return None


def determine_ticket_type(ticket_data: dict, file_name: str) -> str:
    """Determine the ticket type based on content and metadata."""
    # Check if metadata contains type hints
    metadata = ticket_data.get('metadata', {})
    
    # Check for epic indicators
    if any(key in ticket_data for key in ['epic_id', 'strategic_goals', 'success_metrics']):
        return 'epic'
    if 'epic' in metadata.get('type', '').lower():
        return 'epic'
    
    # Check for issue indicators
    if any(key in ticket_data for key in ['issue_id', 'epic_reference', 'acceptance_criteria']):
        return 'issue'
    if 'issue' in metadata.get('type', '').lower():
        return 'issue'
    
    # Check for PR indicators
    if any(key in ticket_data for key in ['pr_id', 'branch_name', 'files_changed', 'review_status']):
        return 'pr'
    if 'pr' in metadata.get('type', '').lower() or 'pull' in metadata.get('type', '').lower():
        return 'pr'
    
    # Check title and description for hints
    title = ticket_data.get('title', '').lower()
    description = ticket_data.get('description', '').lower()
    
    if any(word in title for word in ['epic', 'initiative', 'strategy']):
        return 'epic'
    if any(word in title for word in ['issue', 'feature', 'enhancement', 'bug']):
        return 'issue'
    if any(word in title for word in ['pr', 'pull request', 'merge']):
        return 'pr'
    
    # Default to task
    return 'task'


def generate_new_id(ticket_type: str, counter: int) -> str:
    """Generate a new ID based on ticket type."""
    prefixes = {
        'epic': 'EP',
        'issue': 'ISS',
        'task': 'TSK',
        'pr': 'PR'
    }
    prefix = prefixes.get(ticket_type, 'TSK')
    return f"{prefix}-{counter:04d}"


def migrate_tickets(project_path: Path, dry_run: bool = True) -> List[Tuple[Path, Path, str]]:
    """Migrate tickets to the correct directory structure."""
    tasks_dir = project_path / "tasks"
    tsk_dir = tasks_dir / "tsk"
    
    if not tsk_dir.exists():
        print(f"No tsk directory found at {tsk_dir}")
        return []
    
    # Track migrations
    migrations = []
    
    # Counters for each type
    counters = {
        'epic': 1,
        'issue': 1,
        'task': 1,
        'pr': 1
    }
    
    # Process all TSK files
    for file_path in sorted(tsk_dir.glob("TSK-*.md")):
        print(f"\nProcessing: {file_path.name}")
        
        # Parse the file
        ticket_data = parse_ticket_file(file_path)
        if not ticket_data:
            print(f"  - Could not parse file, skipping")
            continue
        
        # Determine the type
        ticket_type = determine_ticket_type(ticket_data, file_path.name)
        print(f"  - Detected type: {ticket_type}")
        
        # Generate new ID if type changed
        current_id = ticket_data.get('id', file_path.stem)
        if ticket_type != 'task':
            new_id = generate_new_id(ticket_type, counters[ticket_type])
            counters[ticket_type] += 1
            print(f"  - New ID: {new_id} (was {current_id})")
        else:
            new_id = current_id
            # Extract counter from existing TSK ID
            match = re.match(r'TSK-(\d+)', current_id)
            if match:
                counters['task'] = max(counters['task'], int(match.group(1)) + 1)
        
        # Determine new path
        type_dirs = {
            'epic': 'epics',
            'issue': 'issues',
            'task': 'tasks',
            'pr': 'prs'
        }
        new_dir = tasks_dir / type_dirs[ticket_type]
        new_path = new_dir / f"{new_id}.md"
        
        # Update file content if ID changed
        if new_id != current_id:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Update ID in frontmatter
                content = re.sub(
                    r'^(---\s*\n.*?)id:\s*' + re.escape(current_id),
                    r'\1id: ' + new_id,
                    content,
                    count=1,
                    flags=re.MULTILINE | re.DOTALL
                )
                
                # Update ID references in content
                content = content.replace(current_id, new_id)
                
                if not dry_run:
                    # Write updated content to new location
                    new_dir.mkdir(exist_ok=True)
                    with open(new_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"  - Updated and moved to: {new_path}")
            except Exception as e:
                print(f"  - Error updating file: {e}")
                continue
        else:
            # Just move the file
            if not dry_run:
                new_dir.mkdir(exist_ok=True)
                shutil.move(str(file_path), str(new_path))
                print(f"  - Moved to: {new_path}")
        
        migrations.append((file_path, new_path, new_id))
    
    return migrations, counters


def update_config_counters(project_path: Path, counters: dict, dry_run: bool = True):
    """Update configuration with new counters."""
    config_path = project_path / ".ai-trackdown" / "config.yaml"
    
    if not config_path.exists():
        print(f"\nNo config file found at {config_path}")
        return
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
        
        # Update counters
        if 'tasks' not in config:
            config['tasks'] = {}
        
        config['epics'] = config.get('epics', {})
        config['epics']['counter'] = counters['epic']
        
        config['issues'] = config.get('issues', {})
        config['issues']['counter'] = counters['issue']
        
        config['tasks']['counter'] = counters['task']
        
        config['prs'] = config.get('prs', {})
        config['prs']['counter'] = counters['pr']
        
        if not dry_run:
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            print(f"\nUpdated config with new counters")
        else:
            print(f"\nWould update config with counters: {counters}")
            
    except Exception as e:
        print(f"\nError updating config: {e}")


def main():
    """Main migration function."""
    # Check for dry run flag
    dry_run = '--dry-run' in sys.argv or '-n' in sys.argv
    
    # Determine project path
    args = [arg for arg in sys.argv[1:] if not arg.startswith('-')]
    if args:
        project_path = Path(args[0])
    else:
        project_path = Path.cwd()
    
    print(f"AI Trackdown Ticket Structure Migration")
    print(f"======================================")
    print(f"Project path: {project_path}")
    print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
    print()
    
    # Check if project exists
    if not (project_path / "tasks").exists():
        print("Error: No tasks directory found")
        return 1
    
    # Perform migration
    migrations, counters = migrate_tickets(project_path, dry_run)
    
    if migrations:
        print(f"\n\nMigration Summary")
        print(f"=================")
        print(f"Total tickets: {len(migrations)}")
        print(f"Epics: {counters['epic'] - 1}")
        print(f"Issues: {counters['issue'] - 1}")
        print(f"Tasks: {counters['task'] - 1}")
        print(f"PRs: {counters['pr'] - 1}")
        
        # Update config with new counters
        update_config_counters(project_path, counters, dry_run)
        
        if dry_run:
            print(f"\n\nThis was a DRY RUN. No files were moved.")
            print(f"To execute the migration, run without --dry-run flag")
        else:
            # Remove empty tsk directory
            tsk_dir = project_path / "tasks" / "tsk"
            if tsk_dir.exists() and not list(tsk_dir.iterdir()):
                tsk_dir.rmdir()
                print(f"\nRemoved empty tsk directory")
    else:
        print("No tickets found to migrate")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())