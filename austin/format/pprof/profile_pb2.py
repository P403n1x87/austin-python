# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: profile.proto

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database


# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='profile.proto',
  package='perftools.profiles',
  syntax='proto3',
  serialized_options=b'\n\035com.google.perftools.profilesB\014ProfileProto',
  create_key=_descriptor._internal_create_key,
  serialized_pb=b'\n\rprofile.proto\x12\x12perftools.profiles\"\xd5\x03\n\x07Profile\x12\x32\n\x0bsample_type\x18\x01 \x03(\x0b\x32\x1d.perftools.profiles.ValueType\x12*\n\x06sample\x18\x02 \x03(\x0b\x32\x1a.perftools.profiles.Sample\x12,\n\x07mapping\x18\x03 \x03(\x0b\x32\x1b.perftools.profiles.Mapping\x12.\n\x08location\x18\x04 \x03(\x0b\x32\x1c.perftools.profiles.Location\x12.\n\x08\x66unction\x18\x05 \x03(\x0b\x32\x1c.perftools.profiles.Function\x12\x14\n\x0cstring_table\x18\x06 \x03(\t\x12\x13\n\x0b\x64rop_frames\x18\x07 \x01(\x03\x12\x13\n\x0bkeep_frames\x18\x08 \x01(\x03\x12\x12\n\ntime_nanos\x18\t \x01(\x03\x12\x16\n\x0e\x64uration_nanos\x18\n \x01(\x03\x12\x32\n\x0bperiod_type\x18\x0b \x01(\x0b\x32\x1d.perftools.profiles.ValueType\x12\x0e\n\x06period\x18\x0c \x01(\x03\x12\x0f\n\x07\x63omment\x18\r \x03(\x03\x12\x1b\n\x13\x64\x65\x66\x61ult_sample_type\x18\x0e \x01(\x03\"\'\n\tValueType\x12\x0c\n\x04type\x18\x01 \x01(\x03\x12\x0c\n\x04unit\x18\x02 \x01(\x03\"V\n\x06Sample\x12\x13\n\x0blocation_id\x18\x01 \x03(\x04\x12\r\n\x05value\x18\x02 \x03(\x03\x12(\n\x05label\x18\x03 \x03(\x0b\x32\x19.perftools.profiles.Label\"@\n\x05Label\x12\x0b\n\x03key\x18\x01 \x01(\x03\x12\x0b\n\x03str\x18\x02 \x01(\x03\x12\x0b\n\x03num\x18\x03 \x01(\x03\x12\x10\n\x08num_unit\x18\x04 \x01(\x03\"\xdd\x01\n\x07Mapping\x12\n\n\x02id\x18\x01 \x01(\x04\x12\x14\n\x0cmemory_start\x18\x02 \x01(\x04\x12\x14\n\x0cmemory_limit\x18\x03 \x01(\x04\x12\x13\n\x0b\x66ile_offset\x18\x04 \x01(\x04\x12\x10\n\x08\x66ilename\x18\x05 \x01(\x03\x12\x10\n\x08\x62uild_id\x18\x06 \x01(\x03\x12\x15\n\rhas_functions\x18\x07 \x01(\x08\x12\x15\n\rhas_filenames\x18\x08 \x01(\x08\x12\x18\n\x10has_line_numbers\x18\t \x01(\x08\x12\x19\n\x11has_inline_frames\x18\n \x01(\x08\"v\n\x08Location\x12\n\n\x02id\x18\x01 \x01(\x04\x12\x12\n\nmapping_id\x18\x02 \x01(\x04\x12\x0f\n\x07\x61\x64\x64ress\x18\x03 \x01(\x04\x12&\n\x04line\x18\x04 \x03(\x0b\x32\x18.perftools.profiles.Line\x12\x11\n\tis_folded\x18\x05 \x01(\x08\")\n\x04Line\x12\x13\n\x0b\x66unction_id\x18\x01 \x01(\x04\x12\x0c\n\x04line\x18\x02 \x01(\x03\"_\n\x08\x46unction\x12\n\n\x02id\x18\x01 \x01(\x04\x12\x0c\n\x04name\x18\x02 \x01(\x03\x12\x13\n\x0bsystem_name\x18\x03 \x01(\x03\x12\x10\n\x08\x66ilename\x18\x04 \x01(\x03\x12\x12\n\nstart_line\x18\x05 \x01(\x03\x42-\n\x1d\x63om.google.perftools.profilesB\x0cProfileProtob\x06proto3'
)




