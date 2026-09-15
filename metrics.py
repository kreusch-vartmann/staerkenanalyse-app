# metrics.py - Prometheus-Metriken
"""Definiert Prometheus-Metriken für die App."""

from prometheus_client import Counter, Histogram

# Metriken definieren
REQUEST_COUNT = Counter(
    'flask_request_count', 
    'App Request Count', 
    ['method', 'endpoint', 'http_status']
)
REQUEST_LATENCY = Histogram(
    'flask_request_latency_seconds', 
    'App Request Latency', 
    ['method', 'endpoint']
)
KI_API_LATENCY = Histogram(
    'ki_api_latency_seconds', 
    'KI API Latency', 
    ['model']
)
KI_API_ERRORS = Counter(
    'ki_api_errors_total', 
    'KI API Errors', 
    ['model', 'error_type']
)