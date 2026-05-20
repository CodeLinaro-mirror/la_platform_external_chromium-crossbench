from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class GpuCounterConfig(_message.Message):
    __slots__ = ("counter_period_ns", "counter_ids", "counter_names", "instrumented_sampling", "instrumented_sampling_config", "fix_gpu_clock")
    class InstrumentedSamplingConfig(_message.Message):
        __slots__ = ("activity_name_filters", "activity_tx_include_globs", "activity_tx_exclude_globs", "activity_ranges")
        class ActivityNameFilter(_message.Message):
            __slots__ = ("name_glob", "name_base")
            class NameBase(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
                __slots__ = ()
                MANGLED_KERNEL_NAME: _ClassVar[GpuCounterConfig.InstrumentedSamplingConfig.ActivityNameFilter.NameBase]
                DEMANGLED_KERNEL_NAME: _ClassVar[GpuCounterConfig.InstrumentedSamplingConfig.ActivityNameFilter.NameBase]
                FUNCTION_NAME: _ClassVar[GpuCounterConfig.InstrumentedSamplingConfig.ActivityNameFilter.NameBase]
            MANGLED_KERNEL_NAME: GpuCounterConfig.InstrumentedSamplingConfig.ActivityNameFilter.NameBase
            DEMANGLED_KERNEL_NAME: GpuCounterConfig.InstrumentedSamplingConfig.ActivityNameFilter.NameBase
            FUNCTION_NAME: GpuCounterConfig.InstrumentedSamplingConfig.ActivityNameFilter.NameBase
            NAME_GLOB_FIELD_NUMBER: _ClassVar[int]
            NAME_BASE_FIELD_NUMBER: _ClassVar[int]
            name_glob: str
            name_base: GpuCounterConfig.InstrumentedSamplingConfig.ActivityNameFilter.NameBase
            def __init__(self, name_glob: _Optional[str] = ..., name_base: _Optional[_Union[GpuCounterConfig.InstrumentedSamplingConfig.ActivityNameFilter.NameBase, str]] = ...) -> None: ...
        class ActivityRange(_message.Message):
            __slots__ = ("skip", "count")
            SKIP_FIELD_NUMBER: _ClassVar[int]
            COUNT_FIELD_NUMBER: _ClassVar[int]
            skip: int
            count: int
            def __init__(self, skip: _Optional[int] = ..., count: _Optional[int] = ...) -> None: ...
        ACTIVITY_NAME_FILTERS_FIELD_NUMBER: _ClassVar[int]
        ACTIVITY_TX_INCLUDE_GLOBS_FIELD_NUMBER: _ClassVar[int]
        ACTIVITY_TX_EXCLUDE_GLOBS_FIELD_NUMBER: _ClassVar[int]
        ACTIVITY_RANGES_FIELD_NUMBER: _ClassVar[int]
        activity_name_filters: _containers.RepeatedCompositeFieldContainer[GpuCounterConfig.InstrumentedSamplingConfig.ActivityNameFilter]
        activity_tx_include_globs: _containers.RepeatedScalarFieldContainer[str]
        activity_tx_exclude_globs: _containers.RepeatedScalarFieldContainer[str]
        activity_ranges: _containers.RepeatedCompositeFieldContainer[GpuCounterConfig.InstrumentedSamplingConfig.ActivityRange]
        def __init__(self, activity_name_filters: _Optional[_Iterable[_Union[GpuCounterConfig.InstrumentedSamplingConfig.ActivityNameFilter, _Mapping]]] = ..., activity_tx_include_globs: _Optional[_Iterable[str]] = ..., activity_tx_exclude_globs: _Optional[_Iterable[str]] = ..., activity_ranges: _Optional[_Iterable[_Union[GpuCounterConfig.InstrumentedSamplingConfig.ActivityRange, _Mapping]]] = ...) -> None: ...
    COUNTER_PERIOD_NS_FIELD_NUMBER: _ClassVar[int]
    COUNTER_IDS_FIELD_NUMBER: _ClassVar[int]
    COUNTER_NAMES_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENTED_SAMPLING_FIELD_NUMBER: _ClassVar[int]
    INSTRUMENTED_SAMPLING_CONFIG_FIELD_NUMBER: _ClassVar[int]
    FIX_GPU_CLOCK_FIELD_NUMBER: _ClassVar[int]
    counter_period_ns: int
    counter_ids: _containers.RepeatedScalarFieldContainer[int]
    counter_names: _containers.RepeatedScalarFieldContainer[str]
    instrumented_sampling: bool
    instrumented_sampling_config: GpuCounterConfig.InstrumentedSamplingConfig
    fix_gpu_clock: bool
    def __init__(self, counter_period_ns: _Optional[int] = ..., counter_ids: _Optional[_Iterable[int]] = ..., counter_names: _Optional[_Iterable[str]] = ..., instrumented_sampling: _Optional[bool] = ..., instrumented_sampling_config: _Optional[_Union[GpuCounterConfig.InstrumentedSamplingConfig, _Mapping]] = ..., fix_gpu_clock: _Optional[bool] = ...) -> None: ...
