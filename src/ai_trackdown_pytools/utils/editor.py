"""Editor utilities for AI Trackdown PyTools."""

import os
import subprocess
from pathlib import Path
from typing import Optional

from ai_trackdown_pytools.core.config import Config


class EditorUtils:
    """Editor utilities for opening files."""

    @staticmethod
    def get_default_editor() -> str:
        """Get default editor from configuration or environment."""
        config = Config.load()

        # Try configuration first
        editor = config.get("editor.default")
        if editor:
            return editor

        # Try environment variables
        for env_var in ["VISUAL", "EDITOR"]:
            editor = os.getenv(env_var)
            if editor:
                return editor

        # Platform-specific defaults
        import platform

        system = platform.system().lower()

        if system == "darwin":  # macOS
            return "open"
        elif system == "windows":
            return "notepad"
        else:  # Linux and others
            return "nano"

    @staticmethod
    def open_file(file_path: Path, editor: Optional[str] = None) -> bool:
        """Open file in editor."""
        if not file_path.exists():
            return False

        if editor is None:
            editor = EditorUtils.get_default_editor()

        try:
            # Handle special cases
            if editor == "open":  # macOS open command
                subprocess.run(["open", str(file_path)], check=True)
            elif editor in ["code", "subl", "atom"]:  # Modern editors
                subprocess.run([editor, str(file_path)], check=True)
            else:  # Terminal editors
                subprocess.run([editor, str(file_path)], check=True)

            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    @staticmethod
    def is_editor_available(editor: str) -> bool:
        """Check if editor is available."""
        try:
            subprocess.run(
                [editor, "--version"], capture_output=True, check=True, timeout=5
            )
            return True
        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            subprocess.TimeoutExpired,
        ):
            return False
