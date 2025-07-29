"""Unit tests for version management module."""

import pytest

from ai_trackdown_pytools.version import (
    CURRENT_VERSION,
    FEATURES,
    Version,
    check_version_compatibility,
    format_version_info,
    get_feature_version,
    get_latest_version,
    get_version,
    get_version_history,
    get_version_info,
    has_feature,
    is_development_version,
    is_stable_version,
    list_available_features,
    validate_version_string,
)


class TestVersion:
    """Test the Version class."""

    def test_parse_valid_versions(self):
        """Test parsing valid semantic versions."""
        # Basic versions
        v1 = Version.parse("1.0.0")
        assert v1.major == 1
        assert v1.minor == 0
        assert v1.patch == 0
        assert v1.pre_release is None
        assert v1.build_metadata is None

        # Pre-release versions
        v2 = Version.parse("1.0.0-alpha")
        assert v2.major == 1
        assert v2.pre_release == "alpha"

        v3 = Version.parse("1.0.0-alpha.1")
        assert v3.pre_release == "alpha.1"

        v4 = Version.parse("1.0.0-0.3.7")
        assert v4.pre_release == "0.3.7"

        # Build metadata
        v5 = Version.parse("1.0.0+20130313144700")
        assert v5.build_metadata == "20130313144700"

        # Combined
        v6 = Version.parse("1.0.0-beta+exp.sha.5114f85")
        assert v6.pre_release == "beta"
        assert v6.build_metadata == "exp.sha.5114f85"

    def test_parse_invalid_versions(self):
        """Test parsing invalid versions raises ValueError."""
        invalid_versions = [
            "1",
            "1.0",
            "1.0.0.0",
            "1.0.0-",
            "1.0.0+",
            "01.0.0",  # Leading zeros
            "1.01.0",
            "1.0.01",
            "",
            "invalid",
            "1.0.0-",
            "1.0.0+",
        ]

        for invalid_version in invalid_versions:
            with pytest.raises(ValueError, match="Invalid semantic version"):
                Version.parse(invalid_version)

    def test_version_string_conversion(self):
        """Test converting version back to string."""
        test_cases = [
            "1.0.0",
            "0.1.0",
            "1.0.0-alpha",
            "1.0.0-alpha.1",
            "1.0.0+build.1",
            "1.0.0-beta+exp.sha.5114f85",
        ]

        for version_str in test_cases:
            version = Version.parse(version_str)
            assert str(version) == version_str

    def test_version_comparison(self):
        """Test version comparison operations."""
        v1 = Version(1, 0, 0)
        v2 = Version(1, 1, 0)
        v3 = Version(2, 0, 0)

        assert v1 < v2
        assert v2 < v3
        assert v1 < v3

        assert v2 > v1
        assert v3 > v2
        assert v3 > v1

        assert v1 == Version(1, 0, 0)
        assert v1 != v2

    def test_is_pre_release(self):
        """Test pre-release detection."""
        stable = Version(1, 0, 0)
        pre_release = Version(1, 0, 0, pre_release="alpha")

        assert not stable.is_pre_release()
        assert pre_release.is_pre_release()

    def test_is_stable(self):
        """Test stable version detection."""
        stable = Version(1, 0, 0)
        pre_release = Version(1, 0, 0, pre_release="alpha")
        dev_version = Version(0, 9, 0)

        assert stable.is_stable()
        assert not pre_release.is_stable()
        assert not dev_version.is_stable()  # 0.x is not stable

    def test_version_bumping(self):
        """Test version bumping methods."""
        v = Version(1, 2, 3)

        major_bump = v.bump_major()
        assert major_bump == Version(2, 0, 0)

        minor_bump = v.bump_minor()
        assert minor_bump == Version(1, 3, 0)

        patch_bump = v.bump_patch()
        assert patch_bump == Version(1, 2, 4)

    def test_to_release(self):
        """Test converting pre-release to release version."""
        pre_release = Version(1, 0, 0, pre_release="alpha")
        release = pre_release.to_release()

        assert release == Version(1, 0, 0)
        assert not release.is_pre_release()


