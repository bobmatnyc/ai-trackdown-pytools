# Sync Adapter Implementation Guide

**Date**: 2025-07-29  
**Project**: AI Trackdown PyTools  
**Purpose**: Implementation guide for platform sync adapters

## Quick Start Implementation

### 1. Base Adapter Interface

```python
# src/ai_trackdown_pytools/sync/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from ai_trackdown_pytools.core.models import TaskModel, TaskStatus, Priority

class SyncAdapter(ABC):
    """Base class for all sync adapters"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.authenticated = False
        self.last_sync = None
        
    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the platform"""
        pass
    
    @abstractmethod
    def pull_tasks(self, since: Optional[datetime] = None) -> List[TaskModel]:
        """Pull tasks from platform since given timestamp"""
        pass
    
    @abstractmethod
    def push_task(self, task: TaskModel) -> Dict[str, Any]:
        """Push a new task to platform, return platform metadata"""
        pass
    
    @abstractmethod
    def update_task(self, task: TaskModel) -> Dict[str, Any]:
        """Update existing task on platform"""
        pass
    
    @abstractmethod
    def delete_task(self, platform_id: str) -> bool:
        """Delete task from platform"""
        pass
    
    @abstractmethod
    def map_to_platform(self, task: TaskModel) -> Dict[str, Any]:
        """Map TaskModel to platform-specific format"""
        pass
    
    @abstractmethod
    def map_from_platform(self, platform_data: Dict[str, Any]) -> TaskModel:
        """Map platform data to TaskModel"""
        pass
```

### 2. JIRA Adapter Implementation

