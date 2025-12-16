import os
import sys
import re
import argparse
from dataclasses import dataclass
from pprint import pprint
from google.protobuf import descriptor_pb2
from jinja2 import Environment, FileSystemLoader
from typing import Dict, List
from . import gen_const 

jinja_env = Environment(
    loader=FileSystemLoader(searchpath=['./src/pbdecoder_gen/template', './template']),
)

"""
BL = Sequential Parser (Baseline)
TPP = Two-Pass Parallel Parser
SPP = Speculative Parallel Parser
"""
NAMESPACE_BL = "BL"
NAMESPACE_TPP = "TPP"
NAMESPACE_SPP = "SPP"

prototype_to_cpptype = {
    "uint32": "uint32_t",
    "uint64": "uint64_t",
    "int32": "int32_t",
    "int64": "int64_t",
    "bool": "bool",
    "string": "std::string",
    "bytes": "std::string",
    "double": "double",
    "float": "float",
}

wiretype_to_prototype = {
    0:{"uint32", "int32", "uint64", "int64", "bool"},
    1:{"double"},
    5:{"float"},
}

prototype_to_wiretype = {proto: key for key, protos in wiretype_to_prototype.items() for proto in protos}

partial_parse_templates = {
    0: {"_uint32", "_int32", "_uint64", "_int64", "_bool"},
    1: {"_double", "_float"},
    2: {"_uint32_array", "_int32_array", "_uint64_array", "_int64_array", "_bool_array"},
    3: {"_double_array", "_float_array"},
    4: {"_string", "_bytes"},
}

@dataclass
class Field:
    field_id: int
    name: str
    is_repeated: bool
    is_embedded_message: bool
    proto_type: str

    @property
    def cpp_type_single(self) -> str:
        if self.is_embedded_message:
            return self.proto_type + "*"
        return prototype_to_cpptype[self.proto_type] 

    @property
    def cpp_type(self) -> str:
        if self.is_repeated:
            return f"std::vector<{self.cpp_type_single}>"
        else:
            return self.cpp_type_single

    @property
    def wire_type(self) -> int:
        if self.is_repeated or self.proto_type in ["string", "bytes"] or self.is_embedded_message:
            return 2
        if self.proto_type in wiretype_to_prototype[1]:
            return 1
        if self.proto_type in wiretype_to_prototype[5]:
            return 5
        return 0
    
    @property
    def tag(self) -> int:
        return (self.field_id << 3) | self.wire_type
    
    @property
    def cpp_type_default_value(self):
        if self.is_repeated:
            return None
        if self.is_embedded_message:
            return "nullptr"
        if self.cpp_type in ["int32_t", "int64_t", "uint32_t", "uint64_t", "double", "float"]:
            return "0"
        if self.cpp_type in ["bool"]:
            return "false"
        return None
    
    @property
    def ptype(self):
        '''
        only used in Speculative Parsing
        '''
        if (self.proto_type in wiretype_to_prototype[0] or \
            self.proto_type in wiretype_to_prototype[1] or \
             self.proto_type in wiretype_to_prototype[5]) and self.is_repeated:
            return "_" + self.proto_type + "_array"

        if not self.is_embedded_message:
            return "_" + self.proto_type

        return self.proto_type

desctype_to_prototype = {
    descriptor_pb2.FieldDescriptorProto.TYPE_UINT32: "uint32",
    descriptor_pb2.FieldDescriptorProto.TYPE_UINT64: "uint64",
    descriptor_pb2.FieldDescriptorProto.TYPE_INT32:  "int32",
    descriptor_pb2.FieldDescriptorProto.TYPE_INT64:  "int64",
    descriptor_pb2.FieldDescriptorProto.TYPE_BOOL:   "bool",
    descriptor_pb2.FieldDescriptorProto.TYPE_STRING: "string",
    descriptor_pb2.FieldDescriptorProto.TYPE_BYTES:  "bytes",
    descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE: "double",
    descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT:  "float",
}

def _short_type_name(full_name: str) -> str:
    """
    .pkg.Message -> Message
    Message      -> Message
    """
    if full_name.startswith("."):
        full_name = full_name[1:]
    return full_name.split(".")[-1]

def load_descriptor_set(path: str) -> descriptor_pb2.FileDescriptorSet:
    fds = descriptor_pb2.FileDescriptorSet()
    with open(path, "rb") as f:
        fds.ParseFromString(f.read())
    return fds

def parse_proto_from_descriptor(desc_path: str) -> Dict[str, List[Field]]:
    fds = load_descriptor_set(desc_path)

    if len(fds.file) != 1:
        raise ValueError(
            f"Expected exactly 1 proto file in descriptor_set, but got {len(fds.file)}. "
            f"Currently only single proto file is supported."
        )

    file_desc = fds.file[0]

    messages: Dict[str, List[Field]] = {}

    for msg_desc in file_desc.message_type:
        if msg_desc.nested_type:
            raise ValueError(
                f"Nested messages are not supported (found nested types inside message '{msg_desc.name}')."
            )

        msg_name = msg_desc.name
        fields: List[Field] = []

        for f in msg_desc.field:
            is_repeated = (
                f.label == descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
            )

            if f.type == descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE:
                proto_type = _short_type_name(f.type_name)
            elif f.type in desctype_to_prototype:
                proto_type = desctype_to_prototype[f.type]
            else:
                raise ValueError(
                    f"Unsupported field type: {f.type} (field={f.name})"
                )

            # set is_embedded_message later
            fields.append(
                Field(
                    field_id=f.number,
                    name=f.name,
                    is_repeated=is_repeated,
                    is_embedded_message=False,
                    proto_type=proto_type,
                )
            )

        fields.sort(key=lambda x: x.field_id)
        messages[msg_name] = fields

    num_of_field = 0
    message_names = set(messages.keys())

    for _, fields in messages.items():
        num_of_field += len(fields)
        for field in fields:
            if field.proto_type in message_names:
                field.is_embedded_message = True
            elif field.proto_type not in prototype_to_cpptype:
                raise ValueError(f"Unsupported type: {field.proto_type}")

    print(f"The total number of message: {len(messages)}")
    print(f"The total number of field: {num_of_field}")

    return messages

