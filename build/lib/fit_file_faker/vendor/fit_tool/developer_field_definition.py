import struct

from fit_file_faker.vendor.fit_tool.base_type import BaseType
from fit_file_faker.vendor.fit_tool.developer_field import DeveloperField


class DeveloperFieldDefinition:
    PACK_FORMAT = 'BBB'

    def __init__(self, field_id: int, size: int, developer_data_index: int):
        self.field_id = field_id
        self.size = size
        self.developer_data_index = developer_data_index

    def to_bytes(self):
        return struct.pack(self.PACK_FORMAT, self.field_id, self.size,
                           self.developer_data_index)

    @classmethod
    def from_bytes(cls, bytes_buffer, offset=0):
        field_id, size, developer_data_index = struct.unpack_from(cls.PACK_FORMAT, bytes_buffer, offset)

        return cls(field_id, size, developer_data_index)

    @classmethod
    def field_definition_size(cls):
        return struct.calcsize(cls.PACK_FORMAT)

    @classmethod
    def from_field(cls, field: DeveloperField, min_string_size: int = 0):
        if field.base_type == BaseType.STRING:
            size = max(field.size, min_string_size)
        else:
            size = field.size

        return cls(field_id=field.field_id, size=size, developer_data_index=field.developer_data_index)