```python
# src/ai_trackdown_pytools/sync/jira_adapter.py
from jira import JIRA
from typing import List, Dict, Any, Optional
from datetime import datetime
import os

from ai_trackdown_pytools.sync.base import SyncAdapter
from ai_trackdown_pytools.core.models import TaskModel, TaskStatus, Priority

class JiraAdapter(SyncAdapter):
    """JIRA sync adapter implementation"""
    
    # Status mapping
    STATUS_TO_JIRA = {
        TaskStatus.OPEN: "To Do",
        TaskStatus.IN_PROGRESS: "In Progress",
        TaskStatus.COMPLETED: "Done",
        TaskStatus.CANCELLED: "Won't Do",
        TaskStatus.BLOCKED: "Blocked"
    }
    
    STATUS_FROM_JIRA = {v: k for k, v in STATUS_TO_JIRA.items()}
    
    # Priority mapping
    PRIORITY_TO_JIRA = {
        Priority.LOW: "Low",
        Priority.MEDIUM: "Medium",
        Priority.HIGH: "High",
        Priority.CRITICAL: "Highest"
    }
    
    PRIORITY_FROM_JIRA = {v: k for k, v in PRIORITY_TO_JIRA.items()}
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.jira = None
        self.project_key = config.get('project_key', 'PROJ')
        
    def authenticate(self) -> bool:
        """Authenticate with JIRA"""
        try:
            server = self.config.get('server')
            email = self.config.get('email') or os.getenv('JIRA_EMAIL')
            api_token = self.config.get('api_token') or os.getenv('JIRA_API_TOKEN')
            
            self.jira = JIRA(
                server=server,
                basic_auth=(email, api_token)
            )
            
            # Test authentication
            self.jira.myself()
            self.authenticated = True
            return True
            
        except Exception as e:
            print(f"JIRA authentication failed: {e}")
            return False
    
    def pull_tasks(self, since: Optional[datetime] = None) -> List[TaskModel]:
        """Pull tasks from JIRA"""
        if not self.authenticated:
            raise RuntimeError("Not authenticated with JIRA")
        
        # Build JQL query
        jql = f"project = {self.project_key}"
        if since:
            jql += f" AND updated >= '{since.strftime('%Y-%m-%d %H:%M')}'"
        
        # Search issues
        issues = self.jira.search_issues(jql, maxResults=False)
        
        tasks = []
        for issue in issues:
            try:
                task = self.map_from_platform(issue.raw)
                tasks.append(task)
            except Exception as e:
                print(f"Error mapping JIRA issue {issue.key}: {e}")
                
        return tasks
    
    def push_task(self, task: TaskModel) -> Dict[str, Any]:
        """Create new issue in JIRA"""
        if not self.authenticated:
            raise RuntimeError("Not authenticated with JIRA")
        
        issue_dict = self.map_to_platform(task)
        issue = self.jira.create_issue(**issue_dict)
        
        return {
            'jira_id': issue.id,
            'jira_key': issue.key,
            'jira_url': f"{self.config['server']}/browse/{issue.key}"
        }
    
    def update_task(self, task: TaskModel) -> Dict[str, Any]:
        """Update existing JIRA issue"""
        if not self.authenticated:
            raise RuntimeError("Not authenticated with JIRA")
        
        jira_key = task.metadata.get('jira_key')
        if not jira_key:
            raise ValueError("Task missing jira_key in metadata")
        
        issue = self.jira.issue(jira_key)
        update_fields = self.map_to_platform(task)
        
        # Remove project key from updates
        update_fields.pop('project', None)
        
        issue.update(**update_fields)
        
        return {
            'jira_id': issue.id,
            'jira_key': issue.key,
            'updated': True
        }
    
    def delete_task(self, platform_id: str) -> bool:
        """Delete JIRA issue"""
        if not self.authenticated:
            raise RuntimeError("Not authenticated with JIRA")
        
        try:
            issue = self.jira.issue(platform_id)
            issue.delete()
            return True
        except Exception as e:
            print(f"Error deleting JIRA issue {platform_id}: {e}")
            return False
    
    def map_to_platform(self, task: TaskModel) -> Dict[str, Any]:
        """Map TaskModel to JIRA issue format"""
        fields = {
            'project': {'key': self.project_key},
            'summary': task.title,
            'description': task.description or '',
            'issuetype': {'name': 'Task'},
        }
        
        # Map status
        if task.status in self.STATUS_TO_JIRA:
            # Note: Status transitions must be handled separately in JIRA
            pass
        
        # Map priority
        if task.priority in self.PRIORITY_TO_JIRA:
            fields['priority'] = {'name': self.PRIORITY_TO_JIRA[task.priority]}
        
        # Map assignee
        if task.assignees and len(task.assignees) > 0:
            fields['assignee'] = {'emailAddress': task.assignees[0]}
        
        # Map labels
        if task.tags:
            fields['labels'] = task.tags
        
        # Map due date
        if hasattr(task, 'due_date') and task.due_date:
            fields['duedate'] = task.due_date.isoformat()
        
        return fields
    
    def map_from_platform(self, jira_data: Dict[str, Any]) -> TaskModel:
        """Map JIRA issue to TaskModel"""
        fields = jira_data.get('fields', {})
        
        # Map basic fields
        task_data = {
            'id': f"TSK-{jira_data['id']}",  # Generate local ID
            'title': fields.get('summary', 'Untitled'),
            'description': fields.get('description', ''),
            'created_at': datetime.fromisoformat(fields['created'].replace('Z', '+00:00')),
            'updated_at': datetime.fromisoformat(fields['updated'].replace('Z', '+00:00')),
            'metadata': {
                'jira_id': jira_data['id'],
                'jira_key': jira_data['key'],
                'jira_url': jira_data.get('self', ''),
                'source': 'jira'
            }
        }
        
        # Map status
        status_name = fields.get('status', {}).get('name', 'To Do')
        task_data['status'] = self.STATUS_FROM_JIRA.get(
            status_name, 
            TaskStatus.OPEN
        )
        
        # Map priority
        priority_name = fields.get('priority', {}).get('name', 'Medium')
        task_data['priority'] = self.PRIORITY_FROM_JIRA.get(
            priority_name,
            Priority.MEDIUM
        )
        
        # Map assignees
        assignee = fields.get('assignee')
        if assignee:
            task_data['assignees'] = [assignee.get('emailAddress', assignee.get('displayName'))]
        else:
            task_data['assignees'] = []
        
        # Map tags from labels
        task_data['tags'] = fields.get('labels', [])
        
        # Map due date
        if fields.get('duedate'):
            task_data['due_date'] = datetime.fromisoformat(fields['duedate']).date()
        
        return TaskModel(**task_data)
```

### 3. ClickUp Adapter Implementation

