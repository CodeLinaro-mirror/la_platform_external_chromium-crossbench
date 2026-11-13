from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class EtwConfig(_message.Message):
    __slots__ = ("kernel_flags", "scheduler_provider_events", "memory_provider_events", "file_provider_events", "stack_sampling_events", "disk_provider_events", "system_io_provider_events", "stack_sampling_debug_ids")
    class KernelFlag(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        CSWITCH: _ClassVar[EtwConfig.KernelFlag]
        DISPATCHER: _ClassVar[EtwConfig.KernelFlag]
    CSWITCH: EtwConfig.KernelFlag
    DISPATCHER: EtwConfig.KernelFlag
    class DebugId(_message.Message):
        __slots__ = ("path", "debug_id")
        PATH_FIELD_NUMBER: _ClassVar[int]
        DEBUG_ID_FIELD_NUMBER: _ClassVar[int]
        path: str
        debug_id: str
        def __init__(self, path: _Optional[str] = ..., debug_id: _Optional[str] = ...) -> None: ...
    KERNEL_FLAGS_FIELD_NUMBER: _ClassVar[int]
    SCHEDULER_PROVIDER_EVENTS_FIELD_NUMBER: _ClassVar[int]
    MEMORY_PROVIDER_EVENTS_FIELD_NUMBER: _ClassVar[int]
    FILE_PROVIDER_EVENTS_FIELD_NUMBER: _ClassVar[int]
    STACK_SAMPLING_EVENTS_FIELD_NUMBER: _ClassVar[int]
    DISK_PROVIDER_EVENTS_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_IO_PROVIDER_EVENTS_FIELD_NUMBER: _ClassVar[int]
    STACK_SAMPLING_DEBUG_IDS_FIELD_NUMBER: _ClassVar[int]
    kernel_flags: _containers.RepeatedScalarFieldContainer[EtwConfig.KernelFlag]
    scheduler_provider_events: _containers.RepeatedScalarFieldContainer[str]
    memory_provider_events: _containers.RepeatedScalarFieldContainer[str]
    file_provider_events: _containers.RepeatedScalarFieldContainer[str]
    stack_sampling_events: _containers.RepeatedScalarFieldContainer[str]
    disk_provider_events: _containers.RepeatedScalarFieldContainer[str]
    system_io_provider_events: _containers.RepeatedScalarFieldContainer[str]
    stack_sampling_debug_ids: _containers.RepeatedCompositeFieldContainer[EtwConfig.DebugId]
    def __init__(self, kernel_flags: _Optional[_Iterable[_Union[EtwConfig.KernelFlag, str]]] = ..., scheduler_provider_events: _Optional[_Iterable[str]] = ..., memory_provider_events: _Optional[_Iterable[str]] = ..., file_provider_events: _Optional[_Iterable[str]] = ..., stack_sampling_events: _Optional[_Iterable[str]] = ..., disk_provider_events: _Optional[_Iterable[str]] = ..., system_io_provider_events: _Optional[_Iterable[str]] = ..., stack_sampling_debug_ids: _Optional[_Iterable[_Union[EtwConfig.DebugId, _Mapping]]] = ...) -> None: ...
