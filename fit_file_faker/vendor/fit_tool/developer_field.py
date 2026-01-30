from typing import List as list

from fit_file_faker.vendor.fit_tool.base_type import BaseType
from fit_file_faker.vendor.fit_tool.field import Field
from fit_file_faker.vendor.fit_tool.field_component import FieldComponent
from fit_file_faker.vendor.fit_tool.sub_field import SubField


class DeveloperField(Field):
    def __init__(self, field_id: int = 0, name: str = '', base_type: BaseType = BaseType.ENUM, offset: float = None,
                 scale: float = None, units: str = '', is_accumulated: bool = False,
                 is_expanded_field=False, sub_fields: list[SubField] = None, components: list[FieldComponent] = None,
                 size: int = 0, growable: bool = False, type_name: str = '', developer_data_index: int = 0):
        super().__init__(field_id=field_id, name=name, base_type=base_type, offset=offset, scale=scale,
                         units=units, is_accumulated=is_accumulated, is_expanded_field=is_expanded_field,
                         sub_fields=sub_fields, components=components, size=size, growable=growable,
                         type_name=type_name)
        self.developer_data_index = developer_data_index

    @classmethod
    def from_developer_field(cls, other, size: int = None):
        size_ = size if size is not None else other.size
        return cls(field_id=other.field_id, name=other.name, base_type=other.base_type, offset=other.offset,
                   scale=other.scale, units=other.units, is_accumulated=other.is_accumulated,
                   is_expanded_field=other.is_expanded_field, sub_fields=other.sub_fields, components=other.components,
                   size=size_, growable=other.growable, type_name=other.type_name,
                   developer_data_index=other.developer_data_index)
