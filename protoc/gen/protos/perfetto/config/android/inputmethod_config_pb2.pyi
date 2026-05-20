from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class InputMethodConfig(_message.Message):
    __slots__ = ("client", "service", "manager_service")
    CLIENT_FIELD_NUMBER: _ClassVar[int]
    SERVICE_FIELD_NUMBER: _ClassVar[int]
    MANAGER_SERVICE_FIELD_NUMBER: _ClassVar[int]
    client: bool
    service: bool
    manager_service: bool
    def __init__(self, client: _Optional[bool] = ..., service: _Optional[bool] = ..., manager_service: _Optional[bool] = ...) -> None: ...