_PROFILE = _descriptor.Descriptor(
  name='Profile',
  full_name='perftools.profiles.Profile',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='sample_type', full_name='perftools.profiles.Profile.sample_type', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='sample', full_name='perftools.profiles.Profile.sample', index=1,
      number=2, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='mapping', full_name='perftools.profiles.Profile.mapping', index=2,
      number=3, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='location', full_name='perftools.profiles.Profile.location', index=3,
      number=4, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='function', full_name='perftools.profiles.Profile.function', index=4,
      number=5, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='string_table', full_name='perftools.profiles.Profile.string_table', index=5,
      number=6, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='drop_frames', full_name='perftools.profiles.Profile.drop_frames', index=6,
      number=7, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='keep_frames', full_name='perftools.profiles.Profile.keep_frames', index=7,
      number=8, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='time_nanos', full_name='perftools.profiles.Profile.time_nanos', index=8,
      number=9, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='duration_nanos', full_name='perftools.profiles.Profile.duration_nanos', index=9,
      number=10, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='period_type', full_name='perftools.profiles.Profile.period_type', index=10,
      number=11, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='period', full_name='perftools.profiles.Profile.period', index=11,
      number=12, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='comment', full_name='perftools.profiles.Profile.comment', index=12,
      number=13, type=3, cpp_type=2, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='default_sample_type', full_name='perftools.profiles.Profile.default_sample_type', index=13,
      number=14, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=38,
  serialized_end=507,
)


_VALUETYPE = _descriptor.Descriptor(
  name='ValueType',
  full_name='perftools.profiles.ValueType',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='type', full_name='perftools.profiles.ValueType.type', index=0,
      number=1, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='unit', full_name='perftools.profiles.ValueType.unit', index=1,
      number=2, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=509,
  serialized_end=548,
)


_SAMPLE = _descriptor.Descriptor(
  name='Sample',
  full_name='perftools.profiles.Sample',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='location_id', full_name='perftools.profiles.Sample.location_id', index=0,
      number=1, type=4, cpp_type=4, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='value', full_name='perftools.profiles.Sample.value', index=1,
      number=2, type=3, cpp_type=2, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='label', full_name='perftools.profiles.Sample.label', index=2,
      number=3, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=550,
  serialized_end=636,
)


_LABEL = _descriptor.Descriptor(
  name='Label',
  full_name='perftools.profiles.Label',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='key', full_name='perftools.profiles.Label.key', index=0,
      number=1, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='str', full_name='perftools.profiles.Label.str', index=1,
      number=2, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='num', full_name='perftools.profiles.Label.num', index=2,
      number=3, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='num_unit', full_name='perftools.profiles.Label.num_unit', index=3,
      number=4, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=638,
  serialized_end=702,
)


_MAPPING = _descriptor.Descriptor(
  name='Mapping',
  full_name='perftools.profiles.Mapping',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='id', full_name='perftools.profiles.Mapping.id', index=0,
      number=1, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='memory_start', full_name='perftools.profiles.Mapping.memory_start', index=1,
      number=2, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='memory_limit', full_name='perftools.profiles.Mapping.memory_limit', index=2,
      number=3, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='file_offset', full_name='perftools.profiles.Mapping.file_offset', index=3,
      number=4, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='filename', full_name='perftools.profiles.Mapping.filename', index=4,
      number=5, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='build_id', full_name='perftools.profiles.Mapping.build_id', index=5,
      number=6, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='has_functions', full_name='perftools.profiles.Mapping.has_functions', index=6,
      number=7, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='has_filenames', full_name='perftools.profiles.Mapping.has_filenames', index=7,
      number=8, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='has_line_numbers', full_name='perftools.profiles.Mapping.has_line_numbers', index=8,
      number=9, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='has_inline_frames', full_name='perftools.profiles.Mapping.has_inline_frames', index=9,
      number=10, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=705,
  serialized_end=926,
)


_LOCATION = _descriptor.Descriptor(
  name='Location',
  full_name='perftools.profiles.Location',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='id', full_name='perftools.profiles.Location.id', index=0,
      number=1, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='mapping_id', full_name='perftools.profiles.Location.mapping_id', index=1,
      number=2, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='address', full_name='perftools.profiles.Location.address', index=2,
      number=3, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='line', full_name='perftools.profiles.Location.line', index=3,
      number=4, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='is_folded', full_name='perftools.profiles.Location.is_folded', index=4,
      number=5, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=928,
  serialized_end=1046,
)


_LINE = _descriptor.Descriptor(
  name='Line',
  full_name='perftools.profiles.Line',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='function_id', full_name='perftools.profiles.Line.function_id', index=0,
      number=1, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='line', full_name='perftools.profiles.Line.line', index=1,
      number=2, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=1048,
  serialized_end=1089,
)


