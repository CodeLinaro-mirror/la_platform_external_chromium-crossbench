from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class DisplayVideoConfig(_message.Message):
    __slots__ = ("scale", "format", "key_frame_interval_secs", "max_stream_size_bytes", "bitrate_bps")
    class Format(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        FORMAT_UNSPECIFIED: _ClassVar[DisplayVideoConfig.Format]
        FORMAT_H264: _ClassVar[DisplayVideoConfig.Format]
        FORMAT_HEVC: _ClassVar[DisplayVideoConfig.Format]
    FORMAT_UNSPECIFIED: DisplayVideoConfig.Format
    FORMAT_H264: DisplayVideoConfig.Format
    FORMAT_HEVC: DisplayVideoConfig.Format
    SCALE_FIELD_NUMBER: _ClassVar[int]
    FORMAT_FIELD_NUMBER: _ClassVar[int]
    KEY_FRAME_INTERVAL_SECS_FIELD_NUMBER: _ClassVar[int]
    MAX_STREAM_SIZE_BYTES_FIELD_NUMBER: _ClassVar[int]
    BITRATE_BPS_FIELD_NUMBER: _ClassVar[int]
    scale: float
    format: DisplayVideoConfig.Format
    key_frame_interval_secs: int
    max_stream_size_bytes: int
    bitrate_bps: int
    def __init__(self, scale: _Optional[float] = ..., format: _Optional[_Union[DisplayVideoConfig.Format, str]] = ..., key_frame_interval_secs: _Optional[int] = ..., max_stream_size_bytes: _Optional[int] = ..., bitrate_bps: _Optional[int] = ...) -> None: ...
