"""Platform-specific and internationalization edge case tests.

This test suite focuses on:
- Windows/macOS/Linux compatibility edge cases
- Unicode and internationalization issues
- File system encoding differences
- Path separator normalization
- Case sensitivity issues
- Locale-specific formatting
- Character encoding edge cases
"""

import locale
import os
import platform
from pathlib import Path

import pytest

from ai_trackdown_pytools.core.config import Config
from ai_trackdown_pytools.utils.frontmatter import FrontmatterParser
from ai_trackdown_pytools.utils.validation import SchemaValidator


class TestPlatformSpecificEdgeCases:
    """Test platform-specific edge cases."""

    def test_windows_long_path_handling(self, temp_dir: Path):
        """Test Windows long path limitations."""
        if platform.system() != "Windows":
            pytest.skip("Windows-specific test")

        # Windows has a 260 character path limit (historically)
        long_path_components = [
            "very_long_directory_name_that_could_cause_issues_on_windows_systems",
            "another_extremely_long_directory_name_for_testing_path_limits",
            "and_yet_another_very_long_name_to_push_boundaries",
            "final_component_with_a_really_long_name_for_testing",
        ]

        current_path = temp_dir
        try:
            for component in long_path_components:
                current_path = current_path / component
                if len(str(current_path)) > 250:  # Approach Windows limit
                    break
                current_path.mkdir(parents=True, exist_ok=True)

            # Try to create config in long path
            config_path = current_path / "config.yaml"
            config = Config.create_default(config_path)

            assert config_path.exists()

        except OSError as e:
            if (
                "path too long" in str(e).lower()
                or "filename too long" in str(e).lower()
            ):
                # Expected on systems with path limitations
                pytest.skip(f"Path length limitation hit: {e}")
            else:
                raise

    def test_unix_case_sensitivity(self, temp_dir: Path):
        """Test case sensitivity handling on Unix systems."""
        if platform.system() == "Windows":
            pytest.skip("Unix-specific test")

        # Create files with different cases
        files = [temp_dir / "Test.md", temp_dir / "test.md", temp_dir / "TEST.md"]

        for i, file_path in enumerate(files):
            file_path.write_text(
                f"""---
id: TSK-{i:04d}
title: Case Test {i}
case: {file_path.name}
---

Content {i}.
"""
            )

        # All files should exist independently on case-sensitive systems
        assert all(f.exists() for f in files)

        # Should be able to parse all files
        parser = FrontmatterParser()
        parsed_data = []

        for file_path in files:
            frontmatter, content, result = parser.parse_file(file_path)
            assert result.valid
            parsed_data.append(frontmatter)

        # Each should have different case in filename reference
        cases = [data["case"] for data in parsed_data]
        assert len(set(cases)) == 3, "Case sensitivity not working properly"

    def test_macos_hfs_normalization(self, temp_dir: Path):
        """Test macOS HFS+ filename normalization issues."""
        if platform.system() != "Darwin":
            pytest.skip("macOS-specific test")

        # Unicode normalization differences (NFC vs NFD)
        # é can be represented as single character (NFC) or e + combining accent (NFD)
        nfc_filename = "café.md"  # NFC form
        nfd_filename = "cafe\u0301.md"  # NFD form (e + combining acute accent)

        nfc_path = temp_dir / nfc_filename
        nfd_path = temp_dir / nfd_filename

        # Create file with NFC name
        nfc_path.write_text(
            """---
title: NFC Test
encoding: NFC
---

NFC content.
"""
        )

        # Try to access with NFD name - may or may not work depending on filesystem
        parser = FrontmatterParser()

        try:
            frontmatter_nfc, content_nfc, result_nfc = parser.parse_file(nfc_path)
            assert result_nfc.valid

            # Test if NFD access works (filesystem dependent)
            if nfd_path.exists():
                frontmatter_nfd, content_nfd, result_nfd = parser.parse_file(nfd_path)
                assert result_nfd.valid

        except Exception as e:
            # Some normalization issues are expected
            assert "unicode" in str(e).lower() or "encoding" in str(e).lower()

    def test_path_separator_normalization(self, temp_dir: Path):
        """Test path separator normalization across platforms."""
        # Test mixed separators
        mixed_separators = [
            "project\\subdir/file.md",
            "project/subdir\\file.md",
            "project\\\\subdir//file.md",
            "project////subdir\\\\\\file.md",
        ]

        for mixed_path in mixed_separators:
            # Should normalize to platform-appropriate separators
            normalized_path = temp_dir / mixed_path

            # Create directory structure
            normalized_path.parent.mkdir(parents=True, exist_ok=True)
            normalized_path.write_text("---\ntitle: Path Test\n---\nContent")

            # Should be accessible
            assert normalized_path.exists()

            # Should use correct separators for platform
            path_str = str(normalized_path)
            if platform.system() == "Windows":
                assert "\\" in path_str or "/" in path_str  # Windows accepts both
            else:
                assert "/" in path_str  # Unix systems use forward slash

    def test_windows_reserved_names(self, temp_dir: Path):
        """Test handling of Windows reserved filenames."""
        if platform.system() != "Windows":
            pytest.skip("Windows-specific test")

        reserved_names = [
            "CON",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "COM2",
            "COM3",
            "COM4",
            "COM5",
            "COM6",
            "COM7",
            "COM8",
            "COM9",
            "LPT1",
            "LPT2",
            "LPT3",
            "LPT4",
            "LPT5",
            "LPT6",
            "LPT7",
            "LPT8",
            "LPT9",
        ]

        for reserved_name in reserved_names:
            reserved_path = temp_dir / f"{reserved_name}.md"

            try:
                reserved_path.write_text("---\ntitle: Reserved Name Test\n---\nContent")

                # If creation succeeds, file should be accessible
                if reserved_path.exists():
                    parser = FrontmatterParser()
                    frontmatter, content, result = parser.parse_file(reserved_path)
                    # Should either work or fail gracefully

            except OSError:
                # Expected for truly reserved names
                pass

    def test_special_characters_in_paths(self, temp_dir: Path):
        """Test handling of special characters in file paths."""
        special_chars = [
            "file with spaces.md",
            "file-with-dashes.md",
            "file_with_underscores.md",
            "file.with.dots.md",
            "file@with@symbols.md",
            "file#with#hash.md",
            "file%with%percent.md",
            "file&with&ampersand.md",
        ]

        if platform.system() != "Windows":
            # Unix systems can handle more special characters
            special_chars.extend(
                ["file:with:colons.md", "file<with>brackets.md", "file|with|pipes.md"]
            )

        for special_name in special_chars:
            special_path = temp_dir / special_name

            try:
                special_path.write_text(
                    f"""---
title: Special Character Test
filename: {special_name}
---

Content for {special_name}.
"""
                )

                if special_path.exists():
                    parser = FrontmatterParser()
                    frontmatter, content, result = parser.parse_file(special_path)
                    assert result.valid
                    assert frontmatter["filename"] == special_name

            except (OSError, ValueError) as e:
                # Some special characters may not be allowed
                assert "invalid" in str(e).lower() or "illegal" in str(e).lower()

    def test_file_system_encoding_differences(self, temp_dir: Path):
        """Test file system encoding differences across platforms."""
        # Test various encodings that might be used by different file systems
        test_encodings = ["utf-8", "latin-1", "cp1252"]

        if platform.system() == "Windows":
            test_encodings.append("cp1252")  # Windows default

        for encoding in test_encodings:
            try:
                test_content = f"""---
title: Encoding Test {encoding}
encoding: {encoding}
special: café résumé naïve
---

Content with special characters: café résumé naïve
Encoding: {encoding}
"""

                encoded_file = temp_dir / f"encoding_test_{encoding}.md"

                # Write with specific encoding
                with open(encoded_file, "w", encoding=encoding) as f:
                    f.write(test_content)

                # Read back and parse
                parser = FrontmatterParser()
                frontmatter, content, result = parser.parse_file(encoded_file)

                if result.valid:
                    assert frontmatter["encoding"] == encoding
                    assert "café" in frontmatter["special"]

            except (UnicodeError, LookupError):
                # Some encodings may not be supported
                pass


