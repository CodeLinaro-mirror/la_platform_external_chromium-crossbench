from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class AndroidProcessStateConfig(_message.Message):
    __slots__ = ("dump_process_metadata",)
    DUMP_PROCESS_METADATA_FIELD_NUMBER: _ClassVar[int]
    dump_process_metadata: bool
    def __init__(self, dump_process_metadata: _Optional[bool] = ...) -> None: ...
