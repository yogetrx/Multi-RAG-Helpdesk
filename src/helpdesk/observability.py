
import os
import logging

from dotenv import load_dotenv
from microsoft.opentelemetry import use_microsoft_opentelemetry

load_dotenv()

logger = logging.getLogger(__name__)


def configure_observability() -> None:
    connection_string = os.getenv(
        "APPLICATIONINSIGHTS_CONNECTION_STRING"
    )

    if not connection_string:
        logger.warning(
            "Application Insights connection string missing. "
            "Telemetry export disabled."
        )
        return

    use_microsoft_opentelemetry(
        enable_azure_monitor=True,
        azure_monitor_connection_string=connection_string,
        azure_monitor_enable_live_metrics=False,
        azure_monitor_enable_performance_counters=False,
    )

    logger.info("OpenTelemetry configured with Azure Monitor.")
