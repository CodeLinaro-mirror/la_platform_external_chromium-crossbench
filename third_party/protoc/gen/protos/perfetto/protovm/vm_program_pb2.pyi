from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class VmCursorEnum(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    VM_CURSOR_UNSPECIFIED: _ClassVar[VmCursorEnum]
    VM_CURSOR_SRC: _ClassVar[VmCursorEnum]
    VM_CURSOR_DST: _ClassVar[VmCursorEnum]
    VM_CURSOR_BOTH: _ClassVar[VmCursorEnum]
VM_CURSOR_UNSPECIFIED: VmCursorEnum
VM_CURSOR_SRC: VmCursorEnum
VM_CURSOR_DST: VmCursorEnum
VM_CURSOR_BOTH: VmCursorEnum

class VmProgram(_message.Message):
    __slots__ = ("version", "instructions")
    VERSION_FIELD_NUMBER: _ClassVar[int]
    INSTRUCTIONS_FIELD_NUMBER: _ClassVar[int]
    version: int
    instructions: _containers.RepeatedCompositeFieldContainer[VmInstruction]
    def __init__(self, version: _Optional[int] = ..., instructions: _Optional[_Iterable[_Union[VmInstruction, _Mapping]]] = ...) -> None: ...

class VmInstruction(_message.Message):
    __slots__ = ("select", "reg_load", "merge", "set", "abort_level", "nested_instructions")
    class AbortLevel(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        SKIP_CURRENT_INSTRUCTION: _ClassVar[VmInstruction.AbortLevel]
        SKIP_CURRENT_INSTRUCTION_AND_BREAK_OUTER: _ClassVar[VmInstruction.AbortLevel]
        ABORT: _ClassVar[VmInstruction.AbortLevel]
    SKIP_CURRENT_INSTRUCTION: VmInstruction.AbortLevel
    SKIP_CURRENT_INSTRUCTION_AND_BREAK_OUTER: VmInstruction.AbortLevel
    ABORT: VmInstruction.AbortLevel
    SELECT_FIELD_NUMBER: _ClassVar[int]
    REG_LOAD_FIELD_NUMBER: _ClassVar[int]
    MERGE_FIELD_NUMBER: _ClassVar[int]
    SET_FIELD_NUMBER: _ClassVar[int]
    DEL_FIELD_NUMBER: _ClassVar[int]
    ABORT_LEVEL_FIELD_NUMBER: _ClassVar[int]
    NESTED_INSTRUCTIONS_FIELD_NUMBER: _ClassVar[int]
    select: VmOpSelect
    reg_load: VmOpRegLoad
    merge: VmOpMerge
    set: VmOpSet
    abort_level: VmInstruction.AbortLevel
    nested_instructions: _containers.RepeatedCompositeFieldContainer[VmInstruction]
    def __init__(self, select: _Optional[_Union[VmOpSelect, _Mapping]] = ..., reg_load: _Optional[_Union[VmOpRegLoad, _Mapping]] = ..., merge: _Optional[_Union[VmOpMerge, _Mapping]] = ..., set: _Optional[_Union[VmOpSet, _Mapping]] = ..., abort_level: _Optional[_Union[VmInstruction.AbortLevel, str]] = ..., nested_instructions: _Optional[_Iterable[_Union[VmInstruction, _Mapping]]] = ..., **kwargs) -> None: ...

class VmOpSelect(_message.Message):
    __slots__ = ("cursor", "relative_path", "create_if_not_exist")
    class PathComponent(_message.Message):
        __slots__ = ("field_id", "array_index", "map_key_field_id", "is_repeated", "register_to_match", "store_foreach_index_into_register")
        FIELD_ID_FIELD_NUMBER: _ClassVar[int]
        ARRAY_INDEX_FIELD_NUMBER: _ClassVar[int]
        MAP_KEY_FIELD_ID_FIELD_NUMBER: _ClassVar[int]
        IS_REPEATED_FIELD_NUMBER: _ClassVar[int]
        REGISTER_TO_MATCH_FIELD_NUMBER: _ClassVar[int]
        STORE_FOREACH_INDEX_INTO_REGISTER_FIELD_NUMBER: _ClassVar[int]
        field_id: int
        array_index: int
        map_key_field_id: int
        is_repeated: bool
        register_to_match: int
        store_foreach_index_into_register: int
        def __init__(self, field_id: _Optional[int] = ..., array_index: _Optional[int] = ..., map_key_field_id: _Optional[int] = ..., is_repeated: _Optional[bool] = ..., register_to_match: _Optional[int] = ..., store_foreach_index_into_register: _Optional[int] = ...) -> None: ...
    CURSOR_FIELD_NUMBER: _ClassVar[int]
    RELATIVE_PATH_FIELD_NUMBER: _ClassVar[int]
    CREATE_IF_NOT_EXIST_FIELD_NUMBER: _ClassVar[int]
    cursor: VmCursorEnum
    relative_path: _containers.RepeatedCompositeFieldContainer[VmOpSelect.PathComponent]
    create_if_not_exist: bool
    def __init__(self, cursor: _Optional[_Union[VmCursorEnum, str]] = ..., relative_path: _Optional[_Iterable[_Union[VmOpSelect.PathComponent, _Mapping]]] = ..., create_if_not_exist: _Optional[bool] = ...) -> None: ...

class VmOpRegLoad(_message.Message):
    __slots__ = ("cursor", "dst_register")
    CURSOR_FIELD_NUMBER: _ClassVar[int]
    DST_REGISTER_FIELD_NUMBER: _ClassVar[int]
    cursor: VmCursorEnum
    dst_register: int
    def __init__(self, cursor: _Optional[_Union[VmCursorEnum, str]] = ..., dst_register: _Optional[int] = ...) -> None: ...

class VmOpMerge(_message.Message):
    __slots__ = ("skip_submessages",)
    SKIP_SUBMESSAGES_FIELD_NUMBER: _ClassVar[int]
    skip_submessages: bool
    def __init__(self, skip_submessages: _Optional[bool] = ...) -> None: ...

class VmOpSet(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class VmOpDel(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...
