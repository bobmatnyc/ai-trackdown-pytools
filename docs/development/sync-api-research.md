# Sync Adapter API Research Report

**Date**: 2025-07-29  
**Project**: AI Trackdown PyTools  
**Purpose**: Research external platform APIs for implementing sync adapters

## Executive Summary

This report provides comprehensive research on ClickUp, Linear, and JIRA APIs for implementing sync adapters in the AI Trackdown PyTools project. Each platform offers different API architectures, authentication methods, and field structures that need to be mapped to our TaskModel.

## Platform API Overview

### 1. ClickUp API v2

#### Authentication
- **Personal API Token**: Simple token-based auth for personal use
  - Generate from Settings → Apps → API Token
  - Include in `Authorization` header
- **OAuth 2.0**: For multi-user applications
  - More secure and manageable
  - Requires OAuth app registration

#### Rate Limits
- Basic/Unlimited/Business: 100 requests/minute/token
- Business Plus: 1,000 requests/minute/token
- Enterprise: 10,000 requests/minute/token

#### Core Endpoints for Sync
```
GET    /team                     # Get teams
GET    /team/{team_id}/space      # Get spaces
GET    /list/{list_id}/task       # Get tasks
POST   /list/{list_id}/task       # Create task
PUT    /task/{task_id}            # Update task
GET    /task/{task_id}            # Get single task
DELETE /task/{task_id}            # Delete task
```

#### Data Model Mapping
```python
# ClickUp Task → TaskModel
{
    "id": "task_id",              # → metadata.clickup_id
    "name": "Task Name",           # → title
    "description": "...",          # → description  
    "status": {"status": "open"},  # → status (needs mapping)
    "priority": {"priority": "high"}, # → priority (needs mapping)
    "assignees": [...],            # → assignees
    "tags": [...],                 # → tags
    "date_created": "...",         # → created_at
    "date_updated": "...",         # → updated_at
    "due_date": "...",             # → due_date
    "time_estimate": ...,          # → estimated_hours (ms to hours)
    "custom_fields": [...]         # → metadata.custom_fields
}
```

### 2. Linear GraphQL API

#### Authentication
- **Personal API Keys**: For personal scripts
  - Pass as `Authorization: <API_KEY>` header
- **OAuth 2.0**: For applications
  - Pass as `Authorization: Bearer <ACCESS_TOKEN>` header

#### Rate Limits  
- API Key auth: 1,500 requests/hour/user
- OAuth app auth: 500 requests/hour/user/app

#### GraphQL Endpoint
```
POST https://api.linear.app/graphql
```

#### Core Queries/Mutations for Sync
```graphql
# List issues
query {
  issues(first: 100) {
    nodes {
      id
      title
      description
      state { name }
      priority
      assignee { email }
      labels { nodes { name } }
      createdAt
      updatedAt
      dueDate
    }
  }
}

# Create issue
mutation CreateIssue($input: IssueCreateInput!) {
  issueCreate(input: $input) {
    issue { id }
    success
  }
}

# Update issue  
mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
  issueUpdate(id: $id, input: $input) {
    issue { id }
    success
  }
}
```

#### Data Model Mapping
```python
# Linear Issue → TaskModel
{
    "id": "issue_id",              # → metadata.linear_id
    "title": "Issue Title",        # → title
    "description": "...",          # → description
    "state": {"name": "Todo"},     # → status (needs mapping)
    "priority": 1,                 # → priority (1-4 scale to our enum)
    "assignee": {"email": "..."},  # → assignees
    "labels": [{"name": "..."}],   # → tags
    "createdAt": "...",            # → created_at
    "updatedAt": "...",            # → updated_at
    "dueDate": "...",              # → due_date
    "estimate": ...,               # → estimated_hours
}
```

### 3. JIRA REST API v3

#### Authentication
- **API Token + Email**: For JIRA Cloud (recommended)
  - Use email address + API token in basic auth
  - Generate token from Atlassian account settings
- **OAuth 2.0**: For production applications
  - More complex but more secure

#### Rate Limits
- Varies by plan and endpoint
- Generally 50-100 requests per minute

#### Core Endpoints for Sync
```
GET    /rest/api/3/search         # Search issues with JQL
POST   /rest/api/3/issue          # Create issue
PUT    /rest/api/3/issue/{key}    # Update issue
GET    /rest/api/3/issue/{key}    # Get single issue
DELETE /rest/api/3/issue/{key}    # Delete issue
GET    /rest/api/3/field          # Get custom fields
```