```python
# src/ai_trackdown_pytools/sync/clickup_adapter.py
from pyclickup import ClickUp
from typing import List, Dict, Any, Optional
from datetime import datetime
import os

from ai_trackdown_pytools.sync.base import SyncAdapter
from ai_trackdown_pytools.core.models import TaskModel, TaskStatus, Priority

class ClickUpAdapter(SyncAdapter):
    """ClickUp sync adapter implementation"""
    
    # Status mapping (customizable per list)
    DEFAULT_STATUS_MAP = {
        TaskStatus.OPEN: "open",
        TaskStatus.IN_PROGRESS: "in progress",
        TaskStatus.COMPLETED: "closed",
        TaskStatus.CANCELLED: "archived",
        TaskStatus.BLOCKED: "blocked"
    }
    
    # Priority mapping (ClickUp uses 1-4, 1 being highest)
    PRIORITY_TO_CLICKUP = {
        Priority.CRITICAL: 1,
        Priority.HIGH: 2,
        Priority.MEDIUM: 3,
        Priority.LOW: 4
    }
    
    PRIORITY_FROM_CLICKUP = {v: k for k, v in PRIORITY_TO_CLICKUP.items()}
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.clickup = None
        self.list_id = config.get('list_id')
        
    def authenticate(self) -> bool:
        """Authenticate with ClickUp"""
        try:
            api_token = self.config.get('api_token') or os.getenv('CLICKUP_API_TOKEN')
            self.clickup = ClickUp(api_token)
            
            # Test authentication by getting user
            self.clickup.user
            self.authenticated = True
            return True
            
        except Exception as e:
            print(f"ClickUp authentication failed: {e}")
            return False
    
    def pull_tasks(self, since: Optional[datetime] = None) -> List[TaskModel]:
        """Pull tasks from ClickUp"""
        if not self.authenticated:
            raise RuntimeError("Not authenticated with ClickUp")
        
        # Get list
        list_obj = self.clickup.lists.get_list(self.list_id)
        
        # Get tasks with optional date filter
        params = {}
        if since:
            params['date_updated_gt'] = int(since.timestamp() * 1000)  # ClickUp uses milliseconds
        
        tasks_data = list_obj.get_tasks(**params)
        
        tasks = []
        for task_data in tasks_data:
            try:
                task = self.map_from_platform(task_data)
                tasks.append(task)
            except Exception as e:
                print(f"Error mapping ClickUp task {task_data.get('id')}: {e}")
                
        return tasks
    
    def push_task(self, task: TaskModel) -> Dict[str, Any]:
        """Create new task in ClickUp"""
        if not self.authenticated:
            raise RuntimeError("Not authenticated with ClickUp")
        
        task_data = self.map_to_platform(task)
        list_obj = self.clickup.lists.get_list(self.list_id)
        
        created_task = list_obj.create_task(**task_data)
        
        return {
            'clickup_id': created_task['id'],
            'clickup_url': created_task.get('url', '')
        }
    
    def update_task(self, task: TaskModel) -> Dict[str, Any]:
        """Update existing ClickUp task"""
        if not self.authenticated:
            raise RuntimeError("Not authenticated with ClickUp")
        
        clickup_id = task.metadata.get('clickup_id')
        if not clickup_id:
            raise ValueError("Task missing clickup_id in metadata")
        
        update_data = self.map_to_platform(task)
        
        # ClickUp API endpoint for updating task
        # Using direct API call as pyclickup might not support all updates
        import requests
        
        headers = {
            'Authorization': self.clickup.token,
            'Content-Type': 'application/json'
        }
        
        response = requests.put(
            f'https://api.clickup.com/api/v2/task/{clickup_id}',
            headers=headers,
            json=update_data
        )
        
        if response.status_code == 200:
            return {
                'clickup_id': clickup_id,
                'updated': True
            }
        else:
            raise Exception(f"Failed to update task: {response.text}")
    
    def delete_task(self, platform_id: str) -> bool:
        """Delete ClickUp task"""
        if not self.authenticated:
            raise RuntimeError("Not authenticated with ClickUp")
        
        try:
            # Direct API call for deletion
            import requests
            
            headers = {'Authorization': self.clickup.token}
            response = requests.delete(
                f'https://api.clickup.com/api/v2/task/{platform_id}',
                headers=headers
            )
            
            return response.status_code == 204
            
        except Exception as e:
            print(f"Error deleting ClickUp task {platform_id}: {e}")
            return False
    
    def map_to_platform(self, task: TaskModel) -> Dict[str, Any]:
        """Map TaskModel to ClickUp task format"""
        data = {
            'name': task.title,
            'description': task.description or '',
            'tags': task.tags,
        }
        
        # Map status
        if task.status in self.DEFAULT_STATUS_MAP:
            data['status'] = self.DEFAULT_STATUS_MAP[task.status]
        
        # Map priority
        if task.priority in self.PRIORITY_TO_CLICKUP:
            data['priority'] = self.PRIORITY_TO_CLICKUP[task.priority]
        
        # Map assignees (ClickUp uses user IDs, need lookup)
        if task.assignees:
            # This would require user ID lookup
            pass
        
        # Map due date
        if hasattr(task, 'due_date') and task.due_date:
            data['due_date'] = int(task.due_date.timestamp() * 1000)
        
        # Map time estimate
        if hasattr(task, 'estimated_hours') and task.estimated_hours:
            data['time_estimate'] = int(task.estimated_hours * 3600 * 1000)  # Convert to milliseconds
        
        return data
    
    def map_from_platform(self, clickup_data: Dict[str, Any]) -> TaskModel:
        """Map ClickUp task to TaskModel"""
        task_data = {
            'id': f"TSK-{clickup_data['id']}",  # Generate local ID
            'title': clickup_data.get('name', 'Untitled'),
            'description': clickup_data.get('description', ''),
            'created_at': datetime.fromtimestamp(int(clickup_data['date_created']) / 1000),
            'updated_at': datetime.fromtimestamp(int(clickup_data['date_updated']) / 1000),
            'metadata': {
                'clickup_id': clickup_data['id'],
                'clickup_url': clickup_data.get('url', ''),
                'source': 'clickup'
            }
        }
        
        # Map status
        status = clickup_data.get('status', {}).get('status', 'open')
        # Reverse lookup in status map
        for ts, cs in self.DEFAULT_STATUS_MAP.items():
            if cs == status.lower():
                task_data['status'] = ts
                break
        else:
            task_data['status'] = TaskStatus.OPEN
        
        # Map priority
        priority = clickup_data.get('priority')
        if priority and priority.get('priority'):
            priority_num = int(priority['priority'])
            task_data['priority'] = self.PRIORITY_FROM_CLICKUP.get(
                priority_num,
                Priority.MEDIUM
            )
        else:
            task_data['priority'] = Priority.MEDIUM
        
        # Map assignees
        assignees = clickup_data.get('assignees', [])
        task_data['assignees'] = [a.get('email', a.get('username')) for a in assignees]
        
        # Map tags
        task_data['tags'] = [tag['name'] for tag in clickup_data.get('tags', [])]
        
        # Map due date
        if clickup_data.get('due_date'):
            task_data['due_date'] = datetime.fromtimestamp(
                int(clickup_data['due_date']) / 1000
            ).date()
        
        # Map time estimate
        if clickup_data.get('time_estimate'):
            task_data['estimated_hours'] = int(clickup_data['time_estimate']) / (3600 * 1000)
        
        return TaskModel(**task_data)
```

