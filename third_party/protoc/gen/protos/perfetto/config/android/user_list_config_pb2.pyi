from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class AndroidUserListConfig(_message.Message):
    __slots__ = ("user_type_filter",)
    USER_TYPE_FILTER_FIELD_NUMBER: _ClassVar[int]
    user_type_filter: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, user_type_filter: _Optional[_Iterable[str]] = ...) -> None: ...