#### Data Model Mapping
```python
# JIRA Issue → TaskModel
{
    "id": "10001",                 # → metadata.jira_id
    "key": "PROJ-123",             # → metadata.jira_key
    "fields": {
        "summary": "Issue Title",  # → title
        "description": "...",      # → description
        "status": {"name": "To Do"}, # → status (needs mapping)
        "priority": {"name": "High"}, # → priority (needs mapping)
        "assignee": {"emailAddress": "..."}, # → assignees
        "labels": [...],           # → tags
        "created": "...",          # → created_at
        "updated": "...",          # → updated_at
        "duedate": "...",          # → due_date
        "timeoriginalestimate": ..., # → estimated_hours (seconds to hours)
        "customfield_*": ...       # → metadata.custom_fields
    }
}
```

## Python Library Assessment

### 1. ClickUp Python Libraries

#### PyClickUp (Recommended)
- **Repository**: https://github.com/jpetrucciani/pyclickup
- **Installation**: `pip install pyclickup`
- **Status**: Active community library
- **Example**:
```python
from pyclickup import ClickUp

clickup = ClickUp("$ACCESS_TOKEN")
team = clickup.teams[0]
space = team.spaces[0]
tasks = space.lists[0].get_tasks()
```

#### ClickUp Python Client
- **Repository**: https://github.com/secdevopsai/ClickUp
- **Installation**: `pip install clickup-python`
- **Status**: Less actively maintained

### 2. Linear Python Libraries

**No Official Python SDK** - Use generic GraphQL clients:

#### GQL (Recommended)
- **Installation**: `pip install gql[all]`
- **Example**:
```python
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

transport = RequestsHTTPTransport(
    url="https://api.linear.app/graphql",
    headers={"Authorization": api_key}
)

client = Client(transport=transport)
```

### 3. JIRA Python Library

#### jira-python (Official, Recommended)
- **Installation**: `pip install jira`
- **Version**: 3.10.5+ 
- **Status**: Official Atlassian library, actively maintained
- **Example**:
```python
from jira import JIRA

jira = JIRA(
    server="https://your-domain.atlassian.net",
    basic_auth=("email@example.com", "api-token")
)

issues = jira.search_issues('project=PROJ')
```

## Feature Comparison Matrix

| Feature | ClickUp | Linear | JIRA | Notes |
|---------|---------|--------|------|-------|
| **API Type** | REST v2 | GraphQL | REST v3 | |
| **Auth Methods** | Token, OAuth2 | API Key, OAuth2 | API Token, OAuth2 | All support OAuth2 |
| **Webhooks** | ✅ | ✅ | ✅ | Real-time updates |
| **Custom Fields** | ✅ | ✅ | ✅ | Extensive support |
| **Attachments** | ✅ | ✅ | ✅ | File upload APIs |
| **Comments** | ✅ | ✅ | ✅ | Thread support |
| **Bulk Operations** | ✅ | ✅ | ✅ | Batch APIs |
| **Rate Limits** | 100-10k/min | 500-1500/hr | ~100/min | Varies by plan |
| **Python SDK** | Community | None | Official | |
| **Field Types** | 15+ types | 10+ types | 20+ types | All very flexible |
| **Status Workflow** | Custom | Custom | Custom | Needs mapping |
| **Time Tracking** | ✅ | ✅ | ✅ | Different formats |
| **Dependencies** | ✅ | ✅ | ✅ (Links) | |
| **Subtasks** | ✅ | ✅ | ✅ | Hierarchical |

## Implementation Complexity Analysis

### 1. ClickUp Adapter

**Estimated Effort**: Medium (3-4 days)

**Technical Challenges**:
- Complex workspace/space/list hierarchy
- Custom field type mapping
- Status workflow mapping (customizable per list)
- Time estimate conversion (milliseconds)

**Implementation Steps**:
1. Authenticate and get workspace structure
2. Map ClickUp statuses to TaskStatus enum
3. Handle custom fields in metadata
4. Implement two-way sync with field mapping
5. Handle attachments and comments

### 2. Linear Adapter

**Estimated Effort**: Medium-High (4-5 days)

**Technical Challenges**:
- GraphQL query complexity
- No official Python SDK
- Pagination with cursor-based system
- State machine mapping
- Priority number to enum mapping

**Implementation Steps**:
1. Set up GraphQL client with authentication
2. Build queries for issues, projects, and teams
3. Map Linear states to TaskStatus enum
4. Handle GraphQL mutations for updates
5. Implement webhook listener for real-time sync

