"""Template management utilities for AI Trackdown PyTools."""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from jinja2 import Environment, FileSystemLoader, Template

from ai_trackdown_pytools.core.config import Config


class TemplateError(Exception):
    """Exception raised for template-related errors."""

    pass


class TemplateEngine:
    """Template engine for processing Jinja2 templates."""

    def __init__(self, template_dirs: Optional[List[Path]] = None):
        """Initialize template engine."""
        self.template_dirs = template_dirs or []

        # Set up Jinja2 environment
        if self.template_dirs:
            loader = FileSystemLoader([str(d) for d in self.template_dirs])
        else:
            loader = FileSystemLoader([])

        self.env = Environment(loader=loader)

    def render_template(self, template_name: str, variables: Dict[str, Any]) -> str:
        """Render template with variables."""
        try:
            template = self.env.get_template(template_name)
            return template.render(**variables)
        except Exception as e:
            raise TemplateError(
                f"Failed to render template {template_name}: {e}"
            ) from e

    def render_string(self, template_string: str, variables: Dict[str, Any]) -> str:
        """Render template string with variables."""
        try:
            template = Template(template_string)
            return template.render(**variables)
        except Exception as e:
            raise TemplateError(f"Failed to render template string: {e}") from e

    def validate_template(self, template_string: str) -> bool:
        """Validate template syntax."""
        try:
            Template(template_string)
            return True
        except Exception:
            return False

    def list_templates(self) -> List[str]:
        """List available templates."""
        templates = []
        for template_dir in self.template_dirs:
            if template_dir.exists():
                for template_file in template_dir.rglob("*.j2"):
                    rel_path = template_file.relative_to(template_dir)
                    templates.append(str(rel_path))
        return sorted(templates)


