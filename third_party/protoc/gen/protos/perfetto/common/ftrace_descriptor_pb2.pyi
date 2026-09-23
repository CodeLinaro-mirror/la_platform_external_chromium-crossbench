from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class FtraceDescriptor(_message.Message):
    __slots__ = ("atrace_categories",)
    class AtraceCategory(_message.Message):
        __slots__ = ("name", "description")
        NAME_FIELD_NUMBER: _ClassVar[int]
        DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
        name: str
        description: str
        def __init__(self, name: _Optional[str] = ..., description: _Optional[str] = ...) -> None: ...
    ATRACE_CATEGORIES_FIELD_NUMBER: _ClassVar[int]
    atrace_categories: _containers.RepeatedCompositeFieldContainer[FtraceDescriptor.AtraceCategory]
    def __init__(self, atrace_categories: _Optional[_Iterable[_Union[FtraceDescriptor.AtraceCategory, _Mapping]]] = ...) -> None: ...
