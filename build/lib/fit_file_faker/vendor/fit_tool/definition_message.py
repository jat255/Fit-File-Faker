import struct
from typing import Dict as dict
from typing import List as list
from typing import Optional

from fit_file_faker.vendor.fit_tool.developer_field import DeveloperField
from fit_file_faker.vendor.fit_tool.developer_field_definition import DeveloperFieldDefinition
from fit_file_faker.vendor.fit_tool.endian import Endian
from fit_file_faker.vendor.fit_tool.field_definition import FieldDefinition
from fit_file_faker.vendor.fit_tool.message import Message
from fit_file_faker.vendor.fit_tool.utils.logging import logger


class DefinitionMessage(Message):

    def __init__(self, local_id: int = 0, global_id: int = 0, endian: Endian = Endian.LITTLE,
                 field_definitions: list[FieldDefinition] = None,
                 developer_field_definitions: list[DeveloperFieldDefinition] = None
                 ):
        super().__init__(local_id=local_id, global_id=global_id,
                         size=DefinitionMessage.calculate_size(field_definitions, developer_field_definitions),
                         endian=endian)

        self.field_definitions = field_definitions if field_definitions else []
        self.developer_field_definitions = developer_field_definitions if developer_field_definitions else []

    @property
    def defined_data_size(self) -> int:
        size = 0
        for field_definition in self.field_definitions:
            size += field_definition.size

        for developer_field_definition in self.developer_field_definitions:
            size += developer_field_definition.size

        return size

    def has_developer_fields(self) -> bool:
        return len(self.developer_field_definitions) > 0

    def get_field_definition(self, field_id: int) -> Optional[FieldDefinition]:
        return next((x for x in self.field_definitions if x.field_id == field_id), None)

    def remove_field(self, field_id: int):
        field_definition = self.get_field_definition(field_id)
        if field_definition:
            self.field_definitions.remove(field_definition)
            self.size = DefinitionMessage.calculate_size(self.field_definitions, self.developer_field_definitions)

    def remove_developer_field(self, developer_data_index: int, field_id: int):
        field_definition = self.get_developer_field_definition(developer_data_index, field_id)
        if field_definition:
            self.developer_field_definitions.remove(field_definition)
            self.size = DefinitionMessage.calculate_size(self.field_definitions, self.developer_field_definitions)

    def add_field_definition(self, definition: FieldDefinition):
        self.field_definitions.append(definition)

    def get_developer_field_definition(self, developer_data_index: int, field_id: int) \
            -> Optional[DeveloperFieldDefinition]:
        return next((x for x in self.developer_field_definitions if
                     x.developer_data_index == developer_data_index and x.field_id == field_id), None)

    def add_developer_field_definition(self, definition: DeveloperFieldDefinition):
        self.developer_field_definitions.append(definition)

    def to_row(self) -> list:
        from fit_file_faker.vendor.fit_tool.profile.messages.message_factory import MessageFactory
        values = []
        message = MessageFactory.from_definition(self, [])
        values.append(message.name)

        for field_definition in self.field_definitions:
            field = message.get_field(field_definition.field_id)

            if not field:
                logger.warning(f'Field id:{field_definition.field_id} could not be found in message: {message.name}')
                continue

            values.append(field.name)
            values.append(field_definition.size)
            values.append('bytes')

        for field_definition in self.developer_field_definitions:
            field = self.get_developer_field_definition(field_definition.developer_data_index,
                                                        field_definition.field_id)

            if not field:
                logger.warning(f'Field id:{field_definition.field_id} could not be found in message: {message.name}')
                continue

            values.append(f'[{field.developer_data_index},{field.field_id}]');
            values.append(field.size)
            ''
            values.append('bytes')

        return values

    def to_bytes(self) -> bytes:
        bytes_buffer = bytearray()
        endian_symbol = '<' if self.endian == Endian.LITTLE else '>'

        # reserved
        bytes_buffer.append(0)

        # architecture
        bytes_buffer.append(0 if self.endian == Endian.LITTLE else 1)

        # global id
        buffer = struct.pack(f'{endian_symbol}H', self.global_id)
        bytes_buffer += buffer

        # field count
        bytes_buffer.append(len(self.field_definitions))

        # field definitions
        for fd in self.field_definitions:
            bytes_buffer += fd.to_bytes()

        # developer field definitions
        if self.developer_field_definitions:
            bytes_buffer.append(len(self.developer_field_definitions))

            # developer field definitions
            for fd in self.developer_field_definitions:
                bytes_buffer += fd.to_bytes()

        return bytes(bytes_buffer)

    def get_developer_fields(self, developer_fields_by_data_index: dict) -> list[DeveloperField]:
        developer_fields = []

        for field_definition in self.developer_field_definitions:
            developer_field = developer_fields_by_data_index[field_definition.developer_data_index][
                field_definition.field_id]
            if developer_field:
                sized_developer_field = DeveloperField.from_developer_field(developer_field, size=field_definition.size)
                developer_fields.append(sized_developer_field)

        return developer_fields

    @classmethod
    def from_bytes(cls, bytes_buffer: bytes, offset: int = 0, has_developer_fields: bool = False):

        # reserved
        offset += 1

        # architecture
        value, = struct.unpack_from('B', bytes_buffer, offset)
        endian = Endian(value)
        endian_symbol = '<' if endian == Endian.LITTLE else '>'
        offset += 1

        # global id
        global_id, = struct.unpack_from(f'{endian_symbol}H', bytes_buffer, offset)
        offset += 2

        # number of fields
        field_count, = struct.unpack_from('B', bytes_buffer, offset)
        offset += 1

        # Field definitions;
        field_definitions = []
        field_definition_size = FieldDefinition.field_definition_size()
        for i in range(field_count):
            fd_bytes = bytes_buffer[offset:offset + field_definition_size]
            field_definition = FieldDefinition.from_bytes(fd_bytes)
            field_definitions.append(field_definition)
            offset += field_definition_size

        # Developer Field definitions;
        developer_field_definitions = []
        if has_developer_fields:
            dev_field_count, = struct.unpack_from('B', bytes_buffer, offset)
            offset += 1

            developer_field_definition_size = DeveloperFieldDefinition.field_definition_size()
            for i in range(dev_field_count):
                fd_bytes = bytes_buffer[offset:offset + developer_field_definition_size]
                field_definition = DeveloperFieldDefinition.from_bytes(fd_bytes)
                developer_field_definitions.append(field_definition)
                offset += developer_field_definition_size

        return cls(endian=endian, global_id=global_id, field_definitions=field_definitions,
                   developer_field_definitions=developer_field_definitions)

    @classmethod
    def from_data_message(cls, data_message, min_string_size: int = 0):

        if data_message.definition_message:
            return data_message.definition_message

        field_definitions = []

        for field in data_message.fields:
            if field.is_valid():
                field_definitions.append(FieldDefinition.from_field(field, min_string_size=min_string_size))

        developer_field_definitions = []
        for field in data_message.developer_fields:
            if field.is_valid():
                developer_field_definitions.append(
                    DeveloperFieldDefinition.from_field(field, min_string_size=min_string_size))

        return cls(
            endian=data_message.endian,
            global_id=data_message.global_id,
            local_id=data_message.local_id,
            field_definitions=field_definitions,
            developer_field_definitions=developer_field_definitions)

    @staticmethod
    def calculate_size(field_definitions: list[FieldDefinition],
                       developer_field_definitions: list[DeveloperFieldDefinition]):
        field_definitions_count = len(field_definitions) if field_definitions else 0
        developer_field_definitions_count = len(developer_field_definitions) if developer_field_definitions else 0

        if developer_field_definitions_count == 0:
            return 5 + FieldDefinition.field_definition_size() * field_definitions_count + DeveloperFieldDefinition.field_definition_size() * developer_field_definitions_count
        else:
            return 5 + FieldDefinition.field_definition_size() * field_definitions_count + 1 + DeveloperFieldDefinition.field_definition_size() * developer_field_definitions_count

    def supports(self, other) -> bool:
        if self.global_id != other.global_id:
            return False

        if self.local_id != other.local_id:
            return False

        if self.endian != other.endian:
            return False

        if len(self.field_definitions) != len(other.field_definitions):
            return False

        for i in range(len(self.field_definitions)):
            field_definition = self.field_definitions[i]
            other_field_definition = other.field_definitions[i]

            if field_definition.field_id != other_field_definition.field_id:
                return False

            if field_definition.base_type != other_field_definition.base_type:
                return False

            if field_definition.size < other_field_definition.size:
                return False

        if len(self.developer_field_definitions) != len(other.developer_field_definitions):
            return False

        for i in range(len(self.developer_field_definitions)):
            field_definition = self.developer_field_definitions[i]
            other_field_definition = other.developer_field_definitions[i]

            if field_definition.field_id != other_field_definition.field_id:
                return False

            if field_definition.size < other_field_definition.size:
                return False

        return True
