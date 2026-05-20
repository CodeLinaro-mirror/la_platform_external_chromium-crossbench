from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class TrackEventCategory(_message.Message):
    __slots__ = ("name", "description", "tags")
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    TAGS_FIELD_NUMBER: _ClassVar[int]
    name: str
    description: str
    tags: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, name: _Optional[str] = ..., description: _Optional[str] = ..., tags: _Optional[_Iterable[str]] = ...) -> None: ...

class TrackEventDescriptor(_message.Message):
    __slots__ = ("available_categories",)
    AVAILABLE_CATEGORIES_FIELD_NUMBER: _ClassVar[int]
    available_categories: _containers.RepeatedCompositeFieldContainer[TrackEventCategory]
    def __init__(self, available_categories: _Optional[_Iterable[_Union[TrackEventCategory, _Mapping]]] = ...) -> None: ...
