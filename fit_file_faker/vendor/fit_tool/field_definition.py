import struct

from fit_file_faker.vendor.fit_tool.base_type import BaseType


class FieldDefinition:
    PACK_FORMAT = 'BBB'

    def __init__(self, field_id: int, size: int, base_type: BaseType):
        self.field_id = field_id
        self.size = size
        self.base_type = base_type

    def to_bytes(self):
        return struct.pack(self.PACK_FORMAT, self.field_id, self.size,
                           self.base_type.value)

    @classmethod
    def from_bytes(cls, bytes_buffer, offset=0):
        field_id, size, type_value = struct.unpack_from(cls.PACK_FORMAT, bytes_buffer, offset)

        return cls(field_id, size, BaseType(type_value))

    @classmethod
    def field_definition_size(cls):
        return struct.calcsize(cls.PACK_FORMAT)

    @classmethod
    def from_field(cls, field, min_string_size: int = 0):
        if field.base_type == BaseType.STRING:
            size = max(field.size, min_string_size)
        else:
            size = field.size

        return cls(field_id=field.field_id, size=size, base_type=field.base_type)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__
