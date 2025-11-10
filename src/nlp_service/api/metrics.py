"""Prometheus metrics configuration."""

from prometheus_client import Counter, Histogram, Info

# Request metrics
requests_total = Counter(
    "nlp_requests_total",
    "Total number of analysis requests",
    ["user_id"]
)

requests_success = Counter(
    "nlp_requests_success_total",
    "Total number of successful requests"
)

requests_failed = Counter(
    "nlp_requests_failed_total",
    "Total number of failed requests",
    ["error_type"]
)

# Latency metrics
request_latency = Histogram(
    "nlp_request_latency_seconds",
    "Request latency in seconds",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

heuristic_latency = Histogram(
    "nlp_heuristic_latency_seconds",
    "Heuristic parser latency in seconds",
    buckets=[0.01, 0.05, 0.1, 0.2, 0.5]
)

llm_latency = Histogram(
    "nlp_llm_latency_seconds",
    "LLM parser latency in seconds",
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0]
)

# LLM metrics
llm_calls_total = Counter(
    "nlp_llm_calls_total",
    "Total number of LLM API calls"
)

llm_errors_total = Counter(
    "nlp_llm_errors_total",
    "Total number of LLM errors"
)

llm_tokens_used = Counter(
    "nlp_llm_tokens_used_total",
    "Total tokens used by LLM"
)

# Action metrics
actions_extracted = Histogram(
    "nlp_actions_extracted",
    "Number of actions extracted per request",
    buckets=[0, 1, 2, 3, 5, 10, 20]
)

# Cache metrics
cache_hits = Counter(
    "nlp_cache_hits_total",
    "Total number of cache hits"
)

cache_misses = Counter(
    "nlp_cache_misses_total",
    "Total number of cache misses"
)

# Application info
app_info = Info("nlp_service", "NLP service information")
app_info.info({
    "version": "0.1.0",
    "service": "nlp-service"
})
