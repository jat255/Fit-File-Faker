from typing import List as list

from fit_file_faker.vendor.fit_tool.data_message import DataMessage
from fit_file_faker.vendor.fit_tool.definition_message import DefinitionMessage
from fit_file_faker.vendor.fit_tool.developer_field import DeveloperField
from fit_file_faker.vendor.fit_tool.field import Field


class GenericMessage(DataMessage):
    NAME = 'generic'

    def __init__(self, definition_message: DefinitionMessage, developer_fields: list[DeveloperField] = None):
        fields = [Field.from_field_definition(definition) for definition in definition_message.field_definitions]
        super().__init__(global_id=definition_message.global_id, local_id=definition_message.local_id,
                         endian=definition_message.endian, name=GenericMessage.NAME,
                         definition_message=definition_message, fields=fields, developer_fields=developer_fields)

    #
    # final bool growable;

    @classmethod
    def from_bytes(cls, definition_message: DefinitionMessage, developer_fields: list[DeveloperField],
                   bytes_buffer: bytes, offset: int = 0):
        message = GenericMessage(definition_message=definition_message)
        message.read_from_bytes(bytes_buffer)
        return message
