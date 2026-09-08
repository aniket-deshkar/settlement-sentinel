from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from prometheus_client import Counter, Histogram
import os
provider = TracerProvider()
if os.getenv('OTEL_CONSOLE') == '1':
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer('settlement-sentinel')
RUNS = Counter('sentinel_runs_total','Investigations', ['outcome'])
LATENCY = Histogram('sentinel_run_seconds','Investigation latency')
DECISIONS = Counter('sentinel_decisions_total','Review outcomes',['decision'])
