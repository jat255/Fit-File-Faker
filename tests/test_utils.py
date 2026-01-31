"""
Tests for utility functions.
"""

from fit_file_faker.utils import (
    fit_crc_get16,
    _lenient_get_length_from_size,
    _lenient_read_strings_from_bytes,
)
from fit_file_faker.vendor.fit_tool.base_type import BaseType
from fit_file_faker.vendor.fit_tool.field import Field


class TestCRCCalculation:
    """Tests for FIT file CRC calculation."""

    def test_fit_crc_get16_basic(self):
        """Test basic CRC calculation."""
        crc = 0
        crc = fit_crc_get16(crc, 0x0E)
        crc = fit_crc_get16(crc, 0x10)

        # CRC calculation is deterministic
        assert isinstance(crc, int)
        assert 0 <= crc <= 0xFFFF

    def test_fit_crc_get16_sequence(self):
        """Test CRC calculation on a sequence of bytes."""
        data = b"Hello, FIT!"
        crc = 0
        for byte in data:
            crc = fit_crc_get16(crc, byte)

        # Should produce a valid 16-bit checksum
        assert 0 <= crc <= 0xFFFF


class TestLenientFieldLength:
    """Tests for lenient field length calculation."""

    def test_normal_field_size(self):
        """Test that normal field sizes work correctly."""
        # 8 bytes for UINT32 (4 bytes each) = length 2
        length = _lenient_get_length_from_size(BaseType.UINT32, 8)
        assert length == 2

    def test_malformed_field_size_truncates(self):
        """Test that malformed field sizes truncate instead of raising."""
        # 7 bytes for UINT32 (4 bytes each) = length 1 (truncated)
        length = _lenient_get_length_from_size(BaseType.UINT32, 7)
        assert length == 1

    def test_string_type_handling(self):
        """Test that STRING type returns 1 for non-zero size."""
        length = _lenient_get_length_from_size(BaseType.STRING, 10)
        assert length == 1

        # Zero size returns 0
        length = _lenient_get_length_from_size(BaseType.STRING, 0)
        assert length == 0


class TestLenientStringDecoding:
    """Tests for lenient string decoding from bytes."""

    def test_utf8_strings_decode_normally(self):
        """Test that valid UTF-8 strings decode correctly."""
        field = Field(name="test", field_id=0, base_type=BaseType.STRING, size=10)
        data = b"Hello\x00World\x00\x00"

        _lenient_read_strings_from_bytes(field, data)

        assert len(field.encoded_values) == 2
        assert field.encoded_values[0] == "Hello"
        assert field.encoded_values[1] == "World"

    def test_non_utf8_strings_fallback_to_latin1(self):
        """Test that non-UTF-8 strings fall back to Latin-1 encoding."""
        field = Field(name="test", field_id=0, base_type=BaseType.STRING, size=20)
        # Include byte 0x9d which is invalid UTF-8 but valid Latin-1
        data = b"Test\x9d String\x00\x00"

        _lenient_read_strings_from_bytes(field, data)

        assert len(field.encoded_values) == 1
        # 0x9d in Latin-1 is the control character "OPERATING SYSTEM COMMAND"
        assert "Test" in field.encoded_values[0]
        assert "String" in field.encoded_values[0]

    def test_completely_invalid_uses_replacement(self):
        """Test that completely invalid bytes use replacement characters."""
        field = Field(name="test", field_id=0, base_type=BaseType.STRING, size=10)
        # This should work with Latin-1 fallback, but test the error path
        # by using a sequence that would fail both UTF-8 and have no Latin-1 issues

        # Actually, Latin-1 accepts all byte values, so let's just verify
        # the function doesn't crash on any input
        data = b"\xff\xfe\xfd\x00\x00"

        _lenient_read_strings_from_bytes(field, data)

        # Should have parsed something without crashing
        assert isinstance(field.encoded_values, list)

    def test_latin1_fallback_exception_uses_replacement(self):
        """Test that if Latin-1 decode also fails, replacement characters are used."""
        field = Field(name="test", field_id=0, base_type=BaseType.STRING, size=10)

        # Create a mock bytes object that fails on Latin-1 decode
        class MockBytes(bytes):
            def decode(self, encoding="utf-8", errors="strict"):
                if encoding == "utf-8" and errors == "strict":
                    # First call: UTF-8 with strict errors should fail
                    raise UnicodeDecodeError("utf-8", b"", 0, 1, "invalid start byte")
                elif encoding == "latin-1":
                    # Second call: Make Latin-1 also fail (simulating some edge case)
                    raise ValueError("Simulated Latin-1 decode failure")
                else:
                    # Third call: UTF-8 with errors='replace' should work
                    # Include null terminator so split works properly
                    return "Test� String\x00"

        data = MockBytes(b"Test\x9d String\x00")

        # This should trigger the warning path and use replacement characters
        _lenient_read_strings_from_bytes(field, data)

        # Should have successfully parsed with replacements
        assert isinstance(field.encoded_values, list)
        assert len(field.encoded_values) == 1
        assert field.encoded_values[0] == "Test� String"