class TestUnicodeAndInternationalization:
    """Test Unicode and internationalization edge cases."""

    def test_unicode_in_all_fields(self):
        """Test Unicode characters in all possible fields."""
        validator = SchemaValidator()

        unicode_task = {
            "id": "TSK-0001",
            "title": "Unicode Test: 测试 🚀 Тест αβγ ñoël",
            "description": """
Multi-language description:
- English: Hello World! 
- Chinese: 你好世界！测试
- Russian: Привет мир! Тест
- Greek: Γεια σας κόσμε! δοκιμή
- Arabic: مرحبا بالعالم! اختبار
- Japanese: こんにちは世界！テスト
- Emoji: 🌍🚀💫⭐🎉
""",
            "assignees": ["用户", "пользователь", "χρήστης", "مستخدم", "ユーザー"],
            "tags": ["标签", "тег", "ετικέτα", "علامة", "タグ", "🏷️"],
            "priority": "medium",
            "status": "open",
            "metadata": {
                "chinese": "中文测试",
                "russian": "Русский тест",
                "arabic": "اختبار عربي",
                "japanese": "日本語テスト",
                "emoji": "🎯🔥💯",
            },
        }

        result = validator.validate_task(unicode_task)
        assert result["valid"] is True

    def test_right_to_left_languages(self):
        """Test right-to-left language handling."""
        validator = SchemaValidator()

        rtl_task = {
            "id": "TSK-0001",
            "title": "اختبار النص من اليمين إلى اليسار",  # Arabic RTL
            "description": "עברית: בדיקה של כתיבה מימין לשמאל",  # Hebrew RTL
            "assignees": ["محمد", "יוסף"],  # Arabic and Hebrew names
            "tags": ["عربي", "עברית", "RTL"],
            "priority": "medium",
            "status": "open",
            "notes": """
Mixed LTR and RTL text:
This is English (LTR) followed by Arabic: هذا نص عربي
And Hebrew: זהו טקסט עברי
Back to English again.
""",
        }

        result = validator.validate_task(rtl_task)
        assert result["valid"] is True

    def test_unicode_normalization_forms(self, temp_dir: Path):
        """Test different Unicode normalization forms."""
        import unicodedata

        # Test different normalization forms of the same character
        # é can be represented in multiple ways
        test_cases = [
            ("NFC", unicodedata.normalize("NFC", "café")),
            ("NFD", unicodedata.normalize("NFD", "café")),
            ("NFKC", unicodedata.normalize("NFKC", "café")),
            ("NFKD", unicodedata.normalize("NFKD", "café")),
        ]

        parser = FrontmatterParser()

        for norm_form, normalized_text in test_cases:
            test_file = temp_dir / f"unicode_{norm_form}.md"
            test_file.write_text(
                f"""---
title: Unicode {norm_form} Test
text: {normalized_text}
normalization: {norm_form}
---

Content with {norm_form}: {normalized_text}
"""
            )

            frontmatter, content, result = parser.parse_file(test_file)
            assert result.valid
            assert frontmatter["normalization"] == norm_form
            assert (
                "café" in frontmatter["text"]
            )  # Should contain café regardless of normalization

    def test_locale_specific_formatting(self):
        """Test locale-specific formatting issues."""
        import datetime

        # Save current locale
        original_locale = locale.getlocale()

        try:
            # Test with different locales if available
            test_locales = [
                ("en_US", "UTF-8"),
                ("fr_FR", "UTF-8"),
                ("de_DE", "UTF-8"),
                ("ja_JP", "UTF-8"),
                ("zh_CN", "UTF-8"),
            ]

            validator = SchemaValidator()

            for locale_name, encoding in test_locales:
                try:
                    # Try to set locale
                    if platform.system() == "Windows":
                        locale_str = locale_name.replace("_", "-")
                    else:
                        locale_str = f"{locale_name}.{encoding}"

                    locale.setlocale(locale.LC_ALL, locale_str)

                    # Test date formatting in this locale
                    now = datetime.datetime.now()
                    formatted_date = now.strftime("%x")  # Locale-specific date format

                    task_data = {
                        "id": "TSK-0001",
                        "title": f"Locale Test {locale_name}",
                        "created_at": now.isoformat(),
                        "locale_date": formatted_date,
                        "priority": "medium",
                        "status": "open",
                    }

                    result = validator.validate_task(task_data)
                    assert result["valid"] is True

                except locale.Error:
                    # Locale not available on this system
                    continue

        finally:
            # Restore original locale
            try:
                locale.setlocale(locale.LC_ALL, original_locale)
            except locale.Error:
                pass

    def test_emoji_and_symbols_handling(self):
        """Test handling of emoji and special symbols."""
        validator = SchemaValidator()

        emoji_task = {
            "id": "TSK-0001",
            "title": "🚀 Emoji Test 💫 Project",
            "description": """
Emoji categories:
- Faces: 😀😃😄😁😆😅😂🤣😊😇
- Objects: 🎯🔥💎⚡🌟💯🎉🎊🎁🏆
- Animals: 🐶🐱🐭🐹🐰🦊🐻🐼🐨🐯
- Food: 🍎🍊🍌🍇🥝🍓🥭🍑🥥🥑
- Flags: 🇺🇸🇬🇧🇫🇷🇩🇪🇯🇵🇨🇳🇷🇺
""",
            "assignees": ["👨‍💻", "👩‍💻", "🧑‍🔬"],
            "tags": ["🏷️emoji", "💻tech", "🎯goals", "🚀launch"],
            "priority": "medium",
            "status": "open",
            "metadata": {
                "mood": "😊",
                "complexity": "🔥🔥🔥",
                "progress": "▓▓▓░░░░░░░",
                "symbols": "α β γ δ ε ζ η θ ι κ λ μ ν ξ ο π ρ σ τ υ φ χ ψ ω",
            },
        }

        result = validator.validate_task(emoji_task)
        assert result["valid"] is True

    def test_zero_width_characters(self):
        """Test handling of zero-width characters and invisible Unicode."""
        validator = SchemaValidator()

        # Zero-width characters that might cause issues
        invisible_chars = [
            "\u200b",  # Zero Width Space
            "\u200c",  # Zero Width Non-Joiner
            "\u200d",  # Zero Width Joiner
            "\ufeff",  # Zero Width No-Break Space (BOM)
            "\u2060",  # Word Joiner
        ]

        for char in invisible_chars:
            task_data = {
                "id": "TSK-0001",
                "title": f"Invisible{char}Character{char}Test",
                "description": f"Text with{char}invisible{char}characters",
                "priority": "medium",
                "status": "open",
            }

            result = validator.validate_task(task_data)
            # Should handle gracefully, may or may not be valid

    def test_surrogate_pairs_handling(self):
        """Test handling of Unicode surrogate pairs."""
        validator = SchemaValidator()

        # Characters that require surrogate pairs in UTF-16
        surrogate_chars = [
            "𝐀𝐁𝐂",  # Mathematical Bold letters
            "𝕏𝕐𝕫",  # Mathematical Double-Struck letters
            "🚀🌟💫",  # Emoji requiring surrogate pairs
            "𝒜𝒷𝒸𝒹ℯ𝒻𝑔",  # Script letters
            "𝔄𝔅ℭ𝔇𝔈𝔉𝔊",  # Fraktur letters
        ]

        for surrogate_text in surrogate_chars:
            task_data = {
                "id": "TSK-0001",
                "title": f"Surrogate Test: {surrogate_text}",
                "description": f"Content with surrogate pairs: {surrogate_text}",
                "priority": "medium",
                "status": "open",
            }

            result = validator.validate_task(task_data)
            assert result["valid"] is True

    def test_mixed_script_handling(self):
        """Test handling of mixed scripts in single text."""
        validator = SchemaValidator()

        mixed_script_text = """
Mixed script example:
- Latin + Greek: Hello Κόσμε (Kosme)
- Latin + Cyrillic: Hello Мир (Mir)  
- Latin + Arabic: Hello العالم (Al-Alam)
- Latin + Chinese: Hello 世界 (Shìjiè)
- Latin + Japanese: Hello 世界 (Sekai)
- Numbers: 123 ١٢٣ 一二三
- Mixed emoji: Hello 👋 世界 🌍 Мир 🌎
"""

        task_data = {
            "id": "TSK-0001",
            "title": "Mixed Script Test",
            "description": mixed_script_text,
            "priority": "medium",
            "status": "open",
        }

        result = validator.validate_task(task_data)
        assert result["valid"] is True


