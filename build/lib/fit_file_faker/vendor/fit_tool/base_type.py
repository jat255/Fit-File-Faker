from enum import Enum, unique
from typing import Optional


@unique
class BaseType(Enum):
    ENUM = 0
    SINT8 = 1
    UINT8 = 2
    SINT16 = 131
    UINT16 = 132
    SINT32 = 133
    UINT32 = 134
    STRING = 7
    FLOAT32 = 136
    FLOAT64 = 137
    UINT8Z = 10
    UINT16Z = 139
    UINT32Z = 140
    BYTE = 13
    SINT64 = 142
    UINT64 = 143
    UINT64Z = 144

    @property
    def size(self) -> int:
        if self == BaseType.ENUM:
            return 1
        elif self == BaseType.SINT8:
            return 1
        elif self == BaseType.UINT8:
            return 1
        elif self == BaseType.SINT16:
            return 2
        elif self == BaseType.UINT16:
            return 2
        elif self == BaseType.SINT32:
            return 4
        elif self == BaseType.UINT32:
            return 4
        elif self == BaseType.STRING:
            return 1
        elif self == BaseType.FLOAT32:
            return 4
        elif self == BaseType.FLOAT64:
            return 8
        elif self == BaseType.UINT8Z:
            return 1
        elif self == BaseType.UINT16Z:
            return 2
        elif self == BaseType.UINT32Z:
            return 4
        elif self == BaseType.BYTE:
            return 1
        elif self == BaseType.SINT64:
            return 8
        elif self == BaseType.UINT64:
            return 8
        elif self == BaseType.UINT64Z:
            return 8
        else:
            return 0

    def is_integer(self) -> bool:
        if self in [BaseType.SINT8, BaseType.UINT8, BaseType.SINT16, BaseType.UINT16, BaseType.UINT16Z, BaseType.SINT32,
                    BaseType.UINT32, BaseType.UINT32Z, BaseType.SINT64, BaseType.UINT64, BaseType.UINT64Z]:
            return True
        else:
            return False

    def is_signed_integer(self) -> bool:
        if self in [BaseType.SINT8, BaseType.SINT16, BaseType.SINT32, BaseType.SINT64]:
            return True
        else:
            return False

    def is_big(self) -> bool:
        if self in [BaseType.SINT64, BaseType.UINT64, BaseType.UINT64Z]:
            return True
        else:
            return False

    def is_string(self) -> bool:
        return self == BaseType.STRING

    def is_float(self) -> bool:
        if self in [BaseType.FLOAT32, BaseType.FLOAT64]:
            return True
        else:
            return False

    def is_valid(self, value) -> bool:
        if value is None:
            return False

        if self.min is None or self.max is None:
            return True

        return self.min <= value <= self.max

    def invalid_raw_value(self) -> int:
        if self == BaseType.ENUM:
            return 0xff
        elif self == BaseType.SINT8:
            return 0x7f
        elif self == BaseType.UINT8:
            return 0xff
        elif self == BaseType.SINT16:
            return 0x7fff
        elif self == BaseType.UINT16:
            return 0xffff
        elif self == BaseType.SINT32:
            return 0x7fffffff
        elif self == BaseType.UINT32:
            return 0xffffffff
        elif self == BaseType.STRING:
            return 0x00
        elif self == BaseType.FLOAT32:
            return 0xffffffff
        elif self == BaseType.FLOAT64:
            return 0xffffffffffffffff
        elif self == BaseType.UINT8Z:
            return 0x00
        elif self == BaseType.UINT16Z:
            return 0x0000
        elif self == BaseType.UINT32Z:
            return 0x00000000
        elif self == BaseType.BYTE:
            return 0xff
        elif self == BaseType.SINT64:
            return 0x7fffffffffffffff
        elif self == BaseType.UINT64:
            return 0xffffffffffffffff
        elif self == BaseType.UINT64Z:
            return 0x0000000000000000
        else:
            return 0

    @property
    def max(self) -> Optional[int]:
        if self == BaseType.ENUM:
            return 0xff
        elif self == BaseType.SINT8:
            return 0x7f
        elif self == BaseType.UINT8:
            return 0xff
        elif self == BaseType.SINT16:
            return 0x7fff
        elif self == BaseType.UINT16:
            return 0xffff
        elif self == BaseType.SINT32:
            return 0x7fffffff
        elif self == BaseType.UINT32:
            return 0xffffffff
        elif self == BaseType.STRING:
            return None
        elif self == BaseType.FLOAT32:
            return None
        elif self == BaseType.FLOAT64:
            return None
        elif self == BaseType.UINT8Z:
            return 0xff
        elif self == BaseType.UINT16Z:
            return 0xffff
        elif self == BaseType.UINT32Z:
            return 0xffffffff
        elif self == BaseType.BYTE:
            return 0xff
        elif self == BaseType.SINT64:
            return 0x7fffffffffffffff
        elif self == BaseType.UINT64:
            return 0xffffffffffffffff
        elif self == BaseType.UINT64Z:
            return 0xffffffffffffffff
        else:
            return 0

    @property
    def min(self) -> Optional[int]:
        if self == BaseType.ENUM:
            return 0x00
        elif self == BaseType.SINT8:
            return -0x80
        elif self == BaseType.UINT8:
            return 0x00
        elif self == BaseType.SINT16:
            return -0x8000
        elif self == BaseType.UINT16:
            return 0x0000
        elif self == BaseType.SINT32:
            return -0x80000000
        elif self == BaseType.UINT32:
            return 0x00000000
        elif self == BaseType.STRING:
            return None
        elif self == BaseType.FLOAT32:
            return None
        elif self == BaseType.FLOAT64:
            return None
        elif self == BaseType.UINT8Z:
            return 0x00
        elif self == BaseType.UINT16Z:
            return 0x0000
        elif self == BaseType.UINT32Z:
            return 0x00000000
        elif self == BaseType.BYTE:
            return 0x00
        elif self == BaseType.SINT64:
            return -0x8000000000000000
        elif self == BaseType.UINT64:
            return 0x0000000000000000
        elif self == BaseType.UINT64Z:
            return 0x0000000000000000
        else:
            return None

    @classmethod
    def from_name(cls, name: str):
        if name == 'enum':
            return cls.ENUM
        elif name == 'sint8':
            return cls.SINT8
        elif name == 'uint8':
            return BaseType.UINT8
        elif name == 'sint16':
            return BaseType.SINT16
        elif name == 'uint16':
            return BaseType.UINT16
        elif name == 'sint32':
            return BaseType.SINT32
        elif name == 'uint32':
            return BaseType.UINT32
        elif name == 'string':
            return BaseType.STRING
        elif name == 'float32':
            return BaseType.FLOAT32
        elif name == 'float64':
            return BaseType.FLOAT64
        elif name == 'uint8z':
            return BaseType.UINT8Z
        elif name == 'uint16z':
            return BaseType.UINT16Z
        elif name == 'uint32z':
            return BaseType.UINT32Z
        elif name == 'byte':
            return BaseType.BYTE
        elif name == 'sint64':
            return BaseType.SINT64
        elif name == 'uint64':
            return BaseType.UINT64
        elif name == 'uint64z':
            return BaseType.UINT64Z
        else:
            return None


class FieldType:

    def __init__(self, name: str, base_type: BaseType):
        self.name = name
        self.base_type = base_type
        self.names_by_value = {}
        self.values_by_name = {}

    def add_value(self, name, value):
        self.names_by_value[value] = name
        self.values_by_name[name] = value

    def get_value_by_name(self, name):
        return self.values_by_name.get(name)

    def get_name_by_value(self, value):
        return self.names_by_value.get(value)
