# Migration Guide: From Legacy Sync to Adapter System

This guide helps you migrate from the legacy GitHub-only sync system to the new multi-platform adapter system.

## Overview

The new sync adapter system maintains full backward compatibility while adding support for multiple platforms and enhanced features. Your existing GitHub sync configurations and workflows will continue to work without modification.

## What's Changed

### Old System (Legacy)
- GitHub-only support
- Limited configuration options
- Basic pull/push functionality
- Hard-coded GitHub integration

### New System (Adapter-based)
- Multiple platform support (GitHub, ClickUp, Linear, JIRA)
- Flexible configuration system
- Enhanced error handling
- Extensible architecture
- Dry-run mode
- Advanced filtering options
- Batch operations

## Command Structure Changes

### GitHub Sync Commands

#### Old Commands (Still Supported)
```bash
# Legacy GitHub commands
aitrackdown sync github pull
aitrackdown sync github push
aitrackdown sync github status
```

#### New Commands (Recommended)
```bash
# New unified platform commands
aitrackdown sync platform github pull
aitrackdown sync platform github push
aitrackdown sync platform github status
```

### New Platform Commands

```bash
# Other platforms use the same structure
aitrackdown sync platform clickup pull
aitrackdown sync platform linear push
aitrackdown sync platform jira status
```

## Configuration Migration

### Existing GitHub Configuration

Your existing GitHub configuration in `.aitrackdown/sync.json` remains valid:

```json
{
  "github": {
    "repository": "owner/repo",
    "token": "ghp_xxxxx"
  },
  "last_sync": {
    "github": "2024-01-15T10:30:00"
  }
}
```

### Enhanced Configuration Options

The new system supports additional configuration options:

```json
{
  "github": {
    "repository": "owner/repo",
    "token": "ghp_xxxxx",
    "api_url": "https://api.github.com",
    "batch_size": 50,
    "timeout": 30
  },
  "clickup": {
    "token": "pk_xxxxx",
    "list_id": "123456789"
  },
  "linear": {
    "token": "lin_api_xxxxx",
    "team_id": "TEAM-ABC"
  }
}
```

## Feature Comparison

| Feature | Legacy System | New Adapter System |
|---------|--------------|-------------------|
| GitHub support | ✅ | ✅ |
| Other platforms | ❌ | ✅ |
| Dry-run mode | Limited | ✅ Full support |
| Batch operations | ❌ | ✅ |
| Custom field mapping | ❌ | ✅ |
| Rate limit handling | Basic | ✅ Advanced |
| Error recovery | Basic | ✅ Enhanced |
| Type filtering | ❌ | ✅ |
| Status mapping | ❌ | ✅ |

## Migration Steps

### Step 1: Verify Current Setup

Check your current GitHub sync configuration:

```bash
# Check existing configuration
cat .aitrackdown/sync.json

# Test with legacy command
aitrackdown sync github status
```

### Step 2: Test New Commands

Test the new commands with your existing configuration:

```bash
# Test new command structure (no changes needed)
aitrackdown sync platform github status

# Should show same information as legacy command
```

### Step 3: Explore New Features

Try new features without affecting your workflow:

```bash
# Test dry-run mode
aitrackdown sync platform github pull --dry-run

# View available platforms
aitrackdown sync list-available
```

### Step 4: Update Scripts

If you have automation scripts, update them gradually:

```bash
#!/bin/bash
# Old script
aitrackdown sync github pull
aitrackdown sync github push

# Updated script (both work)
aitrackdown sync platform github pull
aitrackdown sync platform github push
```

### Step 5: Add New Platforms (Optional)

Configure additional platforms as needed:

```bash
# Add ClickUp integration
aitrackdown sync config clickup --key token --value pk_xxxxx
aitrackdown sync config clickup --key list_id --value 123456789

# Test new platform
aitrackdown sync platform clickup status
```

## Backward Compatibility

### What's Guaranteed

1. **All legacy commands continue to work**
   - No breaking changes
   - Same behavior as before
   - Configuration format unchanged

2. **Existing sync state preserved**
   - Last sync timestamps maintained
   - Item mappings preserved
   - No data loss

3. **GitHub CLI integration unchanged**
   - `gh` CLI authentication still works
   - Token authentication still supported

### Deprecation Notice

The legacy GitHub-specific commands are deprecated but will remain functional:

```bash
# These commands show a deprecation notice but still work
aitrackdown sync github pull
aitrackdown sync github push
aitrackdown sync github status

# Notice: "This command is deprecated. Use 'aitrackdown sync platform github <action>' instead"
```

## Common Migration Scenarios

### Scenario 1: Simple GitHub User

If you only use GitHub sync and have simple needs:

**No action required!** Your existing setup continues to work. Consider using new commands for access to enhanced features like dry-run mode.

### Scenario 2: Power User with Automation

If you have scripts or CI/CD using sync commands:

