"""
gRPC сервер для Inference Engine.

Архітектурне рішення (для магістерської):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Чому gRPC, а не REST для inference:
1. Protobuf бінарна серіалізація — у 3-10x менший розмір ніж JSON
2. HTTP/2 multiplexing — один TCP connection для всіх запитів
3. Строга типізація контрактів через .proto файли
4. Підтримка streaming (для batch inference)

Для зв'язку Gateway → Inference це критично:
кожна транзакція вимагає класифікації з latency < 5ms,
а REST+JSON додав би 2-3ms оверхеду на серіалізацію.
"""

import os
import sys
import time
import logging
from concurrent import futures

import grpc
from grpc_health.v1 import health, health_pb2, health_pb2_grpc
from grpc_reflection.v1alpha import reflection

# Додаємо generated папку до sys.path для імпорту згенерованих proto класів
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'generated'))

import transaction_pb2
import inference_pb2
import inference_pb2_grpc

from priority_engine import PriorityEngine
from metrics_store import MetricsStore

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("inference-engine")


class InferenceServicer(inference_pb2_grpc.InferenceServiceServicer):
    """
    Реалізація gRPC InferenceService.

    Три RPC методи:
    - GetPriority: класифікація однієї транзакції
    - GetBatchPriority: класифікація пакета транзакцій
    - UpdateSystemMetrics: оновлення метрик від інших сервісів
    """

    def __init__(self):
        self._engine = PriorityEngine()
        self._metrics = MetricsStore()
        logger.info("InferenceServicer initialized")

    def GetPriority(self, request, context):
        tx = self._proto_tx_to_dict(request.transaction)
        system_state = self._proto_state_to_dict(request.current_state) if request.HasField("current_state") else None

        if system_state is None:
            system_state = self._metrics.get_aggregated()

        result = self._engine.classify(tx, system_state)

        logger.info("Classified tx=%s → %s (score=%.3f, %dms)",
                     tx.get("id", "?"), result.priority.name,
                     result.score, result.inference_time_ms)

        return inference_pb2.PriorityResponse(
            priority=result.priority,
            score=result.score,
            reason=result.reason,
            inference_time_ms=result.inference_time_ms,
        )

    def GetBatchPriority(self, request, context):
        system_state = self._proto_state_to_dict(request.current_state) if request.HasField("current_state") else self._metrics.get_aggregated()
        responses = []

        for proto_tx in request.transactions:
            tx = self._proto_tx_to_dict(proto_tx)
            result = self._engine.classify(tx, system_state)
            responses.append(inference_pb2.PriorityResponse(
                priority=result.priority,
                score=result.score,
                reason=result.reason,
                inference_time_ms=result.inference_time_ms,
            ))

        logger.info("Batch classified %d transactions", len(responses))
        return inference_pb2.BatchPriorityResponse(responses=responses)

    def UpdateSystemMetrics(self, request, context):
        self._metrics.record(
            source=request.source,
            cpu=request.cpu_usage,
            memory=request.memory_usage,
            lag=request.consumer_lag,
            timestamp=request.timestamp,
        )

        aggregated = self._metrics.get_aggregated()
        self._engine.update_system_state(
            cpu=aggregated["cpu_usage"],
            memory=aggregated["memory_usage"],
            lag=aggregated["consumer_lag"],
            threshold=aggregated["dynamic_threshold"],
            consumers=aggregated["active_consumers"],
        )

        logger.debug("System metrics updated from %s", request.source)
        return inference_pb2.MetricsAck(success=True, message="Metrics recorded")

    @staticmethod
    def _proto_tx_to_dict(tx) -> dict:
        type_names = {
            0: "PAYMENT", 1: "REFUND", 2: "HEALTH_CHECK",
            3: "BALANCE_UPDATE", 4: "ADMIN_ACTION",
        }
        return {
            "id": tx.id,
            "user_id": tx.user_id,
            "amount": tx.amount,
            "currency": tx.currency,
            "region": tx.region,
            "type": type_names.get(tx.type, "PAYMENT"),
            "retry_count": tx.retry_count,
            "timestamp": tx.timestamp,
            "metadata": dict(tx.metadata),
        }

    @staticmethod
    def _proto_state_to_dict(state) -> dict:
        return {
            "cpu_usage": state.cpu_usage,
            "memory_usage": state.memory_usage,
            "consumer_lag": state.consumer_lag,
            "dynamic_threshold": state.dynamic_threshold,
            "active_consumers": state.active_consumers,
        }


def serve():
    port = os.getenv("GRPC_PORT", "50051")
    workers = int(os.getenv("GRPC_WORKERS", "10"))

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=workers))

    inference_pb2_grpc.add_InferenceServiceServicer_to_server(
        InferenceServicer(), server
    )

    # Health checking — потрібно щоб Docker healthcheck (grpc_health_probe) працював
    health_servicer = health.HealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
    health_servicer.set("inference.InferenceService", health_pb2.HealthCheckResponse.SERVING)
    health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)

    # Reflection — дозволяє інструментам типу grpcurl автоматично
    # знаходити сервіси та методи без .proto файлів
    service_names = (
        inference_pb2.DESCRIPTOR.services_by_name["InferenceService"].full_name,
        health_pb2.DESCRIPTOR.services_by_name["Health"].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(service_names, server)

    server.add_insecure_port(f"[::]:{port}")
    server.start()

    logger.info("Inference Engine started on port %s with %d workers", port, workers)

    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.stop(grace=5)


if __name__ == "__main__":
    serve()
