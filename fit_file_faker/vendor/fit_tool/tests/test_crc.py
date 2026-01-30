import unittest

from fit_file_faker.vendor.fit_tool.utils.crc import crc16


class TestCRC(unittest.TestCase):
    def test_crc16(self):
        data = '123456789'.encode('utf-8')
        result = crc16(data)
        self.assertEqual(result, 0xBB3D)