class TestVersionFunctions:
    """Test version utility functions."""

    def test_get_version(self):
        """Test getting version string."""
        version = get_version()
        assert isinstance(version, str)
        assert version == "1.0.0"  # Current version

    def test_get_version_info(self):
        """Test getting version info object."""
        version_info = get_version_info()
        assert isinstance(version_info, Version)
        assert version_info == CURRENT_VERSION

    def test_is_development_version(self):
        """Test development version detection."""
        # Current version is 1.0.0, which is not development
        assert not is_development_version()

    def test_is_stable_version(self):
        """Test stable version detection."""
        # Current version is 1.0.0, which is stable
        assert is_stable_version()

    def test_format_version_info(self):
        """Test version info formatting."""
        info = format_version_info()
        assert "AI Trackdown PyTools" in info
        assert "1.0.0" in info
        # Version 1.0.0 is stable, no beta tag

    @pytest.mark.parametrize(
        "required,expected",
        [
            ("1.0.0", True),  # Exact match
            ("1.0.1", False),  # Higher patch version
            ("0.9.0", False),  # Different major version
            ("2.0.0", False),  # Different major version
        ],
    )
    def test_check_version_compatibility(self, required, expected):
        """Test version compatibility checking."""
        assert check_version_compatibility(required) == expected

    def test_check_version_compatibility_invalid(self):
        """Test version compatibility with invalid version string."""
        assert not check_version_compatibility("invalid")

    @pytest.mark.parametrize(
        "version_string,expected",
        [
            ("1.0.0", True),
            ("0.9.0", True),
            ("1.0.0-alpha", True),
            ("1.0.0+build", True),
            ("invalid", False),
            ("1.0", False),
            ("", False),
        ],
    )
    def test_validate_version_string(self, version_string, expected):
        """Test version string validation."""
        assert validate_version_string(version_string) == expected

    def test_get_version_history(self):
        """Test getting version history."""
        history = get_version_history()
        assert isinstance(history, list)
        assert "1.0.0" in history

        # Ensure it returns a copy
        history.append("test")
        assert "test" not in get_version_history()

    def test_get_latest_version(self):
        """Test getting latest version."""
        latest = get_latest_version()
        assert latest == "1.0.0"


class TestFeatureFlags:
    """Test feature flag functionality."""

    def test_has_feature_existing(self):
        """Test checking for existing features."""
        assert has_feature("semantic_versioning")
        assert has_feature("comprehensive_testing")
        assert has_feature("template_system")

    def test_has_feature_nonexistent(self):
        """Test checking for non-existent features."""
        assert not has_feature("nonexistent_feature")

    def test_get_feature_version_existing(self):
        """Test getting version for existing features."""
        version = get_feature_version("semantic_versioning")
        assert version == "0.9.0"

    def test_get_feature_version_nonexistent(self):
        """Test getting version for non-existent features."""
        version = get_feature_version("nonexistent_feature")
        assert version is None

    def test_list_available_features(self):
        """Test listing available features."""
        features = list_available_features()

        assert isinstance(features, dict)
        assert "semantic_versioning" in features
        assert features["semantic_versioning"] == "0.9.0"

        # All current features should be available since we're at 0.9.0
        for feature_name in FEATURES:
            assert feature_name in features


class TestVersionConstants:
    """Test version constants and global variables."""

    def test_current_version(self):
        """Test CURRENT_VERSION constant."""
        assert isinstance(CURRENT_VERSION, Version)
        assert CURRENT_VERSION.major == 0
        assert CURRENT_VERSION.minor == 9
        assert CURRENT_VERSION.patch == 0

    def test_features_dict(self):
        """Test FEATURES dictionary."""
        assert isinstance(FEATURES, dict)

        # Check that all feature versions are valid
        for feature, version in FEATURES.items():
            assert validate_version_string(
                version
            ), f"Invalid version for {feature}: {version}"

        # Check expected features are present
        expected_features = [
            "semantic_versioning",
            "comprehensive_testing",
            "enhanced_cli",
            "template_system",
            "json_validation",
            "git_integration",
        ]

        for feature in expected_features:
            assert feature in FEATURES


