import os.path

from openpyxl import load_workbook

from fit_file_faker.vendor.fit_tool import SDK_VERSION
from fit_file_faker.vendor.fit_tool.base_type import FieldType, BaseType
from fit_file_faker.vendor.fit_tool.field import Field, ArrayType


class Message:

    def __init__(self, id_, name):
        self.id = id_
        self.name = name
        self.fields_by_id = {}
        self.fields_by_name = {}

    def add_field(self, field: Field):
        self.fields_by_id[field.field_id] = field
        self.fields_by_name[field.name] = field

    def get_field_by_name(self, name):
        return self.fields_by_name.get(name)

    def get_field_by_id(self, id_):
        return self.fields_by_id.get(id_)

    def get_fields(self):
        return list(self.fields_by_id.values())


def parse_array_field(value):
    if value is None:
        return None, None
    if value == '[N]':
        return ArrayType.VARIABLE, None

    return ArrayType.FIXED, int(value[1:-1])


class Profile:

    def __init__(self):
        self.messages_by_id = {}
        self.messages_by_name = {}
        self.types_by_name = {}
        self.type_class_name_by_name = {}

    def get_message_by_name(self, name):
        return self.messages_by_name.get(name)

    def get_message_by_id(self, id_):
        return self.messages_by_id.get(id_)

    def get_type_by_name(self, name):

        # Next check if it is derived type
        type_ = self.types_by_name.get(name)
        if not type_:
            raise Exception('Type: {} not found in profile.'.format(name))
        return type_

    def add_message(self, message):
        self.messages_by_id[message.id] = message
        self.messages_by_name[message.name] = message

    def add_type(self, type_: FieldType):
        self.types_by_name[type_.name] = type_

    # def add_dev_field(self, record):
    #     # array = None
    #     # components = None
    #     # bits = None
    #     # accumulate = None
    #     # fit_base_unit_id = None
    #     # native_mesg_num = None
    #     # native_field_num = None
    #
    #     data = {}
    #     for field in record.fields:
    #         data[field.name] = field.value
    #
    #     developer_data_index = int(data['developer_data_index'])
    #     message = self.get_message_by_id(developer_data_index)
    #
    #     if not message:
    #         message = Message(developer_data_index,
    #                           'dev-' + str(developer_data_index))
    #         self.add_message(message)
    #
    #     # First check if it is a base type
    #     # base_type = BASE_TYPE_BY_ID.get(data.get('fit_base_type_id'))
    #     base_type = None
    #
    #     field = Field(field_id=data.get('field_definition_number'),
    #                   name=data.get('field_name'),
    #                   base_type=base_type,
    #                   scale=data.get('scale', 1),
    #                   offset=data.get('offset', 0),
    #                   units=data.get('units')
    #                   )
    #     message.add_field(field)

    def get_messages(self):
        return list(self.messages_by_id.values())

    @classmethod
    def get_default_profile(cls):

        xlsx_filename = os.path.join(os.path.dirname(__file__), f'Profile_{SDK_VERSION}.xlsx')
        print(f'Loading profile from {xlsx_filename}...')
        profile = Profile.load(xlsx_filename)

        return profile

    @classmethod
    def load(cls, filename):
        profile = cls()
        wb = load_workbook(filename=filename, read_only=True, data_only=True)

        #
        # Parse the Types worksheet
        #
        ws = wb['Types']
        current_type = None
        for index, row in enumerate(ws.rows):
            if index == 0:
                continue

            type_name = row[0].value
            type_base_type_name = row[1].value

            if not type_name and not current_type:
                continue

            if type_name:
                # We are on a new type. Create it and start adding values to
                # it.
                type_base_type = BaseType.from_name(type_base_type_name)
                if not type_base_type:
                    # TODO: add proper logging
                    print(
                        'Warning: Unknown base_type {}'.format(type_base_type))
                    continue
                current_type = FieldType(type_name, type_base_type)
                profile.add_type(current_type)
            else:
                name = row[2].value

                if name:
                    value = row[3].value
                    if isinstance(value, str):
                        value = int(value, 0)
                    current_type.add_value(name, value)

        profile.add_type(FieldType('bool', BaseType.from_name('uint8')))

        #
        # Parse the Messages worksheet
        #
        ws = wb['Messages']
        current_message = None
        for index, row in enumerate(ws.rows):
            if index == 0:
                continue

            message_name = row[0].value

            if not message_name and not current_message:
                continue

            if message_name:
                # We are on a new message. Create it and start adding values to
                # it.
                message_id = profile.get_type_by_name(
                    'mesg_num').values_by_name[message_name]

                current_message = Message(message_id, message_name)
                profile.add_message(current_message)
            else:
                field_id = row[1].value
                field_name = row[2].value
                field_type_name = row[3].value
                array_type, array_fixed_length = parse_array_field(row[4].value)
                # components = row[5].value
                scale = row[6].value if row[6].value is not None else 1

                # Components are not supported yet
                if isinstance(scale, str):
                    scale = 1

                offset = row[7].value if row[7].value is not None else 0
                units = row[8].value
                if units:
                    units = units.replace('\n', '')

                if units == 'semicircles':
                    units = 'degrees'
                    scale = 2147483648 / 180.0

                if field_type_name == 'date_time':
                    units = 'ms'
                    scale = 1.0 / 1000.0
                    offset = -631065600000

                # bits = row[9].value
                # accumulate = row[10].value
                raw_ref_field_names = row[11].value
                raw_ref_field_values = row[12].value

                ref_field_names = []
                if raw_ref_field_names:
                    ref_field_names = [name.strip()
                                       for name in raw_ref_field_names.split(',')]

                ref_field_values = []
                if raw_ref_field_values:
                    ref_field_values = [value.strip()
                                        for value in raw_ref_field_values.split(',')]

                if field_name == 'custom_target_power_high' or field_name == 'custom_target_power_low':
                    ref_field_names.append('target_type')
                    ref_field_values.append('power_3s')

                    ref_field_names.append('target_type')
                    ref_field_values.append('power_10s')

                    ref_field_names.append('target_type')
                    ref_field_values.append('power_30s')

                    ref_field_names.append('target_type')
                    ref_field_values.append('power_lap')

                if field_name == 'custom_target_heart_rate_high' or field_name == 'custom_target_heart_rate_low':
                    ref_field_names.append('target_type')
                    ref_field_values.append('heart_rate_lap')

                if field_name == 'custom_target_speed_high' or field_name == 'custom_target_speed_low':
                    ref_field_names.append('target_type')
                    ref_field_values.append('speed_lap')

                # comment = row[13].value
                if field_id is not None or field_name is not None:

                    # First check if it is a base type
                    base_type_ = BaseType.from_name(field_type_name)

                    # if not see if it is a derived type in the profile
                    if base_type_:
                        type_ = None
                    else:
                        type_ = profile.get_type_by_name(field_type_name)
                        base_type_ = type_.base_type

                    ref_field_map = {}
                    for ref_index, ref_name in enumerate(ref_field_names):
                        if ref_name in ref_field_map:
                            ref_field_map[ref_name].append(ref_field_values[ref_index])
                        else:
                            ref_field_map[ref_name] = [ref_field_values[ref_index]]

                    field_or_subfield = Field(field_id=field_id,
                                              name=field_name,
                                              base_type=base_type_,
                                              scale=scale,
                                              offset=offset,
                                              units=units,
                                              ref_field_map=ref_field_map,
                                              type_name=field_type_name,
                                              array_type=array_type,
                                              array_fixed_length=array_fixed_length
                                              )

                    # todo: hack for now, should add to class
                    field_or_subfield.type_ = type_

                    is_field = field_id is not None

                    if is_field:
                        field = field_or_subfield
                        current_message.add_field(field)
                    else:
                        subfield = field_or_subfield
                        field.sub_fields.append(subfield)

        cls._resolve_subfield_references(profile)

        wb.close()

        return profile

    @staticmethod
    def _resolve_subfield_references(profile):
        for _, message in profile.messages_by_id.items():
            for _, field in message.fields_by_id.items():
                for subfield in field.sub_fields:
                    if subfield.ref_field_map:
                        resolved_map = {}
                        for key, values in subfield.ref_field_map.items():
                            field = message.get_field_by_name(key)
                            resolved_values = []
                            for item in values:
                                resolved_value = profile.get_type_by_name(field.type_name).get_value_by_name(item)
                                resolved_values.append(resolved_value)
                            resolved_map[key] = resolved_values

                        subfield.ref_field_map = resolved_map

    def create_field(self, msg_name, field_name, value, length=1):
        msg = self.get_message_by_name(msg_name)
        clz = msg.get_field_by_name(field_name)
        clz.length = length
        field = clz(value=value)
        return field

    def create_field_definition(self, msg_name, field_name, length=1):
        msg = self.get_message_by_name(msg_name)
        return msg.get_field_by_name(field_name).to_field_definition(length=length)