_FUNCTION = _descriptor.Descriptor(
  name='Function',
  full_name='perftools.profiles.Function',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='id', full_name='perftools.profiles.Function.id', index=0,
      number=1, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='name', full_name='perftools.profiles.Function.name', index=1,
      number=2, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='system_name', full_name='perftools.profiles.Function.system_name', index=2,
      number=3, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='filename', full_name='perftools.profiles.Function.filename', index=3,
      number=4, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='start_line', full_name='perftools.profiles.Function.start_line', index=4,
      number=5, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=1091,
  serialized_end=1186,
)

_PROFILE.fields_by_name['sample_type'].message_type = _VALUETYPE
_PROFILE.fields_by_name['sample'].message_type = _SAMPLE
_PROFILE.fields_by_name['mapping'].message_type = _MAPPING
_PROFILE.fields_by_name['location'].message_type = _LOCATION
_PROFILE.fields_by_name['function'].message_type = _FUNCTION
_PROFILE.fields_by_name['period_type'].message_type = _VALUETYPE
_SAMPLE.fields_by_name['label'].message_type = _LABEL
_LOCATION.fields_by_name['line'].message_type = _LINE
DESCRIPTOR.message_types_by_name['Profile'] = _PROFILE
DESCRIPTOR.message_types_by_name['ValueType'] = _VALUETYPE
DESCRIPTOR.message_types_by_name['Sample'] = _SAMPLE
DESCRIPTOR.message_types_by_name['Label'] = _LABEL
DESCRIPTOR.message_types_by_name['Mapping'] = _MAPPING
DESCRIPTOR.message_types_by_name['Location'] = _LOCATION
DESCRIPTOR.message_types_by_name['Line'] = _LINE
DESCRIPTOR.message_types_by_name['Function'] = _FUNCTION
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

Profile = _reflection.GeneratedProtocolMessageType('Profile', (_message.Message,), {
  'DESCRIPTOR' : _PROFILE,
  '__module__' : 'profile_pb2'
  # @@protoc_insertion_point(class_scope:perftools.profiles.Profile)
  })
_sym_db.RegisterMessage(Profile)

ValueType = _reflection.GeneratedProtocolMessageType('ValueType', (_message.Message,), {
  'DESCRIPTOR' : _VALUETYPE,
  '__module__' : 'profile_pb2'
  # @@protoc_insertion_point(class_scope:perftools.profiles.ValueType)
  })
_sym_db.RegisterMessage(ValueType)

Sample = _reflection.GeneratedProtocolMessageType('Sample', (_message.Message,), {
  'DESCRIPTOR' : _SAMPLE,
  '__module__' : 'profile_pb2'
  # @@protoc_insertion_point(class_scope:perftools.profiles.Sample)
  })
_sym_db.RegisterMessage(Sample)

Label = _reflection.GeneratedProtocolMessageType('Label', (_message.Message,), {
  'DESCRIPTOR' : _LABEL,
  '__module__' : 'profile_pb2'
  # @@protoc_insertion_point(class_scope:perftools.profiles.Label)
  })
_sym_db.RegisterMessage(Label)

Mapping = _reflection.GeneratedProtocolMessageType('Mapping', (_message.Message,), {
  'DESCRIPTOR' : _MAPPING,
  '__module__' : 'profile_pb2'
  # @@protoc_insertion_point(class_scope:perftools.profiles.Mapping)
  })
_sym_db.RegisterMessage(Mapping)

Location = _reflection.GeneratedProtocolMessageType('Location', (_message.Message,), {
  'DESCRIPTOR' : _LOCATION,
  '__module__' : 'profile_pb2'
  # @@protoc_insertion_point(class_scope:perftools.profiles.Location)
  })
_sym_db.RegisterMessage(Location)

Line = _reflection.GeneratedProtocolMessageType('Line', (_message.Message,), {
  'DESCRIPTOR' : _LINE,
  '__module__' : 'profile_pb2'
  # @@protoc_insertion_point(class_scope:perftools.profiles.Line)
  })
_sym_db.RegisterMessage(Line)

Function = _reflection.GeneratedProtocolMessageType('Function', (_message.Message,), {
  'DESCRIPTOR' : _FUNCTION,
  '__module__' : 'profile_pb2'
  # @@protoc_insertion_point(class_scope:perftools.profiles.Function)
  })
_sym_db.RegisterMessage(Function)


DESCRIPTOR._options = None
# @@protoc_insertion_point(module_scope)
