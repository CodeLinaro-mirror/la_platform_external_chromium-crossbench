from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class SystemInfoConfig(_message.Message):
    __slots__ = ("irq_names",)
    IRQ_NAMES_FIELD_NUMBER: _ClassVar[int]
    irq_names: bool
    def __init__(self, irq_names: _Optional[bool] = ...) -> None: ...
