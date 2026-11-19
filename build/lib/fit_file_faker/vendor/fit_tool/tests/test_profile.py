# nosetests --nocapture  tests/test_demo.py


import unittest

from fit_file_faker.vendor.fit_tool.fit import Profile


class TestFitFile(unittest.TestCase):

    def test_profile(self):
        profile = Profile.get_default_profile();

        for type_name in profile.types_by_name:
            profile_type = profile.types_by_name[type_name]
            print(f'{type_name}', profile_type)
