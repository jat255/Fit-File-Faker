import datetime
import struct
import unittest

from fit_file_faker.vendor.fit_tool.base_type import BaseType
from fit_file_faker.vendor.fit_tool.definition_message import DefinitionMessage
from fit_file_faker.vendor.fit_tool.developer_field import DeveloperField
from fit_file_faker.vendor.fit_tool.fit_file import FitFile
from fit_file_faker.vendor.fit_tool.fit_file_builder import FitFileBuilder
from fit_file_faker.vendor.fit_tool.fit_file_header import FitFileHeader
from fit_file_faker.vendor.fit_tool.message import Message
from fit_file_faker.vendor.fit_tool.profile.messages.developer_data_id_message import DeveloperDataIdMessage
from fit_file_faker.vendor.fit_tool.profile.messages.event_message import EventMessage
from fit_file_faker.vendor.fit_tool.profile.messages.field_description_message import FieldDescriptionMessage
from fit_file_faker.vendor.fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_file_faker.vendor.fit_tool.profile.messages.record_message import RecordMessage
from fit_file_faker.vendor.fit_tool.profile.profile_type import FileType, Manufacturer, Event, EventType
from fit_file_faker.vendor.fit_tool.record import Record
from fit_file_faker.vendor.fit_tool.utils.crc import crc16


class TestWriteActivityFile(unittest.TestCase):

    def setUp(self):
        super().setUp()

    def shortDescription(self):
        return None

    def test_write_activity_file_iteratively(self):
        """Test for writing activity file iteratively
        """
        start_timestamp_millis = round(datetime.datetime(2022, 5, 10, 5, 5, 5).timestamp()) * 1000
        timestamp = start_timestamp_millis

        records_crc = 0
        records_size = 0

        def write_message(message_: Message):
            """Helper method to write message to a file while accumulating records size and records crc"""
            nonlocal records_crc
            nonlocal records_size

            record_ = Record.from_message(message_)
            buffer_ = record_.to_bytes()
            file_object.write(buffer_)
            records_size += len(buffer_)
            records_crc = crc16(buffer_, crc=records_crc)

        out_path = '../tests/out/activity_iterative.fit'
        with open(out_path, 'wb') as file_object:
            # Create a placeholder 14 byte header (includes a crc). We overwrite these bytes after all the records
            # have been written.
            header = FitFileHeader(records_size=0, crc=0)
            file_object.write(header.to_bytes())

            message = FileIdMessage()
            message.type = FileType.ACTIVITY
            message.manufacturer = Manufacturer.STAGES_CYCLING
            message.product = 1
            message.time_created = timestamp
            message.serial_number = 0x12345678
            definition = DefinitionMessage.from_data_message(message)
            write_message(definition)
            write_message(message)

            # It is a best practice to include timer start and stop events in all Activity files. A timer start event
            # should occur before the first Record message in the file, and a timer stop event should occur after the
            # last Record message in the file when the activity recording is complete. Timer stop and start events
            # should be used anytime the activity recording has been paused and resumed. Record messages should not be
            # encoded to the file when the timer is paused.
            message = EventMessage()
            message.event = Event.TIMER
            message.event_type = EventType.START
            message.timestamp = timestamp
            definition = DefinitionMessage.from_data_message(message)
            write_message(definition)
            write_message(message)

            timestamp += 1000
            distance = 0

            message = RecordMessage()
            message.position_lat = 40.0
            message.position_long = -105.2613892
            message.distance = distance
            message.timestamp = timestamp
            definition = DefinitionMessage.from_data_message(message)
            write_message(definition)  # write the definition only once for all the record messages
            write_message(message)

            distance += 5
            timestamp += 1000
            message = RecordMessage()
            message.position_lat = 40.0
            message.position_long = -105.1613892
            message.distance = distance
            message.timestamp = timestamp
            write_message(message)

            message = EventMessage()
            message.event = Event.TIMER
            message.event_type = EventType.STOP
            message.timestamp = timestamp
            definition = DefinitionMessage.from_data_message(message)
            write_message(definition)
            write_message(message)

            # write crc
            buffer = struct.pack('<H', records_crc)
            file_object.write(buffer)

            # inject updated FIT file header at start of file with a header crc
            header = FitFileHeader(records_size=records_size, gen_crc=True)
            file_object.seek(0)
            file_object.write(header.to_bytes())

        # read back the file
        with open(out_path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            # for row in fit_file.to_rows():
            #     print(row)
            record_message_index = 0
            for record in fit_file.records:
                message = record.message
                if isinstance(message, RecordMessage):
                    self.assertEqual(message.distance, record_message_index * 5)
                    record_message_index += 1

    def test_write_activity_with_developer_data_fields(self):
        """Test encoding an activity with developer data fields.
        """
        # Set auto_define to true, so that the builder creates the required Definition Messages for us.
        builder = FitFileBuilder(auto_define=True, min_string_size=50)

        message = FileIdMessage()
        message.type = FileType.ACTIVITY
        message.manufacturer = Manufacturer.DEVELOPMENT.value
        message.product = 1231
        message.time_created = round(datetime.datetime.now().timestamp() * 1000)
        message.serial_number = 0x12345678
        builder.add(message)

        developer_data_index = 0
        message = DeveloperDataIdMessage()
        message.application_id = b'123456'
        message.developer_data_index = developer_data_index
        builder.add(message)

        # Define the developer field
        doughnuts_earned_field_name = 'doughnuts_earned'
        doughnuts_earned_field_units = 'doughnuts'
        message = FieldDescriptionMessage()
        message.developer_data_index = developer_data_index
        message.field_definition_number = 0
        message.fit_base_type_id = BaseType.SINT8
        message.field_name = doughnuts_earned_field_name
        message.units = doughnuts_earned_field_units
        builder.add(message)

        # Add a record message with an addition doughnuts earned developer field
        dev_field = DeveloperField(developer_data_index=developer_data_index, field_id=0, size=1)
        dev_field.set_value(0, 5)

        message = RecordMessage(developer_fields=[dev_field])
        message.distance = 0
        message.power = 100
        builder.add(message)

        # Finally build the FIT file object and write it to a file
        fit_file = builder.build()

        out_path = '../tests/out/activity_with_developer_data.fit'

        fit_file.to_file(out_path)
        csv_path = '../tests/out/activity_with_developer_data.csv'
        fit_file.to_csv(csv_path)

        # read back the file
        with open(out_path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            for row in fit_file.to_rows():
                print(row)
            for record in fit_file.records:
                message = record.message
                if isinstance(message, RecordMessage):
                    self.assertEqual(message.developer_fields[0].name, doughnuts_earned_field_name)
                    self.assertEqual(message.developer_fields[0].get_value(0), 5)
                    self.assertEqual(message.developer_fields[0].units, doughnuts_earned_field_units)
