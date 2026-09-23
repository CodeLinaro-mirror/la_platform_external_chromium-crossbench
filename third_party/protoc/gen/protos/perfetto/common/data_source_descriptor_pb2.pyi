from protos.perfetto.common import ftrace_descriptor_pb2 as _ftrace_descriptor_pb2
from protos.perfetto.common import gpu_counter_descriptor_pb2 as _gpu_counter_descriptor_pb2
from protos.perfetto.common import track_event_descriptor_pb2 as _track_event_descriptor_pb2
from protos.perfetto.protovm import vm_program_pb2 as _vm_program_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class DataSourceDescriptor(_message.Message):
    __slots__ = ("name", "id", "will_notify_on_stop", "will_notify_on_start", "handles_incremental_state_clear", "no_flush", "protovm_program", "gpu_counter_descriptor", "track_event_descriptor", "ftrace_descriptor")
    NAME_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    WILL_NOTIFY_ON_STOP_FIELD_NUMBER: _ClassVar[int]
    WILL_NOTIFY_ON_START_FIELD_NUMBER: _ClassVar[int]
    HANDLES_INCREMENTAL_STATE_CLEAR_FIELD_NUMBER: _ClassVar[int]
    NO_FLUSH_FIELD_NUMBER: _ClassVar[int]
    PROTOVM_PROGRAM_FIELD_NUMBER: _ClassVar[int]
    GPU_COUNTER_DESCRIPTOR_FIELD_NUMBER: _ClassVar[int]
    TRACK_EVENT_DESCRIPTOR_FIELD_NUMBER: _ClassVar[int]
    FTRACE_DESCRIPTOR_FIELD_NUMBER: _ClassVar[int]
    name: str
    id: int
    will_notify_on_stop: bool
    will_notify_on_start: bool
    handles_incremental_state_clear: bool
    no_flush: bool
    protovm_program: _vm_program_pb2.VmProgram
    gpu_counter_descriptor: _gpu_counter_descriptor_pb2.GpuCounterDescriptor
    track_event_descriptor: _track_event_descriptor_pb2.TrackEventDescriptor
    ftrace_descriptor: _ftrace_descriptor_pb2.FtraceDescriptor
    def __init__(self, name: _Optional[str] = ..., id: _Optional[int] = ..., will_notify_on_stop: _Optional[bool] = ..., will_notify_on_start: _Optional[bool] = ..., handles_incremental_state_clear: _Optional[bool] = ..., no_flush: _Optional[bool] = ..., protovm_program: _Optional[_Union[_vm_program_pb2.VmProgram, _Mapping]] = ..., gpu_counter_descriptor: _Optional[_Union[_gpu_counter_descriptor_pb2.GpuCounterDescriptor, _Mapping]] = ..., track_event_descriptor: _Optional[_Union[_track_event_descriptor_pb2.TrackEventDescriptor, _Mapping]] = ..., ftrace_descriptor: _Optional[_Union[_ftrace_descriptor_pb2.FtraceDescriptor, _Mapping]] = ...) -> None: ...
