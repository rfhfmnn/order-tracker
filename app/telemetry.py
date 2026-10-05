import atexit
import logging
import os
import sys
from typing import Optional

from opentelemetry import _logs, metrics, trace
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import (
    BatchLogRecordProcessor,
    ConsoleLogRecordExporter,
    SimpleLogRecordProcessor,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)

_meter_provider: Optional[MeterProvider] = None
_tracer_provider: Optional[TracerProvider] = None
_logger_provider: Optional[LoggerProvider] = None
_initialized = False


class SafeStream:
    """Wraps sys.stdout so that if it is closed during shutdown/test teardown, writes are safely ignored."""

    def write(self, s):
        try:
            if sys.stdout and not sys.stdout.closed:
                sys.stdout.write(s)
                sys.stdout.flush()
        except Exception:
            pass

    def flush(self):
        try:
            if sys.stdout and not sys.stdout.closed:
                sys.stdout.flush()
        except Exception:
            pass


def init_telemetry():
    global _meter_provider, _tracer_provider, _logger_provider, _initialized
    if _initialized:
        return

    service_name = os.getenv("OTEL_SERVICE_NAME", "order-tracker")
    resource = Resource.create({"service.name": service_name})
    stream = SafeStream()

    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    otlp_insecure_str = os.getenv("OTEL_EXPORTER_OTLP_INSECURE", "true").lower()
    otlp_insecure = otlp_insecure_str in ("true", "1", "yes")

    # 1. Traces
    _tracer_provider = TracerProvider(resource=resource)
    _tracer_provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter(out=stream)))
    if otlp_endpoint:
        _tracer_provider.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(
                    endpoint=otlp_endpoint,
                    insecure=otlp_insecure,
                )
            )
        )
    trace.set_tracer_provider(_tracer_provider)

    # 2. Metrics
    metric_readers = [
        PeriodicExportingMetricReader(
            ConsoleMetricExporter(out=stream),
            export_interval_millis=60000,
        )
    ]
    if otlp_endpoint:
        metric_readers.append(
            PeriodicExportingMetricReader(
                OTLPMetricExporter(
                    endpoint=otlp_endpoint,
                    insecure=otlp_insecure,
                ),
                export_interval_millis=5000,
            )
        )
    _meter_provider = MeterProvider(resource=resource, metric_readers=metric_readers)
    metrics.set_meter_provider(_meter_provider)

    # 3. Logs
    _logger_provider = LoggerProvider(resource=resource)
    _logger_provider.add_log_record_processor(
        SimpleLogRecordProcessor(ConsoleLogRecordExporter(out=stream))
    )
    if otlp_endpoint:
        _logger_provider.add_log_record_processor(
            BatchLogRecordProcessor(
                OTLPLogExporter(
                    endpoint=otlp_endpoint,
                    insecure=otlp_insecure,
                )
            )
        )
    _logs.set_logger_provider(_logger_provider)

    handler = LoggingHandler(level=logging.INFO, logger_provider=_logger_provider)
    app_logger = logging.getLogger("order-tracker")
    app_logger.setLevel(logging.INFO)
    app_logger.addHandler(handler)

    _initialized = True


# Initialize on load
init_telemetry()

tracer = trace.get_tracer("order-tracker")
meter = metrics.get_meter("order-tracker")
logger = logging.getLogger("order-tracker")

# Metric counters for request tracking
http_requests_counter = meter.create_counter(
    name="http_requests_total",
    description="Total count of HTTP requests",
    unit="1",
)

order_lookup_requests_counter = meter.create_counter(
    name="order_lookup_requests_total",
    description="Total count of order lookup requests",
    unit="1",
)


def flush_telemetry():
    try:
        if _meter_provider:
            _meter_provider.force_flush()
        if _tracer_provider:
            _tracer_provider.force_flush()
        if _logger_provider:
            _logger_provider.force_flush()
    except Exception:
        pass


def shutdown_telemetry():
    try:
        if _meter_provider:
            _meter_provider.shutdown()
        if _tracer_provider:
            _tracer_provider.shutdown()
        if _logger_provider:
            _logger_provider.shutdown()
    except Exception:
        pass


atexit.register(shutdown_telemetry)
