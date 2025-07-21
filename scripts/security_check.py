#!/usr/bin/env python3
"""
Security check script for AI Trackdown PyTools.

This script validates that tokens are properly configured and not exposed.
"""
import os
import sys
import subprocess
from pathlib import Path
import re


def check_file_for_tokens(file_path, patterns):
    """Check if a file contains any token patterns."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            for pattern_name, pattern in patterns.items():
                if re.search(pattern, content):
                    return pattern_name
    except Exception:
        pass
    return None


def main():
    """Run security checks."""
    print("🔒 AI Trackdown PyTools Security Check")
    print("=" * 50)
    
    issues = []
    warnings = []
    
    # Token patterns to search for
    token_patterns = {
        'GitHub Token': r'ghp_[a-zA-Z0-9]{36}',
        'GitHub OAuth': r'gho_[a-zA-Z0-9]{36}',
        'GitHub App': r'ghs_[a-zA-Z0-9]{36}',
        'GitHub Refresh': r'ghr_[a-zA-Z0-9]{36}',
        'PyPI Token': r'pypi-[a-zA-Z0-9_\-]{50,}',
        'NPM Token': r'npm_[a-zA-Z0-9]{36}',
    }
    
    # Check 1: .env file security
    print("\n1. Checking .env file security...")
    env_file = Path('.env')
    if env_file.exists():
        # Check permissions
        stat_info = env_file.stat()
        mode = oct(stat_info.st_mode)[-3:]
        if mode != '600':
            warnings.append(f".env file has permissions {mode}, should be 600")
            print(f"   ⚠️  .env has loose permissions: {mode}")
        else:
            print("   ✅ .env has secure permissions (600)")
        
        # Check if it's in git
        try:
            result = subprocess.run(
                ['git', 'ls-files', '.env'],
                capture_output=True,
                text=True
            )
            if result.stdout.strip():
                issues.append(".env file is tracked by git!")
                print("   ❌ .env is tracked by git!")
            else:
                print("   ✅ .env is not tracked by git")
        except Exception:
            pass
    else:
        print("   ℹ️  No .env file found")
    
    # Check 2: .gitignore configuration
    print("\n2. Checking .gitignore configuration...")
    gitignore = Path('.gitignore')
    if gitignore.exists():
        with open(gitignore, 'r') as f:
            content = f.read()
            if '.env' in content:
                print("   ✅ .env is in .gitignore")
            else:
                issues.append(".env is not in .gitignore")
                print("   ❌ .env is not in .gitignore")
            
            if '.env.*' in content or '.env*' in content:
                print("   ✅ .env.* files are in .gitignore")
            else:
                warnings.append(".env.* pattern not in .gitignore")
                print("   ⚠️  .env.* pattern not in .gitignore")
    
    # Check 3: Scan for exposed tokens
    print("\n3. Scanning for exposed tokens...")
    exclude_dirs = {'.git', 'node_modules', 'venv', '__pycache__', 'dist', 'build'}
    exposed_count = 0
    
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if file.startswith('.env') and file != '.env.example':
                continue
            
            # Skip security documentation files
            if file in ['docs/security/SECURITY_TOKEN_VALIDATION_REPORT.md', 'docs/security/SECURE_TOKEN_USAGE_GUIDE.md']:
                continue
                
            file_path = Path(root) / file
            if file_path.suffix in ['.py', '.md', '.txt', '.yml', '.yaml', '.json', '.js']:
                token_type = check_file_for_tokens(file_path, token_patterns)
                if token_type:
                    exposed_count += 1
                    issues.append(f"Possible {token_type} in {file_path}")
                    print(f"   ❌ Possible {token_type} found in: {file_path}")
    
    if exposed_count == 0:
        print("   ✅ No exposed tokens found in tracked files")
    
    # Check 4: Environment variables
    print("\n4. Checking environment variables...")
    env_vars = {
        'GITHUB_TOKEN': 'GitHub operations',
        'PYPI_TOKEN': 'PyPI publishing',
        'TWINE_PASSWORD': 'Twine uploads',
    }
    
    configured = []
    for var, purpose in env_vars.items():
        if os.getenv(var):
            configured.append(var)
            print(f"   ✅ {var} is configured for {purpose}")
    
    if not configured:
        print("   ℹ️  No token environment variables configured")
    
    # Check 5: GitHub Actions secrets
    print("\n5. Checking GitHub Actions configuration...")
    workflow_dir = Path('.github/workflows')
    if workflow_dir.exists():
        uses_secrets = False
        for workflow_file in workflow_dir.glob('*.yml'):
            with open(workflow_file, 'r') as f:
                content = f.read()
                if '${{ secrets.' in content:
                    uses_secrets = True
                    
                # Check for hardcoded tokens
                for pattern_name, pattern in token_patterns.items():
                    if re.search(pattern, content):
                        issues.append(f"Hardcoded {pattern_name} in {workflow_file.name}")
                        print(f"   ❌ Hardcoded {pattern_name} in {workflow_file.name}")
        
        if uses_secrets:
            print("   ✅ GitHub Actions use secrets properly")
    
    # Check 6: PyPI configuration
    print("\n6. Checking PyPI configuration...")
    pypirc = Path.home() / '.pypirc'
    if pypirc.exists():
        stat_info = pypirc.stat()
        mode = oct(stat_info.st_mode)[-3:]
        if mode != '600':
            warnings.append(f"~/.pypirc has permissions {mode}, should be 600")
            print(f"   ⚠️  ~/.pypirc has loose permissions: {mode}")
        else:
            print("   ✅ ~/.pypirc has secure permissions")
    else:
        print("   ℹ️  No ~/.pypirc file found")
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Security Check Summary")
    print("=" * 50)
    
    if not issues and not warnings:
        print("✅ All security checks passed!")
        print("\nYour token configuration appears to be secure.")
    else:
        if issues:
            print(f"\n❌ Critical Issues Found ({len(issues)}):")
            for issue in issues:
                print(f"   • {issue}")
        
        if warnings:
            print(f"\n⚠️  Warnings ({len(warnings)}):")
            for warning in warnings:
                print(f"   • {warning}")
        
        print("\n🔧 Recommended Actions:")
        if any('exposed' in issue.lower() or 'hardcoded' in issue.lower() for issue in issues):
            print("   1. Revoke any exposed tokens immediately")
            print("   2. Generate new tokens")
            print("   3. Remove exposed tokens from files")
        if any('permissions' in warning for warning in warnings):
            print("   • Fix file permissions with: chmod 600 <file>")
        if any('.gitignore' in issue or '.gitignore' in warning for issue in issues for warning in warnings):
            print("   • Update .gitignore to exclude sensitive files")
    
    # Exit with error if critical issues found
    sys.exit(1 if issues else 0)


if __name__ == "__main__":
    main()