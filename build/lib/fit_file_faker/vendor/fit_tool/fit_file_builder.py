from typing import List as list

from fit_file_faker.vendor.fit_tool.data_message import DataMessage
from fit_file_faker.vendor.fit_tool.definition_message import DefinitionMessage
from fit_file_faker.vendor.fit_tool.fit_file import FitFile
from fit_file_faker.vendor.fit_tool.fit_file_header import FitFileHeader
from fit_file_faker.vendor.fit_tool.message import Message
from fit_file_faker.vendor.fit_tool.record import Record
from fit_file_faker.vendor.fit_tool.utils.crc import crc16


def calc_records_size(records: list[Record]) -> int:
    size = 0
    for record in records:
        size += record.size
    return size


def calc_crc(header: FitFileHeader, records: [Record]):
    crc = crc16(header.to_bytes())
    for record in records:
        crc = crc16(record.to_bytes(), crc=crc)
    return crc


class FitFileBuilder:

    def __init__(self, auto_define: bool = True, min_string_size: int = 0):
        self.auto_define = auto_define
        self.min_string_size = min_string_size
        self.records = []
        self.definition_map = {}

    def add(self, message: Message):
        if isinstance(message, DataMessage):
            stored_definition = self.definition_map.get(message.local_id)

            if stored_definition is None:
                if self.auto_define:
                    new_definition = DefinitionMessage.from_data_message(message, min_string_size=self.min_string_size)
                    self.definition_map[message.local_id] = new_definition
                    self.records.append(Record.from_message(new_definition))
                else:
                    raise Exception(f'Message has not been defined: ${message.name} local_id: ${message.local_id}')
            else:
                new_definition = DefinitionMessage.from_data_message(message, min_string_size=self.min_string_size)
                if not stored_definition.supports(new_definition):
                    if self.auto_define:
                        self.definition_map[new_definition.local_id] = new_definition
                        self.records.append(Record.from_message(new_definition))
                    else:
                        raise Exception(
                            f'The definition does not support this message. record:{len(self.records) + 1} name:{message.name} local_id:{message.local_id}')

            if message.definition_message is None:
                message.set_definition_message(self.definition_map[message.local_id])
        elif isinstance(message, DefinitionMessage):
            self.definition_map[message.local_id] = message

        record = Record.from_message(message)
        self.records.append(record)

    def add_all(self, messages: list[Message]):
        for message in messages:
            self.add(message)

    def build(self) -> FitFile:
        records_size = calc_records_size(self.records)
        header = FitFileHeader(records_size=records_size)

        crc = calc_crc(header, self.records)
        return FitFile(header, self.records, crc)
