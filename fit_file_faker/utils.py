"""Utility functions for Fit File Faker.

This module provides utility functions including a monkey patch for fit_tool
to handle malformed FIT files from certain manufacturers (e.g., COROS) and
a CRC-16 checksum calculation function.

The fit_tool patch is automatically applied when the fit_editor module is
imported, making it transparent to users of the library.
"""

import logging

from fit_file_faker.vendor.fit_tool.base_type import BaseType
from fit_file_faker.vendor.fit_tool.field import Field

_logger = logging.getLogger("garmin")
_original_get_length_from_size = Field.get_length_from_size
_original_read_strings_from_bytes = Field.read_strings_from_bytes


def _lenient_read_strings_from_bytes(self, bytes_buffer: bytes):
    """Lenient string decoder that handles non-UTF-8 encoded strings.

    This is a replacement for `fit_tool`'s `Field.read_strings_from_bytes` that
    handles FIT files with non-UTF-8 encoded strings more gracefully. Some devices
    use Windows-1252, Latin-1, or other encodings instead of UTF-8.

    The function tries multiple decoding strategies:
    1. UTF-8 (standard)
    2. Latin-1 / ISO-8859-1 (fallback)
    3. Replace invalid bytes with � (last resort)

    Args:
        bytes_buffer: Raw bytes containing null-terminated strings.

    Note:
        When non-UTF-8 encoding is detected, a debug message is logged.
        This allows processing to continue even with malformed string data.
    """
    # Try UTF-8 first (standard FIT specification)
    try:
        string_container = bytes_buffer.decode("utf-8")
    except UnicodeDecodeError:
        # Try Latin-1 (ISO-8859-1) which accepts all byte values
        # This is common for devices that don't properly encode UTF-8
        try:
            _logger.debug("Failed to decode string as UTF-8, trying Latin-1 encoding")
            string_container = bytes_buffer.decode("latin-1")
        except Exception:
            # Last resort: replace invalid bytes
            _logger.warning(
                "Failed to decode string with UTF-8 and Latin-1, using replacement characters"
            )
            string_container = bytes_buffer.decode("utf-8", errors="replace")

    strings = string_container.split("\u0000")
    strings = strings[:-1]
    strings = [x for x in strings if x]
    self.encoded_values = []
    self.encoded_values.extend(strings)


def _lenient_get_length_from_size(base_type: "BaseType", size: int) -> int:
    """Lenient field length calculator that truncates instead of raising exceptions.

    This is a replacement for `fit_tool`'s `Field.get_length_from_size` that handles
    malformed FIT files more gracefully. Some manufacturers (e.g., COROS) create
    FIT files where field sizes are not exact multiples of their base type size.
    Instead of failing with an exception, this function truncates to the nearest
    valid length.

    Args:
        base_type: The `BaseType` of the field (`STRING`, `BYTE`, `UINT8`, etc.).
        size: The declared size of the field in bytes.

    Returns:
        length: The field length (number of values, not bytes). For `STRING` and `BYTE`
            types, returns 0 for size 0 and 1 otherwise. For other types, returns
            `size // base_type.size` (truncated integer division).

    Note:
        When truncation occurs (size not a multiple of `base_type.size`), a debug
        message is logged. This typically indicates a malformed FIT file but
        allows processing to continue.

    Examples:
        >>> # Normal case: 8 bytes for UINT32 (4 bytes each) = length 2
        >>> _lenient_get_length_from_size(BaseType.UINT32, 8)
        2

        >>> # Malformed case: 7 bytes for UINT32 = length 1 (truncated)
        >>> _lenient_get_length_from_size(BaseType.UINT32, 7)
        1
    """
    if base_type == BaseType.STRING or base_type == BaseType.BYTE:
        return 0 if size == 0 else 1
    else:
        length = size // base_type.size

        if length * base_type.size != size:
            _logger.debug(
                f"Field size ({size}) not multiple of type size ({base_type.size}), "
                f"truncating to length {length}"
            )
            return length

        return length


def apply_fit_tool_patch():
    """Apply monkey patch to `fit_tool` to handle malformed FIT files.

    Replaces `fit_tool`'s `Field.get_length_from_size` method with a more lenient
    version that truncates field lengths instead of raising exceptions when
    field sizes aren't exact multiples of their base type size.

    Also replaces `Field.read_strings_from_bytes` to handle non-UTF-8 encoded
    strings gracefully by falling back to Latin-1 or replacement characters.

    This patch is essential for processing FIT files from manufacturers like
    COROS that don't strictly follow the FIT specification. Without it,
    fit_tool would raise exceptions and refuse to process these files.

    The patch is automatically applied when the fit_editor module is imported,
    so users don't need to call this function manually.

    Note:
        This is a global monkey patch that affects all subsequent `fit_tool`
        operations in the same Python process. It's applied once at module
        import time.

    Examples:
        >>> # Typically called automatically, but can be invoked manually:
        >>> from fit_file_faker.utils import apply_fit_tool_patch
        >>> apply_fit_tool_patch()
        >>> # Now fit_tool can handle COROS files without errors
    """
    Field.get_length_from_size = staticmethod(_lenient_get_length_from_size)
    Field.read_strings_from_bytes = _lenient_read_strings_from_bytes


def fit_crc_get16(crc: int, byte: int) -> int:
    """Calculate FIT file CRC-16 checksum for a single byte.

    Implements the CRC-16 algorithm used by FIT files. This function processes
    one byte at a time and should be called repeatedly for each byte in the
    data to calculate a complete checksum.

    The algorithm uses a lookup table and processes the byte in two 4-bit
    nibbles (lower 4 bits first, then upper 4 bits) to compute the CRC.

    Args:
        crc: Current CRC value (16-bit unsigned integer). Use 0 for the
            first byte in the sequence.
        byte: Byte value to add to the checksum (8-bit unsigned integer,
            0-255).

    Returns:
        Updated CRC value (16-bit unsigned integer) after processing this byte.

    Examples:
        >>> # Calculate CRC for a single byte
        >>> crc = fit_crc_get16(0, 0x42)
        >>> print(f"CRC: {crc:#06x}")
        CRC: 0x...
        >>>
        >>> # Calculate CRC for a byte array
        >>> def calculate_fit_crc(data: bytes) -> int:
        ...     '''Calculate CRC-16 for FIT file data.'''
        ...     crc = 0
        ...     for byte in data:
        ...         crc = fit_crc_get16(crc, byte)
        ...     return crc
        >>>
        >>> data = b"\\x0e\\x10\\x43\\x08\\x28\\x06\\x00\\x00"
        >>> checksum = calculate_fit_crc(data)

    Note:
        This is the standard CRC-16 algorithm used in FIT file headers
        and data records. It's primarily used for validation but is not
        currently required by `fit_file_faker` since `fit_tool` handles CRC
        calculation automatically.
    """
    crc_table = [
        0x0000,
        0xCC01,
        0xD801,
        0x1400,
        0xF001,
        0x3C00,
        0x2800,
        0xE401,
        0xA001,
        0x6C00,
        0x7800,
        0xB401,
        0x5000,
        0x9C01,
        0x8801,
        0x4400,
    ]

    # Compute checksum of lower four bits of byte
    tmp = crc_table[crc & 0xF]
    crc = (crc >> 4) & 0x0FFF
    crc = crc ^ tmp ^ crc_table[byte & 0xF]

    # Now compute checksum of upper four bits of byte
    tmp = crc_table[crc & 0xF]
    crc = (crc >> 4) & 0x0FFF
    crc = crc ^ tmp ^ crc_table[(byte >> 4) & 0xF]

    return crc
