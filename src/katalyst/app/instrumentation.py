from opentelemetry import trace as trace_api
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk import trace as trace_sdk
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from openinference.instrumentation.langchain import LangChainInstrumentor
from openinference.instrumentation import TraceConfig
from dotenv import load_dotenv
from katalyst.katalyst_core.utils.logger import get_logger
import os
import threading

log = get_logger()
load_dotenv()

_instrumentation_initialized = threading.Event()

def _setup_instrumentation(service_name: str = "default_service"):
    """
    Setup instrumentation for Phoenix only.
    """
    if _instrumentation_initialized.is_set():
        log.info("Instrumentation already initialized")
        return

    try:
        tracer_provider = trace_sdk.TracerProvider()
        otel_platform = os.getenv("OTEL_PLATFORM")
        log.info(f"OTEL_PLATFORM: {otel_platform}")
        if otel_platform == "phoenix":
            phoenix_api_key = os.getenv("PHOENIX_API_KEY")
            if not phoenix_api_key:
                log.error("PHOENIX_API_KEY not found in environment variables")
                return
            oltp_exporter_endpoint = os.getenv(
                "OTEL_EXPORTER_OTLP_ENDPOINT", "http://phoenix:6006/v1/traces"
            )
            if "localhost" in oltp_exporter_endpoint:
                span_exporter = OTLPSpanExporter(
                    endpoint=oltp_exporter_endpoint,
                    headers={"authorization": f"Bearer {phoenix_api_key}"},
                    timeout=5,
                )
            else:
                span_exporter = OTLPSpanExporter(
                    endpoint=oltp_exporter_endpoint,
                    headers={"authorization": f"Bearer {phoenix_api_key}"},
                    timeout=10,
                )
        else:
            log.warning(f"{otel_platform} not supported, skipping instrumentation")
            return

        span_processor = BatchSpanProcessor(
            span_exporter,
            max_queue_size=1024 * 3,
            schedule_delay_millis=1000,
            export_timeout_millis=5000,
            max_export_batch_size=128,
        )
        tracer_provider.add_span_processor(span_processor)
        trace_api.set_tracer_provider(tracer_provider)

        config = TraceConfig(
    hide_llm_invocation_parameters=True,
)
        LangChainInstrumentor().instrument(skip_dep_check=True, config=config)
       
        # try:
        #     tracer = trace_api.get_tracer(service_name)
        #     with tracer.start_as_current_span("connection_verification_span") as span:
        #         span.set_attribute("service.name", service_name)
        #         span.add_event("setup_complete", {"status": "success"})
        #         log.info(f"Successfully set up instrumentation for {service_name}")
        # except Exception as e:
        #     log.warning(f"Instrumentation verification failed, but continuing: {e}")

        log.info("Phoenix monitoring initialized")
        _instrumentation_initialized.set()
    except Exception as e:
        log.error("Failed to initialize Phoenix monitoring", exc_info=e)
        log.warning("Continuing without instrumentation to avoid blocking application")

def init_instrumentation(service_name: str = "default_service"):
    """
    Initialize Phoenix monitoring for FastAPI
    """
    try:
        _setup_instrumentation(service_name=service_name)
    except Exception as e:
        log.error("Failed to initialize Phoenix monitoring", exc_info=e)
    finally:
        try:
            tracer_provider = trace_api.get_tracer_provider()
            if hasattr(tracer_provider, "force_flush"):
                tracer_provider.force_flush(timeout_millis=2000)
        except Exception as e:
            log.warning(f"Failed to flush telemetry on shutdown: {e}")
