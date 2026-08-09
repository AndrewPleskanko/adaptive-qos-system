"""
Адаптивний алгоритм пріоритезації транзакцій.

Підтримує два режими роботи:
1. ML-режим: використовує навчену модель Decision Tree (якщо файл .pkl існує)
2. Rule-based режим: використовує математичні правила (fallback)

Для магістерської — це дозволяє порівняти ефективність ML vs Rule-based
підходів у розділі "Експериментальні дослідження".
"""

import os
import time
import pickle
import logging
from dataclasses import dataclass
from enum import IntEnum

import numpy as np

logger = logging.getLogger(__name__)

TYPE_MAP = {"PAYMENT": 0, "REFUND": 1, "HEALTH_CHECK": 2, "BALANCE_UPDATE": 3, "ADMIN_ACTION": 4}
REGION_MAP = {"US": 0, "EU": 1, "UK": 2, "DEFAULT": 3}


class Priority(IntEnum):
    LOW = 0
    STANDARD = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class SystemState:
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    consumer_lag: int = 0
    dynamic_threshold: float = 0.5
    active_consumers: int = 1


@dataclass
class PriorityResult:
    priority: Priority
    score: float
    reason: str
    inference_time_ms: int


TRANSACTION_TYPE_WEIGHTS = {
    "ADMIN_ACTION": 0.95,
    "BALANCE_UPDATE": 0.7,
    "PAYMENT": 0.5,
    "REFUND": 0.6,
    "HEALTH_CHECK": 0.1,
}

DEFAULT_THRESHOLDS = {
    Priority.CRITICAL: 0.85,
    Priority.HIGH: 0.60,
    Priority.STANDARD: 0.30,
}


