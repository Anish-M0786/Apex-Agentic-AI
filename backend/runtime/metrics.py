"""Lightweight in-memory metrics for the Apex AI Runtime."""

from __future__ import annotations

from threading import Lock


class RuntimeMetrics:
    """Thread-safe in-memory request metrics.

    Tracks request counts, success/failure rates, and latency.
    Does not persist data or store user prompts.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self.request_count: int = 0
        self.successful_requests: int = 0
        self.failed_requests: int = 0
        self.total_latency_ms: int = 0
        self.last_latency_ms: int = 0
        self.last_model: str = ''

    def record(self, success: bool, latency_ms: int, model: str) -> None:
        """Record the outcome of a generation request."""
        with self._lock:
            self.request_count += 1
            if success:
                self.successful_requests += 1
            else:
                self.failed_requests += 1
            self.total_latency_ms += latency_ms
            self.last_latency_ms = latency_ms
            self.last_model = model

    def snapshot(self) -> dict:
        """Return a point-in-time copy of all metrics."""
        with self._lock:
            avg = (
                self.total_latency_ms / self.request_count
                if self.request_count > 0
                else 0
            )
            return {
                'request_count': self.request_count,
                'successful_requests': self.successful_requests,
                'failed_requests': self.failed_requests,
                'average_latency_ms': avg,
                'last_latency_ms': self.last_latency_ms,
                'model_used': self.last_model,
            }

    def reset(self) -> None:
        """Reset all counters to zero. Used for testing."""
        with self._lock:
            self.request_count = 0
            self.successful_requests = 0
            self.failed_requests = 0
            self.total_latency_ms = 0
            self.last_latency_ms = 0
            self.last_model = ''


metrics = RuntimeMetrics()
