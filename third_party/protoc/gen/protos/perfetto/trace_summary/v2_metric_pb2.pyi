from protos.perfetto.perfetto_sql import structured_query_pb2 as _structured_query_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf.internal import python_message as _python_message
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class TraceMetricV2Spec(_message.Message):
    __slots__ = ("id", "dimensions_specs", "dimensions", "value", "query", "dimension_uniqueness", "unit", "custom_unit", "polarity", "bundle_id", "interned_dimension_specs")
    class DimensionType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        DIMENSION_TYPE_UNSPECIFIED: _ClassVar[TraceMetricV2Spec.DimensionType]
        STRING: _ClassVar[TraceMetricV2Spec.DimensionType]
        INT64: _ClassVar[TraceMetricV2Spec.DimensionType]
        DOUBLE: _ClassVar[TraceMetricV2Spec.DimensionType]
        BOOLEAN: _ClassVar[TraceMetricV2Spec.DimensionType]
    DIMENSION_TYPE_UNSPECIFIED: TraceMetricV2Spec.DimensionType
    STRING: TraceMetricV2Spec.DimensionType
    INT64: TraceMetricV2Spec.DimensionType
    DOUBLE: TraceMetricV2Spec.DimensionType
    BOOLEAN: TraceMetricV2Spec.DimensionType
    class DimensionUniqueness(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        DIMENSION_UNIQUENESS_UNSPECIFIED: _ClassVar[TraceMetricV2Spec.DimensionUniqueness]
        NOT_UNIQUE: _ClassVar[TraceMetricV2Spec.DimensionUniqueness]
        UNIQUE: _ClassVar[TraceMetricV2Spec.DimensionUniqueness]
    DIMENSION_UNIQUENESS_UNSPECIFIED: TraceMetricV2Spec.DimensionUniqueness
    NOT_UNIQUE: TraceMetricV2Spec.DimensionUniqueness
    UNIQUE: TraceMetricV2Spec.DimensionUniqueness
    class MetricUnit(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        METRIC_UNIT_UNSPECIFIED: _ClassVar[TraceMetricV2Spec.MetricUnit]
        COUNT: _ClassVar[TraceMetricV2Spec.MetricUnit]
        TIME_NANOS: _ClassVar[TraceMetricV2Spec.MetricUnit]
        TIME_MICROS: _ClassVar[TraceMetricV2Spec.MetricUnit]
        TIME_MILLIS: _ClassVar[TraceMetricV2Spec.MetricUnit]
        TIME_SECONDS: _ClassVar[TraceMetricV2Spec.MetricUnit]
        TIME_HOURS: _ClassVar[TraceMetricV2Spec.MetricUnit]
        TIME_DAYS: _ClassVar[TraceMetricV2Spec.MetricUnit]
        BYTES: _ClassVar[TraceMetricV2Spec.MetricUnit]
        KILOBYTES: _ClassVar[TraceMetricV2Spec.MetricUnit]
        MEGABYTES: _ClassVar[TraceMetricV2Spec.MetricUnit]
        SECONDS_PER_HOUR: _ClassVar[TraceMetricV2Spec.MetricUnit]
        BOUNDED_PERCENTAGE: _ClassVar[TraceMetricV2Spec.MetricUnit]
        PERCENTAGE: _ClassVar[TraceMetricV2Spec.MetricUnit]
        MINUTES_PER_DAY: _ClassVar[TraceMetricV2Spec.MetricUnit]
        MILLI_AMPS: _ClassVar[TraceMetricV2Spec.MetricUnit]
        PERCENT_PER_HOUR: _ClassVar[TraceMetricV2Spec.MetricUnit]
        MILLI_AMP_HOURS: _ClassVar[TraceMetricV2Spec.MetricUnit]
        PERCENT_PER_HOUR_LEGACY: _ClassVar[TraceMetricV2Spec.MetricUnit]
        MILLI_WATTS: _ClassVar[TraceMetricV2Spec.MetricUnit]
        COUNT_PER_SECOND: _ClassVar[TraceMetricV2Spec.MetricUnit]
        KILOBYTES_PER_HOUR: _ClassVar[TraceMetricV2Spec.MetricUnit]
        MILLI_WATT_HOURS: _ClassVar[TraceMetricV2Spec.MetricUnit]
        COUNT_PER_HOUR: _ClassVar[TraceMetricV2Spec.MetricUnit]
        COUNT_DELTA_PER_HOUR: _ClassVar[TraceMetricV2Spec.MetricUnit]
        BYTES_DELTA_PER_HOUR: _ClassVar[TraceMetricV2Spec.MetricUnit]
        CORRELATION_COEFFICIENT: _ClassVar[TraceMetricV2Spec.MetricUnit]
        MILLI_VOLTS: _ClassVar[TraceMetricV2Spec.MetricUnit]
        CELSIUS: _ClassVar[TraceMetricV2Spec.MetricUnit]
        MICRO_AMP_HOURS: _ClassVar[TraceMetricV2Spec.MetricUnit]
        TIME_MINS: _ClassVar[TraceMetricV2Spec.MetricUnit]
        DECIBEL_MILLIWATTS: _ClassVar[TraceMetricV2Spec.MetricUnit]
        KILOBYTES_PER_SECOND: _ClassVar[TraceMetricV2Spec.MetricUnit]
    METRIC_UNIT_UNSPECIFIED: TraceMetricV2Spec.MetricUnit
    COUNT: TraceMetricV2Spec.MetricUnit
    TIME_NANOS: TraceMetricV2Spec.MetricUnit
    TIME_MICROS: TraceMetricV2Spec.MetricUnit
    TIME_MILLIS: TraceMetricV2Spec.MetricUnit
    TIME_SECONDS: TraceMetricV2Spec.MetricUnit
    TIME_HOURS: TraceMetricV2Spec.MetricUnit
    TIME_DAYS: TraceMetricV2Spec.MetricUnit
    BYTES: TraceMetricV2Spec.MetricUnit
    KILOBYTES: TraceMetricV2Spec.MetricUnit
    MEGABYTES: TraceMetricV2Spec.MetricUnit
    SECONDS_PER_HOUR: TraceMetricV2Spec.MetricUnit
    BOUNDED_PERCENTAGE: TraceMetricV2Spec.MetricUnit
    PERCENTAGE: TraceMetricV2Spec.MetricUnit
    MINUTES_PER_DAY: TraceMetricV2Spec.MetricUnit
    MILLI_AMPS: TraceMetricV2Spec.MetricUnit
    PERCENT_PER_HOUR: TraceMetricV2Spec.MetricUnit
    MILLI_AMP_HOURS: TraceMetricV2Spec.MetricUnit
    PERCENT_PER_HOUR_LEGACY: TraceMetricV2Spec.MetricUnit
    MILLI_WATTS: TraceMetricV2Spec.MetricUnit
    COUNT_PER_SECOND: TraceMetricV2Spec.MetricUnit
    KILOBYTES_PER_HOUR: TraceMetricV2Spec.MetricUnit
    MILLI_WATT_HOURS: TraceMetricV2Spec.MetricUnit
    COUNT_PER_HOUR: TraceMetricV2Spec.MetricUnit
    COUNT_DELTA_PER_HOUR: TraceMetricV2Spec.MetricUnit
    BYTES_DELTA_PER_HOUR: TraceMetricV2Spec.MetricUnit
    CORRELATION_COEFFICIENT: TraceMetricV2Spec.MetricUnit
    MILLI_VOLTS: TraceMetricV2Spec.MetricUnit
    CELSIUS: TraceMetricV2Spec.MetricUnit
    MICRO_AMP_HOURS: TraceMetricV2Spec.MetricUnit
    TIME_MINS: TraceMetricV2Spec.MetricUnit
    DECIBEL_MILLIWATTS: TraceMetricV2Spec.MetricUnit
    KILOBYTES_PER_SECOND: TraceMetricV2Spec.MetricUnit
    class MetricPolarity(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        POLARITY_UNSPECIFIED: _ClassVar[TraceMetricV2Spec.MetricPolarity]
        HIGHER_IS_BETTER: _ClassVar[TraceMetricV2Spec.MetricPolarity]
        LOWER_IS_BETTER: _ClassVar[TraceMetricV2Spec.MetricPolarity]
        NOT_APPLICABLE: _ClassVar[TraceMetricV2Spec.MetricPolarity]
    POLARITY_UNSPECIFIED: TraceMetricV2Spec.MetricPolarity
    HIGHER_IS_BETTER: TraceMetricV2Spec.MetricPolarity
    LOWER_IS_BETTER: TraceMetricV2Spec.MetricPolarity
    NOT_APPLICABLE: TraceMetricV2Spec.MetricPolarity
    class DimensionSpec(_message.Message):
        __slots__ = ("name", "type", "display_name", "display_help", "doc_link")
        NAME_FIELD_NUMBER: _ClassVar[int]
        TYPE_FIELD_NUMBER: _ClassVar[int]
        DISPLAY_NAME_FIELD_NUMBER: _ClassVar[int]
        DISPLAY_HELP_FIELD_NUMBER: _ClassVar[int]
        DOC_LINK_FIELD_NUMBER: _ClassVar[int]
        name: str
        type: TraceMetricV2Spec.DimensionType
        display_name: str
        display_help: str
        doc_link: str
        def __init__(self, name: _Optional[str] = ..., type: _Optional[_Union[TraceMetricV2Spec.DimensionType, str]] = ..., display_name: _Optional[str] = ..., display_help: _Optional[str] = ..., doc_link: _Optional[str] = ...) -> None: ...
    class InternedDimensionSpec(_message.Message):
        __slots__ = ("key_column_spec", "data_column_specs", "query")
        class ColumnSpec(_message.Message):
            __slots__ = ("name", "type")
            NAME_FIELD_NUMBER: _ClassVar[int]
            TYPE_FIELD_NUMBER: _ClassVar[int]
            name: str
            type: TraceMetricV2Spec.DimensionType
            def __init__(self, name: _Optional[str] = ..., type: _Optional[_Union[TraceMetricV2Spec.DimensionType, str]] = ...) -> None: ...
        KEY_COLUMN_SPEC_FIELD_NUMBER: _ClassVar[int]
        DATA_COLUMN_SPECS_FIELD_NUMBER: _ClassVar[int]
        QUERY_FIELD_NUMBER: _ClassVar[int]
        key_column_spec: TraceMetricV2Spec.InternedDimensionSpec.ColumnSpec
        data_column_specs: _containers.RepeatedCompositeFieldContainer[TraceMetricV2Spec.InternedDimensionSpec.ColumnSpec]
        query: _structured_query_pb2.PerfettoSqlStructuredQuery
        def __init__(self, key_column_spec: _Optional[_Union[TraceMetricV2Spec.InternedDimensionSpec.ColumnSpec, _Mapping]] = ..., data_column_specs: _Optional[_Iterable[_Union[TraceMetricV2Spec.InternedDimensionSpec.ColumnSpec, _Mapping]]] = ..., query: _Optional[_Union[_structured_query_pb2.PerfettoSqlStructuredQuery, _Mapping]] = ...) -> None: ...
    ID_FIELD_NUMBER: _ClassVar[int]
    DIMENSIONS_SPECS_FIELD_NUMBER: _ClassVar[int]
    DIMENSIONS_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    QUERY_FIELD_NUMBER: _ClassVar[int]
    DIMENSION_UNIQUENESS_FIELD_NUMBER: _ClassVar[int]
    UNIT_FIELD_NUMBER: _ClassVar[int]
    CUSTOM_UNIT_FIELD_NUMBER: _ClassVar[int]
    POLARITY_FIELD_NUMBER: _ClassVar[int]
    BUNDLE_ID_FIELD_NUMBER: _ClassVar[int]
    INTERNED_DIMENSION_SPECS_FIELD_NUMBER: _ClassVar[int]
    id: str
    dimensions_specs: _containers.RepeatedCompositeFieldContainer[TraceMetricV2Spec.DimensionSpec]
    dimensions: _containers.RepeatedScalarFieldContainer[str]
    value: str
    query: _structured_query_pb2.PerfettoSqlStructuredQuery
    dimension_uniqueness: TraceMetricV2Spec.DimensionUniqueness
    unit: TraceMetricV2Spec.MetricUnit
    custom_unit: str
    polarity: TraceMetricV2Spec.MetricPolarity
    bundle_id: str
    interned_dimension_specs: _containers.RepeatedCompositeFieldContainer[TraceMetricV2Spec.InternedDimensionSpec]
    def __init__(self, id: _Optional[str] = ..., dimensions_specs: _Optional[_Iterable[_Union[TraceMetricV2Spec.DimensionSpec, _Mapping]]] = ..., dimensions: _Optional[_Iterable[str]] = ..., value: _Optional[str] = ..., query: _Optional[_Union[_structured_query_pb2.PerfettoSqlStructuredQuery, _Mapping]] = ..., dimension_uniqueness: _Optional[_Union[TraceMetricV2Spec.DimensionUniqueness, str]] = ..., unit: _Optional[_Union[TraceMetricV2Spec.MetricUnit, str]] = ..., custom_unit: _Optional[str] = ..., polarity: _Optional[_Union[TraceMetricV2Spec.MetricPolarity, str]] = ..., bundle_id: _Optional[str] = ..., interned_dimension_specs: _Optional[_Iterable[_Union[TraceMetricV2Spec.InternedDimensionSpec, _Mapping]]] = ...) -> None: ...

class TraceMetricV2TemplateSpec(_message.Message):
    __slots__ = ("id_prefix", "dimensions_specs", "dimensions", "value_columns", "value_column_specs", "interned_dimension_specs", "query", "dimension_uniqueness", "disable_auto_bundling")
    class ValueColumnSpec(_message.Message):
        __slots__ = ("name", "unit", "custom_unit", "polarity", "display_name", "display_help", "doc_link")
        Extensions: _python_message._ExtensionDict
        NAME_FIELD_NUMBER: _ClassVar[int]
        UNIT_FIELD_NUMBER: _ClassVar[int]
        CUSTOM_UNIT_FIELD_NUMBER: _ClassVar[int]
        POLARITY_FIELD_NUMBER: _ClassVar[int]
        DISPLAY_NAME_FIELD_NUMBER: _ClassVar[int]
        DISPLAY_HELP_FIELD_NUMBER: _ClassVar[int]
        DOC_LINK_FIELD_NUMBER: _ClassVar[int]
        name: str
        unit: TraceMetricV2Spec.MetricUnit
        custom_unit: str
        polarity: TraceMetricV2Spec.MetricPolarity
        display_name: str
        display_help: str
        doc_link: str
        def __init__(self, name: _Optional[str] = ..., unit: _Optional[_Union[TraceMetricV2Spec.MetricUnit, str]] = ..., custom_unit: _Optional[str] = ..., polarity: _Optional[_Union[TraceMetricV2Spec.MetricPolarity, str]] = ..., display_name: _Optional[str] = ..., display_help: _Optional[str] = ..., doc_link: _Optional[str] = ...) -> None: ...
    ID_PREFIX_FIELD_NUMBER: _ClassVar[int]
    DIMENSIONS_SPECS_FIELD_NUMBER: _ClassVar[int]
    DIMENSIONS_FIELD_NUMBER: _ClassVar[int]
    VALUE_COLUMNS_FIELD_NUMBER: _ClassVar[int]
    VALUE_COLUMN_SPECS_FIELD_NUMBER: _ClassVar[int]
    INTERNED_DIMENSION_SPECS_FIELD_NUMBER: _ClassVar[int]
    QUERY_FIELD_NUMBER: _ClassVar[int]
    DIMENSION_UNIQUENESS_FIELD_NUMBER: _ClassVar[int]
    DISABLE_AUTO_BUNDLING_FIELD_NUMBER: _ClassVar[int]
    id_prefix: str
    dimensions_specs: _containers.RepeatedCompositeFieldContainer[TraceMetricV2Spec.DimensionSpec]
    dimensions: _containers.RepeatedScalarFieldContainer[str]
    value_columns: _containers.RepeatedScalarFieldContainer[str]
    value_column_specs: _containers.RepeatedCompositeFieldContainer[TraceMetricV2TemplateSpec.ValueColumnSpec]
    interned_dimension_specs: _containers.RepeatedCompositeFieldContainer[TraceMetricV2Spec.InternedDimensionSpec]
    query: _structured_query_pb2.PerfettoSqlStructuredQuery
    dimension_uniqueness: TraceMetricV2Spec.DimensionUniqueness
    disable_auto_bundling: bool
    def __init__(self, id_prefix: _Optional[str] = ..., dimensions_specs: _Optional[_Iterable[_Union[TraceMetricV2Spec.DimensionSpec, _Mapping]]] = ..., dimensions: _Optional[_Iterable[str]] = ..., value_columns: _Optional[_Iterable[str]] = ..., value_column_specs: _Optional[_Iterable[_Union[TraceMetricV2TemplateSpec.ValueColumnSpec, _Mapping]]] = ..., interned_dimension_specs: _Optional[_Iterable[_Union[TraceMetricV2Spec.InternedDimensionSpec, _Mapping]]] = ..., query: _Optional[_Union[_structured_query_pb2.PerfettoSqlStructuredQuery, _Mapping]] = ..., dimension_uniqueness: _Optional[_Union[TraceMetricV2Spec.DimensionUniqueness, str]] = ..., disable_auto_bundling: _Optional[bool] = ...) -> None: ...

class TraceMetricV2Bundle(_message.Message):
    __slots__ = ("bundle_id", "row", "specs", "interned_dimension_bundles")
    class Row(_message.Message):
        __slots__ = ("values", "dimension")
        class Value(_message.Message):
            __slots__ = ("null_value", "double_value")
            class Null(_message.Message):
                __slots__ = ()
                def __init__(self) -> None: ...
            NULL_VALUE_FIELD_NUMBER: _ClassVar[int]
            DOUBLE_VALUE_FIELD_NUMBER: _ClassVar[int]
            null_value: TraceMetricV2Bundle.Row.Value.Null
            double_value: float
            def __init__(self, null_value: _Optional[_Union[TraceMetricV2Bundle.Row.Value.Null, _Mapping]] = ..., double_value: _Optional[float] = ...) -> None: ...
        class Dimension(_message.Message):
            __slots__ = ("string_value", "int64_value", "double_value", "null_value", "bool_value")
            class Null(_message.Message):
                __slots__ = ()
                def __init__(self) -> None: ...
            STRING_VALUE_FIELD_NUMBER: _ClassVar[int]
            INT64_VALUE_FIELD_NUMBER: _ClassVar[int]
            DOUBLE_VALUE_FIELD_NUMBER: _ClassVar[int]
            NULL_VALUE_FIELD_NUMBER: _ClassVar[int]
            BOOL_VALUE_FIELD_NUMBER: _ClassVar[int]
            string_value: str
            int64_value: int
            double_value: float
            null_value: TraceMetricV2Bundle.Row.Dimension.Null
            bool_value: bool
            def __init__(self, string_value: _Optional[str] = ..., int64_value: _Optional[int] = ..., double_value: _Optional[float] = ..., null_value: _Optional[_Union[TraceMetricV2Bundle.Row.Dimension.Null, _Mapping]] = ..., bool_value: _Optional[bool] = ...) -> None: ...
        VALUES_FIELD_NUMBER: _ClassVar[int]
        DIMENSION_FIELD_NUMBER: _ClassVar[int]
        values: _containers.RepeatedCompositeFieldContainer[TraceMetricV2Bundle.Row.Value]
        dimension: _containers.RepeatedCompositeFieldContainer[TraceMetricV2Bundle.Row.Dimension]
        def __init__(self, values: _Optional[_Iterable[_Union[TraceMetricV2Bundle.Row.Value, _Mapping]]] = ..., dimension: _Optional[_Iterable[_Union[TraceMetricV2Bundle.Row.Dimension, _Mapping]]] = ...) -> None: ...
    class InternedDimensionBundle(_message.Message):
        __slots__ = ("interned_dimension_rows",)
        class InternedDimensionRow(_message.Message):
            __slots__ = ("key_dimension_value", "interned_dimension_values")
            KEY_DIMENSION_VALUE_FIELD_NUMBER: _ClassVar[int]
            INTERNED_DIMENSION_VALUES_FIELD_NUMBER: _ClassVar[int]
            key_dimension_value: TraceMetricV2Bundle.Row.Dimension
            interned_dimension_values: _containers.RepeatedCompositeFieldContainer[TraceMetricV2Bundle.Row.Dimension]
            def __init__(self, key_dimension_value: _Optional[_Union[TraceMetricV2Bundle.Row.Dimension, _Mapping]] = ..., interned_dimension_values: _Optional[_Iterable[_Union[TraceMetricV2Bundle.Row.Dimension, _Mapping]]] = ...) -> None: ...
        INTERNED_DIMENSION_ROWS_FIELD_NUMBER: _ClassVar[int]
        interned_dimension_rows: _containers.RepeatedCompositeFieldContainer[TraceMetricV2Bundle.InternedDimensionBundle.InternedDimensionRow]
        def __init__(self, interned_dimension_rows: _Optional[_Iterable[_Union[TraceMetricV2Bundle.InternedDimensionBundle.InternedDimensionRow, _Mapping]]] = ...) -> None: ...
    BUNDLE_ID_FIELD_NUMBER: _ClassVar[int]
    ROW_FIELD_NUMBER: _ClassVar[int]
    SPECS_FIELD_NUMBER: _ClassVar[int]
    INTERNED_DIMENSION_BUNDLES_FIELD_NUMBER: _ClassVar[int]
    bundle_id: str
    row: _containers.RepeatedCompositeFieldContainer[TraceMetricV2Bundle.Row]
    specs: _containers.RepeatedCompositeFieldContainer[TraceMetricV2Spec]
    interned_dimension_bundles: _containers.RepeatedCompositeFieldContainer[TraceMetricV2Bundle.InternedDimensionBundle]
    def __init__(self, bundle_id: _Optional[str] = ..., row: _Optional[_Iterable[_Union[TraceMetricV2Bundle.Row, _Mapping]]] = ..., specs: _Optional[_Iterable[_Union[TraceMetricV2Spec, _Mapping]]] = ..., interned_dimension_bundles: _Optional[_Iterable[_Union[TraceMetricV2Bundle.InternedDimensionBundle, _Mapping]]] = ...) -> None: ...
