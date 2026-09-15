# tests/unit/test_logging.py
"""Tests für Structlog-Logging."""

import json
import structlog
from io import StringIO


def test_structlog_json_output():
    """Testet, ob Structlog JSON-Logs korrekt generiert."""
    log_stream = StringIO()

    # Structlog-Konfiguration: Ausgabe direkt in den Puffer schreiben.
    # (Vorher wurde ein logging-StreamHandler erzeugt, der nie an einen
    # Logger gebunden war, während PrintLoggerFactory nach stdout schrieb –
    # der Puffer blieb dadurch leer.)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO
        logger_factory=structlog.PrintLoggerFactory(file=log_stream),
    )

    try:
        logger = structlog.get_logger()
        logger.info("Testnachricht", key="value")

        log_output = log_stream.getvalue().strip()
        log_data = json.loads(log_output)

        assert log_data["event"] == "Testnachricht"
        assert log_data["key"] == "value"
        assert "timestamp" in log_data
        assert log_data["level"] == "info"
    finally:
        # Globale structlog-Konfiguration zurücksetzen, damit nachfolgende
        # Tests (und der App-Logger) nicht in diesen Puffer schreiben.
        structlog.reset_defaults()
