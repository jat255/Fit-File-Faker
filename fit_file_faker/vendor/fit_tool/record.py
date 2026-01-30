from typing import Dict as dict
from typing import List as list

from fit_file_faker.vendor.fit_tool.data_message import DataMessage
from fit_file_faker.vendor.fit_tool.definition_message import DefinitionMessage
from fit_file_faker.vendor.fit_tool.developer_field import DeveloperField
from fit_file_faker.vendor.fit_tool.message import Message


class RecordHeader:
    """The record header indicates whether the record content contains a definition message, a normal data message or a
     compressed timestamp data message. The record header also has a Local Message Type field that references the local
     message in the data record to its global FIT message."""

    HEADER_SIZE = 1
    IS_TIME_COMPRESSED_BIT_MASK = 0x80  # bits 7
    IS_DEFINITION_BIT_MASK = 0x40  # bits 6
    HAS_DEVELOPER_FIELDS_BIT_MASK = 0x20  # bits 5

    NORMAL_LOCAL_ID_BIT_MASK = 0x0f  # bits 0-3
    TIME_COMPRESSED_LOCAL_ID_BIT_MASK = 0x60  # bits 5-6 (0b0110 0000)
    TIME_OFFSET_BIT_MASK = 0x1f  # bits 0-4 (0b0001 1111)

    MAX_NORMAL_LOCAL_ID = 15
    MAX_TIME_COMPRESSED_LOCAL_ID = 3

    def __init__(self, is_time_compressed: bool = False, is_definition: bool = True, has_developer_fields: bool = False,
                 local_id: int = 0, time_offset_seconds: int = 0):
        # time compressed if true, otherwise normal header
        self.is_time_compressed = is_time_compressed

        # if true body contains a definition message, otherwise  body contains a data message
        self.is_definition = is_definition

        # if true messages also contain developer fields
        self.has_developer_fields = has_developer_fields
        self.local_id = local_id

        # only valid if this is a time compressed header
        self.time_offset_seconds = time_offset_seconds

    @property
    def size(self):
        return RecordHeader.HEADER_SIZE

    @classmethod
    def from_message(cls, message: Message):

        if isinstance(message, DefinitionMessage):
            has_developer_fields = message.has_developer_fields()
            return cls(
                has_developer_fields=has_developer_fields,
                local_id=message.local_id)
        else:
            return cls(is_definition=False, local_id=message.local_id)

    @classmethod
    def from_bytes(cls, bytes_buffer: bytes, offset: int = 0):
        byte = bytes_buffer[offset]

        is_time_compressed = (byte & cls.IS_TIME_COMPRESSED_BIT_MASK) == cls.IS_TIME_COMPRESSED_BIT_MASK
        if is_time_compressed:
            local_id = (byte & cls.TIME_COMPRESSED_LOCAL_ID_BIT_MASK) >> 5
            time_offset_seconds = byte & cls.TIME_OFFSET_BIT_MASK

            return cls(is_time_compressed=True, local_id=local_id, time_offset_seconds=time_offset_seconds)
        else:
            is_definition = (byte & cls.IS_DEFINITION_BIT_MASK) == cls.IS_DEFINITION_BIT_MASK
            has_developer_fields = (byte & cls.HAS_DEVELOPER_FIELDS_BIT_MASK) == cls.HAS_DEVELOPER_FIELDS_BIT_MASK
            local_id = byte & cls.NORMAL_LOCAL_ID_BIT_MASK

            return cls(is_definition=is_definition, has_developer_fields=has_developer_fields, local_id=local_id)

    def to_bytes(self):

        byte = 0x00

        if self.is_time_compressed:
            byte |= RecordHeader.IS_TIME_COMPRESSED_BIT_MASK
            byte |= (self.local_id << 5) & RecordHeader.TIME_COMPRESSED_LOCAL_ID_BIT_MASK
            byte |= self.time_offset_seconds & RecordHeader.TIME_OFFSET_BIT_MASK
        else:
            # normal header
            if self.is_definition:
                byte |= RecordHeader.IS_DEFINITION_BIT_MASK
                if self.has_developer_fields:
                    byte |= RecordHeader.HAS_DEVELOPER_FIELDS_BIT_MASK

            byte |= (self.local_id & RecordHeader.NORMAL_LOCAL_ID_BIT_MASK)

        return byte.to_bytes(1, 'little')

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def to_row(self) -> []:
        header_string = 'Definition' if self.is_definition else 'Data'
        return [header_string, self.local_id]


class Record:

    def __init__(self, header: RecordHeader, message: Message):
        self.header = header
        self.message = message

    @property
    def local_id(self) -> int:
        return self.header.local_id

    @property
    def is_definition(self) -> bool:
        return self.header.is_definition

    @property
    def size(self) -> int:
        return self.header.size + self.message.size

    @classmethod
    def from_message(cls, message: Message):
        header = RecordHeader.from_message(message)
        return cls(header, message)

    @classmethod
    def from_bytes(cls, definition_messages: dict[int, DefinitionMessage], bytes_buffer: bytes, offset: int = 0,
                   developer_fields_by_data_index: dict[int, dict[int, DeveloperField]] = None):
        header = RecordHeader.from_bytes(bytes_buffer, offset=offset)
        offset += header.size

        if header.is_definition:
            message = DefinitionMessage.from_bytes(bytes_buffer, offset=offset,
                                                   has_developer_fields=header.has_developer_fields)
        else:
            definition_message = definition_messages[header.local_id]

            if not definition_message:
                raise Exception(f'DefinitionMessage not defined for local_id: {header.local_id}')

            if developer_fields_by_data_index:
                developer_fields = definition_message.get_developer_fields(developer_fields_by_data_index)
            else:
                developer_fields = []
            message = DataMessage.from_bytes(definition_message, developer_fields, bytes_buffer, offset=offset)

        return cls(header, message)

    def to_bytes(self):
        return self.header.to_bytes() + self.message.to_bytes()

    def to_row(self) -> list:
        row = []
        row.extend(self.header.to_row())
        row.extend(self.message.to_row())
        return row

    def defined_size(self, definition_message: DefinitionMessage = None) -> int:
        if self.header.is_definition:
            return self.size
        elif definition_message:
            return self.header.size + definition_message.defined_data_size
        else:
            return 0
