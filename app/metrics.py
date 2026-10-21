from prometheus_client import Counter, Histogram

REQUESTS = Counter(
    "medanon_http_requests_total",
    "HTTP requests by method, route template and status code",
    ["method", "route", "status"],
)

LATENCY = Histogram(
    "medanon_http_request_duration_seconds",
    "HTTP request latency by method and route template",
    ["method", "route"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)

FILES = Counter(
    "medanon_files_processed_total",
    "DICOM uploads by outcome",
    ["result"],  # ok | rejected | too_large | error
)

ELEMENTS_CHANGED = Counter(
    "medanon_phi_elements_changed_total",
    "Identifying elements removed, replaced or truncated",
)
