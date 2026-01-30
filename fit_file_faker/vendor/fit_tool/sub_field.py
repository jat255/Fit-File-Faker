from typing import Dict as dict
from typing import List as list

from fit_file_faker.vendor.fit_tool.base_type import BaseType
from fit_file_faker.vendor.fit_tool.field_component import FieldComponent


class SubField:

    def __init__(self, name: str = 'unknown', base_type: BaseType = BaseType.ENUM, scale: float = 1.0,
                 offset: float = 1.0, units: str = '', reference_map: dict[int, list[int]] = None,
                 components=None):
        if components is None:
            components = []
        self.name = name
        self.base_type = base_type
        self.scale = scale
        self.offset = offset
        self.units = units

        self.reference_map = reference_map or {}
        self.components = components or []

    def add_component(self, component: FieldComponent):
        self.components.add(component)

    def is_valid(self, fields: list) -> bool:
        for field_id in self.reference_map:
            field = next((x for x in fields if x.field_id == field_id), None)
            if field is None or field.is_not_valid():
                continue

            if self.reference_map[field_id] and field.get_value() in self.reference_map:
                return True

        return False
