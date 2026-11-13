from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class SystemdJournaldConfig(_message.Message):
    __slots__ = ("min_prio", "filter_identifiers", "filter_units")
    MIN_PRIO_FIELD_NUMBER: _ClassVar[int]
    FILTER_IDENTIFIERS_FIELD_NUMBER: _ClassVar[int]
    FILTER_UNITS_FIELD_NUMBER: _ClassVar[int]
    min_prio: int
    filter_identifiers: _containers.RepeatedScalarFieldContainer[str]
    filter_units: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, min_prio: _Optional[int] = ..., filter_identifiers: _Optional[_Iterable[str]] = ..., filter_units: _Optional[_Iterable[str]] = ...) -> None: ...
