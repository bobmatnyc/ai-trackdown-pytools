"""Utility functions for saving and loading ticket models to/from YAML files.

This module provides simple functions to save and load ticket models directly
to/from YAML files, useful for testing and other scenarios where you need
direct file access without going through TaskManager.

WHY: While TaskManager handles the full workflow with markdown files and frontmatter,
tests and other utilities often need simpler direct YAML serialization for
ticket models. This module provides that functionality.
"""

from datetime import date, datetime
from pathlib import Path
from typing import Type, TypeVar, Union

import yaml

from ai_trackdown_pytools.core.models import BaseTicketModel

# Type variable for ticket models
T = TypeVar("T", bound=BaseTicketModel)


def datetime_representer(dumper, data):
    """Custom representer for datetime objects in YAML.

    WHY: Ensures datetime objects are serialized consistently as ISO strings
    in YAML files, matching the format expected by the models.
    """
    return dumper.represent_scalar("tag:yaml.org,2002:str", data.isoformat())


def date_representer(dumper, data):
    """Custom representer for date objects in YAML.

    WHY: Ensures date objects are serialized consistently as ISO strings
    in YAML files, matching the format expected by the models.
    """
    return dumper.represent_scalar("tag:yaml.org,2002:str", data.isoformat())


# Register custom representers
yaml.add_representer(datetime, datetime_representer)
yaml.add_representer(date, date_representer)


def save_ticket(ticket: BaseTicketModel, file_path: Union[str, Path]) -> None:
    """Save a ticket model to a YAML file.

    WHY: Provides a simple way to persist ticket models to YAML files
    for testing and utility purposes, using Pydantic's dict export with
    proper datetime serialization.

    Args:
        ticket: The ticket model to save
        file_path: Path where to save the YAML file
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert model to dict, using Pydantic's serialization
    ticket_dict = ticket.model_dump(mode="json")

    # Write to YAML file
    with open(file_path, "w", encoding="utf-8") as f:
        yaml.dump(ticket_dict, f, default_flow_style=False, sort_keys=False)


def load_ticket(file_path: Union[str, Path], model_class: Type[T]) -> T:
    """Load a ticket model from a YAML file.

    WHY: Provides a simple way to load ticket models from YAML files
    for testing and utility purposes, with proper model validation.

    Args:
        file_path: Path to the YAML file
        model_class: The Pydantic model class to instantiate

    Returns:
        An instance of the specified model class

    Raises:
        FileNotFoundError: If the file doesn't exist
        yaml.YAMLError: If the file isn't valid YAML
        ValidationError: If the data doesn't match the model schema
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Ticket file not found: {file_path}")

    # Read YAML file
    with open(file_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Parse datetime strings back to datetime objects
    if isinstance(data, dict):
        for field in ["created_at", "updated_at", "resolved_at", "merged_at"]:
            if field in data and isinstance(data[field], str):
                data[field] = datetime.fromisoformat(data[field])

        # Parse date strings back to date objects
        for field in ["due_date", "target_date"]:
            if field in data and isinstance(data[field], str):
                data[field] = date.fromisoformat(data[field])

    # Create and return model instance
    return model_class(**data)
