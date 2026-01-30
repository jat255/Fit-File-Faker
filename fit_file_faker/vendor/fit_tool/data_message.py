from typing import List as list
from typing import Optional

from fit_file_faker.vendor.fit_tool.definition_message import DefinitionMessage
from fit_file_faker.vendor.fit_tool.developer_field import DeveloperField
from fit_file_faker.vendor.fit_tool.endian import Endian
from fit_file_faker.vendor.fit_tool.field import Field
from fit_file_faker.vendor.fit_tool.message import Message
from fit_file_faker.vendor.fit_tool.utils.logging import logger


class DataMessage(Message):

    def __init__(self, local_id: int = 0, global_id: int = 0, endian: Endian = Endian.LITTLE,
                 name: str = '',
                 definition_message: DefinitionMessage = None,
                 fields: list[Field] = None,
                 developer_fields: list[DeveloperField] = None
                 ):
        super().__init__(local_id=local_id, global_id=global_id,
                         endian=endian)

        self.name = name
        self.definition_message = definition_message
        self.fields = fields if fields else []
        self.developer_fields = developer_fields if developer_fields else []

    @staticmethod
    def from_definition(definition_message: DefinitionMessage, developer_fields: list[DeveloperField]):
        from fit_file_faker.vendor.fit_tool.profile.messages.message_factory import MessageFactory
        return MessageFactory.from_definition(definition_message, developer_fields)

    @classmethod
    def from_bytes(cls, definition_message: DefinitionMessage, developer_fields: list[DeveloperField],
                   bytes_buffer: bytes, offset: int = 0):
        message = DataMessage.from_definition(definition_message, developer_fields)
        message.read_from_bytes(bytes_buffer, offset)
        return message

    @property
    def size(self) -> int:
        message_size = 0
        for field in self.fields:
            if field.is_valid():
                message_size += field.size

        for field in self.developer_fields:
            if field.is_valid():
                message_size += field.size

        return message_size

    @size.setter
    def size(self, _size: int):
        pass

    def set_definition_message(self, definition_message: DefinitionMessage):
        self.definition_message = definition_message
        for field in self.fields:
            field_definition = definition_message.get_field_definition(field.field_id)
            if field_definition:
                field.size = field_definition.size
            else:
                field.size = 0

        for field in self.developer_fields:
            field_definition = definition_message.get_developer_field_definition(field.developer_data_index,
                                                                                 field.field_id)
            if field_definition:
                field.size = field_definition.size
            else:
                field.size = 0

    def get_field(self, field_id: int) -> Optional[Field]:
        return next((x for x in self.fields if x.field_id == field_id), None)

    def get_field_by_name(self, name: str) -> Optional[Field]:
        return next((x for x in self.fields if x.name == name), None)

    def clear_field_by_id(self, field_id: int):
        field = self.get_field(field_id)
        if field:
            field.clear()
            if self.definition_message:
                self.definition_message.remove_field(field_id)

    def remove_field(self, field_id: int):
        self.clear_field_by_id(field_id)

    def get_developer_field(self, developer_data_index: int, field_id: int) -> Optional[DeveloperField]:
        return next(iter([x for x in self.developer_fields if
                          x.developer_data_index == developer_data_index and x.field_id == field_id]))

    def get_developer_field_by_name(self, name: str) -> Optional[DeveloperField]:
        return next(iter([x for x in self.developer_fields if x.name == name]))

    def read_from_bytes(self, bytes_buffer: bytes, offset: int = 0):
        start = offset

        if not self.definition_message:
            raise Exception('DefinitionMessage cannot be null.')

        for field_definition in self.definition_message.field_definitions:
            field = self.get_field(field_definition.field_id)

            if not field:
                logger.warning(
                    f'Field id: {field_definition.field_id} is not defined for message {self.name}:{self.global_id}. Skipping this field')
                start += field_definition.size
                continue

            if field.is_valid():
                field_bytes = bytes_buffer[start:start + field.size]
                field.read_all_from_bytes(field_bytes, endian=self.endian)
                start += field.size
            else:
                raise Exception(f'Field ${field.name} is empty')

        for developer_field_definition in self.definition_message.developer_field_definitions:
            field = self.get_developer_field(developer_field_definition.developer_data_index,
                                             developer_field_definition.field_id)

            if not field:
                logger.warning(
                    f'Developer Field id: {developer_field_definition.field_id} is not defined for message {self.name}:{self.global_id}. Skipping this field')
                start += developer_field_definition.size
                continue

            if field.is_valid():
                field_bytes = bytes_buffer[start:start + field.size]
                field.read_all_from_bytes(field_bytes, endian=self.endian)
                start += field.size
            else:
                raise Exception(f'Developer Field ${field.name} is empty')

    def to_row(self) -> list:
        row = [self.name]

        if self.definition_message:
            for field_definition in self.definition_message.field_definitions:
                field = self.get_field(field_definition.field_id)
                if field is None:
                    # logger.w('Field for id: ${fieldDefinition.id} not found.');
                    continue

                if field.is_valid():
                    sub_field = field.get_valid_sub_field(self.fields)
                    row.extend(field.to_row(sub_field=sub_field))
                else:
                    raise Exception(f'Field for id: {field_definition.field_id} is not valid.')

            for field_definition in self.definition_message.developer_field_definitions:
                field = self.get_developer_field(field_definition.developer_data_index, field_definition.field_id)

                if field is None:
                    raise Exception(
                        f'Developer field for id: {field_definition.developer_data_index}:{field_definition.field_id} not found.')

                if field.is_valid():
                    sub_field = field.get_valid_sub_field(self.fields)
                    row.extend(field.to_row(sub_field=sub_field))
                else:
                    raise Exception(f'Developer Field for id: {field_definition.field_id} is not valid.')

        else:
            for field in self.fields:
                if field.is_valid():
                    sub_field = field.get_valid_sub_field(self.fields)
                    row.extend(field.to_row(sub_field=sub_field))

            for field in self.developer_fields:
                if field.is_valid():
                    sub_field = field.get_valid_sub_field(self.fields)
                    row.extend(field.to_row(sub_field=sub_field))

        return row

    def to_bytes(self) -> bytes:
        bytes_buffer = b''

        if self.definition_message:
            for field_definition in self.definition_message.field_definitions:
                field = self.get_field(field_definition.field_id)
                if field is None:
                    # logger.w('Field for id: ${fieldDefinition.id} not found.');
                    continue

                if field.is_valid():
                    bytes_buffer += field.to_bytes(endian=self.endian)
                else:
                    raise Exception(f'Field for id: {field_definition.field_id} is not valid.')

            for field_definition in self.definition_message.developer_field_definitions:
                field = self.get_developer_field(field_definition.developer_data_index, field_definition.field_id)

                if field is None:
                    raise Exception(
                        f'Developer field for id: {field_definition.developer_data_index}:{field_definition.field_id} not found.')

                if field.is_valid():
                    bytes_buffer += field.to_bytes(endian=self.endian)
                else:
                    raise Exception(f'Developer Field for id: {field_definition.field_id} is not valid.')

        else:
            for field in self.fields:
                if field.is_valid():
                    bytes_buffer += field.to_bytes(endian=self.endian)

            for field in self.developer_fields:
                if field.is_valid():
                    bytes_buffer += field.to_bytes(endian=self.endian)

        return bytes_buffer