### 4. Linear Adapter Implementation

```python
# src/ai_trackdown_pytools/sync/linear_adapter.py
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
from typing import List, Dict, Any, Optional
from datetime import datetime
import os

from ai_trackdown_pytools.sync.base import SyncAdapter
from ai_trackdown_pytools.core.models import TaskModel, TaskStatus, Priority

class LinearAdapter(SyncAdapter):
    """Linear sync adapter implementation"""
    
    # Status mapping
    STATUS_TO_LINEAR = {
        TaskStatus.OPEN: "Todo",
        TaskStatus.IN_PROGRESS: "In Progress",
        TaskStatus.COMPLETED: "Done",
        TaskStatus.CANCELLED: "Canceled",
        TaskStatus.BLOCKED: "Todo"  # Linear doesn't have blocked state
    }
    
    # Priority mapping (Linear uses 0-4, 0 being none)
    PRIORITY_TO_LINEAR = {
        Priority.CRITICAL: 1,
        Priority.HIGH: 2,
        Priority.MEDIUM: 3,
        Priority.LOW: 4
    }
    
    PRIORITY_FROM_LINEAR = {v: k for k, v in PRIORITY_TO_LINEAR.items()}
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.client = None
        self.team_id = config.get('team_id')
        
    def authenticate(self) -> bool:
        """Authenticate with Linear"""
        try:
            api_key = self.config.get('api_key') or os.getenv('LINEAR_API_KEY')
            
            transport = RequestsHTTPTransport(
                url="https://api.linear.app/graphql",
                headers={"Authorization": api_key}
            )
            
            self.client = Client(transport=transport, fetch_schema_from_transport=True)
            
            # Test authentication
            query = gql("""
                query {
                    viewer {
                        id
                        email
                    }
                }
            """)
            
            self.client.execute(query)
            self.authenticated = True
            return True
            
        except Exception as e:
            print(f"Linear authentication failed: {e}")
            return False
    
    def pull_tasks(self, since: Optional[datetime] = None) -> List[TaskModel]:
        """Pull issues from Linear"""
        if not self.authenticated:
            raise RuntimeError("Not authenticated with Linear")
        
        # Build query with optional date filter
        filter_clause = ""
        if since:
            filter_clause = f', filter: {{ updatedAt: {{ gte: "{since.isoformat()}" }} }}'
        
        query = gql(f"""
            query {{
                issues(first: 100{filter_clause}) {{
                    nodes {{
                        id
                        title
                        description
                        state {{
                            name
                        }}
                        priority
                        assignee {{
                            email
                            displayName
                        }}
                        labels {{
                            nodes {{
                                name
                            }}
                        }}
                        createdAt
                        updatedAt
                        dueDate
                        estimate
                    }}
                }}
            }}
        """)
        
        result = self.client.execute(query)
        
        tasks = []
        for issue in result['issues']['nodes']:
            try:
                task = self.map_from_platform(issue)
                tasks.append(task)
            except Exception as e:
                print(f"Error mapping Linear issue {issue['id']}: {e}")
                
        return tasks
    
    def push_task(self, task: TaskModel) -> Dict[str, Any]:
        """Create new issue in Linear"""
        if not self.authenticated:
            raise RuntimeError("Not authenticated with Linear")
        
        issue_data = self.map_to_platform(task)
        
        mutation = gql("""
            mutation CreateIssue($input: IssueCreateInput!) {
                issueCreate(input: $input) {
                    issue {
                        id
                        url
                    }
                    success
                }
            }
        """)
        
        variables = {"input": issue_data}
        result = self.client.execute(mutation, variable_values=variables)
        
        if result['issueCreate']['success']:
            issue = result['issueCreate']['issue']
            return {
                'linear_id': issue['id'],
                'linear_url': issue['url']
            }
        else:
            raise Exception("Failed to create Linear issue")
    
    def update_task(self, task: TaskModel) -> Dict[str, Any]:
        """Update existing Linear issue"""
        if not self.authenticated:
            raise RuntimeError("Not authenticated with Linear")
        
        linear_id = task.metadata.get('linear_id')
        if not linear_id:
            raise ValueError("Task missing linear_id in metadata")
        
        update_data = self.map_to_platform(task)
        
        mutation = gql("""
            mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
                issueUpdate(id: $id, input: $input) {
                    issue {
                        id
                    }
                    success
                }
            }
        """)
        
        variables = {
            "id": linear_id,
            "input": update_data
        }
        
        result = self.client.execute(mutation, variable_values=variables)
        
        if result['issueUpdate']['success']:
            return {
                'linear_id': linear_id,
                'updated': True
            }
        else:
            raise Exception("Failed to update Linear issue")
    
    def delete_task(self, platform_id: str) -> bool:
        """Archive Linear issue (Linear doesn't delete, only archives)"""
        if not self.authenticated:
            raise RuntimeError("Not authenticated with Linear")
        
        try:
            mutation = gql("""
                mutation ArchiveIssue($id: String!) {
                    issueArchive(id: $id) {
                        success
                    }
                }
            """)
            
            variables = {"id": platform_id}
            result = self.client.execute(mutation, variable_values=variables)
            
            return result['issueArchive']['success']
            
        except Exception as e:
            print(f"Error archiving Linear issue {platform_id}: {e}")
            return False
    
    def map_to_platform(self, task: TaskModel) -> Dict[str, Any]:
        """Map TaskModel to Linear issue format"""
        data = {
            'title': task.title,
            'description': task.description or '',
            'teamId': self.team_id,
        }
        
        # Map priority
        if task.priority in self.PRIORITY_TO_LINEAR:
            data['priority'] = self.PRIORITY_TO_LINEAR[task.priority]
        
        # Map labels (tags)
        if task.tags:
            data['labelIds'] = []  # Would need to look up label IDs
        
        # Map due date
        if hasattr(task, 'due_date') and task.due_date:
            data['dueDate'] = task.due_date.isoformat()
        
        # Map estimate
        if hasattr(task, 'estimated_hours') and task.estimated_hours:
            data['estimate'] = int(task.estimated_hours)  # Linear uses points, not hours
        
        # Note: Status transitions in Linear require workflow state IDs
        # This would need additional API calls to map properly
        
        return data
    
    def map_from_platform(self, linear_data: Dict[str, Any]) -> TaskModel:
        """Map Linear issue to TaskModel"""
        task_data = {
            'id': f"TSK-{linear_data['id']}",  # Generate local ID
            'title': linear_data.get('title', 'Untitled'),
            'description': linear_data.get('description', ''),
            'created_at': datetime.fromisoformat(linear_data['createdAt'].replace('Z', '+00:00')),
            'updated_at': datetime.fromisoformat(linear_data['updatedAt'].replace('Z', '+00:00')),
            'metadata': {
                'linear_id': linear_data['id'],
                'source': 'linear'
            }
        }
        
        # Map status
        state_name = linear_data.get('state', {}).get('name', 'Todo')
        # Simple mapping - would need more sophisticated state mapping
        if 'Done' in state_name or 'Completed' in state_name:
            task_data['status'] = TaskStatus.COMPLETED
        elif 'Progress' in state_name:
            task_data['status'] = TaskStatus.IN_PROGRESS
        elif 'Cancel' in state_name:
            task_data['status'] = TaskStatus.CANCELLED
        else:
            task_data['status'] = TaskStatus.OPEN
        
        # Map priority
        priority = linear_data.get('priority', 0)
        task_data['priority'] = self.PRIORITY_FROM_LINEAR.get(
            priority,
            Priority.MEDIUM
        )
        
        # Map assignee
        assignee = linear_data.get('assignee')
        if assignee:
            task_data['assignees'] = [assignee.get('email', assignee.get('displayName'))]
        else:
            task_data['assignees'] = []
        
        # Map labels to tags
        labels = linear_data.get('labels', {}).get('nodes', [])
        task_data['tags'] = [label['name'] for label in labels]
        
        # Map due date
        if linear_data.get('dueDate'):
            task_data['due_date'] = datetime.fromisoformat(linear_data['dueDate']).date()
        
        # Map estimate to hours (Linear uses points)
        if linear_data.get('estimate'):
            task_data['estimated_hours'] = float(linear_data['estimate'])
        
        return TaskModel(**task_data)
```

