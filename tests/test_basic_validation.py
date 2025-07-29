#!/usr/bin/env python3
"""Basic test of the validation system."""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    # Test JSON schema loading
    from ai_trackdown_pytools.utils.validation import SchemaValidator

    print("✓ Successfully imported SchemaValidator")

    validator = SchemaValidator()
    schemas = validator.list_schemas()
    print(f"✓ Available schemas: {schemas}")

    # Test basic validation with simple data
    from datetime import datetime

    task_data = {
        "id": "TSK-0001",
        "title": "Test Task",
        "status": "open",
        "priority": "medium",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }

    print("✓ Testing task validation...")
    result = validator._validate_against_json_schema(task_data, "task")
    print(f"✓ JSON Schema validation: valid={result.valid}")
    if result.errors:
        for error in result.errors:
            print(f"  Error: {error}")

    # Test with invalid data
    invalid_task = {
        "id": "INVALID-001",  # Wrong format
        "title": "",  # Empty title
        "status": "invalid_status",
    }

    print("✓ Testing invalid task validation...")
    result = validator._validate_against_json_schema(invalid_task, "task")
    print(
        f"✓ Invalid task validation: valid={result.valid}, errors={len(result.errors)}"
    )

    print("\n🎉 Basic validation system is working correctly!")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
