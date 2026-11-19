# nosetests --nocapture  tests/test_fit_file_header.py

import unittest

from fit_file_faker.vendor.fit_tool.fit_file_header import ProtocolVersion, ProfileVersion, FitFileHeader


class TestFitFileHeader(unittest.TestCase):

    def shortDescription(self):
        return None

    def test_protocol_version(self):
        protocol_version = ProtocolVersion(2, 3)
        self.assertEqual('2.3', str(protocol_version))

        bytes1 = protocol_version.to_bytes()

        pv2 = ProtocolVersion.from_bytes(bytes1)
        bytes2 = pv2.to_bytes()

        self.assertEqual(bytes1, bytes2)

    def test_profile_version(self):
        profile_version = ProfileVersion(21, 60)
        self.assertEqual('21.60', str(profile_version))

        bytes1 = profile_version.to_bytes()

        pv2 = ProfileVersion.from_bytes(bytes1)
        bytes2 = pv2.to_bytes()

        self.assertEqual(bytes1, bytes2)

    def test_generate_crc(self):
        protocol_version = ProtocolVersion(2, 3)
        profile_version = ProfileVersion(21, 60)

        FitFileHeader.generate_crc(protocol_version, profile_version, 6552343)

    def test_conversion_without_crc(self):
        header1 = FitFileHeader(protocol_version=ProtocolVersion(2, 3), profile_version=ProfileVersion(21, 60),
                                records_size=4294967295)
        bytes1 = header1.to_bytes()
        self.assertEqual(12, len(bytes1))

        header2 = FitFileHeader.from_bytes(bytes1)
        bytes2 = header2.to_bytes()

        self.assertEqual(bytes1, bytes2)

    def test_conversion_with_crc(self):
        header1 = FitFileHeader(protocol_version=ProtocolVersion(2, 3), profile_version=ProfileVersion(21, 60),
                                records_size=4294967295, crc=500)
        bytes1 = header1.to_bytes()
        self.assertEqual(14, len(bytes1))

        header2 = FitFileHeader.from_bytes(bytes1)
        bytes2 = header2.to_bytes()

        self.assertEqual(bytes1, bytes2)