### 5. Sync Manager

```python
# src/ai_trackdown_pytools/sync/manager.py
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
from pathlib import Path

from ai_trackdown_pytools.sync.base import SyncAdapter
from ai_trackdown_pytools.sync.jira_adapter import JiraAdapter
from ai_trackdown_pytools.sync.clickup_adapter import ClickUpAdapter
from ai_trackdown_pytools.sync.linear_adapter import LinearAdapter
from ai_trackdown_pytools.core.task import TaskManager

class SyncManager:
    """Manages synchronization with external platforms"""
    
    ADAPTERS = {
        'jira': JiraAdapter,
        'clickup': ClickUpAdapter,
        'linear': LinearAdapter
    }
    
    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.task_manager = TaskManager(project_path)
        self.sync_state_file = project_path / '.aitrackdown' / 'sync_state.json'
        self.sync_state = self._load_sync_state()
        
    def _load_sync_state(self) -> Dict[str, Any]:
        """Load sync state from file"""
        if self.sync_state_file.exists():
            with open(self.sync_state_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_sync_state(self):
        """Save sync state to file"""
        self.sync_state_file.parent.mkdir(exist_ok=True)
        with open(self.sync_state_file, 'w') as f:
            json.dump(self.sync_state, f, indent=2, default=str)
    
    def get_adapter(self, platform: str, config: Dict[str, Any]) -> SyncAdapter:
        """Get sync adapter for platform"""
        if platform not in self.ADAPTERS:
            raise ValueError(f"Unknown platform: {platform}")
        
        adapter_class = self.ADAPTERS[platform]
        return adapter_class(config)
    
    def sync_pull(self, platform: str, config: Dict[str, Any]) -> Tuple[int, int]:
        """Pull tasks from platform"""
        adapter = self.get_adapter(platform, config)
        
        if not adapter.authenticate():
            raise RuntimeError(f"Failed to authenticate with {platform}")
        
        # Get last sync time
        platform_state = self.sync_state.get(platform, {})
        last_sync = platform_state.get('last_pull')
        if last_sync:
            last_sync = datetime.fromisoformat(last_sync)
        
        # Pull tasks
        remote_tasks = adapter.pull_tasks(since=last_sync)
        
        created = 0
        updated = 0
        
        for remote_task in remote_tasks:
            # Check if task exists locally
            platform_id_key = f'{platform}_id'
            existing_tasks = [
                t for t in self.task_manager.list_tasks()
                if t.metadata.get(platform_id_key) == remote_task.metadata[platform_id_key]
            ]
            
            if existing_tasks:
                # Update existing task
                existing_task = existing_tasks[0]
                self.task_manager.update_task(
                    existing_task.id,
                    title=remote_task.title,
                    description=remote_task.description,
                    status=remote_task.status.value,
                    priority=remote_task.priority.value,
                    tags=remote_task.tags,
                    assignees=remote_task.assignees,
                    metadata={**existing_task.metadata, **remote_task.metadata}
                )
                updated += 1
            else:
                # Create new task
                self.task_manager.create_task(
                    title=remote_task.title,
                    description=remote_task.description,
                    status=remote_task.status.value,
                    priority=remote_task.priority.value,
                    tags=remote_task.tags,
                    assignees=remote_task.assignees,
                    metadata=remote_task.metadata
                )
                created += 1
        
        # Update sync state
        self.sync_state[platform] = {
            **platform_state,
            'last_pull': datetime.now().isoformat()
        }
        self._save_sync_state()
        
        return created, updated
    
    def sync_push(self, platform: str, config: Dict[str, Any]) -> Tuple[int, int]:
        """Push tasks to platform"""
        adapter = self.get_adapter(platform, config)
        
        if not adapter.authenticate():
            raise RuntimeError(f"Failed to authenticate with {platform}")
        
        platform_id_key = f'{platform}_id'
        
        # Find tasks to sync
        all_tasks = self.task_manager.list_tasks()
        unsynced_tasks = [
            t for t in all_tasks
            if not t.metadata.get(platform_id_key)
        ]
        
        created = 0
        updated = 0
        
        for task in unsynced_tasks:
            try:
                # Push to platform
                platform_metadata = adapter.push_task(task)
                
                # Update local task with platform metadata
                self.task_manager.update_task(
                    task.id,
                    metadata={**task.metadata, **platform_metadata}
                )
                
                created += 1
                
            except Exception as e:
                print(f"Error pushing task {task.id}: {e}")
        
        # Update existing synced tasks
        synced_tasks = [
            t for t in all_tasks
            if t.metadata.get(platform_id_key)
        ]
        
        platform_state = self.sync_state.get(platform, {})
        last_push = platform_state.get('last_push')
        if last_push:
            last_push = datetime.fromisoformat(last_push)
        
        for task in synced_tasks:
            # Only update if modified since last push
            if not last_push or task.updated_at > last_push:
                try:
                    adapter.update_task(task)
                    updated += 1
                except Exception as e:
                    print(f"Error updating task {task.id}: {e}")
        
        # Update sync state
        self.sync_state[platform] = {
            **platform_state,
            'last_push': datetime.now().isoformat()
        }
        self._save_sync_state()
        
        return created, updated
```

