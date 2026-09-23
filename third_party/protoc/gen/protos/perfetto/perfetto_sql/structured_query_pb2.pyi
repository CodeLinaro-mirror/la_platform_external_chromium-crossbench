from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class PerfettoSqlStructuredQuery(_message.Message):
    __slots__ = ("id", "referenced_modules", "table", "sql", "simple_slices", "inner_query", "inner_query_id", "interval_intersect", "experimental_join", "experimental_union", "experimental_add_columns", "experimental_create_slices", "experimental_time_range", "experimental_filter_to_intervals", "experimental_counter_intervals", "experimental_filter_in", "filters", "group_by", "select_columns", "order_by", "limit", "offset", "experimental_filter_group")
    class Table(_message.Message):
        __slots__ = ("table_name", "column_names", "module_name")
        TABLE_NAME_FIELD_NUMBER: _ClassVar[int]
        COLUMN_NAMES_FIELD_NUMBER: _ClassVar[int]
        MODULE_NAME_FIELD_NUMBER: _ClassVar[int]
        table_name: str
        column_names: _containers.RepeatedScalarFieldContainer[str]
        module_name: str
        def __init__(self, table_name: _Optional[str] = ..., column_names: _Optional[_Iterable[str]] = ..., module_name: _Optional[str] = ...) -> None: ...
    class SimpleSlices(_message.Message):
        __slots__ = ("slice_name_glob", "thread_name_glob", "process_name_glob", "track_name_glob")
        SLICE_NAME_GLOB_FIELD_NUMBER: _ClassVar[int]
        THREAD_NAME_GLOB_FIELD_NUMBER: _ClassVar[int]
        PROCESS_NAME_GLOB_FIELD_NUMBER: _ClassVar[int]
        TRACK_NAME_GLOB_FIELD_NUMBER: _ClassVar[int]
        slice_name_glob: str
        thread_name_glob: str
        process_name_glob: str
        track_name_glob: str
        def __init__(self, slice_name_glob: _Optional[str] = ..., thread_name_glob: _Optional[str] = ..., process_name_glob: _Optional[str] = ..., track_name_glob: _Optional[str] = ...) -> None: ...
    class Sql(_message.Message):
        __slots__ = ("sql", "column_names", "dependencies", "preamble")
        class Dependency(_message.Message):
            __slots__ = ("alias", "query")
            ALIAS_FIELD_NUMBER: _ClassVar[int]
            QUERY_FIELD_NUMBER: _ClassVar[int]
            alias: str
            query: PerfettoSqlStructuredQuery
            def __init__(self, alias: _Optional[str] = ..., query: _Optional[_Union[PerfettoSqlStructuredQuery, _Mapping]] = ...) -> None: ...
        SQL_FIELD_NUMBER: _ClassVar[int]
        COLUMN_NAMES_FIELD_NUMBER: _ClassVar[int]
        DEPENDENCIES_FIELD_NUMBER: _ClassVar[int]
        PREAMBLE_FIELD_NUMBER: _ClassVar[int]
        sql: str
        column_names: _containers.RepeatedScalarFieldContainer[str]
        dependencies: _containers.RepeatedCompositeFieldContainer[PerfettoSqlStructuredQuery.Sql.Dependency]
        preamble: str
        def __init__(self, sql: _Optional[str] = ..., column_names: _Optional[_Iterable[str]] = ..., dependencies: _Optional[_Iterable[_Union[PerfettoSqlStructuredQuery.Sql.Dependency, _Mapping]]] = ..., preamble: _Optional[str] = ...) -> None: ...
    class IntervalIntersect(_message.Message):
        __slots__ = ("base", "interval_intersect", "partition_columns")
        BASE_FIELD_NUMBER: _ClassVar[int]
        INTERVAL_INTERSECT_FIELD_NUMBER: _ClassVar[int]
        PARTITION_COLUMNS_FIELD_NUMBER: _ClassVar[int]
        base: PerfettoSqlStructuredQuery
        interval_intersect: _containers.RepeatedCompositeFieldContainer[PerfettoSqlStructuredQuery]
        partition_columns: _containers.RepeatedScalarFieldContainer[str]
        def __init__(self, base: _Optional[_Union[PerfettoSqlStructuredQuery, _Mapping]] = ..., interval_intersect: _Optional[_Iterable[_Union[PerfettoSqlStructuredQuery, _Mapping]]] = ..., partition_columns: _Optional[_Iterable[str]] = ...) -> None: ...
    class ExperimentalFilterToIntervals(_message.Message):
        __slots__ = ("base", "intervals", "partition_columns", "clip_to_intervals", "select_columns")
        BASE_FIELD_NUMBER: _ClassVar[int]
        INTERVALS_FIELD_NUMBER: _ClassVar[int]
        PARTITION_COLUMNS_FIELD_NUMBER: _ClassVar[int]
        CLIP_TO_INTERVALS_FIELD_NUMBER: _ClassVar[int]
        SELECT_COLUMNS_FIELD_NUMBER: _ClassVar[int]
        base: PerfettoSqlStructuredQuery
        intervals: PerfettoSqlStructuredQuery
        partition_columns: _containers.RepeatedScalarFieldContainer[str]
        clip_to_intervals: bool
        select_columns: _containers.RepeatedScalarFieldContainer[str]
        def __init__(self, base: _Optional[_Union[PerfettoSqlStructuredQuery, _Mapping]] = ..., intervals: _Optional[_Union[PerfettoSqlStructuredQuery, _Mapping]] = ..., partition_columns: _Optional[_Iterable[str]] = ..., clip_to_intervals: _Optional[bool] = ..., select_columns: _Optional[_Iterable[str]] = ...) -> None: ...
    class ExperimentalTimeRange(_message.Message):
        __slots__ = ("mode", "ts", "dur")
        class Mode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            STATIC: _ClassVar[PerfettoSqlStructuredQuery.ExperimentalTimeRange.Mode]
            DYNAMIC: _ClassVar[PerfettoSqlStructuredQuery.ExperimentalTimeRange.Mode]
        STATIC: PerfettoSqlStructuredQuery.ExperimentalTimeRange.Mode
        DYNAMIC: PerfettoSqlStructuredQuery.ExperimentalTimeRange.Mode
        MODE_FIELD_NUMBER: _ClassVar[int]
        TS_FIELD_NUMBER: _ClassVar[int]
        DUR_FIELD_NUMBER: _ClassVar[int]
        mode: PerfettoSqlStructuredQuery.ExperimentalTimeRange.Mode
        ts: int
        dur: int
        def __init__(self, mode: _Optional[_Union[PerfettoSqlStructuredQuery.ExperimentalTimeRange.Mode, str]] = ..., ts: _Optional[int] = ..., dur: _Optional[int] = ...) -> None: ...
    class ExperimentalJoin(_message.Message):
        __slots__ = ("type", "left_query", "right_query", "equality_columns", "freeform_condition")
        class Type(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            INNER: _ClassVar[PerfettoSqlStructuredQuery.ExperimentalJoin.Type]
            LEFT: _ClassVar[PerfettoSqlStructuredQuery.ExperimentalJoin.Type]
        INNER: PerfettoSqlStructuredQuery.ExperimentalJoin.Type
        LEFT: PerfettoSqlStructuredQuery.ExperimentalJoin.Type
        class EqualityColumns(_message.Message):
            __slots__ = ("left_column", "right_column")
            LEFT_COLUMN_FIELD_NUMBER: _ClassVar[int]
            RIGHT_COLUMN_FIELD_NUMBER: _ClassVar[int]
            left_column: str
            right_column: str
            def __init__(self, left_column: _Optional[str] = ..., right_column: _Optional[str] = ...) -> None: ...
        class FreeformCondition(_message.Message):
            __slots__ = ("left_query_alias", "right_query_alias", "sql_expression")
            LEFT_QUERY_ALIAS_FIELD_NUMBER: _ClassVar[int]
            RIGHT_QUERY_ALIAS_FIELD_NUMBER: _ClassVar[int]
            SQL_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
            left_query_alias: str
            right_query_alias: str
            sql_expression: str
            def __init__(self, left_query_alias: _Optional[str] = ..., right_query_alias: _Optional[str] = ..., sql_expression: _Optional[str] = ...) -> None: ...
        TYPE_FIELD_NUMBER: _ClassVar[int]
        LEFT_QUERY_FIELD_NUMBER: _ClassVar[int]
        RIGHT_QUERY_FIELD_NUMBER: _ClassVar[int]
        EQUALITY_COLUMNS_FIELD_NUMBER: _ClassVar[int]
        FREEFORM_CONDITION_FIELD_NUMBER: _ClassVar[int]
        type: PerfettoSqlStructuredQuery.ExperimentalJoin.Type
        left_query: PerfettoSqlStructuredQuery
        right_query: PerfettoSqlStructuredQuery
        equality_columns: PerfettoSqlStructuredQuery.ExperimentalJoin.EqualityColumns
        freeform_condition: PerfettoSqlStructuredQuery.ExperimentalJoin.FreeformCondition
        def __init__(self, type: _Optional[_Union[PerfettoSqlStructuredQuery.ExperimentalJoin.Type, str]] = ..., left_query: _Optional[_Union[PerfettoSqlStructuredQuery, _Mapping]] = ..., right_query: _Optional[_Union[PerfettoSqlStructuredQuery, _Mapping]] = ..., equality_columns: _Optional[_Union[PerfettoSqlStructuredQuery.ExperimentalJoin.EqualityColumns, _Mapping]] = ..., freeform_condition: _Optional[_Union[PerfettoSqlStructuredQuery.ExperimentalJoin.FreeformCondition, _Mapping]] = ...) -> None: ...
    class ExperimentalUnion(_message.Message):
        __slots__ = ("queries", "use_union_all")
        QUERIES_FIELD_NUMBER: _ClassVar[int]
        USE_UNION_ALL_FIELD_NUMBER: _ClassVar[int]
        queries: _containers.RepeatedCompositeFieldContainer[PerfettoSqlStructuredQuery]
        use_union_all: bool
        def __init__(self, queries: _Optional[_Iterable[_Union[PerfettoSqlStructuredQuery, _Mapping]]] = ..., use_union_all: _Optional[bool] = ...) -> None: ...
    class ExperimentalAddColumns(_message.Message):
        __slots__ = ("core_query", "input_query", "input_columns", "equality_columns", "freeform_condition")
        CORE_QUERY_FIELD_NUMBER: _ClassVar[int]
        INPUT_QUERY_FIELD_NUMBER: _ClassVar[int]
        INPUT_COLUMNS_FIELD_NUMBER: _ClassVar[int]
        EQUALITY_COLUMNS_FIELD_NUMBER: _ClassVar[int]
        FREEFORM_CONDITION_FIELD_NUMBER: _ClassVar[int]
        core_query: PerfettoSqlStructuredQuery
        input_query: PerfettoSqlStructuredQuery
        input_columns: _containers.RepeatedCompositeFieldContainer[PerfettoSqlStructuredQuery.SelectColumn]
        equality_columns: PerfettoSqlStructuredQuery.ExperimentalJoin.EqualityColumns
        freeform_condition: PerfettoSqlStructuredQuery.ExperimentalJoin.FreeformCondition
        def __init__(self, core_query: _Optional[_Union[PerfettoSqlStructuredQuery, _Mapping]] = ..., input_query: _Optional[_Union[PerfettoSqlStructuredQuery, _Mapping]] = ..., input_columns: _Optional[_Iterable[_Union[PerfettoSqlStructuredQuery.SelectColumn, _Mapping]]] = ..., equality_columns: _Optional[_Union[PerfettoSqlStructuredQuery.ExperimentalJoin.EqualityColumns, _Mapping]] = ..., freeform_condition: _Optional[_Union[PerfettoSqlStructuredQuery.ExperimentalJoin.FreeformCondition, _Mapping]] = ...) -> None: ...
    class ExperimentalCreateSlices(_message.Message):
        __slots__ = ("starts_query", "ends_query", "starts_ts_column", "ends_ts_column")
        STARTS_QUERY_FIELD_NUMBER: _ClassVar[int]
        ENDS_QUERY_FIELD_NUMBER: _ClassVar[int]
        STARTS_TS_COLUMN_FIELD_NUMBER: _ClassVar[int]
        ENDS_TS_COLUMN_FIELD_NUMBER: _ClassVar[int]
        starts_query: PerfettoSqlStructuredQuery
        ends_query: PerfettoSqlStructuredQuery
        starts_ts_column: str
        ends_ts_column: str
        def __init__(self, starts_query: _Optional[_Union[PerfettoSqlStructuredQuery, _Mapping]] = ..., ends_query: _Optional[_Union[PerfettoSqlStructuredQuery, _Mapping]] = ..., starts_ts_column: _Optional[str] = ..., ends_ts_column: _Optional[str] = ...) -> None: ...
    class ExperimentalCounterIntervals(_message.Message):
        __slots__ = ("input_query",)
        INPUT_QUERY_FIELD_NUMBER: _ClassVar[int]
        input_query: PerfettoSqlStructuredQuery
        def __init__(self, input_query: _Optional[_Union[PerfettoSqlStructuredQuery, _Mapping]] = ...) -> None: ...
    class ExperimentalFilterIn(_message.Message):
        __slots__ = ("base", "match_values", "base_column", "match_column")
        BASE_FIELD_NUMBER: _ClassVar[int]
        MATCH_VALUES_FIELD_NUMBER: _ClassVar[int]
        BASE_COLUMN_FIELD_NUMBER: _ClassVar[int]
        MATCH_COLUMN_FIELD_NUMBER: _ClassVar[int]
        base: PerfettoSqlStructuredQuery
        match_values: PerfettoSqlStructuredQuery
        base_column: str
        match_column: str
        def __init__(self, base: _Optional[_Union[PerfettoSqlStructuredQuery, _Mapping]] = ..., match_values: _Optional[_Union[PerfettoSqlStructuredQuery, _Mapping]] = ..., base_column: _Optional[str] = ..., match_column: _Optional[str] = ...) -> None: ...
    class Filter(_message.Message):
        __slots__ = ("column_name", "op", "string_rhs", "double_rhs", "int64_rhs")
        class Operator(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            UNKNOWN: _ClassVar[PerfettoSqlStructuredQuery.Filter.Operator]
            EQUAL: _ClassVar[PerfettoSqlStructuredQuery.Filter.Operator]
            NOT_EQUAL: _ClassVar[PerfettoSqlStructuredQuery.Filter.Operator]
            LESS_THAN: _ClassVar[PerfettoSqlStructuredQuery.Filter.Operator]
            LESS_THAN_EQUAL: _ClassVar[PerfettoSqlStructuredQuery.Filter.Operator]
            GREATER_THAN: _ClassVar[PerfettoSqlStructuredQuery.Filter.Operator]
            GREATER_THAN_EQUAL: _ClassVar[PerfettoSqlStructuredQuery.Filter.Operator]
            IS_NULL: _ClassVar[PerfettoSqlStructuredQuery.Filter.Operator]
            IS_NOT_NULL: _ClassVar[PerfettoSqlStructuredQuery.Filter.Operator]
            GLOB: _ClassVar[PerfettoSqlStructuredQuery.Filter.Operator]
        UNKNOWN: PerfettoSqlStructuredQuery.Filter.Operator
        EQUAL: PerfettoSqlStructuredQuery.Filter.Operator
        NOT_EQUAL: PerfettoSqlStructuredQuery.Filter.Operator
        LESS_THAN: PerfettoSqlStructuredQuery.Filter.Operator
        LESS_THAN_EQUAL: PerfettoSqlStructuredQuery.Filter.Operator
        GREATER_THAN: PerfettoSqlStructuredQuery.Filter.Operator
        GREATER_THAN_EQUAL: PerfettoSqlStructuredQuery.Filter.Operator
        IS_NULL: PerfettoSqlStructuredQuery.Filter.Operator
        IS_NOT_NULL: PerfettoSqlStructuredQuery.Filter.Operator
        GLOB: PerfettoSqlStructuredQuery.Filter.Operator
        COLUMN_NAME_FIELD_NUMBER: _ClassVar[int]
        OP_FIELD_NUMBER: _ClassVar[int]
        STRING_RHS_FIELD_NUMBER: _ClassVar[int]
        DOUBLE_RHS_FIELD_NUMBER: _ClassVar[int]
        INT64_RHS_FIELD_NUMBER: _ClassVar[int]
        column_name: str
        op: PerfettoSqlStructuredQuery.Filter.Operator
        string_rhs: _containers.RepeatedScalarFieldContainer[str]
        double_rhs: _containers.RepeatedScalarFieldContainer[float]
        int64_rhs: _containers.RepeatedScalarFieldContainer[int]
        def __init__(self, column_name: _Optional[str] = ..., op: _Optional[_Union[PerfettoSqlStructuredQuery.Filter.Operator, str]] = ..., string_rhs: _Optional[_Iterable[str]] = ..., double_rhs: _Optional[_Iterable[float]] = ..., int64_rhs: _Optional[_Iterable[int]] = ...) -> None: ...
    class GroupBy(_message.Message):
        __slots__ = ("column_names", "aggregates")
        class Aggregate(_message.Message):
            __slots__ = ("column_name", "op", "result_column_name", "percentile", "custom_sql_expression")
            class Op(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
                __slots__ = ()
                UNSPECIFIED: _ClassVar[PerfettoSqlStructuredQuery.GroupBy.Aggregate.Op]
                COUNT: _ClassVar[PerfettoSqlStructuredQuery.GroupBy.Aggregate.Op]
                SUM: _ClassVar[PerfettoSqlStructuredQuery.GroupBy.Aggregate.Op]
                MIN: _ClassVar[PerfettoSqlStructuredQuery.GroupBy.Aggregate.Op]
                MAX: _ClassVar[PerfettoSqlStructuredQuery.GroupBy.Aggregate.Op]
                MEAN: _ClassVar[PerfettoSqlStructuredQuery.GroupBy.Aggregate.Op]
                MEDIAN: _ClassVar[PerfettoSqlStructuredQuery.GroupBy.Aggregate.Op]
                DURATION_WEIGHTED_MEAN: _ClassVar[PerfettoSqlStructuredQuery.GroupBy.Aggregate.Op]
                COUNT_DISTINCT: _ClassVar[PerfettoSqlStructuredQuery.GroupBy.Aggregate.Op]
                PERCENTILE: _ClassVar[PerfettoSqlStructuredQuery.GroupBy.Aggregate.Op]
                CUSTOM: _ClassVar[PerfettoSqlStructuredQuery.GroupBy.Aggregate.Op]
            UNSPECIFIED: PerfettoSqlStructuredQuery.GroupBy.Aggregate.Op
            COUNT: PerfettoSqlStructuredQuery.GroupBy.Aggregate.Op
            SUM: PerfettoSqlStructuredQuery.GroupBy.Aggregate.Op
            MIN: PerfettoSqlStructuredQuery.GroupBy.Aggregate.Op
            MAX: PerfettoSqlStructuredQuery.GroupBy.Aggregate.Op
            MEAN: PerfettoSqlStructuredQuery.GroupBy.Aggregate.Op
            MEDIAN: PerfettoSqlStructuredQuery.GroupBy.Aggregate.Op
            DURATION_WEIGHTED_MEAN: PerfettoSqlStructuredQuery.GroupBy.Aggregate.Op
            COUNT_DISTINCT: PerfettoSqlStructuredQuery.GroupBy.Aggregate.Op
            PERCENTILE: PerfettoSqlStructuredQuery.GroupBy.Aggregate.Op
            CUSTOM: PerfettoSqlStructuredQuery.GroupBy.Aggregate.Op
            COLUMN_NAME_FIELD_NUMBER: _ClassVar[int]
            OP_FIELD_NUMBER: _ClassVar[int]
            RESULT_COLUMN_NAME_FIELD_NUMBER: _ClassVar[int]
            PERCENTILE_FIELD_NUMBER: _ClassVar[int]
            CUSTOM_SQL_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
            column_name: str
            op: PerfettoSqlStructuredQuery.GroupBy.Aggregate.Op
            result_column_name: str
            percentile: float
            custom_sql_expression: str
            def __init__(self, column_name: _Optional[str] = ..., op: _Optional[_Union[PerfettoSqlStructuredQuery.GroupBy.Aggregate.Op, str]] = ..., result_column_name: _Optional[str] = ..., percentile: _Optional[float] = ..., custom_sql_expression: _Optional[str] = ...) -> None: ...
        COLUMN_NAMES_FIELD_NUMBER: _ClassVar[int]
        AGGREGATES_FIELD_NUMBER: _ClassVar[int]
        column_names: _containers.RepeatedScalarFieldContainer[str]
        aggregates: _containers.RepeatedCompositeFieldContainer[PerfettoSqlStructuredQuery.GroupBy.Aggregate]
        def __init__(self, column_names: _Optional[_Iterable[str]] = ..., aggregates: _Optional[_Iterable[_Union[PerfettoSqlStructuredQuery.GroupBy.Aggregate, _Mapping]]] = ...) -> None: ...
    class SelectColumn(_message.Message):
        __slots__ = ("column_name_or_expression", "alias", "column_name")
        COLUMN_NAME_OR_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
        ALIAS_FIELD_NUMBER: _ClassVar[int]
        COLUMN_NAME_FIELD_NUMBER: _ClassVar[int]
        column_name_or_expression: str
        alias: str
        column_name: str
        def __init__(self, column_name_or_expression: _Optional[str] = ..., alias: _Optional[str] = ..., column_name: _Optional[str] = ...) -> None: ...
    class OrderBy(_message.Message):
        __slots__ = ("ordering_specs",)
        class Direction(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            UNSPECIFIED: _ClassVar[PerfettoSqlStructuredQuery.OrderBy.Direction]
            ASC: _ClassVar[PerfettoSqlStructuredQuery.OrderBy.Direction]
            DESC: _ClassVar[PerfettoSqlStructuredQuery.OrderBy.Direction]
        UNSPECIFIED: PerfettoSqlStructuredQuery.OrderBy.Direction
        ASC: PerfettoSqlStructuredQuery.OrderBy.Direction
        DESC: PerfettoSqlStructuredQuery.OrderBy.Direction
        class OrderingSpec(_message.Message):
            __slots__ = ("column_name", "direction")
            COLUMN_NAME_FIELD_NUMBER: _ClassVar[int]
            DIRECTION_FIELD_NUMBER: _ClassVar[int]
            column_name: str
            direction: PerfettoSqlStructuredQuery.OrderBy.Direction
            def __init__(self, column_name: _Optional[str] = ..., direction: _Optional[_Union[PerfettoSqlStructuredQuery.OrderBy.Direction, str]] = ...) -> None: ...
        ORDERING_SPECS_FIELD_NUMBER: _ClassVar[int]
        ordering_specs: _containers.RepeatedCompositeFieldContainer[PerfettoSqlStructuredQuery.OrderBy.OrderingSpec]
        def __init__(self, ordering_specs: _Optional[_Iterable[_Union[PerfettoSqlStructuredQuery.OrderBy.OrderingSpec, _Mapping]]] = ...) -> None: ...
    class ExperimentalFilterGroup(_message.Message):
        __slots__ = ("op", "filters", "groups", "sql_expressions")
        class Operator(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            UNSPECIFIED: _ClassVar[PerfettoSqlStructuredQuery.ExperimentalFilterGroup.Operator]
            AND: _ClassVar[PerfettoSqlStructuredQuery.ExperimentalFilterGroup.Operator]
            OR: _ClassVar[PerfettoSqlStructuredQuery.ExperimentalFilterGroup.Operator]
        UNSPECIFIED: PerfettoSqlStructuredQuery.ExperimentalFilterGroup.Operator
        AND: PerfettoSqlStructuredQuery.ExperimentalFilterGroup.Operator
        OR: PerfettoSqlStructuredQuery.ExperimentalFilterGroup.Operator
        OP_FIELD_NUMBER: _ClassVar[int]
        FILTERS_FIELD_NUMBER: _ClassVar[int]
        GROUPS_FIELD_NUMBER: _ClassVar[int]
        SQL_EXPRESSIONS_FIELD_NUMBER: _ClassVar[int]
        op: PerfettoSqlStructuredQuery.ExperimentalFilterGroup.Operator
        filters: _containers.RepeatedCompositeFieldContainer[PerfettoSqlStructuredQuery.Filter]
        groups: _containers.RepeatedCompositeFieldContainer[PerfettoSqlStructuredQuery.ExperimentalFilterGroup]
        sql_expressions: _containers.RepeatedScalarFieldContainer[str]
        def __init__(self, op: _Optional[_Union[PerfettoSqlStructuredQuery.ExperimentalFilterGroup.Operator, str]] = ..., filters: _Optional[_Iterable[_Union[PerfettoSqlStructuredQuery.Filter, _Mapping]]] = ..., groups: _Optional[_Iterable[_Union[PerfettoSqlStructuredQuery.ExperimentalFilterGroup, _Mapping]]] = ..., sql_expressions: _Optional[_Iterable[str]] = ...) -> None: ...
    ID_FIELD_NUMBER: _ClassVar[int]
    REFERENCED_MODULES_FIELD_NUMBER: _ClassVar[int]
    TABLE_FIELD_NUMBER: _ClassVar[int]
    SQL_FIELD_NUMBER: _ClassVar[int]
    SIMPLE_SLICES_FIELD_NUMBER: _ClassVar[int]
    INNER_QUERY_FIELD_NUMBER: _ClassVar[int]
    INNER_QUERY_ID_FIELD_NUMBER: _ClassVar[int]
    INTERVAL_INTERSECT_FIELD_NUMBER: _ClassVar[int]
    EXPERIMENTAL_JOIN_FIELD_NUMBER: _ClassVar[int]
    EXPERIMENTAL_UNION_FIELD_NUMBER: _ClassVar[int]
    EXPERIMENTAL_ADD_COLUMNS_FIELD_NUMBER: _ClassVar[int]
    EXPERIMENTAL_CREATE_SLICES_FIELD_NUMBER: _ClassVar[int]
    EXPERIMENTAL_TIME_RANGE_FIELD_NUMBER: _ClassVar[int]
    EXPERIMENTAL_FILTER_TO_INTERVALS_FIELD_NUMBER: _ClassVar[int]
    EXPERIMENTAL_COUNTER_INTERVALS_FIELD_NUMBER: _ClassVar[int]
    EXPERIMENTAL_FILTER_IN_FIELD_NUMBER: _ClassVar[int]
    FILTERS_FIELD_NUMBER: _ClassVar[int]
    GROUP_BY_FIELD_NUMBER: _ClassVar[int]
    SELECT_COLUMNS_FIELD_NUMBER: _ClassVar[int]
    ORDER_BY_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    OFFSET_FIELD_NUMBER: _ClassVar[int]
    EXPERIMENTAL_FILTER_GROUP_FIELD_NUMBER: _ClassVar[int]
    id: str
    referenced_modules: _containers.RepeatedScalarFieldContainer[str]
    table: PerfettoSqlStructuredQuery.Table
    sql: PerfettoSqlStructuredQuery.Sql
    simple_slices: PerfettoSqlStructuredQuery.SimpleSlices
    inner_query: PerfettoSqlStructuredQuery
    inner_query_id: str
    interval_intersect: PerfettoSqlStructuredQuery.IntervalIntersect
    experimental_join: PerfettoSqlStructuredQuery.ExperimentalJoin
    experimental_union: PerfettoSqlStructuredQuery.ExperimentalUnion
    experimental_add_columns: PerfettoSqlStructuredQuery.ExperimentalAddColumns
    experimental_create_slices: PerfettoSqlStructuredQuery.ExperimentalCreateSlices
    experimental_time_range: PerfettoSqlStructuredQuery.ExperimentalTimeRange
    experimental_filter_to_intervals: PerfettoSqlStructuredQuery.ExperimentalFilterToIntervals
    experimental_counter_intervals: PerfettoSqlStructuredQuery.ExperimentalCounterIntervals
    experimental_filter_in: PerfettoSqlStructuredQuery.ExperimentalFilterIn
    filters: _containers.RepeatedCompositeFieldContainer[PerfettoSqlStructuredQuery.Filter]
    group_by: PerfettoSqlStructuredQuery.GroupBy
    select_columns: _containers.RepeatedCompositeFieldContainer[PerfettoSqlStructuredQuery.SelectColumn]
    order_by: PerfettoSqlStructuredQuery.OrderBy
    limit: int
    offset: int
    experimental_filter_group: PerfettoSqlStructuredQuery.ExperimentalFilterGroup
    def __init__(self, id: _Optional[str] = ..., referenced_modules: _Optional[_Iterable[str]] = ..., table: _Optional[_Union[PerfettoSqlStructuredQuery.Table, _Mapping]] = ..., sql: _Optional[_Union[PerfettoSqlStructuredQuery.Sql, _Mapping]] = ..., simple_slices: _Optional[_Union[PerfettoSqlStructuredQuery.SimpleSlices, _Mapping]] = ..., inner_query: _Optional[_Union[PerfettoSqlStructuredQuery, _Mapping]] = ..., inner_query_id: _Optional[str] = ..., interval_intersect: _Optional[_Union[PerfettoSqlStructuredQuery.IntervalIntersect, _Mapping]] = ..., experimental_join: _Optional[_Union[PerfettoSqlStructuredQuery.ExperimentalJoin, _Mapping]] = ..., experimental_union: _Optional[_Union[PerfettoSqlStructuredQuery.ExperimentalUnion, _Mapping]] = ..., experimental_add_columns: _Optional[_Union[PerfettoSqlStructuredQuery.ExperimentalAddColumns, _Mapping]] = ..., experimental_create_slices: _Optional[_Union[PerfettoSqlStructuredQuery.ExperimentalCreateSlices, _Mapping]] = ..., experimental_time_range: _Optional[_Union[PerfettoSqlStructuredQuery.ExperimentalTimeRange, _Mapping]] = ..., experimental_filter_to_intervals: _Optional[_Union[PerfettoSqlStructuredQuery.ExperimentalFilterToIntervals, _Mapping]] = ..., experimental_counter_intervals: _Optional[_Union[PerfettoSqlStructuredQuery.ExperimentalCounterIntervals, _Mapping]] = ..., experimental_filter_in: _Optional[_Union[PerfettoSqlStructuredQuery.ExperimentalFilterIn, _Mapping]] = ..., filters: _Optional[_Iterable[_Union[PerfettoSqlStructuredQuery.Filter, _Mapping]]] = ..., group_by: _Optional[_Union[PerfettoSqlStructuredQuery.GroupBy, _Mapping]] = ..., select_columns: _Optional[_Iterable[_Union[PerfettoSqlStructuredQuery.SelectColumn, _Mapping]]] = ..., order_by: _Optional[_Union[PerfettoSqlStructuredQuery.OrderBy, _Mapping]] = ..., limit: _Optional[int] = ..., offset: _Optional[int] = ..., experimental_filter_group: _Optional[_Union[PerfettoSqlStructuredQuery.ExperimentalFilterGroup, _Mapping]] = ...) -> None: ...
