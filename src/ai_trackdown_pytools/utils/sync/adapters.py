"""Auto-registration of all sync adapters.

WHY: This module imports all adapter implementations to ensure they are registered
with the adapter registry when the sync module is imported. This follows the
pattern of self-registering plugins.

DESIGN DECISION: Each adapter module registers itself at import time using the
register_adapter function at the bottom of the file. This module ensures all
adapters are imported and thus registered. Imports are made conditional to avoid
dependency errors when optional packages are not installed.
"""

import warnings
from typing import List

# Always available - GitHub adapter uses built-in git CLI
from .github_adapter import GitHubAdapter

__all__: List[str] = ["GitHubAdapter"]

# Conditionally import adapters that require optional dependencies
try:
    from .clickup_adapter import ClickUpAdapter

    __all__.append("ClickUpAdapter")
except ImportError as e:
    warnings.warn(
        f"ClickUp adapter not available: {e}. "
        "Install with: pip install ai-trackdown-pytools[sync]",
        ImportWarning,
        stacklevel=2,
    )

try:
    from .linear_adapter import LinearAdapter

    __all__.append("LinearAdapter")
except ImportError as e:
    warnings.warn(
        f"Linear adapter not available: {e}. "
        "Install with: pip install ai-trackdown-pytools[sync]",
        ImportWarning,
        stacklevel=2,
    )

try:
    from .jira_adapter import JiraAdapter

    __all__.append("JiraAdapter")
except ImportError as e:
    warnings.warn(
        f"Jira adapter not available: {e}. "
        "Install with: pip install ai-trackdown-pytools[sync]",
        ImportWarning,
        stacklevel=2,
    )

# Note: Each adapter module should register itself at the bottom with:
# from .registry import register_adapter
# register_adapter("platform_name", AdapterClass)
