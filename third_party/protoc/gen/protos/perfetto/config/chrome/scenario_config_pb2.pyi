from protos.perfetto.config import trace_config_pb2 as _trace_config_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class TriggerRule(_message.Message):
    __slots__ = ("name", "trigger_chance", "delay_ms", "activation_delay_ms", "manual_trigger_name", "histogram", "repeating_interval")
    class HistogramTrigger(_message.Message):
        __slots__ = ("histogram_name", "min_value", "max_value")
        HISTOGRAM_NAME_FIELD_NUMBER: _ClassVar[int]
        MIN_VALUE_FIELD_NUMBER: _ClassVar[int]
        MAX_VALUE_FIELD_NUMBER: _ClassVar[int]
        histogram_name: str
        min_value: int
        max_value: int
        def __init__(self, histogram_name: _Optional[str] = ..., min_value: _Optional[int] = ..., max_value: _Optional[int] = ...) -> None: ...
    class RepeatingInterval(_message.Message):
        __slots__ = ("period_ms", "randomized")
        PERIOD_MS_FIELD_NUMBER: _ClassVar[int]
        RANDOMIZED_FIELD_NUMBER: _ClassVar[int]
        period_ms: int
        randomized: bool
        def __init__(self, period_ms: _Optional[int] = ..., randomized: _Optional[bool] = ...) -> None: ...
    NAME_FIELD_NUMBER: _ClassVar[int]
    TRIGGER_CHANCE_FIELD_NUMBER: _ClassVar[int]
    DELAY_MS_FIELD_NUMBER: _ClassVar[int]
    ACTIVATION_DELAY_MS_FIELD_NUMBER: _ClassVar[int]
    MANUAL_TRIGGER_NAME_FIELD_NUMBER: _ClassVar[int]
    HISTOGRAM_FIELD_NUMBER: _ClassVar[int]
    REPEATING_INTERVAL_FIELD_NUMBER: _ClassVar[int]
    name: str
    trigger_chance: float
    delay_ms: int
    activation_delay_ms: int
    manual_trigger_name: str
    histogram: TriggerRule.HistogramTrigger
    repeating_interval: TriggerRule.RepeatingInterval
    def __init__(self, name: _Optional[str] = ..., trigger_chance: _Optional[float] = ..., delay_ms: _Optional[int] = ..., activation_delay_ms: _Optional[int] = ..., manual_trigger_name: _Optional[str] = ..., histogram: _Optional[_Union[TriggerRule.HistogramTrigger, _Mapping]] = ..., repeating_interval: _Optional[_Union[TriggerRule.RepeatingInterval, _Mapping]] = ...) -> None: ...

class NestedScenarioConfig(_message.Message):
    __slots__ = ("scenario_name", "start_rules", "stop_rules", "upload_rules")
    SCENARIO_NAME_FIELD_NUMBER: _ClassVar[int]
    START_RULES_FIELD_NUMBER: _ClassVar[int]
    STOP_RULES_FIELD_NUMBER: _ClassVar[int]
    UPLOAD_RULES_FIELD_NUMBER: _ClassVar[int]
    scenario_name: str
    start_rules: _containers.RepeatedCompositeFieldContainer[TriggerRule]
    stop_rules: _containers.RepeatedCompositeFieldContainer[TriggerRule]
    upload_rules: _containers.RepeatedCompositeFieldContainer[TriggerRule]
    def __init__(self, scenario_name: _Optional[str] = ..., start_rules: _Optional[_Iterable[_Union[TriggerRule, _Mapping]]] = ..., stop_rules: _Optional[_Iterable[_Union[TriggerRule, _Mapping]]] = ..., upload_rules: _Optional[_Iterable[_Union[TriggerRule, _Mapping]]] = ...) -> None: ...

class ScenarioConfig(_message.Message):
    __slots__ = ("scenario_name", "scenario_description", "start_rules", "stop_rules", "upload_rules", "setup_rules", "trace_config", "nested_scenarios", "use_system_backend")
    SCENARIO_NAME_FIELD_NUMBER: _ClassVar[int]
    SCENARIO_DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    START_RULES_FIELD_NUMBER: _ClassVar[int]
    STOP_RULES_FIELD_NUMBER: _ClassVar[int]
    UPLOAD_RULES_FIELD_NUMBER: _ClassVar[int]
    SETUP_RULES_FIELD_NUMBER: _ClassVar[int]
    TRACE_CONFIG_FIELD_NUMBER: _ClassVar[int]
    NESTED_SCENARIOS_FIELD_NUMBER: _ClassVar[int]
    USE_SYSTEM_BACKEND_FIELD_NUMBER: _ClassVar[int]
    scenario_name: str
    scenario_description: str
    start_rules: _containers.RepeatedCompositeFieldContainer[TriggerRule]
    stop_rules: _containers.RepeatedCompositeFieldContainer[TriggerRule]
    upload_rules: _containers.RepeatedCompositeFieldContainer[TriggerRule]
    setup_rules: _containers.RepeatedCompositeFieldContainer[TriggerRule]
    trace_config: _trace_config_pb2.TraceConfig
    nested_scenarios: _containers.RepeatedCompositeFieldContainer[NestedScenarioConfig]
    use_system_backend: bool
    def __init__(self, scenario_name: _Optional[str] = ..., scenario_description: _Optional[str] = ..., start_rules: _Optional[_Iterable[_Union[TriggerRule, _Mapping]]] = ..., stop_rules: _Optional[_Iterable[_Union[TriggerRule, _Mapping]]] = ..., upload_rules: _Optional[_Iterable[_Union[TriggerRule, _Mapping]]] = ..., setup_rules: _Optional[_Iterable[_Union[TriggerRule, _Mapping]]] = ..., trace_config: _Optional[_Union[_trace_config_pb2.TraceConfig, _Mapping]] = ..., nested_scenarios: _Optional[_Iterable[_Union[NestedScenarioConfig, _Mapping]]] = ..., use_system_backend: _Optional[bool] = ...) -> None: ...

class ChromeFieldTracingConfig(_message.Message):
    __slots__ = ("scenarios",)
    SCENARIOS_FIELD_NUMBER: _ClassVar[int]
    scenarios: _containers.RepeatedCompositeFieldContainer[ScenarioConfig]
    def __init__(self, scenarios: _Optional[_Iterable[_Union[ScenarioConfig, _Mapping]]] = ...) -> None: ...

class TracingTriggerRulesConfig(_message.Message):
    __slots__ = ("rules",)
    RULES_FIELD_NUMBER: _ClassVar[int]
    rules: _containers.RepeatedCompositeFieldContainer[TriggerRule]
    def __init__(self, rules: _Optional[_Iterable[_Union[TriggerRule, _Mapping]]] = ...) -> None: ...
