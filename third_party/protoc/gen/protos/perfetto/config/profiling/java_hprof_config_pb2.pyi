from protos.perfetto.config.profiling import smaps_config_pb2 as _smaps_config_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class JavaHprofConfig(_message.Message):
    __slots__ = ("process_cmdline", "pid", "target_installed_by", "continuous_dump_config", "min_anonymous_memory_kb", "min_java_heap_size_kb", "skip_frozen_processes", "dump_smaps", "smaps_config", "ignored_types", "dump_oome_callstack")
    class ContinuousDumpConfig(_message.Message):
        __slots__ = ("dump_phase_ms", "dump_interval_ms", "scan_pids_only_on_start")
        DUMP_PHASE_MS_FIELD_NUMBER: _ClassVar[int]
        DUMP_INTERVAL_MS_FIELD_NUMBER: _ClassVar[int]
        SCAN_PIDS_ONLY_ON_START_FIELD_NUMBER: _ClassVar[int]
        dump_phase_ms: int
        dump_interval_ms: int
        scan_pids_only_on_start: bool
        def __init__(self, dump_phase_ms: _Optional[int] = ..., dump_interval_ms: _Optional[int] = ..., scan_pids_only_on_start: _Optional[bool] = ...) -> None: ...
    PROCESS_CMDLINE_FIELD_NUMBER: _ClassVar[int]
    PID_FIELD_NUMBER: _ClassVar[int]
    TARGET_INSTALLED_BY_FIELD_NUMBER: _ClassVar[int]
    CONTINUOUS_DUMP_CONFIG_FIELD_NUMBER: _ClassVar[int]
    MIN_ANONYMOUS_MEMORY_KB_FIELD_NUMBER: _ClassVar[int]
    MIN_JAVA_HEAP_SIZE_KB_FIELD_NUMBER: _ClassVar[int]
    SKIP_FROZEN_PROCESSES_FIELD_NUMBER: _ClassVar[int]
    DUMP_SMAPS_FIELD_NUMBER: _ClassVar[int]
    SMAPS_CONFIG_FIELD_NUMBER: _ClassVar[int]
    IGNORED_TYPES_FIELD_NUMBER: _ClassVar[int]
    DUMP_OOME_CALLSTACK_FIELD_NUMBER: _ClassVar[int]
    process_cmdline: _containers.RepeatedScalarFieldContainer[str]
    pid: _containers.RepeatedScalarFieldContainer[int]
    target_installed_by: _containers.RepeatedScalarFieldContainer[str]
    continuous_dump_config: JavaHprofConfig.ContinuousDumpConfig
    min_anonymous_memory_kb: int
    min_java_heap_size_kb: int
    skip_frozen_processes: bool
    dump_smaps: bool
    smaps_config: _smaps_config_pb2.SmapsConfig
    ignored_types: _containers.RepeatedScalarFieldContainer[str]
    dump_oome_callstack: bool
    def __init__(self, process_cmdline: _Optional[_Iterable[str]] = ..., pid: _Optional[_Iterable[int]] = ..., target_installed_by: _Optional[_Iterable[str]] = ..., continuous_dump_config: _Optional[_Union[JavaHprofConfig.ContinuousDumpConfig, _Mapping]] = ..., min_anonymous_memory_kb: _Optional[int] = ..., min_java_heap_size_kb: _Optional[int] = ..., skip_frozen_processes: _Optional[bool] = ..., dump_smaps: _Optional[bool] = ..., smaps_config: _Optional[_Union[_smaps_config_pb2.SmapsConfig, _Mapping]] = ..., ignored_types: _Optional[_Iterable[str]] = ..., dump_oome_callstack: _Optional[bool] = ...) -> None: ...
