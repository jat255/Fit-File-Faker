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
    message.total_elapsed_time = elapsed_time/1000   # seconds
    message.total_timer_time = elapsed_time/1000     # seconds
    message.start_position_lat = course_records[0].position_lat
    message.start_position_long = course_records[0].position_long
    message.end_position_lat = course_records[-1].position_lat
    message.endPositionLong = course_records[-1].position_long
    message.total_distance = course_records[-1].distance
    builder.add(message)

    # Finally build the FIT file object and write it to a file
    fit_file = builder.build()

    out_path = '../tests/out/old_stage_course.fit'
    fit_file.to_file(out_path)
    csv_path = '../tests/out/old_stage_course.csv'
    fit_file.to_csv(csv_path)


if __name__ == "__main__":
    main()
