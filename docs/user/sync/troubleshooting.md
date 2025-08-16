# Sync Adapter Troubleshooting Guide

This guide helps resolve common issues with the sync adapter system across all supported platforms.

## General Troubleshooting

### Enable Debug Mode

For detailed error information:

```bash
# Set debug environment variable
export AITRACKDOWN_DEBUG=true
export AITRACKDOWN_LOG_LEVEL=DEBUG

# Run sync with verbose output
aitrackdown sync platform <platform> pull -v
```

### Check Configuration

Verify your configuration is correct:

```bash
# List current configuration
aitrackdown sync config <platform> --list

# Validate sync configuration file
python -m json.tool .aitrackdown/sync.json

# Check for syntax errors
jq . .aitrackdown/sync.json
```

### Test Connection

Always test connection before syncing:

```bash
# Test platform connection
aitrackdown sync platform <platform> status

# This will show:
# - Authentication status
# - Last sync time
# - Configuration validity
# - Connection health
```

## Common Issues

### Authentication Failures

#### Symptoms
- "Authentication failed" error
- "Invalid credentials" error
- "Unauthorized" or 401 errors

#### General Solutions

1. **Verify credentials are correct**:
   ```bash
   # Check stored credentials (tokens are partially hidden)
   aitrackdown sync config <platform> --list
   ```

2. **Test credentials directly**:
   ```bash
   # GitHub
   gh auth status
   
   # ClickUp
   curl -H "Authorization: pk_xxxxx" https://api.clickup.com/api/v2/user
   
   # Linear
   curl -H "Authorization: lin_api_xxxxx" https://api.linear.app/graphql
   
   # JIRA
   curl -u user@company.com:token https://company.atlassian.net/rest/api/3/myself
   ```

3. **Regenerate tokens** if expired or invalid

4. **Check environment variables**:
   ```bash
   env | grep -E "(GITHUB|CLICKUP|LINEAR|JIRA).*TOKEN"
   ```

### Rate Limiting

#### Symptoms
- "Rate limit exceeded" error
- 429 status code errors
- Sync stops partway through

#### Solutions

1. **Check rate limit status**:
   ```bash
   # GitHub
   gh api rate_limit
   
   # Other platforms show in error message
   ```

2. **Reduce batch size**:
   ```bash
   aitrackdown sync config <platform> --key batch_size --value 25
   ```

3. **Add delays between requests**:
   ```bash
   aitrackdown sync config <platform> --key request_delay --value 1000  # milliseconds
   ```

4. **Wait for rate limit reset**:
   - Error message shows retry_after time
   - Use exponential backoff

### Connection Errors

#### Symptoms
- "Connection refused" error
- "Timeout" errors
- "SSL certificate" errors

#### Solutions

1. **Check network connectivity**:
   ```bash
   # Test platform endpoints
   ping api.github.com
   ping api.clickup.com
   ping api.linear.app
   ping company.atlassian.net
   ```

2. **Verify SSL/TLS**:
   ```bash
   # Test SSL connection
   openssl s_client -connect api.github.com:443
   ```

3. **Check proxy settings**:
   ```bash
   env | grep -i proxy
   
   # Set proxy if needed
   export HTTPS_PROXY=http://proxy.company.com:8080
   ```

4. **Increase timeout**:
   ```bash
   aitrackdown sync config <platform> --key timeout --value 60
   ```

### Configuration Issues

#### Symptoms
- "Missing configuration" error
- "Invalid configuration" error
- Platform not recognized

#### Solutions

1. **Initialize configuration**:
   ```bash
   # Create config directory
   mkdir -p .aitrackdown
   
   # Initialize config file
   echo '{}' > .aitrackdown/sync.json
   ```

2. **Fix JSON syntax**:
   ```bash
   # Validate JSON
   python -m json.tool .aitrackdown/sync.json
   
   # Common issues:
   # - Missing commas
   # - Unclosed quotes
   # - Invalid escape sequences
   ```

3. **Use correct configuration keys**:
   ```bash
   # Show available configuration options
   aitrackdown sync config <platform>
   ```

### Missing or Duplicate Items

#### Symptoms
- Items not appearing after sync
- Same items created multiple times
- Some items skipped

#### Solutions