class TemplateManager:
    """Template manager for AI Trackdown PyTools."""

    def __init__(self):
        """Initialize template manager."""
        self.config = Config.load()
        self._template_dirs = self._get_template_directories()

    def _get_template_directories(self) -> List[Path]:
        """Get template directories in order of precedence."""
        dirs = []

        # Project templates (highest precedence)
        if self.config.project_root:
            project_templates = self.config.project_root / ".ai-trackdown" / "templates"
            if project_templates.exists():
                dirs.append(project_templates)

        # Global user templates
        global_templates = Path.home() / ".ai-trackdown" / "templates"
        if global_templates.exists():
            dirs.append(global_templates)

        # Package templates (lowest precedence)
        package_templates = Path(__file__).parent.parent / "templates"
        if package_templates.exists():
            dirs.append(package_templates)

        return dirs

    def list_templates(
        self, template_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List available templates."""
        templates = []
        seen_names = set()

        for template_dir in self._template_dirs:
            if template_type:
                type_dir = template_dir / template_type
                if not type_dir.exists():
                    continue
                search_dirs = [type_dir]
            else:
                search_dirs = [d for d in template_dir.iterdir() if d.is_dir()]

            for search_dir in search_dirs:
                for template_file in search_dir.glob("*.yaml"):
                    template_name = template_file.stem

                    # Skip if we've already seen this template (higher precedence)
                    if template_name in seen_names:
                        continue

                    seen_names.add(template_name)

                    try:
                        with open(template_file, encoding="utf-8") as f:
                            template_data = yaml.safe_load(f)

                        templates.append(
                            {
                                "name": template_name,
                                "type": template_data.get("type", search_dir.name),
                                "description": template_data.get("description", ""),
                                "version": template_data.get("version", "1.0.0"),
                                "author": template_data.get("author", ""),
                                "path": template_file,
                                "modified": datetime.fromtimestamp(
                                    template_file.stat().st_mtime
                                ),
                            }
                        )
                    except Exception:
                        continue

        return sorted(templates, key=lambda t: t["name"])

    def load_template(self, template_type: str, name: str) -> Optional[Dict[str, Any]]:
        """Load template by type and name."""
        for template_dir in self._template_dirs:
            template_file = template_dir / template_type / f"{name}.yaml"
            if template_file.exists():
                try:
                    with open(template_file, encoding="utf-8") as f:
                        return yaml.safe_load(f)
                except Exception:
                    continue

        return None

    def template_exists(self, template_type: str, name: str) -> bool:
        """Check if template exists."""
        return self.load_template(template_type, name) is not None

    def create_template(
        self, template_type: str, name: str, description: str = "", author: str = ""
    ) -> Path:
        """Create new template."""
        # Use project templates directory if available, otherwise global
        if self.config.project_root:
            template_dir = self.config.project_root / ".ai-trackdown" / "templates"
        else:
            template_dir = Path.home() / ".ai-trackdown" / "templates"

        type_dir = template_dir / template_type
        type_dir.mkdir(parents=True, exist_ok=True)

        template_file = type_dir / f"{name}.yaml"

        # Create default template structure
        template_data = {
            "name": name,
            "description": description,
            "type": template_type,
            "version": "1.0.0",
            "author": author,
            "variables": {
                "title": {
                    "description": f"{template_type.title()} title",
                    "required": True,
                },
                "description": {
                    "description": f"{template_type.title()} description",
                    "default": "",
                },
            },
            "content": "# {{ title }}\n\n{{ description or 'No description provided.' }}\n",
        }

        with open(template_file, "w", encoding="utf-8") as f:
            yaml.dump(template_data, f, default_flow_style=False)

        return template_file

    def apply_template(
        self,
        template_type: str,
        name: str,
        project_path: Path,
        variables: Optional[Dict[str, Any]] = None,
        output_path: Optional[Path] = None,
    ) -> bool:
        """Apply template to create content."""
        template_data = self.load_template(template_type, name)
        if not template_data:
            return False

        # Merge variables
        template_vars = variables or {}

        # Add default variables
        template_vars.update(
            {
                "created_at": datetime.now().isoformat(),
                "project_name": project_path.name,
            }
        )

        # Process template content
        try:
            template = Template(template_data.get("content", ""))
            rendered_content = template.render(**template_vars)

            # Determine output path
            if output_path is None:
                if template_type == "project":
                    output_path = project_path / "README.md"
                else:
                    # Create task file
                    from ai_trackdown_pytools.core.task import TaskManager

                    task_manager = TaskManager(project_path)
                    task = task_manager.create_task(**template_vars)
                    output_path = task.file_path

            # Write rendered content
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(rendered_content)

            return True

        except Exception as e:
            print(f"Template application error: {e}")
            import traceback

            traceback.print_exc()
            return False

    def validate_template(self, template_type: str, name: str) -> Dict[str, Any]:
        """Validate template."""
        template_data = self.load_template(template_type, name)
        if not template_data:
            return {"valid": False, "errors": ["Template not found"]}

        errors = []
        warnings = []

        # Check required fields
        required_fields = ["name", "type", "content"]
        for field in required_fields:
            if field not in template_data:
                errors.append(f"Missing required field: {field}")

        # Check template syntax
        try:
            Template(template_data.get("content", ""))
        except Exception as e:
            errors.append(f"Template syntax error: {e}")

        # Check variables
        variables = template_data.get("variables", {})
        for var_name, var_config in variables.items():
            if not isinstance(var_config, dict):
                warnings.append(f"Variable '{var_name}' should be a dictionary")

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    def install_templates(
        self, source: str, template_name: Optional[str] = None, force: bool = False
    ) -> List[str]:
        """Install templates from external source."""
        # For now, just copy from local path
        # In the future, this could support URLs, Git repos, etc.

        source_path = Path(source)
        if not source_path.exists():
            raise FileNotFoundError(f"Template source not found: {source}")

        # Determine target directory
        if self.config.project_root:
            target_dir = self.config.project_root / ".ai-trackdown" / "templates"
        else:
            target_dir = Path.home() / ".ai-trackdown" / "templates"

        target_dir.mkdir(parents=True, exist_ok=True)

        installed = []

        if source_path.is_file() and source_path.suffix == ".yaml":
            # Single template file
            if template_name:
                target_file = target_dir / "custom" / f"{template_name}.yaml"
            else:
                target_file = target_dir / "custom" / source_path.name

            target_file.parent.mkdir(exist_ok=True)

            if target_file.exists() and not force:
                raise FileExistsError(f"Template already exists: {target_file}")

            shutil.copy2(source_path, target_file)
            installed.append(target_file.stem)

        elif source_path.is_dir():
            # Directory of templates
            for template_file in source_path.rglob("*.yaml"):
                rel_path = template_file.relative_to(source_path)
                target_file = target_dir / rel_path

                if target_file.exists() and not force:
                    continue

                target_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(template_file, target_file)
                installed.append(str(rel_path))

        return installed

    def init_templates(self) -> None:
        """Initialize default templates."""
        # Create basic template structure
        template_dir = Path.home() / ".ai-trackdown" / "templates"

        for template_type in ["task", "issue", "epic", "pr"]:
            type_dir = template_dir / template_type
            type_dir.mkdir(parents=True, exist_ok=True)

            # Create default template if it doesn't exist
            default_template = type_dir / "default.yaml"
            if not default_template.exists():
                self.create_template(
                    template_type=template_type,
                    name="default",
                    description=f"Default {template_type} template",
                    author="AI Trackdown PyTools",
                )


# Utility functions for templates
def load_template(template_type: str, name: str) -> Optional[Dict[str, Any]]:
    """Load template by type and name using global template manager."""
    manager = TemplateManager()
    return manager.load_template(template_type, name)


def render_template(template_type: str, name: str, variables: Dict[str, Any]) -> str:
    """Render template using global template manager."""
    template_data = load_template(template_type, name)
    if not template_data:
        raise TemplateError(f"Template {template_type}/{name} not found")

    try:
        template = Template(template_data.get("content", ""))
        return template.render(**variables)
    except Exception as e:
        raise TemplateError(
            f"Failed to render template {template_type}/{name}: {e}"
        ) from e


def list_templates(template_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """List available templates using global template manager."""
    manager = TemplateManager()
    return manager.list_templates(template_type)


def validate_template(template_type: str, name: str) -> Dict[str, Any]:
    """Validate template using global template manager."""
    manager = TemplateManager()
    return manager.validate_template(template_type, name)


def get_template_variables(template_type: str, name: str) -> Dict[str, Any]:
    """Get template variables definition."""
    template_data = load_template(template_type, name)
    if not template_data:
        return {}

    return template_data.get("variables", {})
