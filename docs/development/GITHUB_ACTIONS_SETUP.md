# GitHub Actions Setup Guide for PyPI Publishing

This guide helps you set up automated PyPI publishing using GitHub Actions.

## Quick Start

### 1. Prerequisites
- GitHub repository with push access
- PyPI account (https://pypi.org)
- TestPyPI account (https://test.pypi.org) - optional but recommended
- GitHub CLI (`gh`) - optional but helpful

### 2. Create PyPI API Tokens

#### Production PyPI Token:
1. Log in to https://pypi.org
2. Go to Account Settings → API tokens
3. Click "Add API token"
4. Name: `ai-trackdown-pytools-github`
5. Scope: "Upload packages" (project-specific if package exists)
6. Copy the token (starts with `pypi-`)

#### Test PyPI Token:
1. Log in to https://test.pypi.org
2. Follow same steps as above
3. Name: `ai-trackdown-pytools-test-github`

### 3. Add Secrets to GitHub

#### Method 1: Using the setup script
```bash
# Create .env file with your tokens
cat > .env << EOF
PYPI_TOKEN=pypi-xxxxxxxxxxxxx
TEST_PYPI_TOKEN=pypi-xxxxxxxxxxxxx
EOF

# Run the setup script
python scripts/setup_github_secrets.py
```

#### Method 2: Manual setup via GitHub UI
1. Go to your repository on GitHub
2. Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Add these secrets:
   - `PYPI_TOKEN`: Your PyPI API token
   - `TEST_PYPI_TOKEN`: Your TestPyPI API token

#### Method 3: Using GitHub CLI
```bash
# Set secrets
gh secret set PYPI_TOKEN --repo yourusername/ai-trackdown-pytools
gh secret set TEST_PYPI_TOKEN --repo yourusername/ai-trackdown-pytools
```

### 4. Create Deployment Environments

1. Go to Settings → Environments
2. Click "New environment"
3. Create two environments:

#### Test Environment:
- Name: `test`
- Environment URL: `https://test.pypi.org/project/ai-trackdown-pytools/`
- No additional protection rules needed

#### Production Environment:
- Name: `production`  
- Environment URL: `https://pypi.org/project/ai-trackdown-pytools/`
- Optional protection rules:
  - Required reviewers
  - Restrict deployment branches to `main`

## Usage

### Automatic Release (Recommended)

1. **Create a version tag:**
   ```bash
   git tag v0.9.1
   git push origin v0.9.1
   ```

2. **Workflow automatically:**
   - Runs all tests
   - Performs security scans
   - Builds the package
   - Publishes to TestPyPI
   - Verifies installation
   - Publishes to PyPI
   - Creates GitHub release

### Manual Release

1. Go to Actions → Release Management
2. Click "Run workflow"
3. Select:
   - Release type (major/minor/patch)
   - Or specify exact version
4. Workflow handles versioning and publishing

### Manual Publishing (Existing Version)

1. Go to Actions → Publish to PyPI
2. Click "Run workflow"
3. Select:
   - Environment: `test` or `production`
   - Skip tests: No (unless necessary)

## Monitoring

### Check Workflow Status
- Go to Actions tab to see running/completed workflows
- Click on a workflow run for detailed logs
- Failed steps show error messages

### Verify Publication
- TestPyPI: https://test.pypi.org/project/ai-trackdown-pytools/
- PyPI: https://pypi.org/project/ai-trackdown-pytools/

### Test Installation
```bash
# From PyPI
pip install ai-trackdown-pytools

# From TestPyPI
pip install -i https://test.pypi.org/simple/ ai-trackdown-pytools
```

## Troubleshooting

### Common Issues

1. **"Invalid or non-existent authentication credentials"**
   - Check PyPI token is correct
   - Ensure token has upload permissions
   - Token might be expired

2. **"Package already exists"**
   - Version already published
   - Can't overwrite existing versions
   - Bump version number

3. **Test failures blocking publish**
   - Fix failing tests
   - Or use manual dispatch with skip tests (not recommended)

4. **Workflow not triggering**
   - Check tag format matches pattern
   - Ensure tag is pushed to GitHub
   - Check branch protection rules

### Debug Commands

```bash
# Check current version
python -c "import toml; print(toml.load('pyproject.toml')['project']['version'])"

# Test build locally
pip install build
python -m build

# Check package contents
tar -tzf dist/*.tar.gz | head -20

# Validate package
pip install twine
twine check dist/*
```

## Security Best Practices

1. **Token Security:**
   - Never commit tokens to repository
   - Use project-scoped tokens when possible
   - Rotate tokens periodically

2. **Environment Protection:**
   - Add approval requirements for production
   - Restrict who can trigger deployments
   - Enable branch protection

3. **Signing (Optional):**
   - Generate GPG key for signing
   - Add GPG_PRIVATE_KEY and GPG_PASSPHRASE secrets
   - Artifacts will be automatically signed

## Advanced Configuration

### Custom Version Patterns
Edit `.github/workflows/publish-pypi.yml`:
```yaml
tags:
  - 'v*.*.*'
  - 'release-*'
  - '[0-9]+.[0-9]+.[0-9]+'
```

### Additional Checks
Add to build job:
```yaml
- name: Custom validation
  run: |
    # Your custom checks
    python scripts/validate_package.py
```

### Notifications
Add Slack/Discord/Email notifications:
```yaml
- name: Send notification
  if: success()
  uses: 8398a7/action-slack@v3
  with:
    status: success
    text: 'Published version ${{ github.ref_name }}'
```

## Support

- GitHub Actions Documentation: https://docs.github.com/actions
- PyPI Help: https://pypi.org/help/
- Project Issues: https://github.com/ai-trackdown/ai-trackdown-pytools/issues