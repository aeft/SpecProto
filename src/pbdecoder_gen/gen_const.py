from .gen_from_proto import Field, prototype_to_cpptype, prototype_to_wiretype
from pprint import pprint

def valid_tags(fields: list[Field]):
    ret = set()
    for field in fields:
        ret.add(field.tag)
        if field.is_repeated and field.proto_type in prototype_to_wiretype:
            ret.add(field.field_id << 3 | prototype_to_wiretype[field.proto_type])
    return list(ret)

def construct_ptypes(messages: dict[str, list[Field]]) -> list[tuple[str, int]]:
    ptypes: list[tuple[str, int]] = []

    visited = set()

    index = 0
    for message_name, fields in messages.items():
        ptypes.append((message_name, index))
        index += 1

    for message_name, fields in messages.items():
        for field in fields:
            if field.ptype not in visited and \
               field.proto_type in prototype_to_cpptype.keys():
                visited.add(field.ptype)
                ptypes.append((field.ptype, index))
                index += 1
    
    return ptypes

def construct_primary_ptype_mapping(messages: dict[str, list[Field]]) -> dict[str, str]:
    primary_ptype_mapping: dict[str, str] = {}
    wiretype2 = {"string", "bytes"}

    for _, fields in messages.items():
        for field in fields:
            if field.proto_type in prototype_to_cpptype.keys():
                primary_ptype_mapping[field.ptype] = field.cpp_type_single if field.proto_type in wiretype2 else field.cpp_type
    
    return primary_ptype_mapping

def construct_candidates_init(messages: dict[str, list[Field]], disable_type_prioritization: bool) -> dict[int, list[str]]:
    candidates_init: dict[int, set[str]] = {}

    for _, fields in messages.items():
        for field in fields:
            if field.tag not in candidates_init:
                candidates_init[field.tag] = set()
            candidates_init[field.tag].add(field.ptype)
    
    embedded_messages = set(messages.keys())

    if disable_type_prioritization:
        print("type prioritization is disabled")
        return {k: sorted(list(v), reverse=True) 
            for k, v in candidates_init.items() }

    # enable type prioritization
    return {k: sorted(sorted(v), key=lambda x: 0 if x in embedded_messages else 1) 
            for k, v in candidates_init.items() }

def construct_candidates(messages: dict[str, list[Field]], disable_type_prioritization: bool) -> dict[str, dict[int, list[str]]]:
    root = list(messages.keys())[0]

    parent: dict[str, set[str]] = {}
    for message_name, fields in messages.items():
        for field in fields:
            if field.ptype not in parent:
                parent[field.ptype] = set()
            parent[field.ptype].add(message_name)

    candidates: dict[str, dict[int, set[str]]] = {}

    visited = set()
    def dfs(start: str, u: str):
        if u == root:
            return
        if u in visited:
            return
        visited.add(u)
        for p in parent[u]:
            for field in messages[p]:
                if field.tag not in candidates[start]:
                    candidates[start][field.tag] = set()
                candidates[start][field.tag].add(field.ptype)
            dfs(start, p)

    for message_name, fields in messages.items():
        for field in fields:
            candidates[field.ptype] = dict()
            visited.clear()
            dfs(field.ptype, field.ptype)
    
    embedded_messages = set(messages.keys())

    if disable_type_prioritization:
        print("type prioritization is disabled")
        # simulate a bad order here
        return {start: {tag: sorted(list(ptypes), reverse=True) for tag, ptypes in tag_ptypes.items()} 
                for start, tag_ptypes in candidates.items()}

    # enable type prioritization
    return {start: {tag: sorted(sorted(ptypes), key=lambda ptype: ((0, ptype) if start == ptype else (1, ptype)) if ptype in embedded_messages else (2, ptype))
                for tag, ptypes in tag_ptypes.items()} 
            for start, tag_ptypes in candidates.items()}

    # only use tag to speculate; prefer the same type
    # candidates_init = construct_candidates_init(messages)
    # candidates = {start: {tag: candidates_init[tag] for tag, ptypes in tag_ptypes.items()} 
    #         for start, tag_ptypes in candidates.items()}
    # return {start: {tag: sorted(list(ptypes), key=lambda ptype: (0 if start == ptype else 1) if ptype in embedded_messages else 2)
    #             for tag, ptypes in tag_ptypes.items()} 
    #         for start, tag_ptypes in candidates.items()}

def construct_merge_type_check(messages: dict[str, list[Field]]) -> dict[str, dict[int, str]]:
    res: dict[str, dict[int, str]] = {}

    for message_name, fields in messages.items():
        res[message_name] = dict()
        for field in fields:
            res[message_name][field.tag] = field.ptype
    
    return res
