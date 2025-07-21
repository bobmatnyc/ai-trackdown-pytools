# Secure Token Usage Guide

This guide provides instructions for securely managing tokens for GitHub and PyPI operations.

## ⚠️ Security First

**NEVER** commit actual tokens to your repository, even in:
- Documentation files
- Example configurations
- Comments in code
- Commit messages
- Issue descriptions

## 🔐 Token Setup

### 1. GitHub Personal Access Token

#### Generate Token:
1. Visit https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Set expiration (recommend 90 days max)
4. Select scopes:
   - `repo` - Full control of private repositories
   - `workflow` - Update GitHub Action workflows (if needed)
5. Generate and copy token immediately

#### Store Securely:
```bash
# Option 1: Environment variable (session)
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# Option 2: Add to .env file (persistent)
echo 'GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx' >> .env

# Option 3: Use GitHub CLI
gh auth login
```

### 2. PyPI API Token

#### Generate Token:
1. Visit https://pypi.org/manage/account/token/
2. Add API token
3. Set token name: `ai-trackdown-pytools-publish`
4. Scope: Limit to project `ai-trackdown-pytools`
5. Create token and copy immediately

#### Store Securely:
```bash
# Option 1: Environment variables
export TWINE_USERNAME="__token__"
export TWINE_PASSWORD="pypi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# Option 2: Create .pypirc file
cat > ~/.pypirc << 'EOF'
[pypi]
username = __token__
password = pypi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
EOF
chmod 600 ~/.pypirc

# Option 3: Add to .env file
cat >> .env << 'EOF'
PYPI_TOKEN=pypi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
EOF
```

## 🚀 Using Tokens

### Local Development

1. **Create .env file** (already in .gitignore):
```bash
cat > .env << 'EOF'
# GitHub Configuration
GITHUB_TOKEN=ghp_YOUR_TOKEN_HERE
GITHUB_OWNER=your-github-username

# PyPI Configuration
PYPI_TOKEN=pypi-YOUR_TOKEN_HERE
EOF

# Secure the file
chmod 600 .env
```

2. **Load environment variables**:
```bash
# Manual loading
source .env
export $(cat .env | xargs)

# Or use python-dotenv
pip install python-dotenv
```

3. **Python usage example**:
```python
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Access tokens
github_token = os.getenv('GITHUB_TOKEN')
pypi_token = os.getenv('PYPI_TOKEN')
```

### GitHub Actions

1. **Add secrets to repository**:
   - Go to Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Add these secrets:
     - `PYPI_TOKEN` - Your PyPI API token
     - `TEST_PYPI_TOKEN` - Your TestPyPI token
     - `GPG_PRIVATE_KEY` - (Optional) For signing releases
     - `GPG_PASSPHRASE` - (Optional) GPG key passphrase

2. **Use in workflows**:
```yaml
- name: Publish to PyPI
  env:
    TWINE_USERNAME: __token__
    TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
  run: |
    twine upload dist/*
```

### Manual Publishing

#### To TestPyPI:
```bash
# Set credentials
export TWINE_USERNAME="__token__"
export TWINE_PASSWORD="your-test-pypi-token"

# Upload
twine upload --repository testpypi dist/*
```

#### To PyPI:
```bash
# Using environment variables
export TWINE_USERNAME="__token__"
export TWINE_PASSWORD="your-pypi-token"
twine upload dist/*

# Or using .pypirc
twine upload dist/*
```

## 🛡️ Security Best Practices

### Token Lifecycle
1. **Generate** tokens with minimal required scopes
2. **Rotate** tokens every 90 days
3. **Revoke** tokens immediately if exposed
4. **Audit** token usage regularly

### Storage Security
1. **Never** hardcode tokens in code
2. **Use** environment variables or secure vaults
3. **Restrict** file permissions (chmod 600)
4. **Exclude** token files in .gitignore

### Development Workflow
```bash
# Before committing
git status  # Check no .env or token files
git diff    # Review changes for tokens

# Use pre-commit hooks
pip install pre-commit detect-secrets
pre-commit install
```

### Emergency Response
If tokens are exposed:
1. **Revoke** immediately via GitHub/PyPI interfaces
2. **Rotate** - generate new tokens
3. **Audit** - check logs for unauthorized usage
4. **Update** - replace tokens in all systems

## 📋 Quick Reference

### Environment Variables
```bash
# GitHub
export GITHUB_TOKEN="ghp_xxxx"
export GITHUB_OWNER="username"

# PyPI
export TWINE_USERNAME="__token__"
export TWINE_PASSWORD="pypi-xxxx"
```

### File Permissions
```bash
# Secure token files
chmod 600 .env
chmod 600 ~/.pypirc
```

### Verification
```bash
# Test GitHub token
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user

# Test PyPI upload (dry run)
twine check dist/*
```

## 🚫 What NOT to Do

```bash
# ❌ NEVER do this:
git add .env
git commit -m "Added tokens"

# ❌ NEVER include in code:
TOKEN = "ghp_actual_token_value"

# ❌ NEVER share in issues:
"My token ghp_xxxx is not working"
```

## ✅ What TO Do

```bash
# ✅ Use placeholders in docs:
GITHUB_TOKEN="your-token-here"

# ✅ Use environment variables:
token = os.getenv('GITHUB_TOKEN')

# ✅ Use secure storage:
gh auth login  # GitHub CLI
```

Remember: Security is everyone's responsibility. When in doubt, ask for help rather than risk exposing credentials.