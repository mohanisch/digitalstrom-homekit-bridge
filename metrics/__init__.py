
from prometheus_client import Counter, Summary, Gauge

REQUESTS = Counter('http_request_total', 'Total number of requests')
request_counter = Counter('http_requests', 'HTTP request', ["status_code"])

REQUEST_TIME = Summary('request_processing_seconds', 'Time spent processing request')

WS_REQUESTS_CHANGE = Counter('ws_request_total', 'Total number of websocket requests')

SYSTEM_USAGE = Gauge('system_usage', 'Hold current system resource usage', ['resource_type'])