class TestEncodingEdgeCases:
    """Test character encoding edge cases."""

    def test_bom_handling(self, temp_dir: Path):
        """Test handling of Byte Order Mark (BOM) characters."""
        # Create files with different BOMs
        bom_types = [
            ("UTF-8", b"\xef\xbb\xbf"),
            ("UTF-16-LE", b"\xff\xfe"),
            ("UTF-16-BE", b"\xfe\xff"),
            ("UTF-32-LE", b"\xff\xfe\x00\x00"),
            ("UTF-32-BE", b"\x00\x00\xfe\xff"),
        ]

        parser = FrontmatterParser()

        for encoding_name, bom in bom_types:
            if encoding_name.startswith("UTF-32"):
                continue  # Skip UTF-32 for simplicity

            bom_file = temp_dir / f"bom_{encoding_name.lower().replace('-', '_')}.md"

            # Create content with BOM
            content = f"""---
title: BOM Test
encoding: {encoding_name}
---

Content with BOM.
"""

            if encoding_name == "UTF-8":
                # Write UTF-8 with BOM
                with open(bom_file, "wb") as f:
                    f.write(bom + content.encode("utf-8"))
            else:
                # For UTF-16, need to encode properly
                try:
                    with open(bom_file, "w", encoding=encoding_name.lower()) as f:
                        f.write(content)
                except (LookupError, UnicodeError):
                    # Encoding not supported
                    continue

            try:
                frontmatter, parsed_content, result = parser.parse_file(bom_file)
                if result.valid:
                    assert frontmatter["title"] == "BOM Test"

            except UnicodeError:
                # Some BOM handling might fail
                pass

    def test_encoding_detection_fallback(self, temp_dir: Path):
        """Test encoding detection and fallback mechanisms."""
        # Create file with ambiguous encoding
        ambiguous_file = temp_dir / "ambiguous_encoding.md"

        # Content that could be interpreted as different encodings
        # Using Latin-1 characters that might be misinterpreted
        latin1_content = """---
title: Encoding Test
author: José María
description: Café résumé naïve
---

Content with special characters: café résumé naïve
""".encode(
            "latin-1"
        )

        with open(ambiguous_file, "wb") as f:
            f.write(latin1_content)

        parser = FrontmatterParser()

        try:
            # Should handle encoding detection gracefully
            frontmatter, content, result = parser.parse_file(ambiguous_file)

            # May succeed or fail, but should not crash
            if result.valid:
                assert "title" in frontmatter

        except UnicodeDecodeError:
            # Expected for encoding mismatches
            pass

    def test_invalid_utf8_sequences(self, temp_dir: Path):
        """Test handling of invalid UTF-8 byte sequences."""
        invalid_file = temp_dir / "invalid_utf8.md"

        # Create file with invalid UTF-8 sequences
        valid_start = b"---\ntitle: Invalid UTF-8 Test\n---\n\n"
        invalid_bytes = b"\xff\xfe\xfd\xfc\xfb"  # Invalid UTF-8
        valid_end = b"\nEnd of content."

        with open(invalid_file, "wb") as f:
            f.write(valid_start + invalid_bytes + valid_end)

        parser = FrontmatterParser()

        try:
            frontmatter, content, result = parser.parse_file(invalid_file)
            # May succeed with replacement characters or fail gracefully

        except UnicodeDecodeError:
            # Expected for invalid UTF-8
            pass

    def test_encoding_consistency_across_platforms(self, temp_dir: Path):
        """Test encoding consistency across different platforms."""
        test_content = """---
title: Encoding Consistency Test
special_chars: "café résumé naïve piñata"
unicode_chars: "αβγδε ñoël 测试 🚀"
---

Multi-language content:
- French: café, résumé, naïve
- Spanish: piñata, niño
- Greek: αβγδε
- Chinese: 测试
- Emoji: 🚀🌟💫
"""

        consistency_file = temp_dir / "consistency_test.md"

        # Write with explicit UTF-8 encoding
        with open(consistency_file, "w", encoding="utf-8") as f:
            f.write(test_content)

        # Read back and verify
        parser = FrontmatterParser()
        frontmatter, content, result = parser.parse_file(consistency_file)

        assert result.valid
        assert "café résumé naïve piñata" in frontmatter["special_chars"]
        assert "🚀" in frontmatter["unicode_chars"]
        assert "café" in content
        assert "测试" in content


# Platform detection utilities
def is_windows():
    """Check if running on Windows."""
    return platform.system() == "Windows"


def is_macos():
    """Check if running on macOS."""
    return platform.system() == "Darwin"


def is_linux():
    """Check if running on Linux."""
    return platform.system() == "Linux"


def get_file_system_type(path: Path):
    """Get file system type for a path."""
    try:
        import psutil

        mount_points = psutil.disk_partitions()

        for mount in mount_points:
            if str(path).startswith(mount.mountpoint):
                return mount.fstype
    except ImportError:
        pass

    return "unknown"


# Test markers for platform-specific tests
pytest.mark.windows = pytest.mark.skipif(
    not is_windows(), reason="Windows-specific test"
)

pytest.mark.macos = pytest.mark.skipif(not is_macos(), reason="macOS-specific test")

pytest.mark.linux = pytest.mark.skipif(not is_linux(), reason="Linux-specific test")

pytest.mark.unicode = pytest.mark.skipif(
    os.environ.get("SKIP_UNICODE_TESTS") == "1", reason="Unicode tests skipped"
)