def generated_file_dir():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, "../../artifact/generated")

def proto_file_prefix(file_path):
    return file_path.split("/")[-1].split(".")[-2]

def convert_proto_to_desc(file_path: str) -> str:
    return os.path.join(generated_file_dir(), proto_file_prefix(file_path) + ".desc")

def header_file_name(namespace, file_path):
    return proto_file_prefix(file_path) + f".{namespace.lower()}.h"

def header_file_path(namespace, file_path):
    return os.path.join(generated_file_dir(), header_file_name(namespace, file_path))

def cpp_file_name(namespace, file_path):
    return proto_file_prefix(file_path) + f".{namespace.lower()}.cpp"

def cpp_file_path(namespace, file_path):
    return os.path.join(generated_file_dir(), cpp_file_name(namespace, file_path))

def test_file_name(file_path):
    return proto_file_prefix(file_path) + f".test.cpp"

def test_file_path(file_path):
    return os.path.join(generated_file_dir(), test_file_name(file_path))

# generate the .pbs.h file
def generate_bl_header(args, messages: dict[str, list[Field]]):
    with open(header_file_path(NAMESPACE_BL, args.file_path), "w") as f:
        f.write(jinja_env.get_template('bl/header.jinja').render(
            proto_file_prefix=proto_file_prefix(args.file_path),
            namespace=NAMESPACE_BL,
            messages=messages,
        ))

def generate_bl_cpp(args, messages: dict[str, list[Field]]):
    with open(cpp_file_path(NAMESPACE_BL, args.file_path), "w") as f:
        f.write(jinja_env.get_template('bl/cpp.jinja').render(
            header_file_name=header_file_name(NAMESPACE_BL, args.file_path),
            namespace=NAMESPACE_BL,
            messages=messages,
            wiretype_to_prototype=wiretype_to_prototype,
        ))

def generate_tpp_header(args, messages: dict[str, list[Field]]):
    with open(header_file_path(NAMESPACE_TPP, args.file_path), "w") as f:
        f.write(jinja_env.get_template('tpp/header.jinja').render(
            proto_file_prefix=proto_file_prefix(args.file_path),
            namespace=NAMESPACE_TPP,
            messages=messages,
            valid_tags=gen_const.valid_tags,
        ))

def generate_tpp_cpp(args, messages: dict[str, list[Field]]):
    with open(cpp_file_path(NAMESPACE_TPP, args.file_path), "w") as f:
        f.write(jinja_env.get_template('tpp/cpp.jinja').render(
            header_file_name=header_file_name(NAMESPACE_TPP, args.file_path),
            namespace=NAMESPACE_TPP,
            messages=messages,
            wiretype_to_prototype=wiretype_to_prototype,
        ))

def generate_spp_header(args, messages: dict[str, list[Field]]):
    with open(header_file_path(NAMESPACE_SPP, args.file_path), "w") as f:
        f.write(jinja_env.get_template('spp/header.jinja').render(
            proto_file_prefix=proto_file_prefix(args.file_path),
            namespace=NAMESPACE_SPP,
            messages=messages,
            main_message_name=list(messages.keys())[0],
            ptypes=gen_const.construct_ptypes(messages),
            primary_ptype_mapping=gen_const.construct_primary_ptype_mapping(messages),
            candidates_init=gen_const.construct_candidates_init(messages, args.disable_type_prioritization),
            candidates=gen_const.construct_candidates(messages, args.disable_type_prioritization),
            merge_type_check=gen_const.construct_merge_type_check(messages),
        ))

def generate_spp_cpp(args, messages: dict[str, list[Field]]):
    with open(cpp_file_path(NAMESPACE_SPP, args.file_path), "w") as f:
        f.write(jinja_env.get_template('spp/cpp.jinja').render(
            header_file_name=header_file_name(NAMESPACE_SPP, args.file_path),
            namespace=NAMESPACE_SPP,
            messages=messages,
            main_message_name=list(messages.keys())[0],
            ptypes=gen_const.construct_ptypes(messages),
            partial_parse_templates=partial_parse_templates,
            wiretype_to_prototype=wiretype_to_prototype,
        ))

# NOTE:
# 1. the first message should be the main message
# 2. the package name should be PB, e.g., package PB;
def generate_test(args, messages: dict[str, list[Field]]):
    with open(test_file_path(args.file_path), "w") as f:
        f.write(jinja_env.get_template('test.jinja').render(
            proto_file_prefix=proto_file_prefix(args.file_path),
            main_message_name=list(messages.keys())[0],
            file_path=args.file_path,
            header_file_name=header_file_name,
            test_bl=True,
            test_tpp=True,
            test_spp=True,
        ))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file_path", help="protobuf schema file path")
    parser.add_argument("--disable_type_prioritization", action="store_true")
    args = parser.parse_args()

    messages = parse_proto_from_descriptor(convert_proto_to_desc(args.file_path))

    generate_bl_header(args, messages)
    generate_bl_cpp(args, messages)

    generate_tpp_header(args, messages)
    generate_tpp_cpp(args, messages)

    generate_spp_header(args, messages)
    generate_spp_cpp(args, messages)

    generate_test(args, messages)


if __name__ == "__main__":
    main()