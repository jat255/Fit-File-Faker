# nosetests --nocapture  tests/test_field.py
import csv
import os
import unittest

from fit_file_faker.vendor.fit_tool.fit_file import FitFile


class TestSdkFiles(unittest.TestCase):

    def setUp(self):
        super().setUp()
        # stream_handler = logging.StreamHandler(sys.stdout)
        # stream_handler.setFormatter(formatter)
        # logger.addHandler(stream_handler)

    def shortDescription(self):
        return None

    def test_developer_data(self):
        """Test decoding activity file with developer fields.
        """
        path = os.path.join(os.path.dirname(__file__), 'data/sdk/DeveloperData.fit')

        with open(path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            # print(f'Profile version: {fit_file.header.profile_version}')
            fit_file.to_rows()

    def test_activity(self):
        """Test decoding activity file.
        """
        path = os.path.join(os.path.dirname(__file__), 'data/sdk/Activity.fit')

        with open(path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            # print(f'Profile version: {fit_file.header.profile_version}')
            rows = fit_file.to_rows()

        out_path = os.path.join(os.path.dirname(__file__), 'out/Activity.csv')
        with open(out_path, 'w', newline='') as csv_file:
            csv_writer = csv.writer(csv_file, delimiter=',',
                                    quotechar='|', quoting=csv.QUOTE_MINIMAL)
            for row in rows:
                csv_writer.writerow(row)

    def test_activity_developer_data(self):
        """Test decoding activity file.
        """
        path = os.path.join(os.path.dirname(__file__), 'data/sdk/activity_developerdata.fit')

        with open(path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            # print(f'Profile version: {fit_file.header.profile_version}')
            rows = fit_file.to_rows()

        out_path = os.path.join(os.path.dirname(__file__), 'out/activity_developerdata.csv')
        with open(out_path, 'w', newline='') as csv_file:
            csv_writer = csv.writer(csv_file, delimiter=',',
                                    quotechar='|', quoting=csv.QUOTE_MINIMAL)
            for row in rows:
                csv_writer.writerow(row)

    def test_activity_low_battery(self):
        """Test decoding activity low battery file.
        """
        path = os.path.join(os.path.dirname(__file__), 'data/sdk/activity_lowbattery.fit')

        with open(path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            # print(f'Profile version: {fit_file.header.profile_version}')
            fit_file.to_rows()

    def test_activity_multi_sport(self):
        """Test decoding activity multisport file.
        """
        path = os.path.join(os.path.dirname(__file__), 'data/sdk/activity_multisport.fit')

        with open(path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            # print(f'Profile version: {fit_file.header.profile_version}')
            fit_file.to_rows()

    def test_activity_poolswim_with_hr(self):
        """Test decoding
        """
        path = os.path.join(os.path.dirname(__file__), 'data/sdk/activity_poolswim_with_hr.fit')

        with open(path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            # print(f'Profile version: {fit_file.header.profile_version}')
            fit_file.to_rows()

    def test_activity_poolswim(self):
        """Test decoding
        """
        path = os.path.join(os.path.dirname(__file__), 'data/sdk/activity_poolswim.fit')

        with open(path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            # print(f'Profile version: {fit_file.header.profile_version}')
            fit_file.to_rows()

    def test_activity_truncated(self):
        """Test decoding
        """
        path = os.path.join(os.path.dirname(__file__), 'data/sdk/activity_truncated.fit')

        with open(path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            # print(f'Profile version: {fit_file.header.profile_version}')
            fit_file.to_rows()

    def test_monitoring_file(self):
        """Test decoding
        """
        path = os.path.join(os.path.dirname(__file__), 'data/sdk/MonitoringFile.fit')

        with open(path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            # print(f'Profile version: {fit_file.header.profile_version}')
            fit_file.to_rows()

    def test_weight_scale_multi_user(self):
        """Test decoding
        """
        path = os.path.join(os.path.dirname(__file__), 'data/sdk/WeightScaleMultiUser.fit')

        with open(path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            # print(f'Profile version: {fit_file.header.profile_version}')
            fit_file.to_rows()

    def test_weight_scale_single_user(self):
        """Test decoding
        """
        path = os.path.join(os.path.dirname(__file__), 'data/sdk/WeightScaleSingleUser.fit')

        with open(path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            # print(f'Profile version: {fit_file.header.profile_version}')
            fit_file.to_rows()

    def test_workout_individual_steps(self):
        """Test decoding
        """
        path = os.path.join(os.path.dirname(__file__), 'data/sdk/WorkoutIndividualSteps.fit')

        with open(path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            # print(f'Profile version: {fit_file.header.profile_version}')
            fit_file.to_rows()

    def test_workout_custom_target_values(self):
        """Test decoding
        """
        path = os.path.join(os.path.dirname(__file__), 'data/sdk/WorkoutCustomTargetValues.fit')

        with open(path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            # print(f'Profile version: {fit_file.header.profile_version}')
            fit_file.to_rows()

    def test_workout_repeat_greater_than_step(self):
        """Test decoding
        """
        path = os.path.join(os.path.dirname(__file__), 'data/sdk/WorkoutRepeatGreaterThanStep.fit')

        with open(path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            # print(f'Profile version: {fit_file.header.profile_version}')
            fit_file.to_rows()

    def test_workout_repeat_steps(self):
        """Test decoding workout repeat steps file.
        """
        path = os.path.join(os.path.dirname(__file__), 'data/sdk/WorkoutRepeatSteps.fit')

        with open(path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            # print(f'Profile version: {fit_file.header.profile_version}')
            fit_file.to_rows()