1. **Check type filters**:
   ```bash
   # View current filters
   aitrackdown sync config <platform> --key included_types --list
   aitrackdown sync config <platform> --key excluded_types --list
   ```

2. **Verify item metadata**:
   ```bash
   # Check if items have platform IDs
   aitrackdown list --format json | jq '.[] | select(.metadata.platform == "github")'
   ```

3. **Force full sync**:
   ```bash
   # Remove sync state to force full sync
   rm .aitrackdown/sync_state.json
   aitrackdown sync platform <platform> pull
   ```

4. **Check platform-specific filters**:
   - GitHub: Only syncs open issues by default
   - ClickUp: Check list_id is correct
   - Linear: Check team_id access
   - JIRA: Check project permissions

## Platform-Specific Issues

### GitHub Issues

#### "Repository not found"
```bash
# Verify repository format
aitrackdown sync config github --key repository --value owner/repo

# Check repository access
gh repo view owner/repo
```

#### "Bad credentials" with gh CLI
```bash
# Re-authenticate GitHub CLI
gh auth logout
gh auth login

# Verify authentication
gh auth status
```

### ClickUp Issues

#### "List not found"
```bash
# Find correct list ID
# 1. Go to ClickUp list
# 2. Check URL: https://app.clickup.com/1234567/v/li/987654321
#    - 987654321 is your list_id

# Or use API to find lists
curl -H "Authorization: pk_xxxxx" \
  https://api.clickup.com/api/v2/team/WORKSPACE_ID/list
```

#### "Invalid status"
```bash
# ClickUp statuses are list-specific
# Get valid statuses for your list
curl -H "Authorization: pk_xxxxx" \
  https://api.clickup.com/api/v2/list/LIST_ID
```

### Linear Issues

#### "Team not found"
```bash
# List available teams
curl -H "Authorization: lin_api_xxxxx" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ teams { nodes { id key name } } }"}' \
  https://api.linear.app/graphql
```

#### GraphQL errors
```bash
# Linear uses GraphQL, errors are in response
# Enable debug mode to see full GraphQL errors
export AITRACKDOWN_DEBUG=true
```

### JIRA Issues

#### "Project doesn't exist"
```bash
# List accessible projects
curl -u user@company.com:token \
  https://company.atlassian.net/rest/api/3/project

# Try using project ID instead of key
aitrackdown sync config jira --key project_id --value 10001
```

#### "Field 'customfield_xxxxx' cannot be set"
```bash
# List all custom fields
curl -u user@company.com:token \
  https://company.atlassian.net/rest/api/3/field | \
  jq '.[] | select(.custom == true) | {id, name}'
```

## Data Integrity Issues

### Corrupted Sync State

#### Symptoms
- Sync behavior inconsistent
- "Invalid sync state" errors

#### Solution
```bash
# Backup current state
cp .aitrackdown/sync_state.json .aitrackdown/sync_state.backup.json

# Reset sync state
rm .aitrackdown/sync_state.json

# Perform fresh sync
aitrackdown sync platform <platform> pull
```

### Metadata Conflicts

#### Symptoms
- Items have conflicting platform IDs
- Sync creates duplicates

#### Solution
```bash
# Find items with metadata issues
aitrackdown list --format json | \
  jq '.[] | select(.metadata | has("github_id") and has("jira_id"))'

# Clear platform metadata for specific platform
aitrackdown list --format json | \
  jq '.[] | del(.metadata.github_id, .metadata.github_url)' > cleaned.json
```

## Performance Issues

### Slow Sync Operations

#### Solutions

1. **Optimize batch size**:
   ```bash
   # Larger batches for good connections
   aitrackdown sync config <platform> --key batch_size --value 100
   
   # Smaller batches for slow/unreliable connections
   aitrackdown sync config <platform> --key batch_size --value 10
   ```

2. **Use filtering**:
   ```bash
   # Only sync specific types
   aitrackdown sync config <platform> --key included_types --value '["issue", "bug"]'
   
   # Exclude large types
   aitrackdown sync config <platform> --key excluded_types --value '["epic"]'
   ```

3. **Sync specific date ranges**:
   ```bash
   # Future feature: sync recent items only
   aitrackdown sync platform <platform> pull --since "2024-01-01"
   ```

### Memory Issues

