import argparse
import os
from pathlib import Path

import inflection
import jinja2

from fit_file_faker.vendor.fit_tool import SDK_VERSION
from fit_file_faker.vendor.fit_tool.base_type import BaseType
from fit_file_faker.vendor.fit_tool.field import Field
from fit_file_faker.vendor.fit_tool.gen.profile import Profile, Message

DEFAULT_BUILD_PATH = '../../build'


def parse_args():
    """
    Parse command line arguments.
    """

    parser = argparse.ArgumentParser(description="""
This script creates profile related source files.

EXAMPLE:
    gen.py build

""")
    # parser.add_argument("build_dir")

    return parser.parse_args()


def convert_type_name(name: str) -> str:
    name = name.replace('wkt_', 'workout_')

    if name[0].isdigit():
        name = 'n' + name

    name = inflection.camelize(name, uppercase_first_letter=True)
    # name = inflection.underscore(name)

    if name in ['File', 'Switch']:
        name += 'Type'
    return name


def convert_type_name2(name: str) -> str:
    name = name.replace('wkt_', 'workout_')

    if name[0].isdigit():
        name = 'n' + name

    name = inflection.underscore(name)

    if name in ['File', 'Switch']:
        name += 'Type'
    return name.upper()


RESERVED_WORDS = ['new', 'switch', 'enum']


def convert_value_name(name: str) -> str:
    if name[0].isdigit():
        name = 'n' + name
    # name = inflection.camelize(name, uppercase_first_letter=False)
    name = inflection.underscore(name).upper()

    if name in RESERVED_WORDS:
        name = name + '_'
    return name


def un_title(name: str) -> str:
    name = name[0].lower() + name[1:]
    return name


def field_name_to_class_name(message: Message, field: Field, name: str) -> str:
    name = name.replace('wkt_', 'workout_')

    # if not a common field then prefix the message name so we don't get class naming conflicts
    if field.field_id not in [253, 254]:
        name = message.name + '_' + name

    name = inflection.camelize(name, uppercase_first_letter=True)

    if not name.endswith('Field'):
        name += 'Field'
    return name


RESERVED_PROPERTY_NAMES = {'name', 'local_id', 'global_id'}


def field_name_to_property_name(message: Message, name: str) -> str:
    name = name.replace('wkt_', 'workout_')

    if name[0].isdigit():
        name = 'n' + name

    # name = inflection.camelize(name, uppercase_first_letter=False)
    name = inflection.underscore(name)

    if name in RESERVED_PROPERTY_NAMES:
        name = message.name + '_' + name
        name = inflection.underscore(name)

    return name


def subfield_name_to_property_name(field: Field, name: str) -> str:
    name = name.replace('wkt_', 'workout_')

    if field.name == 'target_value':
        if not name.startswith('target_'):
            name = 'target_' + name

    if name[0].isdigit():
        name = 'n' + name

    name = inflection.underscore(name)

    # if name in RESERVED_PROPERTY_NAMES:
    #     name = message.name + '_' + name
    #     name = inflection.camelize(name, uppercase_first_letter=False)

    return name


def get_type_name_from_field(field: Field):
    if field.base_type.name == 'STRING':
        return 'str'
    elif 'FLOAT' in field.base_type.name or (field.scale and field.scale != 1):
        return 'float'
    else:
        return 'int'


def get_field_property_type_name(profile: Profile, field: Field) -> str:
    if field.type_name:
        if 'bool' in field.type_name:
            type_name = 'bool'
        elif 'date_time' == field.type_name:
            type_name = 'int'
        elif 'fit_base_type' in field.type_name:
            type_name = 'int'

        elif field.base_type == BaseType.ENUM:
            type_name = profile.type_class_name_by_name[field.type_name]
        else:
            type_name = get_type_name_from_field(field)
    else:
        type_name = get_type_name_from_field(field)

    # handle arrays
    if field.array_type is None:
        return type_name
    else:
        if field.base_type.name == 'BYTE':
            return 'bytes'
        if type_name == 'str':
            return 'str'
        else:
            return f'list[{type_name}]'


