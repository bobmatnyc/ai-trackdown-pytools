# PyPI Publishing Execution Plan

**Date**: 2025-07-21  
**Package**: ai-trackdown-pytools v1.0.0  
**Status**: Ready for Publishing (Awaiting Tokens)

## Pre-Publishing Status

### ✅ Package Readiness
- **Build Status**: Distribution files exist and validated
  - `ai_trackdown_pytools-1.0.0-py3-none-any.whl` (107.5 KB)
  - `ai_trackdown_pytools-1.0.0.tar.gz` (85.4 KB)
- **Validation**: `twine check` PASSED
- **SHA256 Hashes**:
  - Wheel: `2311a75acae71b422983d9d2c4f6bef6778f0c52b0a536481c21e18298a79df0`
  - Source: `de2938424da82036b7e827d105db9cae5938fbffa4e2131f7c21807acd1710f4`

### ❌ Authentication Requirements
- **PyPI Token**: Required but not found in .env
- **Test PyPI Token**: Required but not found in .env

## Execution Steps (When Tokens Available)

### 1. Create .env File with Tokens
```bash
# Create .env file
cat > .env << 'EOF'
# PyPI Configuration
PYPI_TOKEN=pypi-YOUR_ACTUAL_TOKEN_HERE
TEST_PYPI_TOKEN=pypi-YOUR_TEST_TOKEN_HERE

# GitHub Configuration (if needed)
GITHUB_TOKEN=ghp_YOUR_GITHUB_TOKEN_HERE
EOF

# Set proper permissions
chmod 600 .env
```

### 2. Test Publishing Workflow

```bash
# Activate virtual environment
source venv/bin/activate

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Option A: Using environment variables
TWINE_USERNAME=__token__ \
TWINE_PASSWORD=$TEST_PYPI_TOKEN \
twine upload --repository testpypi dist/*

# Option B: Using the test script
python scripts/test_pypi_upload.py
```

### 3. Verify Test Installation

```bash
# Create clean test environment
cd /tmp
python -m venv test_env
source test_env/bin/activate

# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ \
            ai-trackdown-pytools==1.0.0

# Test all entry points
aitrackdown --version  # Should show 1.0.0
atd --help
aitrackdown-init
aitrackdown-status

# Test core functionality
aitrackdown init test-project
cd test-project
aitrackdown task create "Test task"
aitrackdown status
```

### 4. Production PyPI Publishing

```bash
# Only after successful test verification
cd /Users/masa/Projects/managed/ai-trackdown-pytools
source venv/bin/activate

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Upload to production PyPI
TWINE_USERNAME=__token__ \
TWINE_PASSWORD=$PYPI_TOKEN \
twine upload dist/*

# Alternative: Using upload script
python scripts/upload_to_pypi.py
```

### 5. Post-Publishing Verification

```bash
# Wait 1-2 minutes for PyPI to update

# Check PyPI page
open https://pypi.org/project/ai-trackdown-pytools/

# Clean install test
pip uninstall -y ai-trackdown-pytools
pip install ai-trackdown-pytools==1.0.0

# Comprehensive functionality test
aitrackdown --version
aitrackdown init production-test
cd production-test
aitrackdown task create "Production test task"
aitrackdown issue create
aitrackdown pr create
aitrackdown status
```

## Alternative Authentication Methods

### Method 1: ~/.pypirc Configuration
```bash
# Create ~/.pypirc
cat > ~/.pypirc << 'EOF'
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
repository = https://upload.pypi.org/legacy/
username = __token__
password = YOUR_PYPI_TOKEN

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = YOUR_TEST_PYPI_TOKEN
EOF

# Set secure permissions
chmod 600 ~/.pypirc

# Then upload without environment variables
twine upload --repository testpypi dist/*  # For test
twine upload dist/*  # For production
```

### Method 2: Interactive Authentication
```bash
# Twine will prompt for credentials
twine upload dist/*
# Username: __token__
# Password: [paste your token]
```

## Expected Results

### On Successful TestPyPI Publishing
- Package visible at: https://test.pypi.org/project/ai-trackdown-pytools/
- Installation works with test index URL
- All CLI commands functional

### On Successful PyPI Publishing
- Package visible at: https://pypi.org/project/ai-trackdown-pytools/
- Installation via: `pip install ai-trackdown-pytools`
- Package statistics available
- Download tracking enabled

## Troubleshooting Guide

### Common Issues and Solutions

1. **"Invalid or non-existent authentication"**
   - Verify token starts with `pypi-`
   - Ensure using `__token__` as username
   - Check token hasn't been revoked

2. **"HTTPError: 400 Bad Request"**
   - Version already exists (need to increment)
   - Invalid package metadata
   - File size too large

3. **"File already exists"**
   - Version 1.0.0 already uploaded
   - Need to increment to 1.0.1 and rebuild

4. **Test installation fails**
   - Dependencies not available on TestPyPI
   - Use `--extra-index-url https://pypi.org/simple/`

## Security Considerations

1. **Token Management**
   - Never commit tokens to git
   - Use project-scoped tokens
   - Rotate tokens regularly
   - Delete test tokens after use

2. **File Permissions**
   - `.env`: 600 (read/write owner only)
   - `~/.pypirc`: 600 (read/write owner only)

3. **Verification**
   - Always test on TestPyPI first
   - Verify package contents before publishing
   - Check for sensitive data in package

## Next Steps After Publishing

1. **Create GitHub Release**
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   # Create release on GitHub with changelog
   ```

2. **Update Homebrew Formula**
   ```ruby
   # Update sha256 and url in formula
   url "https://files.pythonhosted.org/packages/source/a/ai-trackdown-pytools/ai_trackdown_pytools-1.0.0.tar.gz"
   sha256 "de2938424da82036b7e827d105db9cae5938fbffa4e2131f7c21807acd1710f4"
   ```

3. **Announce Release**
   - Update README with installation instructions
   - Create announcement for users
   - Update documentation

## Summary

The package is **100% ready for publishing**. The only missing components are:
1. PyPI API token (create at https://pypi.org/manage/account/token/)
2. Test PyPI token (create at https://test.pypi.org/manage/account/token/)

Once tokens are added to `.env` or `~/.pypirc`, the publishing process can be completed in under 5 minutes following the steps above.