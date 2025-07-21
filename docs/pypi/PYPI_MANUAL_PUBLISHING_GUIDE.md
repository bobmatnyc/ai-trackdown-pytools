# PyPI Manual Publishing Guide

This guide documents the manual process for publishing `ai-trackdown-pytools` to PyPI.

## Prerequisites

1. **PyPI Account**: You need an account on [pypi.org](https://pypi.org)
2. **API Token**: Generate an API token from your PyPI account settings
3. **Test PyPI Account** (optional): For testing, create an account on [test.pypi.org](https://test.pypi.org)

## Package Information

- **Package Name**: `ai-trackdown-pytools`
- **Current Version**: 1.0.0
- **License**: MIT
- **Python Requirement**: >=3.8

## Build Status

✅ **Package Successfully Built** (2025-07-21)
- Distribution files created in `dist/` directory:
  - `ai_trackdown_pytools-1.0.0-py3-none-any.whl` (wheel)
  - `ai_trackdown_pytools-1.0.0.tar.gz` (source distribution)
- Package validation: **PASSED** (verified with `twine check`)
- Installation test: **PASSED** (all imports and CLI commands working)

## Publishing Steps

### 1. Set Up Authentication

Create or update `~/.pypirc` file with your credentials:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
repository = https://upload.pypi.org/legacy/
username = __token__
password = <your-pypi-api-token>

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = <your-test-pypi-api-token>
```

**Security Note**: Ensure `~/.pypirc` has proper permissions:
```bash
chmod 600 ~/.pypirc
```

### 2. Test Publishing (Recommended)

First, test the upload process with Test PyPI:

```bash
# Activate virtual environment
source venv/bin/activate

# Upload to Test PyPI
twine upload --repository testpypi dist/*

# Test installation from Test PyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ ai-trackdown-pytools
```

### 3. Publish to PyPI

Once testing is successful:

```bash
# Upload to PyPI
twine upload dist/*

# Verify installation
pip install ai-trackdown-pytools
```

### 4. Alternative: Using Environment Variables

If you prefer not to store credentials in a file:

```bash
# Using environment variables
TWINE_USERNAME=__token__ \
TWINE_PASSWORD=<your-pypi-api-token> \
twine upload dist/*
```

### 5. Alternative: Interactive Upload

For one-time uploads with interactive authentication:

```bash
twine upload dist/*
# You'll be prompted for username (use __token__) and password (your API token)
```

## Verification Steps

After publishing:

1. **Check PyPI Page**: Visit https://pypi.org/project/ai-trackdown-pytools/
2. **Test Installation**: 
   ```bash
   pip install ai-trackdown-pytools
   aitrackdown --version
   ```
3. **Verify All Entry Points**:
   ```bash
   aitrackdown --help
   atd --help
   aitrackdown-init
   aitrackdown-status
   ```

## Troubleshooting

### Common Issues

1. **"Invalid or non-existent authentication"**
   - Ensure you're using `__token__` as username
   - Verify your API token is correct and active

2. **"File already exists"**
   - This version has already been uploaded
   - Increment version number and rebuild

3. **"Invalid distribution file"**
   - Run `twine check dist/*` to validate files
   - Rebuild if necessary: `python -m build`

### Build Commands Reference

```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Install build tools
pip install --upgrade build twine

# Build package
python -m build

# Validate package
twine check dist/*

# Test package installation
python scripts/test_package_installation.py
```

## Security Best Practices

1. **Never commit tokens**: Keep API tokens out of version control
2. **Use project-specific tokens**: Create tokens with minimal required permissions
3. **Rotate tokens regularly**: Regenerate tokens periodically
4. **Use 2FA**: Enable two-factor authentication on PyPI account

## Package Contents Summary

The published package includes:
- CLI tools (`aitrackdown`, `atd`)
- Python API for project tracking
- Template system for tasks, issues, PRs
- Git integration
- Rich terminal UI
- Comprehensive validation system

## Next Steps

After successful publication:
1. Create a GitHub release with the same version tag
2. Update documentation with installation instructions
3. Announce the release to users
4. Monitor for any installation issues

## Support

For issues with the package:
- GitHub Issues: https://github.com/ai-trackdown/ai-trackdown-pytools/issues
- Documentation: https://ai-trackdown-pytools.readthedocs.io/