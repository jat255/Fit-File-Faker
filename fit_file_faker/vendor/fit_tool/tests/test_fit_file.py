# nosetests --nocapture  tests/test_fit_file.py


import unittest

from fit_file_faker.vendor.fit_tool.definition_message import DefinitionMessage
from fit_file_faker.vendor.fit_tool.fit_file import FitFile
from fit_file_faker.vendor.fit_tool.fit_file_builder import FitFileBuilder
from fit_file_faker.vendor.fit_tool.profile.messages.workout_step_message import WorkoutStepMessage
from fit_file_faker.vendor.fit_tool.profile.profile_type import WorkoutStepDuration


class TestFitFile(unittest.TestCase):

    def test_conversion_simple(self):
        mesg = WorkoutStepMessage(local_id=0)
        mesg.workout_step_name = '1st step'
        mesg.duration_type = WorkoutStepDuration.DISTANCE

        def_mesg = DefinitionMessage.from_data_message(mesg)

        builder = FitFileBuilder(auto_define=False)
        builder.add(def_mesg)
        builder.add(mesg)

        fit_file = builder.build()

        bytes1 = fit_file.to_bytes()

        fite_file2 = FitFile.from_bytes(bytes1)
        bytes2 = fite_file2.to_bytes()

        print(f'{bytes1}')
        print(f'{bytes2}')
        self.assertEquals(bytes2, bytes1)

    def test_builder_with_auto_define(self):
        mesg1 = WorkoutStepMessage(local_id=0)
        mesg1.workout_step_name = '1st step'
        mesg1.duration_type = WorkoutStepDuration.DISTANCE

        mesg2 = WorkoutStepMessage(local_id=0)
        mesg2.workout_step_name = '2nd step'
        mesg2.duration_type = WorkoutStepDuration.DISTANCE

        builder = FitFileBuilder(auto_define=True, min_string_size=50)
        builder.add(mesg1)
        builder.add(mesg2)

        fit_file = builder.build()

        self.assertEquals(len(fit_file.records), 3)