1. **Keep existing scripts running** - They still work
2. **Update scripts gradually** - Replace commands one at a time
3. **Add error handling** - New system provides better error information
4. **Enable dry-run in testing** - Add `--dry-run` to test changes

Example script update:

```bash
#!/bin/bash
set -e

# Old version
echo "Syncing with GitHub..."
aitrackdown sync github pull
if [ $? -eq 0 ]; then
    aitrackdown sync github push
fi

# New version with enhanced features
echo "Syncing with GitHub..."
aitrackdown sync platform github pull --dry-run
if [ $? -eq 0 ]; then
    aitrackdown sync platform github pull
    aitrackdown sync platform github push --dry-run
    read -p "Proceed with push? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        aitrackdown sync platform github push
    fi
fi
```

### Scenario 3: Multi-Platform Team

If you want to add support for multiple platforms:

1. **Keep GitHub as primary** - No changes to existing workflow
2. **Add platforms incrementally** - One at a time
3. **Test with dry-run** - Verify behavior before syncing
4. **Use platform-specific tags** - Organize items by platform

Example multi-platform setup:

```bash
# Configure platforms
aitrackdown sync config github --key repository --value myorg/myrepo
aitrackdown sync config linear --key team_id --value TEAM-ABC

# Sync from both platforms
aitrackdown sync platform github pull
aitrackdown sync platform linear pull

# Work locally
aitrackdown list

# Push to specific platform
aitrackdown sync platform github push --dry-run
aitrackdown sync platform github push
```

## New Features to Explore

### 1. Dry-Run Mode

Preview changes before applying them:

```bash
# See what would be pulled
aitrackdown sync platform github pull --dry-run

# See what would be pushed
aitrackdown sync platform github push --dry-run
```

### 2. Platform Status

Get detailed sync information:

```bash
# Enhanced status information
aitrackdown sync platform github status
```

### 3. Configuration Management

Better configuration tools:

```bash
# List all configuration
aitrackdown sync config github --list

# See available options
aitrackdown sync config github
```

### 4. Type Filtering

Sync specific item types:

```bash
# Only sync issues (future feature)
aitrackdown sync platform github pull --types issue

# Exclude PRs from sync (future feature)
aitrackdown sync platform github push --exclude-types pr
```

### 5. Multiple Platform Support

Work with multiple platforms:

```bash
# List available platforms
aitrackdown sync list-available

# Configure new platform
aitrackdown sync config jira --key server --value https://company.atlassian.net
```

## Troubleshooting Migration

### Issue: Commands Not Found

**Problem**: New commands not recognized

**Solution**: Update to latest version
```bash
pip install --upgrade ai-trackdown-pytools
```

### Issue: Configuration Not Loading

**Problem**: Platform says "not configured" despite existing config

**Solution**: Check configuration format
```bash
# Verify configuration
cat .aitrackdown/sync.json

# Ensure proper JSON format
python -m json.tool .aitrackdown/sync.json
```

### Issue: Sync State Conflicts

**Problem**: Items appear duplicated after migration

**Solution**: Platform tracking metadata is maintained
- Check item metadata for platform IDs
- Use dry-run to preview operations
- No manual intervention should be needed

### Issue: Authentication Failures

**Problem**: Authentication works with old command but not new

**Solution**: Authentication mechanism unchanged
```bash
# Both use same authentication
aitrackdown sync github status  # Old
aitrackdown sync platform github status  # New

# Verify gh CLI auth
gh auth status
```

## Benefits of Migration

### Immediate Benefits (No Changes Required)

1. **Better error messages** - More informative error handling
2. **Improved performance** - Optimized sync operations
3. **Enhanced stability** - Better connection management

### Benefits with Minor Updates

1. **Dry-run mode** - Preview all changes safely
2. **Better configuration** - More flexible options
3. **Multi-platform ready** - Easy to add new platforms

### Future Benefits

1. **New platforms** - Support for more tools
2. **Advanced features** - Custom field mapping, webhooks
3. **Better integration** - Unified workflow across platforms

## Migration Checklist

- [ ] Verify current GitHub sync works
- [ ] Test new command structure
- [ ] Update any automation scripts
- [ ] Explore dry-run mode
- [ ] Consider adding new platforms
- [ ] Update documentation/runbooks

## Getting Help

### Documentation

- [User Guide](./adapter-guide.md) - Complete adapter system guide
- [Platform Examples](./platform-examples/) - Platform-specific guides
- [API Reference](../../development/sync-adapter-api-reference.md) - Technical details

### Support

- Existing GitHub sync continues to work
- Report issues on GitHub
- Check discussions for tips

### Command Help

```bash
# Get help for any command
aitrackdown sync --help
aitrackdown sync platform --help
```

## Summary

The migration to the new adapter system is designed to be seamless:

1. **No breaking changes** - Everything continues to work
2. **Gradual adoption** - Update at your own pace
3. **Enhanced features** - Available when you need them
4. **Future-proof** - Ready for new platforms and features

Start by trying the new command structure with `--dry-run` to see the enhanced features without any risk!