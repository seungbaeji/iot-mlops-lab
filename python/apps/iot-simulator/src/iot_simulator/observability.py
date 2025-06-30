# observability.py
import json
import logging
import traceback
from contextlib import AbstractContextManager, nullcontext

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import (
    NoOpTracerProvider,
    Span,
    SpanContext,
    Tracer,
    get_current_span,
)
from prometheus_client import Counter, Gauge


def init_tracing(service_name: str, trace_endpoint: str) -> None:
    """
    Initialize OpenTelemetry TracerProvider with OTLP exporter.
    """
    if not trace_endpoint:
        logging.warning("No trace endpoint configured. Tracing disabled.")
        return

    try:
        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)
        processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=trace_endpoint))
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
    except Exception:
        logging.exception("Failed to initialize tracing. Tracing will be disabled.")
        trace.set_tracer_provider(NoOpTracerProvider())


def get_tracer(service_name: str = "iot-simulator") -> Tracer:
    """
    Return tracer. If tracing is not initialized, returns a no-op tracer.
    """
    try:
        return trace.get_tracer(service_name)
    except Exception:
        trace.set_tracer_provider(NoOpTracerProvider())
        return trace.get_tracer(service_name)


def get_span_context(tracer: Tracer | None, name: str) -> AbstractContextManager[Span]:
    if tracer:
        return tracer.start_as_current_span(name)
    return nullcontext(get_current_span())


class Metrics:
    mqtt_sent_total = Counter(
        name="mqtt_sent_total",
        documentation="Number of MQTT messages sent",
        labelnames=["device_id"],
    )

    running_devices = Gauge(
        name="running_devices",
        documentation="Number of devices currently running",
    )


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        span = get_current_span()
        ctx: SpanContext | None = span.get_span_context()

        trace_id = (
            format(ctx.trace_id, "032x") if ctx and ctx.is_valid else "unknown-trace"
        )
        span_id = (
            format(ctx.span_id, "016x") if ctx and ctx.is_valid else "unknown-span"
        )

        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "service": record.name,
            "trace_id": getattr(record, "trace_id", trace_id),
            "span_id": getattr(record, "span_id", span_id),
            "user_id": getattr(record, "user_id", "unknown-user"),
            "logger_name": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process": record.process,
            "thread": record.threadName,
        }

        if record.exc_info:
            log_data["traceback"] = traceback.format_exc().strip().replace("\n", " | ")
        elif hasattr(record, "message") and "RuntimeWarning" in record.message:
            log_data["traceback"] = record.getMessage()

        return json.dumps(log_data, ensure_ascii=False)
