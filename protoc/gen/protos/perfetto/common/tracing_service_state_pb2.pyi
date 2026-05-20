from protos.perfetto.common import data_source_descriptor_pb2 as _data_source_descriptor_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class TracingServiceState(_message.Message):
    __slots__ = ("producers", "data_sources", "tracing_sessions", "supports_tracing_sessions", "num_sessions", "num_sessions_started", "tracing_service_version")
    class Producer(_message.Message):
        __slots__ = ("id", "name", "pid", "uid", "sdk_version", "frozen")
        ID_FIELD_NUMBER: _ClassVar[int]
        NAME_FIELD_NUMBER: _ClassVar[int]
        PID_FIELD_NUMBER: _ClassVar[int]
        UID_FIELD_NUMBER: _ClassVar[int]
        SDK_VERSION_FIELD_NUMBER: _ClassVar[int]
        FROZEN_FIELD_NUMBER: _ClassVar[int]
        id: int
        name: str
        pid: int
        uid: int
        sdk_version: str
        frozen: bool
        def __init__(self, id: _Optional[int] = ..., name: _Optional[str] = ..., pid: _Optional[int] = ..., uid: _Optional[int] = ..., sdk_version: _Optional[str] = ..., frozen: _Optional[bool] = ...) -> None: ...
    class DataSource(_message.Message):
        __slots__ = ("ds_descriptor", "producer_id")
        DS_DESCRIPTOR_FIELD_NUMBER: _ClassVar[int]
        PRODUCER_ID_FIELD_NUMBER: _ClassVar[int]
        ds_descriptor: _data_source_descriptor_pb2.DataSourceDescriptor
        producer_id: int
        def __init__(self, ds_descriptor: _Optional[_Union[_data_source_descriptor_pb2.DataSourceDescriptor, _Mapping]] = ..., producer_id: _Optional[int] = ...) -> None: ...
    class TracingSession(_message.Message):
        __slots__ = ("id", "consumer_uid", "state", "unique_session_name", "buffer_size_kb", "duration_ms", "num_data_sources", "start_realtime_ns", "bugreport_score", "bugreport_filename", "is_started")
        ID_FIELD_NUMBER: _ClassVar[int]
        CONSUMER_UID_FIELD_NUMBER: _ClassVar[int]
        STATE_FIELD_NUMBER: _ClassVar[int]
        UNIQUE_SESSION_NAME_FIELD_NUMBER: _ClassVar[int]
        BUFFER_SIZE_KB_FIELD_NUMBER: _ClassVar[int]
        DURATION_MS_FIELD_NUMBER: _ClassVar[int]
        NUM_DATA_SOURCES_FIELD_NUMBER: _ClassVar[int]
        START_REALTIME_NS_FIELD_NUMBER: _ClassVar[int]
        BUGREPORT_SCORE_FIELD_NUMBER: _ClassVar[int]
        BUGREPORT_FILENAME_FIELD_NUMBER: _ClassVar[int]
        IS_STARTED_FIELD_NUMBER: _ClassVar[int]
        id: int
        consumer_uid: int
        state: str
        unique_session_name: str
        buffer_size_kb: _containers.RepeatedScalarFieldContainer[int]
        duration_ms: int
        num_data_sources: int
        start_realtime_ns: int
        bugreport_score: int
        bugreport_filename: str
        is_started: bool
        def __init__(self, id: _Optional[int] = ..., consumer_uid: _Optional[int] = ..., state: _Optional[str] = ..., unique_session_name: _Optional[str] = ..., buffer_size_kb: _Optional[_Iterable[int]] = ..., duration_ms: _Optional[int] = ..., num_data_sources: _Optional[int] = ..., start_realtime_ns: _Optional[int] = ..., bugreport_score: _Optional[int] = ..., bugreport_filename: _Optional[str] = ..., is_started: _Optional[bool] = ...) -> None: ...
    PRODUCERS_FIELD_NUMBER: _ClassVar[int]
    DATA_SOURCES_FIELD_NUMBER: _ClassVar[int]
    TRACING_SESSIONS_FIELD_NUMBER: _ClassVar[int]
    SUPPORTS_TRACING_SESSIONS_FIELD_NUMBER: _ClassVar[int]
    NUM_SESSIONS_FIELD_NUMBER: _ClassVar[int]
    NUM_SESSIONS_STARTED_FIELD_NUMBER: _ClassVar[int]
    TRACING_SERVICE_VERSION_FIELD_NUMBER: _ClassVar[int]
    producers: _containers.RepeatedCompositeFieldContainer[TracingServiceState.Producer]
    data_sources: _containers.RepeatedCompositeFieldContainer[TracingServiceState.DataSource]
    tracing_sessions: _containers.RepeatedCompositeFieldContainer[TracingServiceState.TracingSession]
    supports_tracing_sessions: bool
    num_sessions: int
    num_sessions_started: int
    tracing_service_version: str
    def __init__(self, producers: _Optional[_Iterable[_Union[TracingServiceState.Producer, _Mapping]]] = ..., data_sources: _Optional[_Iterable[_Union[TracingServiceState.DataSource, _Mapping]]] = ..., tracing_sessions: _Optional[_Iterable[_Union[TracingServiceState.TracingSession, _Mapping]]] = ..., supports_tracing_sessions: _Optional[bool] = ..., num_sessions: _Optional[int] = ..., num_sessions_started: _Optional[int] = ..., tracing_service_version: _Optional[str] = ...) -> None: ...