def main():
    build_path = DEFAULT_BUILD_PATH
    profile_path = os.path.join(build_path, 'profile')
    messages_path = os.path.join(profile_path, 'messages')

    messages_dir = Path(messages_path)
    if messages_dir.exists():
        for p in messages_dir.glob('*.py'):
            p.unlink()
        messages_dir.rmdir()

    profile_dir = Path(profile_path)
    if profile_dir.exists():
        for p in profile_dir.glob('*.py'):
            p.unlink()
        profile_dir.rmdir()

    Path(profile_path).mkdir(parents=True, exist_ok=True)
    Path(messages_path).mkdir(parents=True, exist_ok=True)

    profile = Profile.get_default_profile()

    profile.types_by_name.pop('bool')
    profile.types_by_name.pop('fit_base_type')

    profile_types = list({convert_type_name2(k) for k in profile.types_by_name.keys()})
    profile_types.sort()

    profile.type_class_name_by_name = {k: convert_type_name(k) for k in profile.types_by_name.keys()}

    for message in profile.messages_by_name.values():
        message.field_class_name_by_name = {k: field_name_to_class_name(message, message.fields_by_name[k], k) for k in
                                            message.fields_by_name.keys()}
        message.field_property_name_by_name = {k: field_name_to_property_name(message, k) for k in
                                               message.fields_by_name.keys()}
        message.field_property_type_by_name = {k: get_field_property_type_name(profile, v) for k, v in
                                               message.fields_by_name.items()}
        for field in message.fields_by_name.values():
            field.subfield_property_name_by_name = {}
            field.subfield_property_type_by_name = {}
            for sub_field in field.sub_fields:
                ref_field_key = list(sub_field.ref_field_map.keys())[0]
                sub_field.ref_field = message.fields_by_name[ref_field_key]
                sub_field.ref_field_values = sub_field.ref_field_map[ref_field_key]
                field.subfield_property_name_by_name[sub_field.name] = subfield_name_to_property_name(field,
                                                                                                      sub_field.name)
                field.subfield_property_type_by_name[sub_field.name] = get_field_property_type_name(profile, sub_field)

    for k, v in profile.types_by_name.items():
        profile_type = profile.types_by_name[k]
        profile_type.values_by_name = {convert_value_name(k): v for k, v in profile_type.values_by_name.items()}

    env = jinja2.Environment(loader=jinja2.FileSystemLoader('..'), )

    #
    # Gen profile_type.py
    #
    template = env.get_template('gen/templates/template_profile_type.jinja')
    rendering = template.render(profile=profile, profile_types=profile_types,
                                sdk_version=SDK_VERSION)
    filename = os.path.join(profile_path, 'profile_type.py')
    with (open(filename, 'w')) as file_out:
        file_out.write(rendering)

    for name, message in profile.messages_by_name.items():
        template = env.get_template('gen/templates/template_message.jinja')
        rendering = template.render(profile=profile, sdk_version=SDK_VERSION,
                                    class_name=inflection.camelize(message.name + '_message'),
                                    message=message)
        filename = os.path.join(messages_path, f"{inflection.underscore(message.name + '_message')}.py")
        with (open(filename, 'w')) as file_out:
            file_out.write(rendering)

    message_file_names = [inflection.underscore(message_name + '_message') for message_name in
                          profile.messages_by_name.keys()]
    message_class_names = [inflection.camelize(message_name + '_message') for message_name in
                           profile.messages_by_name.keys()]

    template = env.get_template('gen/templates/template_message_factory.jinja')

    message_names = zip(message_class_names, message_file_names)
    rendering = template.render(profile=profile, sdk_version=SDK_VERSION,
                                message_names=message_names, message_class_names=message_class_names)
    filename = os.path.join(messages_path, f"message_factory.py")
    with (open(filename, 'w')) as file_out:
        file_out.write(rendering)

    template = env.get_template('gen/templates/template_common_fields.jinja')
    rendering = template.render(profile=profile, sdk_version=SDK_VERSION)
    filename = os.path.join(messages_path, f"common_fields.py")
    with (open(filename, 'w')) as file_out:
        file_out.write(rendering)


if __name__ == "__main__":
    main()
