from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from typing import ClassVar as _ClassVar

DESCRIPTOR: _descriptor.FileDescriptor

class SemanticType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SEMANTIC_TYPE_UNSPECIFIED: _ClassVar[SemanticType]
    SEMANTIC_TYPE_ATRACE: _ClassVar[SemanticType]
    SEMANTIC_TYPE_JOB: _ClassVar[SemanticType]
    SEMANTIC_TYPE_WAKELOCK: _ClassVar[SemanticType]
SEMANTIC_TYPE_UNSPECIFIED: SemanticType
SEMANTIC_TYPE_ATRACE: SemanticType
SEMANTIC_TYPE_JOB: SemanticType
SEMANTIC_TYPE_WAKELOCK: SemanticType
