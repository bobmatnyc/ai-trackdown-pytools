"""Version management for AI Trackdown PyTools."""

import os
import re
from pathlib import Path
from typing import NamedTuple, Optional


class Version(NamedTuple):
    """Semantic version representation."""

    major: int
    minor: int
    patch: int
    pre_release: Optional[str] = None
    build_metadata: Optional[str] = None

    @classmethod
    def parse(cls, version_string: str) -> "Version":
        """Parse a semantic version string."""
        # Regex pattern for semantic versioning
        pattern = r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"

        match = re.match(pattern, version_string)
        if not match:
            raise ValueError(f"Invalid semantic version: {version_string}")

        groups = match.groupdict()
        return cls(
            major=int(groups["major"]),
            minor=int(groups["minor"]),
            patch=int(groups["patch"]),
            pre_release=groups.get("prerelease"),
            build_metadata=groups.get("buildmetadata"),
        )

    def __str__(self) -> str:
        """Convert version to string."""
        version_str = f"{self.major}.{self.minor}.{self.patch}"

        if self.pre_release:
            version_str += f"-{self.pre_release}"

        if self.build_metadata:
            version_str += f"+{self.build_metadata}"

        return version_str

    def is_pre_release(self) -> bool:
        """Check if this is a pre-release version."""
        return self.pre_release is not None

    def is_stable(self) -> bool:
        """Check if this is a stable release version."""
        return not self.is_pre_release() and self.major > 0

    def bump_major(self) -> "Version":
        """Bump major version and reset minor/patch."""
        return Version(self.major + 1, 0, 0)

    def bump_minor(self) -> "Version":
        """Bump minor version and reset patch."""
        return Version(self.major, self.minor + 1, 0)

    def bump_patch(self) -> "Version":
        """Bump patch version."""
        return Version(self.major, self.minor, self.patch + 1)

    def to_release(self) -> "Version":
        """Convert to release version (remove pre-release)."""
        return Version(self.major, self.minor, self.patch)


def _get_version():
    """Read version from VERSION file."""
    # Try to find VERSION file in several locations
    possible_paths = [
        Path(__file__).parent / "VERSION",  # Packaged install (primary)
        Path(__file__).parent.parent.parent / "VERSION",  # Development install
        Path(os.getcwd()) / "VERSION",  # Current directory
    ]

    for version_path in possible_paths:
        if version_path.exists():
            return version_path.read_text().strip()

    # Fallback version if VERSION file not found
    return "1.2.0"


# Get version string
__version__ = _get_version()

# Current version as Version object
CURRENT_VERSION = Version.parse(__version__)


def get_version() -> str:
    """Get the current version string."""
    return __version__


def get_version_info() -> Version:
    """Get the current version as a Version object."""
    return CURRENT_VERSION


def is_development_version() -> bool:
    """Check if this is a development version (pre-1.0.0)."""
    return CURRENT_VERSION.major == 0


def is_stable_version() -> bool:
    """Check if this is a stable version."""
    return CURRENT_VERSION.is_stable()


def format_version_info() -> str:
    """Format version information for display."""
    version_info = f"AI Trackdown PyTools v{get_version()}"

    if is_development_version():
        version_info += " (Beta)"
    elif CURRENT_VERSION.is_pre_release():
        version_info += " (Pre-release)"

    return version_info


def check_version_compatibility(required_version: str) -> bool:
    """Check if current version is compatible with required version."""
    try:
        required = Version.parse(required_version)
        current = CURRENT_VERSION

        # For 0.x versions, only same minor version is compatible (patch can be higher)
        if current.major == 0:
            return (
                current.major == required.major
                and current.minor == required.minor
                and current.patch >= required.patch
            )

        # For 1.x+ versions, follow semantic versioning compatibility
        return current.major == required.major and current.minor >= required.minor

    except ValueError:
        return False


def validate_version_string(version_string: str) -> bool:
    """Validate that a version string follows semantic versioning."""
    try:
        Version.parse(version_string)
        return True
    except ValueError:
        return False


# Version history tracking
# This is maintained manually for version history reference
VERSION_HISTORY = [
    "0.9.0",  # Initial semantic versioning implementation
    "1.0.0",  # First stable release - Production ready
    "1.1.0",  # Bug fixes and improvements
    "1.1.1",  # Additional bug fixes
    "1.1.2",  # Bug fixes and improvements
    "1.2.0",  # Major Enhancements and Archive Management
    "1.3.0",  # Workflow improvements and performance optimizations
    "1.4.0",  # Project configuration simplification and dependency updates
]


def get_version_history() -> list[str]:
    """Get the version history."""
    return VERSION_HISTORY.copy()


def get_latest_version() -> str:
    """Get the latest version from history."""
    return VERSION_HISTORY[-1] if VERSION_HISTORY else get_version()


# Version constants for feature flags and compatibility
FEATURES = {
    "semantic_versioning": "0.9.0",
    "comprehensive_testing": "0.9.0",
    "enhanced_cli": "0.9.0",
    "template_system": "0.9.0",
    "json_validation": "0.9.0",
    "git_integration": "0.9.0",
    "production_ready": "1.0.0",
    "pypi_distribution": "1.0.0",
    "comprehensive_test_suite": "1.0.0",
    "security_validated": "1.0.0",
    "archive_management": "1.2.0",
    "issue_close_command": "1.2.0",
    "batch_close_operations": "1.2.0",
    "task_to_issue_migration": "1.2.0",
    "pr_comment_management": "1.2.0",
    "enhanced_validation": "1.2.0",
    "improved_performance": "1.2.0",
    "workflow_improvements": "1.3.0",
    "performance_optimizations": "1.3.0",
    "github_sync_enhancements": "1.3.0",
    "simplified_configuration": "1.4.0",
    "importlib_metadata_versioning": "1.4.0",
    "dependency_updates": "1.4.0",
}


def has_feature(feature_name: str) -> bool:
    """Check if a feature is available in the current version."""
    if feature_name not in FEATURES:
        return False

    feature_version = Version.parse(FEATURES[feature_name])
    return feature_version <= CURRENT_VERSION


def get_feature_version(feature_name: str) -> Optional[str]:
    """Get the version when a feature was introduced."""
    return FEATURES.get(feature_name)


def list_available_features() -> dict[str, str]:
    """List all available features and their introduction versions."""
    available_features = {}
    for feature, version in FEATURES.items():
        if has_feature(feature):
            available_features[feature] = version
    return available_features
