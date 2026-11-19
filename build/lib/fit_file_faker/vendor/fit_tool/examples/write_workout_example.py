import datetime

from fit_file_faker.vendor.fit_tool.fit_file import FitFile
from fit_file_faker.vendor.fit_tool.fit_file_builder import FitFileBuilder
from fit_file_faker.vendor.fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_file_faker.vendor.fit_tool.profile.messages.workout_message import WorkoutMessage
from fit_file_faker.vendor.fit_tool.profile.messages.workout_step_message import WorkoutStepMessage
from fit_file_faker.vendor.fit_tool.profile.profile_type import Sport, Intensity, WorkoutStepDuration, WorkoutStepTarget, Manufacturer, \
    FileType


def main():
    file_id_message = FileIdMessage()
    file_id_message.type = FileType.WORKOUT
    file_id_message.manufacturer = Manufacturer.DEVELOPMENT.value
    file_id_message.product = 0
    file_id_message.time_created = round(datetime.datetime.now().timestamp() * 1000)
    file_id_message.serial_number = 0x12345678

    workout_steps = []
    step = WorkoutStepMessage()
    step.workout_step_name = 'Warm up 10min in Heart Rate Zone 1'
    step.intensity = Intensity.WARMUP
    step.duration_type = WorkoutStepDuration.TIME
    step.duration_time = 600.0
    step.target_type = WorkoutStepTarget.HEART_RATE
    step.target_hr_zone = 1
    workout_steps.append(step)

    step = WorkoutStepMessage()
    step.workout_step_name = 'Bike 40min Power Zone 3'
    step.intensity = Intensity.ACTIVE
    step.duration_type = WorkoutStepDuration.TIME
    step.duration_time = 24000.0
    step.target_type = WorkoutStepTarget.POWER
    step.target_power_zone = 3
    workout_steps.append(step)

    step = WorkoutStepMessage()
    step.workout_step_name = 'Cool Down Until Lap Button Pressed'
    step.intensity = Intensity.COOLDOWN
    step.duration_type = WorkoutStepDuration.OPEN
    step.durationValue = 0
    step.target_type = WorkoutStepTarget.OPEN
    step.target_value = 0
    workout_steps.append(step)

    workout_message = WorkoutMessage()
    workout_message.workoutName = 'Tempo Bike'
    workout_message.sport = Sport.CYCLING
    workout_message.num_valid_steps = len(workout_steps)

    # We set autoDefine to true, so that the builder creates the required
    # Definition Messages for us.
    builder = FitFileBuilder(auto_define=True, min_string_size=50)
    builder.add(file_id_message)
    builder.add(workout_message)
    builder.add_all(workout_steps)

    fit_file = builder.build()

    fit_file.to_file('../tests/out/tempo_bike_workout.fit')

    fit_file2 = FitFile.from_file('../tests/out/tempo_bike_workout.fit')
    fit_file2.to_csv('../tests/out/tempo_bike_workout.csv')


if __name__ == "__main__":
    main()
