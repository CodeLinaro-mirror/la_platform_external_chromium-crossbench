from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class QnxConfig(_message.Message):
    __slots__ = ("qnx_kernel_buffers", "qnx_kernel_kbuffers", "qnx_kernel_wide_events", "qnx_cache_pages", "qnx_cache_max_pages", "qnx_trace_buffer_init_bytes")
    QNX_KERNEL_BUFFERS_FIELD_NUMBER: _ClassVar[int]
    QNX_KERNEL_KBUFFERS_FIELD_NUMBER: _ClassVar[int]
    QNX_KERNEL_WIDE_EVENTS_FIELD_NUMBER: _ClassVar[int]
    QNX_CACHE_PAGES_FIELD_NUMBER: _ClassVar[int]
    QNX_CACHE_MAX_PAGES_FIELD_NUMBER: _ClassVar[int]
    QNX_TRACE_BUFFER_INIT_BYTES_FIELD_NUMBER: _ClassVar[int]
    qnx_kernel_buffers: int
    qnx_kernel_kbuffers: int
    qnx_kernel_wide_events: bool
    qnx_cache_pages: int
    qnx_cache_max_pages: int
    qnx_trace_buffer_init_bytes: int
    def __init__(self, qnx_kernel_buffers: _Optional[int] = ..., qnx_kernel_kbuffers: _Optional[int] = ..., qnx_kernel_wide_events: _Optional[bool] = ..., qnx_cache_pages: _Optional[int] = ..., qnx_cache_max_pages: _Optional[int] = ..., qnx_trace_buffer_init_bytes: _Optional[int] = ...) -> None: ...