## Configuration Examples

### 1. JIRA Configuration
```json
{
  "jira": {
    "server": "https://your-domain.atlassian.net",
    "email": "your-email@example.com",
    "api_token": "your-api-token",
    "project_key": "PROJ"
  }
}
```

### 2. ClickUp Configuration
```json
{
  "clickup": {
    "api_token": "your-clickup-token",
    "list_id": "123456789"
  }
}
```

### 3. Linear Configuration
```json
{
  "linear": {
    "api_key": "your-linear-api-key",
    "team_id": "TEAM-UUID"
  }
}
```

## CLI Integration

```python
# Add to src/ai_trackdown_pytools/commands/sync.py

@app.command()
def adapter(
    platform: str = typer.Argument(..., help="Platform to sync (jira, clickup, linear)"),
    action: str = typer.Argument(..., help="Action to perform (pull, push, status)"),
    config_file: Optional[str] = typer.Option(
        None, "--config", "-c", help="Platform configuration file"
    ),
) -> None:
    """Sync with external platforms using adapters."""
    project_path = Path.cwd()
    
    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)
    
    # Load configuration
    if config_file:
        with open(config_file, 'r') as f:
            platform_config = json.load(f).get(platform, {})
    else:
        # Load from project sync config
        sync_config_file = project_path / '.aitrackdown' / 'sync.json'
        if sync_config_file.exists():
            with open(sync_config_file, 'r') as f:
                platform_config = json.load(f).get(platform, {})
        else:
            console.print(f"[red]No configuration found for {platform}[/red]")
            raise typer.Exit(1)
    
    sync_manager = SyncManager(project_path)
    
    if action == "pull":
        console.print(f"[blue]Pulling tasks from {platform}...[/blue]")
        created, updated = sync_manager.sync_pull(platform, platform_config)
        console.print(f"[green]Created: {created}, Updated: {updated}[/green]")
        
    elif action == "push":
        console.print(f"[blue]Pushing tasks to {platform}...[/blue]")
        created, updated = sync_manager.sync_push(platform, platform_config)
        console.print(f"[green]Created: {created}, Updated: {updated}[/green]")
        
    elif action == "status":
        # Show sync status
        state = sync_manager.sync_state.get(platform, {})
        console.print(Panel.fit(
            f"""[bold blue]{platform.title()} Sync Status[/bold blue]
            
Last Pull: {state.get('last_pull', 'Never')}
Last Push: {state.get('last_push', 'Never')}
            """,
            title="Sync Status",
            border_style="blue"
        ))
```

