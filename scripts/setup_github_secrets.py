#!/usr/bin/env python3
"""
Setup GitHub secrets for automated PyPI publishing.

This script helps configure the necessary secrets in your GitHub repository
for the automated CI/CD workflows.
"""

import os
import sys
import subprocess
import base64
from pathlib import Path
from typing import Optional

try:
    import click
    from dotenv import load_dotenv
except ImportError:
    print("Installing required dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "click", "python-dotenv"])
    import click
    from dotenv import load_dotenv


def run_gh_command(args: list, check: bool = True) -> Optional[str]:
    """Run a GitHub CLI command."""
    cmd = ["gh"] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=check)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        if check:
            click.echo(f"Error: {e.stderr}", err=True)
            raise
        return None


def check_gh_cli():
    """Check if GitHub CLI is installed and authenticated."""
    try:
        run_gh_command(["auth", "status"])
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_repo_info():
    """Get current repository information."""
    try:
        output = run_gh_command(["repo", "view", "--json", "owner,name"])
        import json
        repo_info = json.loads(output)
        return f"{repo_info['owner']['login']}/{repo_info['name']}"
    except:
        # Fallback to git remote
        try:
            remote_url = subprocess.check_output(
                ["git", "remote", "get-url", "origin"], text=True
            ).strip()
            # Parse GitHub URL
            if "github.com" in remote_url:
                parts = remote_url.split("github.com")[-1].strip(":/")
                return parts.replace(".git", "")
        except:
            pass
    return None


def set_secret(repo: str, name: str, value: str):
    """Set a GitHub secret."""
    try:
        run_gh_command(["secret", "set", name, "--repo", repo, "--body", value])
        click.echo(f"✅ Set secret: {name}")
    except subprocess.CalledProcessError:
        click.echo(f"❌ Failed to set secret: {name}", err=True)


def create_environment(repo: str, env_name: str, url: str = ""):
    """Create a deployment environment."""
    # Note: GitHub CLI doesn't support environment creation directly
    # This would need to be done via API or web interface
    click.echo(f"ℹ️  Please create the '{env_name}' environment manually in GitHub settings")
    if url:
        click.echo(f"   URL: {url}")


@click.command()
@click.option("--repo", help="GitHub repository (owner/name)")
@click.option("--env-file", default=".env", help="Environment file to load")
@click.option("--setup-gpg", is_flag=True, help="Setup GPG signing secrets")
def main(repo: Optional[str], env_file: str, setup_gpg: bool):
    """Setup GitHub secrets for automated PyPI publishing."""
    
    # Check GitHub CLI
    if not check_gh_cli():
        click.echo("❌ GitHub CLI not found or not authenticated", err=True)
        click.echo("\nPlease install and authenticate GitHub CLI:")
        click.echo("  brew install gh  # or your package manager")
        click.echo("  gh auth login")
        sys.exit(1)
    
    # Get repository
    if not repo:
        repo = get_repo_info()
        if not repo:
            click.echo("❌ Could not determine repository. Please specify with --repo", err=True)
            sys.exit(1)
    
    click.echo(f"🔧 Setting up secrets for repository: {repo}")
    
    # Load environment variables
    env_path = Path(env_file)
    if env_path.exists():
        load_dotenv(env_file)
        click.echo(f"📄 Loaded environment from: {env_file}")
    
    # Required secrets
    required_secrets = {
        "PYPI_TOKEN": os.getenv("PYPI_TOKEN"),
        "TEST_PYPI_TOKEN": os.getenv("TEST_PYPI_TOKEN") or os.getenv("PYPI_TEST_TOKEN"),
    }
    
    # Optional secrets
    optional_secrets = {}
    if setup_gpg:
        gpg_key = os.getenv("GPG_PRIVATE_KEY")
        if gpg_key and not gpg_key.startswith("-----BEGIN"):
            # Assume it's a file path
            try:
                with open(gpg_key, "rb") as f:
                    gpg_key = base64.b64encode(f.read()).decode()
            except:
                pass
        
        optional_secrets.update({
            "GPG_PRIVATE_KEY": gpg_key,
            "GPG_PASSPHRASE": os.getenv("GPG_PASSPHRASE"),
        })
    
    # Set required secrets
    click.echo("\n📦 Setting required secrets...")
    missing_required = []
    for name, value in required_secrets.items():
        if value:
            set_secret(repo, name, value)
        else:
            missing_required.append(name)
    
    # Set optional secrets
    if optional_secrets:
        click.echo("\n🔐 Setting optional secrets...")
        for name, value in optional_secrets.items():
            if value:
                set_secret(repo, name, value)
    
    # Create environments
    click.echo("\n🌍 Creating deployment environments...")
    create_environment(repo, "test", "https://test.pypi.org/project/ai-trackdown-pytools/")
    create_environment(repo, "production", "https://pypi.org/project/ai-trackdown-pytools/")
    
    # Summary
    click.echo("\n📋 Summary:")
    if missing_required:
        click.echo(f"⚠️  Missing required secrets: {', '.join(missing_required)}")
        click.echo("\nTo set missing secrets manually:")
        for secret in missing_required:
            click.echo(f"  gh secret set {secret} --repo {repo}")
    else:
        click.echo("✅ All required secrets configured!")
    
    click.echo("\n🚀 Next steps:")
    click.echo("1. Create deployment environments in GitHub settings")
    click.echo("2. Configure environment protection rules (optional)")
    click.echo("3. Test workflows with a release tag: git tag v0.9.1 && git push --tags")
    
    # Additional instructions
    if not os.getenv("PYPI_TOKEN"):
        click.echo("\n📝 To get PyPI tokens:")
        click.echo("1. Go to https://pypi.org/manage/account/token/")
        click.echo("2. Create a token with 'Upload packages' scope")
        click.echo("3. Save as PYPI_TOKEN in .env file")
        click.echo("\nFor TestPyPI:")
        click.echo("1. Go to https://test.pypi.org/manage/account/token/")
        click.echo("2. Create a token and save as TEST_PYPI_TOKEN")


if __name__ == "__main__":
    main()