class TestVersionIntegration:
    """Test version module integration with the rest of the package."""

    def test_version_consistency(self):
        """Test version consistency across files."""
        from ai_trackdown_pytools import __version__

        # Version should be consistent
        assert get_version() == __version__
        assert str(CURRENT_VERSION) == __version__

    def test_version_format(self):
        """Test that version follows semantic versioning format."""
        version = get_version()
        assert validate_version_string(version)

        # Parse and verify it's a valid semantic version
        parsed = Version.parse(version)
        assert isinstance(parsed, Version)


class TestVersionEdgeCases:
    """Test edge cases and error conditions."""

    def test_version_equality(self):
        """Test version equality with different objects."""
        v1 = Version(1, 0, 0)
        v2 = Version(1, 0, 0)
        v3 = Version(1, 0, 1)

        assert v1 == v2
        assert v1 != v3
        assert v1 != "1.0.0"  # Different type

    def test_version_with_all_components(self):
        """Test version with all components."""
        version_str = "1.0.0-alpha.1+build.123"
        version = Version.parse(version_str)

        assert version.major == 1
        assert version.minor == 0
        assert version.patch == 0
        assert version.pre_release == "alpha.1"
        assert version.build_metadata == "build.123"
        assert str(version) == version_str

    def test_empty_version_history(self):
        """Test behavior with empty version history."""
        # This tests the fallback behavior
        from ai_trackdown_pytools.version import VERSION_HISTORY

        # Temporarily empty the history
        original_history = VERSION_HISTORY.copy()
        VERSION_HISTORY.clear()

        try:
            latest = get_latest_version()
            assert latest == get_version()  # Should fallback to current version
        finally:
            # Restore original history
            VERSION_HISTORY.extend(original_history)


# Performance tests for version operations
class TestVersionPerformance:
    """Test performance of version operations."""

    def test_version_parsing_performance(self):
        """Test that version parsing is reasonably fast."""
        import time

        version_strings = [
            "1.0.0",
            "1.0.0-alpha",
            "1.0.0+build",
            "1.0.0-alpha.1+build.123",
        ] * 100  # 400 versions to parse

        start_time = time.time()
        for version_str in version_strings:
            Version.parse(version_str)
        end_time = time.time()

        # Should be able to parse 400 versions in less than 1 second
        assert end_time - start_time < 1.0

    def test_feature_checking_performance(self):
        """Test that feature checking is fast."""
        import time

        features = list(FEATURES.keys()) * 100  # Check each feature 100 times

        start_time = time.time()
        for feature in features:
            has_feature(feature)
        end_time = time.time()

        # Should be very fast
        assert end_time - start_time < 0.1


# Parametrized tests for comprehensive coverage
class TestVersionParametrized:
    """Parametrized tests for comprehensive version testing."""

    @pytest.mark.parametrize(
        "major,minor,patch",
        [
            (0, 0, 1),
            (0, 1, 0),
            (1, 0, 0),
            (10, 20, 30),
        ],
    )
    def test_version_creation(self, major, minor, patch):
        """Test creating versions with different numbers."""
        version = Version(major, minor, patch)
        assert version.major == major
        assert version.minor == minor
        assert version.patch == patch

    @pytest.mark.parametrize(
        "version_str,is_dev",
        [
            ("0.1.0", True),
            ("0.9.0", True),
            ("1.0.0", False),
            ("2.1.3", False),
        ],
    )
    def test_development_version_detection(self, version_str, is_dev):
        """Test development version detection for various versions."""
        version = Version.parse(version_str)
        assert (version.major == 0) == is_dev

    @pytest.mark.parametrize(
        "version_str,has_pre",
        [
            ("1.0.0", False),
            ("1.0.0-alpha", True),
            ("1.0.0-beta.1", True),
            ("1.0.0-rc.1", True),
        ],
    )
    def test_pre_release_detection(self, version_str, has_pre):
        """Test pre-release detection for various versions."""
        version = Version.parse(version_str)
        assert version.is_pre_release() == has_pre
