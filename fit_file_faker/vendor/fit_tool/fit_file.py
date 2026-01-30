import csv
import struct
from typing import List as list

from fit_file_faker.vendor.fit_tool.base_type import BaseType
from fit_file_faker.vendor.fit_tool.developer_field import DeveloperField
from fit_file_faker.vendor.fit_tool.fit_file_header import FitFileHeader
from fit_file_faker.vendor.fit_tool.profile.messages.field_description_message import FieldDescriptionMessage
from fit_file_faker.vendor.fit_tool.record import Record
from fit_file_faker.vendor.fit_tool.utils.crc import crc16
from fit_file_faker.vendor.fit_tool.utils.logging import logger


class FitFile:
    def __init__(self, header: FitFileHeader, records: list[Record], crc: int = None):
        self.header = header
        self.records = records
        self.crc = crc  # crc16 of header and records

    @classmethod
    def from_file(cls, path: str):
        with open(path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            return fit_file

    @classmethod
    def from_bytes(cls, bytes_buffer: bytes, check_crc: bool = True):
        crc = 0
        offset = 0

        header_size = bytes_buffer[0]

        header_bytes = bytes_buffer[:header_size]
        header = FitFileHeader.from_bytes(header_bytes)
        crc = crc16(header_bytes, crc=crc)
        offset += header_size

        records = []
        definition_messages = {}
        developer_fields_by_data_index = {}

        record_index = 0
        record_bytes_remaining_count = header.records_size
        while record_bytes_remaining_count > 0:
            record = Record.from_bytes(definition_messages=definition_messages, bytes_buffer=bytes_buffer,
                                       offset=offset, developer_fields_by_data_index=developer_fields_by_data_index)

            if record.is_definition:
                definition_messages[record.local_id] = record.message
            elif isinstance(record.message, FieldDescriptionMessage):
                message = record.message
                developer_field = DeveloperField(developer_data_index=message.developer_data_index,
                                                 field_id=message.field_definition_number,
                                                 base_type=BaseType(message.fit_base_type_id),
                                                 name=message.field_name,
                                                 scale=message.scale,
                                                 offset=message.offset,
                                                 units=message.units)
                if developer_field.developer_data_index not in developer_fields_by_data_index:
                    developer_fields_by_data_index[developer_field.developer_data_index] = {}

                developer_fields_by_data_index[developer_field.developer_data_index][
                    developer_field.field_id] = developer_field

            records.append(record)
            definition_message = definition_messages[record.local_id]
            record_size = record.size
            defined_size = record.defined_size(definition_message)
            crc = crc16(bytes_buffer[offset:offset + defined_size], crc=crc)

            if record_size != defined_size:
                logger.warning(
                    f'Record {record_index}, {record.message}: size ({record_size}) != defined size ({defined_size}). Some fields were not read correctly.')

            actual_bytes = bytes_buffer[offset:offset + defined_size]
            record_bytes = record.to_bytes()

            if actual_bytes != record_bytes:
                logger.warning(f'- {record_index} -\n\tactual: {actual_bytes}\n\trecord: {record_bytes}')

            record_bytes_remaining_count -= defined_size
            offset += defined_size
            record_index += 1

        file_crc, = struct.unpack(f'<H', bytes_buffer[offset:offset + 2])

        if crc != file_crc:
            message = f'Calculated crc ({hex(crc)}) does match crc in file ({hex(file_crc)}).'

            if check_crc:
                raise Exception(message)
            else:
                logger.warning(message)

        return FitFile(header, records, crc)

    def to_bytes(self, check_crc: bool = True):
        calculated_crc = 0
        bytes_buffer = bytearray()
        buffer = self.header.to_bytes()
        calculated_crc = crc16(buffer, crc=calculated_crc)
        bytes_buffer.extend(buffer)

        for record in self.records:
            buffer = record.to_bytes()
            calculated_crc = crc16(buffer, crc=calculated_crc)
            bytes_buffer.extend(buffer)

        if self.crc is None:
            self.crc = calculated_crc

        if self.crc != calculated_crc:
            message = f'Calculated crc ({calculated_crc}) != defined crc ({self.crc})'

            if check_crc:
                raise Exception(message)
            else:
                logger.warn(message)

        buffer = struct.pack('<H', self.crc)
        bytes_buffer.extend(buffer)

        return bytes(bytes_buffer)

    def to_rows(self) -> list[list]:
        result = []

        max_columns = 0
        for record in self.records:
            row = record.to_row()
            max_columns = max(max_columns, len(row))
            result.append(row)

        header_row = ['Type', 'Local ID', 'Message']
        max_fields = (max_columns - 3) // 3

        for i in range(max_fields):
            header_row.extend([f'Field {i}', f'Value {i}', f'Units {i}'])

        result.insert(0, header_row)

        return result

    def to_csv(self, path: str):

        rows = self.to_rows()

        with open(path, 'w', newline='') as csv_file:
            csv_writer = csv.writer(csv_file, delimiter=',',
                                    quotechar='"', quoting=csv.QUOTE_MINIMAL)
            for row in rows:
                csv_writer.writerow(row)

    def to_file(self, path: str):
        with open(path, 'wb') as file_object:
            file_object.write(self.to_bytes())
