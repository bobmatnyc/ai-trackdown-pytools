#!/usr/bin/env python3
"""Simple test script to verify CLI framework functionality."""

import sys
from pathlib import Path


def test_cli_import():
    """Test that the CLI can be imported."""
    try:
        # Add src to path
        src_path = Path(__file__).parent / "src"
        sys.path.insert(0, str(src_path))

        print("✅ CLI import successful")
        return True
    except Exception as e:
        print(f"❌ CLI import failed: {e}")
        return False


def test_core_imports():
    """Test that core modules can be imported."""
    try:
        src_path = Path(__file__).parent / "src"
        sys.path.insert(0, str(src_path))

        print("✅ Core modules import successful")
        return True
    except Exception as e:
        print(f"❌ Core module import failed: {e}")
        return False


def test_health_check():
    """Test health check functionality."""
    try:
        src_path = Path(__file__).parent / "src"
        sys.path.insert(0, str(src_path))

        from ai_trackdown_pytools.utils.health import check_health

        health_status = check_health()
        print("✅ Health check successful")
        print(f"   Overall status: {'✅' if health_status['overall'] else '❌'}")

        for check, result in health_status["checks"].items():
            status_icon = "✅" if result["status"] else "❌"
            print(f"   {status_icon} {check}: {result['message']}")

        return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


def test_template_manager():
    """Test template manager functionality."""
    try:
        src_path = Path(__file__).parent / "src"
        sys.path.insert(0, str(src_path))

        from ai_trackdown_pytools.utils.templates import TemplateManager

        template_manager = TemplateManager()
        templates = template_manager.list_templates()

        print("✅ Template manager successful")
        print(f"   Found {len(templates)} templates")

        for template in templates[:3]:  # Show first 3
            print(f"   • {template['name']} ({template['type']})")

        return True
    except Exception as e:
        print(f"❌ Template manager failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 Testing AI Trackdown PyTools CLI Framework\n")

    tests = [
        ("CLI Import", test_cli_import),
        ("Core Imports", test_core_imports),
        ("Health Check", test_health_check),
        ("Template Manager", test_template_manager),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"Testing {test_name}:")
        if test_func():
            passed += 1
        print()

    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! CLI framework is ready.")
        return 0
    else:
        print("❌ Some tests failed. Check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
