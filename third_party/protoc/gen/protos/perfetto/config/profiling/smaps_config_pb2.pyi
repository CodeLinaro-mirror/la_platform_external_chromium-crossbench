from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ProcessSmapsConfig(_message.Message):
    __slots__ = ("smaps_config", "scope", "read_period_ms", "max_processes_per_period")
    class Scope(_message.Message):
        __slots__ = ("target_cmdline", "target_uid")
        class UidRange(_message.Message):
            __slots__ = ("min_uid", "max_uid", "android_match_across_profiles")
            MIN_UID_FIELD_NUMBER: _ClassVar[int]
            MAX_UID_FIELD_NUMBER: _ClassVar[int]
            ANDROID_MATCH_ACROSS_PROFILES_FIELD_NUMBER: _ClassVar[int]
            min_uid: int
            max_uid: int
            android_match_across_profiles: bool
            def __init__(self, min_uid: _Optional[int] = ..., max_uid: _Optional[int] = ..., android_match_across_profiles: _Optional[bool] = ...) -> None: ...
        TARGET_CMDLINE_FIELD_NUMBER: _ClassVar[int]
        TARGET_UID_FIELD_NUMBER: _ClassVar[int]
        target_cmdline: _containers.RepeatedScalarFieldContainer[str]
        target_uid: _containers.RepeatedCompositeFieldContainer[ProcessSmapsConfig.Scope.UidRange]
        def __init__(self, target_cmdline: _Optional[_Iterable[str]] = ..., target_uid: _Optional[_Iterable[_Union[ProcessSmapsConfig.Scope.UidRange, _Mapping]]] = ...) -> None: ...
    SMAPS_CONFIG_FIELD_NUMBER: _ClassVar[int]
    SCOPE_FIELD_NUMBER: _ClassVar[int]
    READ_PERIOD_MS_FIELD_NUMBER: _ClassVar[int]
    MAX_PROCESSES_PER_PERIOD_FIELD_NUMBER: _ClassVar[int]
    smaps_config: SmapsConfig
    scope: ProcessSmapsConfig.Scope
    read_period_ms: int
    max_processes_per_period: int
    def __init__(self, smaps_config: _Optional[_Union[SmapsConfig, _Mapping]] = ..., scope: _Optional[_Union[ProcessSmapsConfig.Scope, _Mapping]] = ..., read_period_ms: _Optional[int] = ..., max_processes_per_period: _Optional[int] = ...) -> None: ...

class SmapsConfig(_message.Message):
    __slots__ = ("vma_fields", "unaggregated", "name_redaction_rules")
    class VmaField(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        VMA_FIELD_UNKNOWN: _ClassVar[SmapsConfig.VmaField]
        VMA_FIELD_SIZE: _ClassVar[SmapsConfig.VmaField]
        VMA_FIELD_RSS: _ClassVar[SmapsConfig.VmaField]
        VMA_FIELD_ANONYMOUS: _ClassVar[SmapsConfig.VmaField]
        VMA_FIELD_SWAP: _ClassVar[SmapsConfig.VmaField]
        VMA_FIELD_SHARED_CLEAN: _ClassVar[SmapsConfig.VmaField]
        VMA_FIELD_SHARED_DIRTY: _ClassVar[SmapsConfig.VmaField]
        VMA_FIELD_PRIVATE_CLEAN: _ClassVar[SmapsConfig.VmaField]
        VMA_FIELD_PRIVATE_DIRTY: _ClassVar[SmapsConfig.VmaField]
        VMA_FIELD_LOCKED: _ClassVar[SmapsConfig.VmaField]
        VMA_FIELD_PSS: _ClassVar[SmapsConfig.VmaField]
        VMA_FIELD_PSS_DIRTY: _ClassVar[SmapsConfig.VmaField]
        VMA_FIELD_SWAP_PSS: _ClassVar[SmapsConfig.VmaField]
    VMA_FIELD_UNKNOWN: SmapsConfig.VmaField
    VMA_FIELD_SIZE: SmapsConfig.VmaField
    VMA_FIELD_RSS: SmapsConfig.VmaField
    VMA_FIELD_ANONYMOUS: SmapsConfig.VmaField
    VMA_FIELD_SWAP: SmapsConfig.VmaField
    VMA_FIELD_SHARED_CLEAN: SmapsConfig.VmaField
    VMA_FIELD_SHARED_DIRTY: SmapsConfig.VmaField
    VMA_FIELD_PRIVATE_CLEAN: SmapsConfig.VmaField
    VMA_FIELD_PRIVATE_DIRTY: SmapsConfig.VmaField
    VMA_FIELD_LOCKED: SmapsConfig.VmaField
    VMA_FIELD_PSS: SmapsConfig.VmaField
    VMA_FIELD_PSS_DIRTY: SmapsConfig.VmaField
    VMA_FIELD_SWAP_PSS: SmapsConfig.VmaField
    VMA_FIELDS_FIELD_NUMBER: _ClassVar[int]
    UNAGGREGATED_FIELD_NUMBER: _ClassVar[int]
    NAME_REDACTION_RULES_FIELD_NUMBER: _ClassVar[int]
    vma_fields: _containers.RepeatedScalarFieldContainer[SmapsConfig.VmaField]
    unaggregated: bool
    name_redaction_rules: _containers.RepeatedCompositeFieldContainer[RedactionRule]
    def __init__(self, vma_fields: _Optional[_Iterable[_Union[SmapsConfig.VmaField, str]]] = ..., unaggregated: _Optional[bool] = ..., name_redaction_rules: _Optional[_Iterable[_Union[RedactionRule, _Mapping]]] = ...) -> None: ...

class RedactionRule(_message.Message):
    __slots__ = ("pattern", "match_mode", "keep_full", "replacement_name", "keep_file_extension", "keep_path_elements")
    class MatchMode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        MATCH_MODE_UNKNOWN: _ClassVar[RedactionRule.MatchMode]
        MATCH_MODE_PREFIX: _ClassVar[RedactionRule.MatchMode]
        MATCH_MODE_GLOB_PATH: _ClassVar[RedactionRule.MatchMode]
        MATCH_MODE_GLOB_STRING: _ClassVar[RedactionRule.MatchMode]
    MATCH_MODE_UNKNOWN: RedactionRule.MatchMode
    MATCH_MODE_PREFIX: RedactionRule.MatchMode
    MATCH_MODE_GLOB_PATH: RedactionRule.MatchMode
    MATCH_MODE_GLOB_STRING: RedactionRule.MatchMode
    PATTERN_FIELD_NUMBER: _ClassVar[int]
    MATCH_MODE_FIELD_NUMBER: _ClassVar[int]
    KEEP_FULL_FIELD_NUMBER: _ClassVar[int]
    REPLACEMENT_NAME_FIELD_NUMBER: _ClassVar[int]
    KEEP_FILE_EXTENSION_FIELD_NUMBER: _ClassVar[int]
    KEEP_PATH_ELEMENTS_FIELD_NUMBER: _ClassVar[int]
    pattern: str
    match_mode: RedactionRule.MatchMode
    keep_full: bool
    replacement_name: str
    keep_file_extension: bool
    keep_path_elements: int
    def __init__(self, pattern: _Optional[str] = ..., match_mode: _Optional[_Union[RedactionRule.MatchMode, str]] = ..., keep_full: _Optional[bool] = ..., replacement_name: _Optional[str] = ..., keep_file_extension: _Optional[bool] = ..., keep_path_elements: _Optional[int] = ...) -> None: ...