#### For large datasets

```bash
# Monitor memory usage
aitrackdown sync platform <platform> pull &
PID=$!
while kill -0 $PID 2>/dev/null; do
  ps -p $PID -o %mem,rss
  sleep 5
done
```

## Recovery Procedures

### Backup Before Major Operations

```bash
# Backup all data
mkdir -p backups/$(date +%Y%m%d)
cp -r .aitrackdown backups/$(date +%Y%m%d)/

# Export data
aitrackdown export json --output backups/$(date +%Y%m%d)/export.json
```

### Restore from Backup

```bash
# Restore configuration
cp backups/20240101/.aitrackdown/sync.json .aitrackdown/

# Restore sync state
cp backups/20240101/.aitrackdown/sync_state.json .aitrackdown/

# Import data
aitrackdown import json backups/20240101/export.json
```

### Emergency Reset

```bash
# Complete reset (loses sync state)
rm -rf .aitrackdown/sync*.json

# Reconfigure from scratch
aitrackdown sync config <platform> --key <key> --value <value>
```

## Diagnostic Commands

### Platform Health Check

```bash
#!/bin/bash
# Health check script

PLATFORM=$1

echo "Checking $PLATFORM sync health..."

# 1. Configuration
echo -n "Configuration: "
if aitrackdown sync config $PLATFORM --list >/dev/null 2>&1; then
  echo "✓"
else
  echo "✗"
fi

# 2. Authentication
echo -n "Authentication: "
if aitrackdown sync platform $PLATFORM status >/dev/null 2>&1; then
  echo "✓"
else
  echo "✗"
fi

# 3. Connection
echo -n "Connection: "
case $PLATFORM in
  github)
    curl -s -o /dev/null -w "%{http_code}" https://api.github.com
    ;;
  clickup)
    curl -s -o /dev/null -w "%{http_code}" https://api.clickup.com/api/v2/user \
      -H "Authorization: $(aitrackdown sync config clickup --key token)"
    ;;
  # Add other platforms
esac
```

### Sync Verification

```bash
# Verify sync worked correctly
BEFORE=$(aitrackdown list --format json | jq length)
aitrackdown sync platform <platform> pull
AFTER=$(aitrackdown list --format json | jq length)
echo "Items before: $BEFORE, after: $AFTER, added: $((AFTER - BEFORE))"
```

## Getting Help

### Gathering Debug Information

When reporting issues, include:

```bash
# Version information
aitrackdown --version

# Platform configuration (with tokens hidden)
aitrackdown sync config <platform> --list | sed 's/token.*/token: ***/'

# Error logs
aitrackdown sync platform <platform> pull 2>&1 | tee sync-error.log

# System information
uname -a
python --version
```

### Support Channels

1. **Documentation**: Check platform-specific guides
2. **GitHub Issues**: Report bugs with debug information
3. **Discussions**: Ask questions and share solutions

### Common Log Messages

| Message | Meaning | Action |
|---------|---------|--------|
| "Adapter not found" | Platform not supported | Check available platforms |
| "No configuration found" | Platform not configured | Run config commands |
| "Rate limit will reset at" | Hit API limits | Wait or reduce batch size |
| "SSL: CERTIFICATE_VERIFY_FAILED" | SSL/TLS issue | Check certificates/proxy |
| "Connection timeout" | Network issue | Increase timeout or check connection |

## Prevention Tips

1. **Always use dry-run first**:
   ```bash
   aitrackdown sync platform <platform> pull --dry-run
   aitrackdown sync platform <platform> push --dry-run
   ```

2. **Regular backups**:
   ```bash
   # Add to crontab
   0 0 * * * cd /path/to/project && aitrackdown export json --output backups/$(date +\%Y\%m\%d).json
   ```

3. **Monitor sync health**:
   ```bash
   # Check sync age
   LAST_SYNC=$(jq -r ".last_sync.$PLATFORM" .aitrackdown/sync.json)
   echo "Last sync: $LAST_SYNC"
   ```

4. **Version control sync config**:
   ```bash
   # Add to .gitignore
   echo ".aitrackdown/sync.json" >> .gitignore
   
   # But track example config
   cp .aitrackdown/sync.json .aitrackdown/sync.example.json
   # Remove sensitive data from example
   ```