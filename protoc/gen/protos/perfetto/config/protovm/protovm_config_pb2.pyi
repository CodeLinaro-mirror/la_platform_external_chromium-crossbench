from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class ProtoVmConfig(_message.Message):
    __slots__ = ("memory_limit_kb",)
    MEMORY_LIMIT_KB_FIELD_NUMBER: _ClassVar[int]
    memory_limit_kb: int
    def __init__(self, memory_limit_kb: _Optional[int] = ...) -> None: ...
