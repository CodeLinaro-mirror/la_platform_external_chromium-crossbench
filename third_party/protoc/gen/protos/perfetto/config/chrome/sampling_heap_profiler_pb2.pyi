from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class ChromiumSamplingHeapProfilerConfig(_message.Message):
    __slots__ = ("sampling_interval_bytes", "sampling_interval_ms")
    SAMPLING_INTERVAL_BYTES_FIELD_NUMBER: _ClassVar[int]
    SAMPLING_INTERVAL_MS_FIELD_NUMBER: _ClassVar[int]
    sampling_interval_bytes: int
    sampling_interval_ms: int
    def __init__(self, sampling_interval_bytes: _Optional[int] = ..., sampling_interval_ms: _Optional[int] = ...) -> None: ...
