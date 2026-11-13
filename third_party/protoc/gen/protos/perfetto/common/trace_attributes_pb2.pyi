from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class TraceAttributes(_message.Message):
    __slots__ = ("attribute",)
    class Attribute(_message.Message):
        __slots__ = ("key", "long_value", "string_value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        LONG_VALUE_FIELD_NUMBER: _ClassVar[int]
        STRING_VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        long_value: int
        string_value: str
        def __init__(self, key: _Optional[str] = ..., long_value: _Optional[int] = ..., string_value: _Optional[str] = ...) -> None: ...
    ATTRIBUTE_FIELD_NUMBER: _ClassVar[int]
    attribute: _containers.RepeatedCompositeFieldContainer[TraceAttributes.Attribute]
    def __init__(self, attribute: _Optional[_Iterable[_Union[TraceAttributes.Attribute, _Mapping]]] = ...) -> None: ...
