# nosetests --nocapture  tests/test_field.py
import os
import unittest

from fit_file_faker.vendor.fit_tool.fit_file import FitFile


class TestActivityFiles(unittest.TestCase):

    def setUp(self):
        super().setUp()
        # stream_handler = logging.StreamHandler(sys.stdout)
        # stream_handler.setFormatter(formatter)
        # logger.addHandler(stream_handler)

    def shortDescription(self):
        return None

    def test_decode_deprecated_activity(self):
        """Test decoding and activity with deprecated messages and fields.
        """
        path = os.path.join(os.path.dirname(__file__), 'data/activity_deprecated_profile.fit')

        with open(path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            print(f'Profile version: {fit_file.header.profile_version}')
            fit_file.to_rows()

    def test_decode_multiple_developer_index(self):
        """Test decoding activity with multiple developer indexes
        """
        path = os.path.join(os.path.dirname(__file__), 'data/activity_multiple_developer_index.fit')

        with open(path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            print(f'Profile version: {fit_file.header.profile_version}')
            fit_file.to_rows()
