# PyPI Release Checklist

This checklist ensures a smooth release to PyPI for ai-trackdown-pytools.

## Pre-Release Checklist

### Documentation
- [x] README.md updated with:
  - [x] PyPI badges (version, downloads, Python versions)
  - [x] Professional project description
  - [x] Comprehensive installation instructions
  - [x] Real-world usage examples
  - [x] Complete command reference
  - [x] Links to documentation and support

### Package Metadata
- [x] pyproject.toml updated with:
  - [x] Accurate project description
  - [x] Complete author and maintainer information
  - [x] MIT license specification
  - [x] Comprehensive classifiers
  - [x] Extended keywords for discoverability
  - [x] All relevant project URLs

### Package Files
- [x] MANIFEST.in configured to include:
  - [x] README.md, CHANGELOG.md, LICENSE
  - [x] All template files (*.yaml, *.yml)
  - [x] All schema files (*.json)
  - [x] py.typed marker file
  - [x] Proper exclusions for test/build files

### Compatibility
- [x] setup.py created for older pip versions
- [x] py.typed file added for type hint support
- [x] Python version compatibility verified (3.8-3.12)

### Version Management
- [ ] Version number updated in pyproject.toml
- [ ] Version number updated in src/ai_trackdown_pytools/version.py
- [ ] CHANGELOG.md updated with release notes
- [ ] Git tag created for release

## Build and Test

### Local Testing
```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build distribution packages
python -m build

# Check distribution
twine check dist/*

# Test installation in fresh environment
python -m venv test-env
source test-env/bin/activate  # On Windows: test-env\Scripts\activate
pip install dist/*.whl
aitrackdown --version
aitrackdown --help
deactivate
rm -rf test-env
```

### Package Validation
```bash
# Validate package contents
tar -tvf dist/*.tar.gz | head -20
unzip -l dist/*.whl | head -20

# Check for missing files
python -m check_manifest

# Validate metadata
twine check --strict dist/*
```

## Release Process

### 1. Test PyPI Upload (Recommended)
```bash
# Upload to Test PyPI first
twine upload --repository testpypi dist/*

# Test installation from Test PyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ ai-trackdown-pytools
```

### 2. Production PyPI Upload
```bash
# Upload to PyPI
twine upload dist/*

# Verify on PyPI
# Visit: https://pypi.org/project/ai-trackdown-pytools/
```

### 3. Post-Release Verification
```bash
# Test installation from PyPI
pip install ai-trackdown-pytools

# Verify functionality
aitrackdown --version
aitrackdown init project
aitrackdown create task "Test task"
```

## Post-Release Tasks

- [ ] Create GitHub release with changelog
- [ ] Update documentation site
- [ ] Announce release on:
  - [ ] GitHub Discussions
  - [ ] Discord
  - [ ] Twitter/X
  - [ ] Blog
- [ ] Update Homebrew formula (if applicable)
- [ ] Monitor PyPI download statistics
- [ ] Check for user feedback and issues

## Troubleshooting

### Common Issues

1. **Missing files in distribution**
   - Check MANIFEST.in configuration
   - Run `python -m check_manifest`

2. **README not rendering on PyPI**
   - Validate with `twine check dist/*`
   - Check for invalid markdown syntax

3. **Import errors after installation**
   - Verify all packages are included in `[tool.hatch.build]`
   - Check for missing __init__.py files

4. **Version mismatch**
   - Ensure version is synchronized across:
     - pyproject.toml
     - src/ai_trackdown_pytools/version.py
     - Git tags

## Security Considerations

- [ ] No sensitive data in code or documentation
- [ ] API keys and tokens removed
- [ ] Dependencies checked for vulnerabilities
- [ ] License compliance verified

## Final Checks

- [ ] All tests passing
- [ ] Documentation accurate and complete
- [ ] Examples working correctly
- [ ] No TODO or FIXME comments in release code
- [ ] Changelog up to date
- [ ] Version numbers consistent