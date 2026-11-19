import struct
from enum import Enum
from typing import Dict as dict
from typing import List as list
from typing import Optional

from fit_file_faker.vendor.fit_tool.base_type import BaseType
from fit_file_faker.vendor.fit_tool.endian import Endian
from fit_file_faker.vendor.fit_tool.field_component import FieldComponent
from fit_file_faker.vendor.fit_tool.field_definition import FieldDefinition
from fit_file_faker.vendor.fit_tool.sub_field import SubField


class ArrayType(Enum):
    FIXED = 0
    VARIABLE = 1


class Field:
    encoded_values = []

    def __init__(self, field_id: int = 0, name: str = '', base_type: BaseType = BaseType.ENUM,
                 offset: float = None,
                 scale: float = None,
                 units: str = '',
                 is_accumulated: bool = False,
                 is_expanded_field=False,
                 sub_fields: list[SubField] = None,
                 components: list[FieldComponent] = None,
                 size: int = 0,
                 growable: bool = False,
                 type_name: str = '',
                 ref_field_map: dict = None,
                 array_type: ArrayType = None,
                 array_fixed_length: int = None):

        self.field_id = field_id
        self.name = name
        self.base_type = base_type
        self.offset = offset
        self.scale = scale
        self.units = units
        self.is_accumulated = is_accumulated
        self.is_expanded_field = is_expanded_field
        self.sub_fields = sub_fields if sub_fields else []
        self.components = components if components else []
        self.size = size if size else 0
        self.growable = growable
        self.type_name = type_name
        self.ref_field_map = ref_field_map
        self.array_type = array_type
        self.array_fixed_length = array_fixed_length

        self.encoded_values = [None for _ in range(Field.get_length_from_size(base_type, size))]

    @classmethod
    def from_field(cls, other):
        field = Field(field_id=other.field_id, name=other.name, base_type=other.base_type, offset=other.offset,
                      scale=other.scale, units=other.units, is_accumulated=other.is_accumulated,
                      is_expanded_field=other.is_expanded_field, sub_fields=other.sub_fields,
                      components=other.components,
                      size=other.size, growable=other.growable, type_name=other.type_name)
        field.encoded_values = other.encoded_values
        return field

    @classmethod
    def from_field_definition(cls, definition: FieldDefinition):
        field = Field(field_id=definition.field_id, name='field', base_type=definition.base_type,
                      units='', is_accumulated=False, is_expanded_field=False, size=definition.size, growable=False,
                      sub_fields=[], components=[],
                      type_name='')
        field.encoded_values = [None for _ in range(Field.get_length_from_size(definition.base_type, definition.size))]

        return field

    def get_sub_field(self, name: str = None, index: int = None) -> Optional[SubField]:
        if index is not None and 0 <= index < len(self.sub_fields):
            return self.sub_fields[index]

        if name is not None:
            for sub_field in self.sub_fields:
                if sub_field.name == name:
                    return sub_field

        return None

    def get_name(self, sub_field: SubField = None, sub_field_name: str = None, sub_field_index: int = None) -> str:
        if sub_field:
            sb = sub_field
        elif sub_field_name is not None:
            sb = self.get_sub_field(name=sub_field_name)
        elif sub_field_index is not None:
            sb = self.get_sub_field(index=sub_field_index)
        else:
            sb = None

        if sb:
            return sb.name
        else:
            return self.name

    def get_units(self, sub_field: SubField = None, sub_field_name: str = None, sub_field_index: int = None) -> str:
        if sub_field:
            sb = sub_field
        elif sub_field_name is not None:
            sb = self.get_sub_field(name=sub_field_name)
        elif sub_field_index is not None:
            sb = self.get_sub_field(index=sub_field_index)
        else:
            sb = None

        if sb:
            return sb.units
        else:
            return self.units

    def get_base_type(self, sub_field: SubField = None, sub_field_name: str = None,
                      sub_field_index: int = None) -> BaseType:
        if sub_field:
            sb = sub_field
        elif sub_field_name is not None:
            sb = self.get_sub_field(name=sub_field_name)
        elif sub_field_index is not None:
            sb = self.get_sub_field(index=sub_field_index)
        else:
            sb = None

        if sb:
            return sb.base_type
        else:
            return self.base_type

    def get_offset(self, sub_field: SubField = None, sub_field_name: str = None, sub_field_index: int = None) -> \
            Optional[float]:
        if sub_field:
            sb = sub_field
        elif sub_field_name is not None:
            sb = self.get_sub_field(name=sub_field_name)
        elif sub_field_index is not None:
            sb = self.get_sub_field(index=sub_field_index)
        else:
            sb = None

        if sb:
            return sb.offset
        else:
            return self.offset

    def get_scale(self, sub_field: SubField = None, sub_field_name: str = None, sub_field_index: int = None) -> \
            Optional[float]:
        if sub_field:
            sb = sub_field
        elif sub_field_name is not None:
            sb = self.get_sub_field(name=sub_field_name)
        elif sub_field_index is not None:
            sb = self.get_sub_field(index=sub_field_index)
        else:
            sb = None

        if sb:
            return sb.scale
        else:
            return self.scale

    def clear(self):
        self.size = 0
        self.encoded_values = []

    def is_valid(self) -> bool:
        return self.size != 0

    def is_not_valid(self) -> bool:
        return not self.is_valid()

    def get_value(self, index: int = 0, sub_field: SubField = None):
        if index < 0 or index >= len(self.encoded_values):
            return None

        encoded_value = self.encoded_values[index]
        return self.decode_value(encoded_value, sub_field)

    # Return values as a list
    def get_values(self):
        return [self.decode_value(encoded_value) for encoded_value in self.encoded_values]

    def set_values(self, values):
        for index, value in enumerate(values):
            self.set_value(index, value)

    def decode_value(self, encoded_value, sub_field: SubField = None):
        if encoded_value is None or type(encoded_value) == str:
            return encoded_value

        scale = self.get_scale(sub_field=sub_field)
        offset = self.get_offset(sub_field=sub_field)

        if (scale is None or scale == 1.0) and (offset is None or offset == 0.0):
            # no scaling
            value = encoded_value
        else:
            scale = scale if scale is not None else 1.0
            offset = offset if offset is not None else 0.0

            value = self.un_scale_offset_value(encoded_value, scale, offset)
            if self.type_name == 'date_time':
                value = round(value)

        return value

    @staticmethod
    def scale_offset_value(value: float, scale: float, offset: float) -> int:
        encoded_value = round((value + offset) * scale)
        return encoded_value

    @staticmethod
    def un_scale_offset_value(encoded_value: int, scale: float, offset: float) -> float:
        try:
            value = encoded_value / scale - offset
        except Exception as ex:
            raise ex
        return value

    @property
    def length(self) -> int:
        return len(self.encoded_values)

    def set_value(self, index: int, value, sub_field: SubField = None):
        encoded_value = self.encode_value(value, sub_field)
        self.set_encoded_value(index, encoded_value)

    def set_encoded_value(self, index: int, encoded_value, check_validity: bool = True):
        if index < 0:
            return

        if check_validity and self.base_type != BaseType.STRING:
            if not self.base_type.is_valid(encoded_value):
                raise Exception(
                    f'{self.name} encoded value {encoded_value} is not in valid range [{self.base_type.min}, {self.base_type.max}]')

        size_changed = False
        while index >= self.length:
            if (self.base_type != BaseType.STRING or self.array_type is not None) and not self.growable:
                raise Exception('Field is not growable')

            self.encoded_values.append(None)
            size_changed = True

        self.encoded_values[index] = encoded_value

        if size_changed or self.base_type == BaseType.STRING:
            new_size = self.calculate_size()
            if new_size > self.size:
                if not self.growable:
                    raise Exception('Size exceeds fixed field size of $size bytes. Consider making field growable.')
                self.size = new_size

    def encode_value(self, value, sub_field: SubField = None):
        if isinstance(value, str):
            return value

        if value is None:
            encoded_value = self.base_type.invalid_raw_value()
        else:
            scale = self.get_scale(sub_field=sub_field)
            offset = self.get_offset(sub_field=sub_field)
            if isinstance(value, Enum):
                encoded_value = value.value
            elif (scale is None or scale == 1.0) and (offset is None or offset == 0.0):
                encoded_value = int(value)
            else:
                encoded_value = self.scale_offset_value(value, scale, offset)
        return encoded_value

    def read_all_from_bytes(self, bytes_buffer: bytes, endian: Endian = Endian.LITTLE):
        if self.base_type == BaseType.STRING:
            self.read_strings_from_bytes(bytes_buffer)
        else:
            start = 0
            for index in range(len(self.encoded_values)):
                value_bytes = bytes_buffer[start:(start + self.base_type.size)]
                self.read_from_bytes(value_bytes, index, endian=endian)
                start += self.base_type.size

    def read_from_bytes(self, bytes_buffer: bytes, index: int, endian: Endian = Endian.LITTLE):
        if self.base_type == BaseType.STRING:
            raise Exception('Type cannot be string')

        encoded_value = self.get_encoded_value_from_bytes(bytes_buffer, endian=endian)
        self.set_encoded_value(index, encoded_value, check_validity=False)

    def read_strings_from_bytes(self, bytes_buffer: bytes):
        # The number of strings is dynamic and is determined by the number of null
        # terminations in the string container

        string_container = bytes_buffer.decode('utf-8')
        strings = string_container.split('\u0000')
        strings = strings[:-1]
        strings = [x for x in strings if x]
        self.encoded_values = []
        self.encoded_values.extend(strings)

    @staticmethod
    def get_length_from_size(base_type: BaseType, size: int) -> int:
        if base_type == BaseType.STRING:
            return 0 if size == 0 else 1
        else:
            length = size // base_type.size

            if length * base_type.size != size:
                raise Exception('Size is not a multiple of type: size: $size, type: $type')

            return length

    def calculate_size(self) -> int:
        if self.base_type == BaseType.STRING:
            calc_size = 0
            for value in self.encoded_values:
                if isinstance(value, str):
                    calc_size += len(value.encode('utf-8')) + 1
            return calc_size
        else:
            return self.length * self.base_type.size

    def get_encoded_value_from_bytes(self, bytes_buffer: bytes, offset: int = 0, endian: Endian = Endian.LITTLE):
        endian_symbol = '<' if endian == Endian.LITTLE else '>'

        if self.base_type in {BaseType.ENUM, BaseType.UINT8, BaseType.UINT8Z, BaseType.BYTE}:
            value, = struct.unpack_from(f'{endian_symbol}B', bytes_buffer, offset)

        elif self.base_type == BaseType.SINT8:
            value, = struct.unpack_from(f'{endian_symbol}b', bytes_buffer, offset)

        elif self.base_type == BaseType.SINT16:
            value, = struct.unpack_from(f'{endian_symbol}h', bytes_buffer, offset)

        elif self.base_type in {BaseType.UINT16, BaseType.UINT16Z}:
            value, = struct.unpack_from(f'{endian_symbol}H', bytes_buffer, offset)

        elif self.base_type == BaseType.SINT32:
            value, = struct.unpack_from(f'{endian_symbol}i', bytes_buffer, offset)

        elif self.base_type in {BaseType.UINT32, BaseType.UINT32Z}:
            value, = struct.unpack_from(f'{endian_symbol}I', bytes_buffer, offset)

        elif self.base_type == BaseType.SINT64:
            value, = struct.unpack_from(f'{endian_symbol}q', bytes_buffer, offset)

        elif self.base_type in {BaseType.UINT64, BaseType.UINT64Z}:
            value, = struct.unpack_from(f'{endian_symbol}Q', bytes_buffer, offset)

        elif self.base_type == BaseType.FLOAT32:
            value, = struct.unpack_from(f'{endian_symbol}f', bytes_buffer, offset)

        elif self.base_type == BaseType.FLOAT64:
            value, = struct.unpack_from(f'{endian_symbol}d', bytes_buffer, offset)

        elif self.base_type == BaseType.STRING:
            length = len(bytes_buffer) - 1 - offset
            value, = struct.unpack_from(f'{length}s', bytes_buffer, offset)
            value = value.decode('utf-8')
        else:
            value = None

        return value

    def encoded_value_to_bytes(self, encoded_value, endian: Endian = Endian.LITTLE) -> bytes:
        if encoded_value is None:
            raise Exception('Value cannot be None')

        if self.base_type == BaseType.STRING:
            return encoded_value.encode('utf-8') + b'\0'

        endian_symbol = '<' if endian == Endian.LITTLE else '>'
        bytes_buffer = bytearray(b'\0' * self.base_type.size)
        if self.base_type in {BaseType.ENUM, BaseType.UINT8, BaseType.UINT8Z, BaseType.BYTE}:
            struct.pack_into('B', bytes_buffer, 0, encoded_value)

        elif self.base_type == BaseType.SINT8:
            struct.pack_into('b', bytes_buffer, 0, encoded_value)

        elif self.base_type == BaseType.SINT16:
            struct.pack_into(f'{endian_symbol}h', bytes_buffer, 0, encoded_value)

        elif self.base_type in {BaseType.UINT16, BaseType.UINT16Z}:
            struct.pack_into(f'{endian_symbol}H', bytes_buffer, 0, encoded_value)

        elif self.base_type == BaseType.SINT32:
            struct.pack_into(f'{endian_symbol}i', bytes_buffer, 0, encoded_value)

        elif self.base_type in {BaseType.UINT32, BaseType.UINT32Z}:
            struct.pack_into(f'{endian_symbol}I', bytes_buffer, 0, encoded_value)

        elif self.base_type == BaseType.SINT64:
            struct.pack_into(f'{endian_symbol}q', bytes_buffer, 0, encoded_value)

        elif self.base_type in {BaseType.UINT64, BaseType.UINT64Z}:
            struct.pack_into(f'{endian_symbol}Q', bytes_buffer, 0, encoded_value)

        elif self.base_type == BaseType.FLOAT32:
            struct.pack_into(f'{endian_symbol}f', bytes_buffer, 0, encoded_value)

        elif self.base_type == BaseType.FLOAT64:
            struct.pack_into(f'{endian_symbol}d', bytes_buffer, 0, encoded_value)

        return bytes_buffer

    def to_bytes(self, endian: Endian = Endian.LITTLE) -> bytes:
        bytes_buffer = b''
        for value in self.encoded_values:
            bytes_buffer += self.encoded_value_to_bytes(value, endian=endian)

        # sometimes subfields or strings can be less than the allocated field size,
        # so we pad the buffer with 0's to meet the size requirement.
        bytes_buffer = bytes_buffer.ljust(self.size, b'\0')

        return bytes_buffer

    def get_valid_sub_field(self, fields: list) -> Optional[SubField]:
        if not self.sub_fields:
            return None

        for sub_field in self.sub_fields:
            if sub_field.is_valid(fields):
                return sub_field

        return None

    def to_row(self, sub_field: SubField = None) -> list:
        row = []
        values = []

        for i in range(len(self.encoded_values)):
            values.append(self.get_value(index=i, sub_field=sub_field))

        row.append(sub_field.name if sub_field else self.name)

        if len(values) == 1:
            row.append(values[0])
        else:
            values_str = '[' + ','.join([str(v) for v in values]) + ']'
            row.append(values_str)

        row.append(sub_field.units if sub_field else self.units)

        return row