class PriorityEngine:
    """
    Адаптивний движок пріоритезації з підтримкою ML-моделі.

    При ініціалізації намагається завантажити навчену модель з файлу.
    Якщо файл не знайдено — працює в rule-based режимі.
    """

    def __init__(self, model_path: str | None = None):
        self._system_state = SystemState()
        self._thresholds = dict(DEFAULT_THRESHOLDS)
        self._total_inferences = 0
        self._priority_counts = {p: 0 for p in Priority}
        self._ml_model = None
        self._mode = "rule-based"

        if model_path is None:
            model_path = os.getenv("MODEL_PATH", "/app/models/priority_model.pkl")

        self._load_model(model_path)

    def _load_model(self, model_path: str):
        try:
            if os.path.exists(model_path):
                with open(model_path, "rb") as f:
                    self._ml_model = pickle.load(f)
                self._mode = "ml-model"
                logger.info("ML model loaded from %s (mode: ml-model)", model_path)
            else:
                logger.info("No ML model found at %s, using rule-based mode", model_path)
        except Exception as e:
            logger.warning("Failed to load ML model: %s. Using rule-based mode", e)

    def update_system_state(self, cpu: float, memory: float,
                            lag: int, threshold: float, consumers: int):
        self._system_state = SystemState(
            cpu_usage=cpu,
            memory_usage=memory,
            consumer_lag=lag,
            dynamic_threshold=threshold,
            active_consumers=max(consumers, 1),
        )
        self._recalculate_thresholds()

    def classify(self, transaction: dict, system_state: dict | None = None) -> PriorityResult:
        start = time.monotonic_ns()

        if system_state:
            self.update_system_state(
                cpu=system_state.get("cpu_usage", 0),
                memory=system_state.get("memory_usage", 0),
                lag=system_state.get("consumer_lag", 0),
                threshold=system_state.get("dynamic_threshold", 0.5),
                consumers=system_state.get("active_consumers", 1),
            )

        if self._ml_model is not None:
            result = self._classify_ml(transaction)
        else:
            result = self._classify_rules(transaction)

        elapsed_ms = (time.monotonic_ns() - start) // 1_000_000

        self._total_inferences += 1
        self._priority_counts[result.priority] += 1

        return PriorityResult(
            priority=result.priority,
            score=result.score,
            reason=f"[{self._mode}] {result.reason}",
            inference_time_ms=elapsed_ms,
        )

    # ── ML-based класифікація ──────────────────────────────────────

    def _classify_ml(self, tx: dict) -> PriorityResult:
        features = np.array([[
            float(tx.get("amount", 0)),
            TYPE_MAP.get(tx.get("type", "PAYMENT"), 0),
            int(tx.get("retry_count", 0)),
            REGION_MAP.get(tx.get("region", "DEFAULT"), 3),
            self._system_state.cpu_usage,
            self._system_state.memory_usage,
            self._system_state.consumer_lag,
        ]])

        predicted_class = int(self._ml_model.predict(features)[0])
        probabilities = self._ml_model.predict_proba(features)[0]
        confidence = float(probabilities[predicted_class])

        priority = Priority(predicted_class)
        reason = (
            f"type={tx.get('type', '?')}, "
            f"amount={tx.get('amount', 0)}, "
            f"confidence={confidence:.3f}, "
            f"cpu={self._system_state.cpu_usage:.0f}%"
        )

        return PriorityResult(priority=priority, score=confidence, reason=reason, inference_time_ms=0)

    # ── Rule-based класифікація (fallback) ─────────────────────────

    def _classify_rules(self, tx: dict) -> PriorityResult:
        base_score = self._compute_base_score(tx)
        pressure = self._compute_pressure_coefficient()
        final_score = float(np.clip(base_score * pressure, 0.0, 1.0))

        priority = self._score_to_priority(final_score)
        reason = (
            f"type={tx.get('type', '?')}, "
            f"amount={tx.get('amount', 0)}, "
            f"base={base_score:.3f}, "
            f"pressure={pressure:.3f}, "
            f"final={final_score:.3f}"
        )

        return PriorityResult(priority=priority, score=round(final_score, 4), reason=reason, inference_time_ms=0)

    def _compute_base_score(self, tx: dict) -> float:
        scores = []

        tx_type = tx.get("type", "PAYMENT")
        type_score = TRANSACTION_TYPE_WEIGHTS.get(tx_type, 0.5)
        scores.append(("type", type_score, 0.35))

        amount = float(tx.get("amount", 0))
        amount_score = np.clip(amount / 10_000.0, 0.0, 1.0)
        scores.append(("amount", amount_score, 0.25))

        retry = int(tx.get("retry_count", 0))
        retry_score = np.clip(retry / 5.0, 0.0, 1.0)
        scores.append(("retry", retry_score, 0.20))

        region = tx.get("region", "DEFAULT")
        region_score = 0.8 if region in ("US", "EU", "UK") else 0.4
        scores.append(("region", region_score, 0.10))

        currency = tx.get("currency", "USD")
        currency_score = 0.6 if currency in ("USD", "EUR", "GBP") else 0.3
        scores.append(("currency", currency_score, 0.10))

        total = sum(score * weight for _, score, weight in scores)
        return float(np.clip(total, 0.0, 1.0))

    def _compute_pressure_coefficient(self) -> float:
        state = self._system_state
        cpu_factor = 1.0 - (state.cpu_usage / 100.0) * 0.3
        memory_factor = 1.0 - (state.memory_usage / 100.0) * 0.2
        lag_factor = 1.0 - np.clip(state.consumer_lag / 5000.0, 0.0, 0.4)
        coefficient = cpu_factor * memory_factor * lag_factor
        return float(np.clip(coefficient, 0.5, 1.5))

    def _score_to_priority(self, score: float) -> Priority:
        for priority in (Priority.CRITICAL, Priority.HIGH, Priority.STANDARD):
            if score >= self._thresholds[priority]:
                return priority
        return Priority.LOW

    def _recalculate_thresholds(self):
        state = self._system_state
        load = (state.cpu_usage + state.memory_usage) / 200.0
        self._thresholds[Priority.CRITICAL] = DEFAULT_THRESHOLDS[Priority.CRITICAL] + load * 0.1
        self._thresholds[Priority.HIGH] = DEFAULT_THRESHOLDS[Priority.HIGH] + load * 0.1
        self._thresholds[Priority.STANDARD] = DEFAULT_THRESHOLDS[Priority.STANDARD] + load * 0.05

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def stats(self) -> dict:
        return {
            "mode": self._mode,
            "total_inferences": self._total_inferences,
            "priority_distribution": {p.name: c for p, c in self._priority_counts.items()},
            "current_thresholds": {p.name: round(v, 3) for p, v in self._thresholds.items()},
            "system_state": {
                "cpu": self._system_state.cpu_usage,
                "memory": self._system_state.memory_usage,
                "lag": self._system_state.consumer_lag,
            },
        }