### 3. JIRA Adapter  

**Estimated Effort**: Low-Medium (2-3 days)

**Technical Challenges**:
- JQL query construction
- Custom field ID discovery
- Complex permission model
- Issue type variations
- Workflow state mapping

**Implementation Steps**:
1. Authenticate with jira-python
2. Discover project custom fields
3. Map JIRA statuses to TaskStatus enum
4. Handle issue types (Story, Bug, Task, etc.)
5. Implement JQL-based filtering

## Common Implementation Patterns

### 1. Status Mapping Strategy
```python
class StatusMapper:
    """Maps external statuses to TaskStatus enum"""
    
    CLICKUP_STATUS_MAP = {
        "open": TaskStatus.OPEN,
        "in progress": TaskStatus.IN_PROGRESS,
        "closed": TaskStatus.COMPLETED,
        "archived": TaskStatus.CANCELLED
    }
    
    LINEAR_STATUS_MAP = {
        "backlog": TaskStatus.OPEN,
        "todo": TaskStatus.OPEN,
        "in_progress": TaskStatus.IN_PROGRESS,
        "done": TaskStatus.COMPLETED,
        "canceled": TaskStatus.CANCELLED
    }
    
    JIRA_STATUS_MAP = {
        "to do": TaskStatus.OPEN,
        "in progress": TaskStatus.IN_PROGRESS,
        "done": TaskStatus.COMPLETED,
        "won't do": TaskStatus.CANCELLED
    }
```

### 2. Field Mapping Configuration
```python
class FieldMapper:
    """Configurable field mapping between platforms"""
    
    def __init__(self, platform: str):
        self.platform = platform
        self.field_map = self._load_field_map()
    
    def map_to_task_model(self, external_data: dict) -> dict:
        """Map external data to TaskModel fields"""
        mapped = {}
        for ext_field, task_field in self.field_map.items():
            if ext_field in external_data:
                mapped[task_field] = self._convert_value(
                    external_data[ext_field],
                    task_field
                )
        return mapped
```

### 3. Sync Adapter Base Class
```python
class BaseSyncAdapter(ABC):
    """Base class for platform sync adapters"""
    
    @abstractmethod
    def authenticate(self, credentials: dict) -> bool:
        """Authenticate with the platform"""
        pass
    
    @abstractmethod
    def pull_tasks(self, filters: dict) -> List[TaskModel]:
        """Pull tasks from platform"""
        pass
    
    @abstractmethod
    def push_task(self, task: TaskModel) -> dict:
        """Push task to platform"""
        pass
    
    @abstractmethod
    def update_task(self, task_id: str, updates: dict) -> dict:
        """Update task on platform"""
        pass
```

## Testing Requirements

### 1. Unit Tests
- Mock API responses for each platform
- Test field mapping accuracy
- Test status conversions
- Test error handling

### 2. Integration Tests
- Test with sandbox/test accounts
- Verify two-way sync
- Test rate limit handling
- Test webhook processing

### 3. End-to-End Tests
- Full sync cycle testing
- Conflict resolution testing
- Performance testing with large datasets
- Network failure recovery

## Security Considerations

1. **API Key Storage**: Use environment variables or secure key management
2. **Token Refresh**: Implement OAuth token refresh for long-running syncs
3. **Data Sanitization**: Clean data before syncing between platforms
4. **Rate Limit Handling**: Implement exponential backoff
5. **Audit Logging**: Log all sync operations for debugging

## Recommendations

### Priority Order for Implementation
1. **JIRA** (lowest complexity, official SDK)
2. **ClickUp** (good community SDK, REST API)
3. **Linear** (highest complexity, GraphQL without SDK)

### Architecture Recommendations
1. Use adapter pattern with common interface
2. Implement configurable field mapping
3. Add webhook support for real-time updates
4. Use async operations for better performance
5. Implement robust error handling and retry logic

### Next Steps
1. Create base adapter class and interfaces
2. Implement JIRA adapter as proof of concept
3. Add configuration system for field mappings
4. Build webhook receiver for real-time updates
5. Add comprehensive logging and monitoring

## Conclusion

All three platforms provide robust APIs suitable for bidirectional synchronization. JIRA offers the most mature ecosystem with an official Python SDK, while ClickUp provides a simpler REST API with good community support. Linear's GraphQL API is powerful but requires more implementation effort without an official Python SDK.

The key to successful implementation is building a flexible adapter system that can handle the different data models and authentication methods while providing a consistent interface to the AI Trackdown PyTools system.