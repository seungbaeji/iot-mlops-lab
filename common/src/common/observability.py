import json
import logging
import traceback
from contextlib import nullcontext
from typing import Any, ContextManager, Dict, Hashable, Optional, Sequence, Union

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
from prometheus_client import Counter, Gauge, Histogram, Info, Summary


def init_tracing(service_name: str, trace_endpoint: str) -> None:
    """
    Initialize OpenTelemetry TracerProvider with OTLP exporter.

    Args:
        service_name (str): Name of the service for tracing resource.
        trace_endpoint (str): OTLP trace collector endpoint URL.

    Examples:
        >>> init_tracing("my_service", "http://localhost:4318/v1/traces")
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
        logging.info("Tracing initialized.")
    except Exception:
        logging.exception("Failed to initialize tracing. Tracing will be disabled.")
        trace.set_tracer_provider(NoOpTracerProvider())


def get_tracer(service_name: str) -> Tracer:
    """
    Return a tracer for the given service name. If tracing is not initialized, returns a no-op tracer.

    Args:
        service_name (str): Name of the service.

    Returns:
        Tracer: OpenTelemetry tracer instance.

    Examples:
        >>> tracer = get_tracer("my_service")
        >>> with tracer.start_as_current_span("my_span"):
        ...     # do something
    """
    try:
        return trace.get_tracer(service_name)
    except Exception:
        trace.set_tracer_provider(NoOpTracerProvider())
        return trace.get_tracer(service_name)


def span_context(tracer: Optional[Tracer], name: str) -> ContextManager[Span]:
    """
    Returns a context manager for a named tracing span.
    If tracer is None, returns a nullcontext.

    Args:
        tracer (Optional[Tracer]): OpenTelemetry tracer instance or None.
        name (str): Name of the span.

    Returns:
        ContextManager[Span]: Context manager for the span.

    Examples:
        >>> tracer = get_tracer("my_service")
        >>> with span_context(tracer, "my_span"):
        ...     # do something
    """
    if tracer:
        return tracer.start_as_current_span(name)
    return nullcontext(get_current_span())


class MetricFactory:
    """
    Factory for creating and reusing Prometheus metrics (Counter, Gauge, Histogram, Summary, Info)
    with automatic deduplication by name, type, and labelnames.
    """

    def __init__(self, service_name: str):
        """
        Args:
            service_name (str): Prefix for all metric names (usually the service name).
        """
        self.service_name: str = service_name
        self._metrics: Dict[
            Hashable, Union[Counter, Gauge, Histogram, Summary, Info]
        ] = {}

    def _metric_key(
        self,
        metric_type: str,
        name: str,
        labelnames: Optional[Sequence[str]],
        **kwargs: Any,
    ) -> Hashable:
        """
        Generate a unique key for a metric based on type, name, labelnames, and extra options.

        Args:
            metric_type (str): Metric type (e.g., 'counter', 'gauge').
            name (str): Metric name (without service prefix).
            labelnames (Optional[Sequence[str]]): List of label names.
            **kwargs: Additional keyword arguments for metric uniqueness.

        Returns:
            Hashable: Unique key for metric registry.
        """
        key = (
            metric_type,
            name,
            tuple(labelnames or []),
            tuple(sorted(kwargs.items())) if kwargs else None,
        )
        return key

    def counter(
        self,
        name: str,
        documentation: str,
        labelnames: Optional[Sequence[str]] = None,
        **kwargs: Any,
    ) -> Counter:
        """
        Create or get a Prometheus Counter metric.

        Args:
            name (str): Metric name (without service prefix).
            documentation (str): Metric description.
            labelnames (Optional[Sequence[str]]): List of label names.

        Returns:
            Counter: Prometheus Counter metric instance.

        Examples:
            >>> metrics = MetricFactory("my_service")
            >>> counter = metrics.counter("requests_total", "Total requests", ["endpoint"])
            >>> counter.labels(endpoint="/api").inc()
        """
        labelnames = labelnames or []
        key = self._metric_key("counter", name, labelnames)
        if key in self._metrics:
            return self._metrics[key]  # type: ignore
        metric = Counter(
            f"{self.service_name}_{name}", documentation, labelnames=labelnames
        )
        self._metrics[key] = metric
        return metric

    def histogram(
        self,
        name: str,
        documentation: str,
        labelnames: Optional[Sequence[str]] = None,
        buckets: Optional[Sequence[float]] = None,
    ) -> Histogram:
        """
        Create or get a Prometheus Histogram metric.

        Args:
            name (str): Metric name (without service prefix).
            documentation (str): Metric description.
            labelnames (Optional[Sequence[str]]): List of label names.
            buckets (Optional[Sequence[float]]): Histogram buckets.

        Returns:
            Histogram: Prometheus Histogram metric instance.

        Examples:
            >>> metrics = MetricFactory("my_service")
            >>> hist = metrics.histogram("latency_seconds", "Request latency", ["endpoint"], buckets=[0.1, 0.5, 1, 2, 5])
            >>> hist.labels(endpoint="/api").observe(0.42)
        """
        labelnames = labelnames or []
        key = self._metric_key(
            "histogram", name, labelnames, buckets=tuple(buckets) if buckets else None
        )
        if key in self._metrics:
            return self._metrics[key]  # type: ignore
        metric = Histogram(
            f"{self.service_name}_{name}",
            documentation,
            labelnames=labelnames,
            buckets=buckets,
        )
        self._metrics[key] = metric
        return metric

    def gauge(
        self,
        name: str,
        documentation: str,
        labelnames: Optional[Sequence[str]] = None,
        **kwargs: Any,
    ) -> Gauge:
        """
        Create or get a Prometheus Gauge metric.

        Args:
            name (str): Metric name (without service prefix).
            documentation (str): Metric description.
            labelnames (Optional[Sequence[str]]): List of label names.

        Returns:
            Gauge: Prometheus Gauge metric instance.

        Examples:
            >>> metrics = MetricFactory("my_service")
            >>> gauge = metrics.gauge("in_progress", "In progress requests", ["endpoint"])
            >>> gauge.labels(endpoint="/api").inc()
            >>> gauge.labels(endpoint="/api").dec()
        """
        labelnames = labelnames or []
        key = self._metric_key("gauge", name, labelnames)
        if key in self._metrics:
            return self._metrics[key]  # type: ignore
        metric = Gauge(
            f"{self.service_name}_{name}", documentation, labelnames=labelnames
        )
        self._metrics[key] = metric
        return metric

    def summary(
        self,
        name: str,
        documentation: str,
        labelnames: Optional[Sequence[str]] = None,
        objectives: Optional[Dict[float, float]] = None,
        max_age_seconds: Optional[int] = None,
        age_buckets: Optional[int] = None,
        compress_count: Optional[int] = None,
    ) -> Summary:
        """
        Create or get a Prometheus Summary metric.

        Args:
            name (str): Metric name (without service prefix).
            documentation (str): Metric description.
            labelnames (Optional[Sequence[str]]): List of label names.
            objectives (Optional[Dict[float, float]]): Summary quantile objectives.
            max_age_seconds (Optional[int]): Max age for summary observations.
            age_buckets (Optional[int]): Number of age buckets.
            compress_count (Optional[int]): Number of compressions.

        Returns:
            Summary: Prometheus Summary metric instance.

        Examples:
            >>> metrics = MetricFactory("my_service")
            >>> summ = metrics.summary("request_duration_seconds", "Request duration", ["endpoint"])
            >>> summ.labels(endpoint="/api").observe(0.37)
        """
        labelnames = labelnames or []
        kwargs: Dict[str, Any] = {}
        if objectives is not None:
            kwargs["objectives"] = objectives
        if max_age_seconds is not None:
            kwargs["max_age_seconds"] = max_age_seconds
        if age_buckets is not None:
            kwargs["age_buckets"] = age_buckets
        if compress_count is not None:
            kwargs["compress_count"] = compress_count
        key = self._metric_key("summary", name, labelnames, **kwargs)
        if key in self._metrics:
            return self._metrics[key]  # type: ignore
        metric = Summary(
            f"{self.service_name}_{name}",
            documentation,
            labelnames=labelnames,
            **kwargs,
        )
        self._metrics[key] = metric
        return metric

    def info(
        self,
        name: str,
        documentation: str,
        labelnames: Optional[Sequence[str]] = None,
        **kwargs: Any,
    ) -> Info:
        """
        Create or get a Prometheus Info metric.

        Args:
            name (str): Metric name (without service prefix).
            documentation (str): Metric description.
            labelnames (Optional[Sequence[str]]): List of label names.

        Returns:
            Info: Prometheus Info metric instance.

        Examples:
            >>> metrics = MetricFactory("my_service")
            >>> info = metrics.info("build_info", "Build and version info")
            >>> info.info({"version": "1.0.0", "build": "abc123"})
        """
        labelnames = labelnames or []
        key = self._metric_key("info", name, labelnames)
        if key in self._metrics:
            return self._metrics[key]  # type: ignore
        metric = Info(
            f"{self.service_name}_{name}", documentation, labelnames=labelnames
        )
        self._metrics[key] = metric
        return metric


class BaseFormatter(logging.Formatter):
    """
    Base formatter for observability log formatters. Provides common log field extraction.
    """

    def get_log_data(self, record: logging.LogRecord) -> dict:
        span = get_current_span()
        ctx: Optional[SpanContext] = span.get_span_context()
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
        return log_data


class JSONFormatter(BaseFormatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = self.get_log_data(record)
        return json.dumps(log_data, ensure_ascii=False)


class LogfmtFormatter(BaseFormatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = self.get_log_data(record)

        def fmt_value(val):
            if isinstance(val, str):
                if any(c in val for c in ' "='):
                    return '"' + val.replace('"', '"') + '"'
                return val
            return str(val)

        return " ".join(f"{k}={fmt_value(v)}" for k, v in log_data.items())