## Testing Strategy

### 1. Unit Tests
```python
# tests/unit/test_sync_adapters.py
import pytest
from unittest.mock import Mock, patch
from ai_trackdown_pytools.sync.jira_adapter import JiraAdapter
from ai_trackdown_pytools.core.models import TaskModel, TaskStatus

def test_jira_adapter_map_to_platform():
    """Test mapping TaskModel to JIRA format"""
    adapter = JiraAdapter({'project_key': 'TEST'})
    
    task = TaskModel(
        id='TSK-001',
        title='Test Task',
        description='Test Description',
        status=TaskStatus.IN_PROGRESS,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    jira_data = adapter.map_to_platform(task)
    
    assert jira_data['summary'] == 'Test Task'
    assert jira_data['description'] == 'Test Description'
    assert jira_data['project']['key'] == 'TEST'
```

### 2. Integration Tests
```python
# tests/integration/test_sync_manager.py
import pytest
from ai_trackdown_pytools.sync.manager import SyncManager

@pytest.mark.integration
def test_sync_manager_pull(tmp_path):
    """Test pulling tasks from platform"""
    # Set up test project
    project = Project.create(tmp_path)
    sync_manager = SyncManager(tmp_path)
    
    # Mock configuration
    config = {
        'server': 'https://test.atlassian.net',
        'email': 'test@example.com',
        'api_token': 'test-token',
        'project_key': 'TEST'
    }
    
    # Test pull (would need to mock JIRA responses)
    with patch('jira.JIRA'):
        created, updated = sync_manager.sync_pull('jira', config)
        assert created >= 0
        assert updated >= 0
```

## Next Steps

1. Implement webhook receivers for real-time updates
2. Add conflict resolution strategies
3. Implement field mapping configuration UI
4. Add support for attachments and comments
5. Create sync scheduling with cron/systemd
6. Add sync performance metrics and monitoring
7. Implement bulk operations for better performance
8. Add support for custom field mapping rules