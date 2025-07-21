# GitHub Actions Workflows for AI Trackdown PyTools

This directory contains automated CI/CD workflows for the AI Trackdown PyTools project.

## Workflows Overview

### 1. Test Suite (`test.yml`)
**Triggers:** Push to main/develop, Pull requests, Weekly schedule

**Purpose:** Comprehensive testing and quality checks
- **Linting:** Black, Ruff, MyPy
- **Testing:** Multi-OS, multi-Python version matrix
- **Security:** Bandit, Safety, pip-audit
- **Coverage:** Codecov integration
- **Performance:** Benchmark tests
- **Integration:** CLI command testing
- **Documentation:** Sphinx build validation

### 2. PyPI Publishing (`publish-pypi.yml`)
**Triggers:** Version tags (v*.*.*), Manual dispatch

**Purpose:** Automated package publishing
- **Test PyPI:** Initial testing on test.pypi.org
- **Production PyPI:** Final publishing to pypi.org
- **Security:** Optional GPG signing
- **Verification:** Post-publish installation tests
- **Release Notes:** Automatic changelog generation

### 3. Dependency Updates (`dependency-update.yml`)
**Triggers:** Weekly schedule, Manual dispatch

**Purpose:** Automated dependency management
- **Updates:** pip-compile based updates
- **Security:** Vulnerability scanning
- **PR Creation:** Automated pull requests

### 4. Release Management (`release.yml`)
**Triggers:** Manual dispatch only

**Purpose:** Version management and release preparation
- **Versioning:** Automatic version bumping
- **Changelog:** Commitizen-based generation
- **Tagging:** Automated Git tagging
- **Integration:** Triggers PyPI publishing

## Setup Instructions

### 1. Required Repository Secrets

Configure these secrets in your GitHub repository settings:

```yaml
# PyPI Publishing
PYPI_TOKEN: Your PyPI API token for production
TEST_PYPI_TOKEN: Your TestPyPI API token

# Optional: GPG Signing
GPG_PRIVATE_KEY: Your GPG private key (base64 encoded)
GPG_PASSPHRASE: Your GPG key passphrase

# GitHub (usually automatic)
GITHUB_TOKEN: Automatically provided by GitHub Actions
```

### 2. Creating PyPI Tokens

1. **Production PyPI:**
   - Go to https://pypi.org/manage/account/token/
   - Create a new API token with "Upload packages" scope
   - Save as `PYPI_TOKEN` secret

2. **Test PyPI:**
   - Go to https://test.pypi.org/manage/account/token/
   - Create a new API token
   - Save as `TEST_PYPI_TOKEN` secret

### 3. Environment Configuration

The workflows use two deployment environments:

1. **`test` environment:**
   - URL: https://test.pypi.org/project/ai-trackdown-pytools/
   - Used for TestPyPI deployments
   - No manual approval required

2. **`production` environment:**
   - URL: https://pypi.org/project/ai-trackdown-pytools/
   - Used for production PyPI deployments
   - Consider adding manual approval for safety

## Usage Examples

### Manual Release Process

1. **Trigger a new release:**
   ```bash
   # From GitHub Actions tab, run "Release Management"
   # Select release type: major, minor, patch, or prerelease
   ```

2. **Publishing will automatically trigger:**
   - Tests run on multiple Python versions
   - Security scans
   - Build and upload to TestPyPI
   - Verification on TestPyPI
   - Upload to production PyPI
   - GitHub release creation

### Manual Publishing

To manually publish without version changes:

```bash
# From GitHub Actions tab, run "Publish to PyPI"
# Select environment: test or production
# Optionally skip tests (not recommended)
```

### Dependency Updates

Updates are automatically created weekly, or trigger manually:

```bash
# From GitHub Actions tab, run "Dependency Updates"
# Review and merge the created PR
```

## Workflow Features

### Security Features
- Vulnerability scanning with multiple tools
- Software Bill of Materials (SBOM) generation
- License compliance checking
- Optional GPG artifact signing

### Quality Assurance
- Multi-platform testing (Ubuntu, Windows, macOS)
- Python 3.8-3.12 compatibility
- Code coverage with 85% minimum threshold
- Performance benchmarking with regression detection

### Automation
- Automatic version bumping
- Changelog generation from commits
- Release note creation
- Post-publish verification

## Best Practices

1. **Version Tags:**
   - Use semantic versioning: `v1.2.3`
   - Tags automatically trigger publishing

2. **Testing:**
   - All tests must pass before publishing
   - Security scans run on every workflow

3. **Manual Approval:**
   - Consider adding environment protection rules
   - Require reviews for production deployments

4. **GPG Signing:**
   - Optional but recommended for security
   - Requires GPG key setup in secrets

## Troubleshooting

### Common Issues

1. **Publishing Fails:**
   - Check PyPI token permissions
   - Verify package name availability
   - Review twine check output

2. **Test Failures:**
   - Check Python version compatibility
   - Review dependency conflicts
   - Verify test environment setup

3. **Security Scan Failures:**
   - Review vulnerability reports
   - Update affected dependencies
   - Add security exceptions if false positives

### Debugging

Enable debug logging:
```yaml
env:
  ACTIONS_RUNNER_DEBUG: true
  ACTIONS_STEP_DEBUG: true
```

## Maintenance

### Updating Workflows

1. Test changes in a feature branch
2. Use workflow syntax validation
3. Monitor initial runs after merging

### Dependency Management

- Review automated PRs weekly
- Test major updates thoroughly
- Keep security tools updated

### Performance Optimization

- Use caching for dependencies
- Parallelize test matrix
- Optimize workflow triggers