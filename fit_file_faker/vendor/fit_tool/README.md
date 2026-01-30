## FIT File Faker note

Note: this library was vendored as of version 0.9.13, downloaded on 2026-01-30 from [https://bitbucket.org/stagescycling/python_fit_tool.git](https://bitbucket.org/stagescycling/python_fit_tool.git) and is being redistributed unmodified (other than updating import paths) under the terms of the license therein.


## Background

A library for reading and writing Garmin FIT files.

> The Flexible and Interoperable Data Transfer (FIT) protocol is designed specifically for the storing and sharing of data that originates from sport, fitness and health devices. The FIT protocol defines a set of data storage templates (FIT messages) that can be used to store information such as user profiles, activity data, courses, and workouts. It is specifically designed to be compact, interoperable and extensible.

[More info...](https://developer.garmin.com/fit/overview/)

Installation
==================

```
python3 -m pip install --upgrade pip
python3 -m pip install --upgrade fit_tool
```

Command line interface
=======================
```console
usage: fittool [-h] [-v] [-o OUTPUT] [-l LOG] [-t TYPE] FILE

Tool for managing FIT files.

positional arguments:
  FILE                  FIT file to process

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         specify verbose output
  -o OUTPUT, --output OUTPUT
                        Output filename.
  -l LOG, --log LOG     Log filename.
  -t TYPE, --type TYPE  Output format type. Options: csv, fit.
```

### Convert file to CSV
```console
fittool oldstage.fit 
```

Library Usage
=======================

### Reading a FIT file

The following code reads all the bytes from an activity FIT file and then decodes these bytes to create a FIT file
object. We then convert the FIT data to a human-readable CSV file.

```python
from fit_file_faker.vendor.fit_tool.fit_file import FitFile


def main():
    """ The following code reads all the bytes from a FIT formatted file and then decodes these bytes to
        create a FIT file object. We then convert the FIT data to a human-readable CSV file.
    """
    path = '../tests/data/sdk/Activity.fit'
    fit_file = FitFile.from_file(path)

    out_path = '../tests/data/sdk/Activity.csv'
    fit_file.to_csv(out_path)


if __name__ == "__main__":
    main()
```

### Reading a FIT file and plotting some data
```python
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from fit_file_faker.vendor.fit_tool.fit_file import FitFile
from fit_file_faker.vendor.fit_tool.profile.messages.record_message import RecordMessage


def main():
    """ Analyze a FIT file
    """
    mpl.style.use('seaborn')

    print(f'Loading activity file...')
    app_fit = FitFile.from_file('./activity_20211102_133232.fit')
    timestamp1 = []
    power1 = []
    distance1 = []
    speed1 = []
    cadence1 = []
    for record in app_fit.records:
        message = record.message
        if isinstance(message, RecordMessage):
            timestamp1.append(message.timestamp)
            distance1.append(message.distance)
            power1.append(message.power)
            speed1.append(message.speed)
            cadence1.append(message.cadence)

    start_timestamp = timestamp1[0]
    time1 = np.array(timestamp1)
    power1 = np.array(power1)
    speed1 = np.array(speed1)
    cadence1 = np.array(cadence1)
    time1 = (time1 - start_timestamp) / 1000.0  # seconds

    #
    # Plot the data
    #
    ax1 = plt.subplot(311)
    ax1.plot(time1, power1, '-o', label='app [W]')
    ax1.legend(loc="upper right")
    plt.xlabel('Time (s)')
    plt.ylabel('Power (W)')

    plt.subplot(312, sharex=ax1)
    plt.plot(time1, speed1, '-o', label='app [m/s]')
    plt.legend(loc="upper right")
    plt.xlabel('Time (s)')
    plt.ylabel('speed (m/s)')

    plt.subplot(313, sharex=ax1)
    plt.plot(time1, cadence1, '-o', label='app [rpm]')
    plt.legend(loc="upper right")
    plt.xlabel('Time (s)')
    plt.ylabel('cadence (rpm)')

    plt.show()


if __name__ == "__main__":
    main()
```

### Writing a Workout

```python
import datetime

from fit_file_faker.vendor.fit_tool.fit_file_builder import FitFileBuilder
from fit_file_faker.vendor.fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_file_faker.vendor.fit_tool.profile.messages.workout_message import WorkoutMessage
from fit_file_faker.vendor.fit_tool.profile.messages.workout_step_message import WorkoutStepMessage
from fit_file_faker.vendor.fit_tool.profile.profile_type import Sport, Intensity, WorkoutStepDuration, WorkoutStepTarget, Manufacturer,
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

    out_path = '../tests/out/tempo_bike_workout.fit'
    fit_file.to_file(out_path)


if __name__ == "__main__":
    main()
```

### Writing a Course

```python
import datetime

import gpxpy
from geopy.distance import geodesic

from fit_file_faker.vendor.fit_tool.fit_file_builder import FitFileBuilder
from fit_file_faker.vendor.fit_tool.profile.messages.course_message import CourseMessage
from fit_file_faker.vendor.fit_tool.profile.messages.course_point_message import CoursePointMessage
from fit_file_faker.vendor.fit_tool.profile.messages.event_message import EventMessage
from fit_file_faker.vendor.fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_file_faker.vendor.fit_tool.profile.messages.lap_message import LapMessage
from fit_file_faker.vendor.fit_tool.profile.messages.record_message import RecordMessage
from fit_file_faker.vendor.fit_tool.profile.profile_type import FileType, Manufacturer, Sport, Event, EventType, CoursePoint


def main():
    # Set auto_define to true, so that the builder creates the required Definition Messages for us.
    builder = FitFileBuilder(auto_define=True, min_string_size=50)

    # Read position data from a GPX file
    gpx_file = open('../tests/data/old_stage_left_hand_lee.gpx', 'r')
    gpx = gpxpy.parse(gpx_file)

    message = FileIdMessage()
    message.type = FileType.COURSE
    message.manufacturer = Manufacturer.DEVELOPMENT.value
    message.product = 0
    message.timeCreated = round(datetime.datetime.now().timestamp() * 1000)
    message.serialNumber = 0x12345678
    builder.add(message)

    # Every FIT course file MUST contain a Course message
    message = CourseMessage()
    message.courseName = 'old stage'
    message.sport = Sport.CYCLING
    builder.add(message)

    # Timer Events are REQUIRED for FIT course files
    start_timestamp = round(datetime.datetime.now().timestamp() * 1000)
    message = EventMessage()
    message.event = Event.TIMER
    message.event_type = EventType.START
    message.timestamp = start_timestamp
    builder.add(message)

    distance = 0.0
    timestamp = start_timestamp

    course_records = []  # track points

    prev_coordinate = None

    for track_point in gpx.tracks[0].segments[0].points:
        current_coordinate = (track_point.latitude, track_point.longitude)

        # calculate distance from previous coordinate and accumulate distance
        if prev_coordinate:
            delta = geodesic(prev_coordinate, current_coordinate).meters
        else:
            delta = 0.0
        distance += delta

        message = RecordMessage()
        message.position_lat = track_point.latitude
        message.position_long = track_point.longitude
        message.distance = distance
        message.timestamp = timestamp
        course_records.append(message)

        timestamp += 10000
        prev_coordinate = current_coordinate

    builder.add_all(course_records)

    #  Add start and end course points (i.e. way points)
    #
    message = CoursePointMessage()
    message.timestamp = course_records[0].timestamp
    message.position_lat = course_records[0].position_lat
    message.position_long = course_records[0].position_long
    message.type = CoursePoint.SEGMENT_START
    message.course_point_name = 'start'
    builder.add(message)

    message = CoursePointMessage()
    message.timestamp = course_records[-1].timestamp
    message.position_lat = course_records[-1].position_lat
    message.position_long = course_records[-1].position_long
    message.type = CoursePoint.SEGMENT_END
    message.course_point_name = 'end'
    builder.add(message)

    # stop event
    message = EventMessage()
    message.event = Event.TIMER
    message.eventType = EventType.STOP_ALL
    message.timestamp = timestamp
    builder.add(message)

    # Every FIT course file MUST contain a Lap message
    elapsed_time = timestamp - start_timestamp
    message = LapMessage()
    message.timestamp = timestamp
    message.start_time = start_timestamp
    message.total_elapsed_time = elapsed_time
    message.total_timer_time = elapsed_time
    message.start_position_lat = course_records[0].position_lat
    message.start_position_long = course_records[0].position_long
    message.end_position_lat = course_records[-1].position_lat
    message.endPositionLong = course_records[-1].position_long
    message.total_distance = course_records[-1].distance

    # Finally build the FIT file object and write it to a file
    fit_file = builder.build()

    out_path = '../tests/out/old_stage_course.fit'
    fit_file.to_file(out_path)
    csv_path = '../tests/out/old_stage_course.csv'
    fit_file.to_csv(csv_path)


if __name__ == "__main__":
    main()
```
