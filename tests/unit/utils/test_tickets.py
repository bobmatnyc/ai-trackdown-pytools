"""Unit tests for ticket utility functions."""

import pytest

from ai_trackdown_pytools.utils.tickets import (
    PREFIX_TO_TYPE,
    TYPE_TO_PREFIX,
    get_ticket_prefix,
    infer_ticket_type,
    is_valid_ticket_id,
    normalize_ticket_id,
)


class TestInferTicketType:
    """Test cases for infer_ticket_type function."""

    def test_valid_ticket_ids(self):
        """Test inference with valid ticket IDs."""
        assert infer_ticket_type("EP-001") == "epic"
        assert infer_ticket_type("ISS-002") == "issue"
        assert infer_ticket_type("TSK-003") == "task"
        assert infer_ticket_type("PR-004") == "pr"

    def test_case_insensitive(self):
        """Test that inference is case insensitive."""
        assert infer_ticket_type("ep-001") == "epic"
        assert infer_ticket_type("Iss-002") == "issue"
        assert infer_ticket_type("tsk-003") == "task"
        assert infer_ticket_type("pR-004") == "pr"

    def test_invalid_formats(self):
        """Test with invalid ticket ID formats."""
        assert infer_ticket_type("INVALID-005") is None
        assert infer_ticket_type("EP001") is None  # Missing hyphen
        assert infer_ticket_type("EP-") is None  # Missing number
        assert infer_ticket_type("-001") is None  # Missing prefix
        assert infer_ticket_type("EP-ABC") is None  # No digits

    def test_edge_cases(self):
        """Test edge cases."""
        assert infer_ticket_type("") is None
        assert infer_ticket_type(None) is None
        assert infer_ticket_type(123) is None  # Non-string

    def test_complex_numbers(self):
        """Test with various number formats."""
        assert infer_ticket_type("EP-1") == "epic"
        assert infer_ticket_type("ISS-999") == "issue"
        assert infer_ticket_type("TSK-001a") == "task"  # Has digits
        assert infer_ticket_type("PR-123-456") == "pr"  # Extra hyphens in number part


class TestGetTicketPrefix:
    """Test cases for get_ticket_prefix function."""

    def test_valid_types(self):
        """Test with valid ticket types."""
        assert get_ticket_prefix("epic") == "EP"
        assert get_ticket_prefix("issue") == "ISS"
        assert get_ticket_prefix("task") == "TSK"
        assert get_ticket_prefix("pr") == "PR"

    def test_case_insensitive(self):
        """Test that type lookup is case insensitive."""
        assert get_ticket_prefix("EPIC") == "EP"
        assert get_ticket_prefix("Issue") == "ISS"
        assert get_ticket_prefix("TASK") == "TSK"
        assert get_ticket_prefix("Pr") == "PR"

    def test_invalid_types(self):
        """Test with invalid ticket types."""
        with pytest.raises(ValueError, match="Unknown ticket type: invalid"):
            get_ticket_prefix("invalid")

        with pytest.raises(ValueError, match="Unknown ticket type: bug"):
            get_ticket_prefix("bug")

    def test_edge_cases(self):
        """Test edge cases."""
        with pytest.raises(ValueError, match="Invalid ticket type"):
            get_ticket_prefix("")

        with pytest.raises(ValueError, match="Invalid ticket type"):
            get_ticket_prefix(None)

        with pytest.raises(ValueError, match="Invalid ticket type"):
            get_ticket_prefix(123)


class TestIsValidTicketId:
    """Test cases for is_valid_ticket_id function."""

    def test_valid_ids(self):
        """Test with valid ticket IDs."""
        assert is_valid_ticket_id("EP-001") is True
        assert is_valid_ticket_id("ISS-002") is True
        assert is_valid_ticket_id("TSK-003") is True
        assert is_valid_ticket_id("PR-004") is True

    def test_invalid_ids(self):
        """Test with invalid ticket IDs."""
        assert is_valid_ticket_id("INVALID-001") is False
        assert is_valid_ticket_id("EP001") is False
        assert is_valid_ticket_id("") is False
        assert is_valid_ticket_id(None) is False


class TestNormalizeTicketId:
    """Test cases for normalize_ticket_id function."""

    def test_normalization(self):
        """Test ticket ID normalization."""
        assert normalize_ticket_id("ep-001") == "EP-001"
        assert normalize_ticket_id("ISS-002") == "ISS-002"
        assert normalize_ticket_id("tsk-003") == "TSK-003"
        assert normalize_ticket_id("PR-004") == "PR-004"

    def test_invalid_normalization(self):
        """Test normalization with invalid IDs."""
        assert normalize_ticket_id("invalid-001") is None
        assert normalize_ticket_id("EP001") is None
        assert normalize_ticket_id("") is None
        assert normalize_ticket_id(None) is None

    def test_mixed_case(self):
        """Test normalization with mixed case."""
        assert normalize_ticket_id("Ep-001") == "EP-001"
        assert normalize_ticket_id("iSs-002") == "ISS-002"
        assert normalize_ticket_id("TsK-003") == "TSK-003"
        assert normalize_ticket_id("pR-004") == "PR-004"


class TestConstants:
    """Test the constant mappings."""

    def test_prefix_to_type_mapping(self):
        """Test PREFIX_TO_TYPE mapping."""
        assert PREFIX_TO_TYPE["EP"] == "epic"
        assert PREFIX_TO_TYPE["ISS"] == "issue"
        assert PREFIX_TO_TYPE["TSK"] == "task"
        assert PREFIX_TO_TYPE["PR"] == "pr"
        assert len(PREFIX_TO_TYPE) == 4

    def test_type_to_prefix_mapping(self):
        """Test TYPE_TO_PREFIX mapping."""
        assert TYPE_TO_PREFIX["epic"] == "EP"
        assert TYPE_TO_PREFIX["issue"] == "ISS"
        assert TYPE_TO_PREFIX["task"] == "TSK"
        assert TYPE_TO_PREFIX["pr"] == "PR"
        assert len(TYPE_TO_PREFIX) == 4

    def test_mappings_consistency(self):
        """Test that mappings are consistent with each other."""
        # Check that all prefixes map back correctly
        for prefix, ticket_type in PREFIX_TO_TYPE.items():
            assert TYPE_TO_PREFIX[ticket_type] == prefix

        # Check that all types map back correctly
        for ticket_type, prefix in TYPE_TO_PREFIX.items():
            assert PREFIX_TO_TYPE[prefix] == ticket_type
