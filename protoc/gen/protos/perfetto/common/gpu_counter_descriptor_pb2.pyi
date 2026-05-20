from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class GpuCounterDescriptor(_message.Message):
    __slots__ = ("specs", "blocks", "counter_groups", "min_sampling_period_ns", "max_sampling_period_ns", "supports_instrumented_sampling", "supports_counter_names", "supports_counter_name_globs")
    class GpuCounterGroup(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        UNCLASSIFIED: _ClassVar[GpuCounterDescriptor.GpuCounterGroup]
        SYSTEM: _ClassVar[GpuCounterDescriptor.GpuCounterGroup]
        VERTICES: _ClassVar[GpuCounterDescriptor.GpuCounterGroup]
        FRAGMENTS: _ClassVar[GpuCounterDescriptor.GpuCounterGroup]
        PRIMITIVES: _ClassVar[GpuCounterDescriptor.GpuCounterGroup]
        MEMORY: _ClassVar[GpuCounterDescriptor.GpuCounterGroup]
        COMPUTE: _ClassVar[GpuCounterDescriptor.GpuCounterGroup]
        RAY_TRACING: _ClassVar[GpuCounterDescriptor.GpuCounterGroup]
    UNCLASSIFIED: GpuCounterDescriptor.GpuCounterGroup
    SYSTEM: GpuCounterDescriptor.GpuCounterGroup
    VERTICES: GpuCounterDescriptor.GpuCounterGroup
    FRAGMENTS: GpuCounterDescriptor.GpuCounterGroup
    PRIMITIVES: GpuCounterDescriptor.GpuCounterGroup
    MEMORY: GpuCounterDescriptor.GpuCounterGroup
    COMPUTE: GpuCounterDescriptor.GpuCounterGroup
    RAY_TRACING: GpuCounterDescriptor.GpuCounterGroup
    class MeasureUnit(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        NONE: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        BIT: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        KILOBIT: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        MEGABIT: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        GIGABIT: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        TERABIT: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        PETABIT: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        BYTE: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        KILOBYTE: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        MEGABYTE: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        GIGABYTE: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        TERABYTE: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        PETABYTE: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        HERTZ: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        KILOHERTZ: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        MEGAHERTZ: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        GIGAHERTZ: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        TERAHERTZ: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        PETAHERTZ: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        NANOSECOND: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        MICROSECOND: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        MILLISECOND: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        SECOND: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        MINUTE: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        HOUR: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        VERTEX: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        PIXEL: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        TRIANGLE: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        PRIMITIVE: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        FRAGMENT: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        MILLIWATT: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        WATT: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        KILOWATT: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        JOULE: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        VOLT: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        AMPERE: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        CELSIUS: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        FAHRENHEIT: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        KELVIN: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        PERCENT: _ClassVar[GpuCounterDescriptor.MeasureUnit]
        INSTRUCTION: _ClassVar[GpuCounterDescriptor.MeasureUnit]
    NONE: GpuCounterDescriptor.MeasureUnit
    BIT: GpuCounterDescriptor.MeasureUnit
    KILOBIT: GpuCounterDescriptor.MeasureUnit
    MEGABIT: GpuCounterDescriptor.MeasureUnit
    GIGABIT: GpuCounterDescriptor.MeasureUnit
    TERABIT: GpuCounterDescriptor.MeasureUnit
    PETABIT: GpuCounterDescriptor.MeasureUnit
    BYTE: GpuCounterDescriptor.MeasureUnit
    KILOBYTE: GpuCounterDescriptor.MeasureUnit
    MEGABYTE: GpuCounterDescriptor.MeasureUnit
    GIGABYTE: GpuCounterDescriptor.MeasureUnit
    TERABYTE: GpuCounterDescriptor.MeasureUnit
    PETABYTE: GpuCounterDescriptor.MeasureUnit
    HERTZ: GpuCounterDescriptor.MeasureUnit
    KILOHERTZ: GpuCounterDescriptor.MeasureUnit
    MEGAHERTZ: GpuCounterDescriptor.MeasureUnit
    GIGAHERTZ: GpuCounterDescriptor.MeasureUnit
    TERAHERTZ: GpuCounterDescriptor.MeasureUnit
    PETAHERTZ: GpuCounterDescriptor.MeasureUnit
    NANOSECOND: GpuCounterDescriptor.MeasureUnit
    MICROSECOND: GpuCounterDescriptor.MeasureUnit
    MILLISECOND: GpuCounterDescriptor.MeasureUnit
    SECOND: GpuCounterDescriptor.MeasureUnit
    MINUTE: GpuCounterDescriptor.MeasureUnit
    HOUR: GpuCounterDescriptor.MeasureUnit
    VERTEX: GpuCounterDescriptor.MeasureUnit
    PIXEL: GpuCounterDescriptor.MeasureUnit
    TRIANGLE: GpuCounterDescriptor.MeasureUnit
    PRIMITIVE: GpuCounterDescriptor.MeasureUnit
    FRAGMENT: GpuCounterDescriptor.MeasureUnit
    MILLIWATT: GpuCounterDescriptor.MeasureUnit
    WATT: GpuCounterDescriptor.MeasureUnit
    KILOWATT: GpuCounterDescriptor.MeasureUnit
    JOULE: GpuCounterDescriptor.MeasureUnit
    VOLT: GpuCounterDescriptor.MeasureUnit
    AMPERE: GpuCounterDescriptor.MeasureUnit
    CELSIUS: GpuCounterDescriptor.MeasureUnit
    FAHRENHEIT: GpuCounterDescriptor.MeasureUnit
    KELVIN: GpuCounterDescriptor.MeasureUnit
    PERCENT: GpuCounterDescriptor.MeasureUnit
    INSTRUCTION: GpuCounterDescriptor.MeasureUnit
    class GpuCounterSpec(_message.Message):
        __slots__ = ("counter_id", "name", "description", "int_peak_value", "double_peak_value", "numerator_units", "denominator_units", "select_by_default", "groups")
        COUNTER_ID_FIELD_NUMBER: _ClassVar[int]
        NAME_FIELD_NUMBER: _ClassVar[int]
        DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
        INT_PEAK_VALUE_FIELD_NUMBER: _ClassVar[int]
        DOUBLE_PEAK_VALUE_FIELD_NUMBER: _ClassVar[int]
        NUMERATOR_UNITS_FIELD_NUMBER: _ClassVar[int]
        DENOMINATOR_UNITS_FIELD_NUMBER: _ClassVar[int]
        SELECT_BY_DEFAULT_FIELD_NUMBER: _ClassVar[int]
        GROUPS_FIELD_NUMBER: _ClassVar[int]
        counter_id: int
        name: str
        description: str
        int_peak_value: int
        double_peak_value: float
        numerator_units: _containers.RepeatedScalarFieldContainer[GpuCounterDescriptor.MeasureUnit]
        denominator_units: _containers.RepeatedScalarFieldContainer[GpuCounterDescriptor.MeasureUnit]
        select_by_default: bool
        groups: _containers.RepeatedScalarFieldContainer[GpuCounterDescriptor.GpuCounterGroup]
        def __init__(self, counter_id: _Optional[int] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., int_peak_value: _Optional[int] = ..., double_peak_value: _Optional[float] = ..., numerator_units: _Optional[_Iterable[_Union[GpuCounterDescriptor.MeasureUnit, str]]] = ..., denominator_units: _Optional[_Iterable[_Union[GpuCounterDescriptor.MeasureUnit, str]]] = ..., select_by_default: _Optional[bool] = ..., groups: _Optional[_Iterable[_Union[GpuCounterDescriptor.GpuCounterGroup, str]]] = ...) -> None: ...
    class GpuCounterBlock(_message.Message):
        __slots__ = ("block_id", "block_capacity", "name", "description", "counter_ids")
        BLOCK_ID_FIELD_NUMBER: _ClassVar[int]
        BLOCK_CAPACITY_FIELD_NUMBER: _ClassVar[int]
        NAME_FIELD_NUMBER: _ClassVar[int]
        DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
        COUNTER_IDS_FIELD_NUMBER: _ClassVar[int]
        block_id: int
        block_capacity: int
        name: str
        description: str
        counter_ids: _containers.RepeatedScalarFieldContainer[int]
        def __init__(self, block_id: _Optional[int] = ..., block_capacity: _Optional[int] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., counter_ids: _Optional[_Iterable[int]] = ...) -> None: ...
    class GpuCounterGroupSpec(_message.Message):
        __slots__ = ("group_id", "name", "description", "counter_ids")
        GROUP_ID_FIELD_NUMBER: _ClassVar[int]
        NAME_FIELD_NUMBER: _ClassVar[int]
        DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
        COUNTER_IDS_FIELD_NUMBER: _ClassVar[int]
        group_id: int
        name: str
        description: str
        counter_ids: _containers.RepeatedScalarFieldContainer[int]
        def __init__(self, group_id: _Optional[int] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., counter_ids: _Optional[_Iterable[int]] = ...) -> None: ...
    SPECS_FIELD_NUMBER: _ClassVar[int]
    BLOCKS_FIELD_NUMBER: _ClassVar[int]
    COUNTER_GROUPS_FIELD_NUMBER: _ClassVar[int]
    MIN_SAMPLING_PERIOD_NS_FIELD_NUMBER: _ClassVar[int]
    MAX_SAMPLING_PERIOD_NS_FIELD_NUMBER: _ClassVar[int]
    SUPPORTS_INSTRUMENTED_SAMPLING_FIELD_NUMBER: _ClassVar[int]
    SUPPORTS_COUNTER_NAMES_FIELD_NUMBER: _ClassVar[int]
    SUPPORTS_COUNTER_NAME_GLOBS_FIELD_NUMBER: _ClassVar[int]
    specs: _containers.RepeatedCompositeFieldContainer[GpuCounterDescriptor.GpuCounterSpec]
    blocks: _containers.RepeatedCompositeFieldContainer[GpuCounterDescriptor.GpuCounterBlock]
    counter_groups: _containers.RepeatedCompositeFieldContainer[GpuCounterDescriptor.GpuCounterGroupSpec]
    min_sampling_period_ns: int
    max_sampling_period_ns: int
    supports_instrumented_sampling: bool
    supports_counter_names: bool
    supports_counter_name_globs: bool
    def __init__(self, specs: _Optional[_Iterable[_Union[GpuCounterDescriptor.GpuCounterSpec, _Mapping]]] = ..., blocks: _Optional[_Iterable[_Union[GpuCounterDescriptor.GpuCounterBlock, _Mapping]]] = ..., counter_groups: _Optional[_Iterable[_Union[GpuCounterDescriptor.GpuCounterGroupSpec, _Mapping]]] = ..., min_sampling_period_ns: _Optional[int] = ..., max_sampling_period_ns: _Optional[int] = ..., supports_instrumented_sampling: _Optional[bool] = ..., supports_counter_names: _Optional[bool] = ..., supports_counter_name_globs: _Optional[bool] = ...) -> None: ...
