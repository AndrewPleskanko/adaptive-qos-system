import time
import logging
from dataclasses import dataclass, field
from collections import deque

logger = logging.getLogger(__name__)

MAX_HISTORY = 100


@dataclass
class MetricSnapshot:
    source: str
    cpu_usage: float
    memory_usage: float
    consumer_lag: int
    timestamp: int


class MetricsStore:
    def __init__(self, window_size: int = 10):
        self._history: deque[MetricSnapshot] = deque(maxlen=MAX_HISTORY)
        self._window_size = window_size

    def record(self, source: str, cpu: float, memory: float,
               lag: int, timestamp: int) -> None:
        snapshot = MetricSnapshot(
            source=source,
            cpu_usage=cpu,
            memory_usage=memory,
            consumer_lag=lag,
            timestamp=timestamp or int(time.time() * 1000),
        )
        self._history.append(snapshot)
        logger.debug("Recorded metrics from %s: cpu=%.1f%%, mem=%.1f%%, lag=%d",
                      source, cpu, memory, lag)

    def get_aggregated(self) -> dict:
        if not self._history:
            return {
                "cpu_usage": 0.0,
                "memory_usage": 0.0,
                "consumer_lag": 0,
                "active_consumers": 1,
                "dynamic_threshold": 0.5,
                "lag_growth_rate": 0.0,
                "db_pool_active": 0.15,
                "recent_p99_latency": 15.0,
            }

        recent = list(self._history)[-self._window_size:]
        avg_cpu = sum(s.cpu_usage for s in recent) / len(recent)
        avg_mem = sum(s.memory_usage for s in recent) / len(recent)
        max_lag = max(s.consumer_lag for s in recent)
        sources = len(set(s.source for s in recent))

        load = (avg_cpu + avg_mem) / 200.0
        threshold = 0.5 + load * 0.3

        return {
            "cpu_usage": round(avg_cpu, 2),
            "memory_usage": round(avg_mem, 2),
            "consumer_lag": max_lag,
            "active_consumers": max(sources, 1),
            "dynamic_threshold": round(threshold, 3),
            "lag_growth_rate": 0.0,
            "db_pool_active": 0.15,
            "recent_p99_latency": 15.0,
        }

    @property
    def total_records(self) -> int:
        return len(self._history)
