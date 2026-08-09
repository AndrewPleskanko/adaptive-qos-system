"""
Скрипт для генерації синтетичних даних та навчання ML-моделі пріоритезації.

Для магістерської роботи:
━━━━━━━━━━━━━━━━━━━━━━━━━
Цей скрипт імітує збір історичних даних роботи QoS-системи.
Ми навчаємо модель Decision Tree Classifier (Дерево рішень) прогнозувати
клас пріоритету (LOW, STANDARD, HIGH, CRITICAL) на основі вхідних параметрів
транзакції та поточного стану системи.

Перевага Decision Tree:
- Дуже висока швидкість роботи (інференс < 0.1 мс), що критично для високонавантажених систем.
- Легко візуалізується та інтерпретується (можна побудувати графік дерева рішень для диплома).
"""

import os
import pickle
import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# Словники для кодування категоріальних ознак у числа
TYPE_MAP = {"PAYMENT": 0, "REFUND": 1, "HEALTH_CHECK": 2, "BALANCE_UPDATE": 3, "ADMIN_ACTION": 4}
REGION_MAP = {"US": 0, "EU": 1, "UK": 2, "DEFAULT": 3}


def generate_synthetic_data(num_samples=10000):
    """
    Генерує синтетичний датасет на основі наших математичних правил пріоритезації.
    Це імітує накопичені історичні дані реальної платіжної системи.
    """
    np.random.seed(42)

    # 1. Генерація випадкових параметрів транзакцій
    amounts = np.random.exponential(scale=500, size=num_samples)  # більшість сум невеликі, але є довгий хвіст
    amounts = np.clip(amounts, 1.0, 50000.0)

    types = np.random.choice(list(TYPE_MAP.keys()), size=num_samples, p=[0.6, 0.15, 0.05, 0.15, 0.05])
    regions = np.random.choice(list(REGION_MAP.keys()), size=num_samples, p=[0.4, 0.3, 0.1, 0.2])
    retries = np.random.poisson(lam=0.2, size=num_samples)  # більшість мають 0 ретраїв
    retries = np.clip(retries, 0, 5)

    # 2. Генерація стану системи в момент транзакції
    cpu_usages = np.random.uniform(10.0, 95.0, size=num_samples)
    mem_usages = np.random.uniform(20.0, 90.0, size=num_samples)
    lags = np.random.negative_binomial(n=1, p=0.002, size=num_samples)  # більшість лагів малі, але бувають спайки
    lags = np.clip(lags, 0, 5000)

    data = []
    for i in range(num_samples):
        # Розрахунок базового score
        tx_type = types[i]
        amount = amounts[i]
        retry = retries[i]
        reg = regions[i]

        # Базові правила
        if tx_type == "ADMIN_ACTION":
            base_score = 0.95
        elif tx_type == "HEALTH_CHECK":
            base_score = 0.1
        else:
            type_weight = {"PAYMENT": 0.5, "REFUND": 0.6, "BALANCE_UPDATE": 0.4}[tx_type]
            amount_score = min(amount / 10000.0, 1.0)
            retry_score = min(retry / 5.0, 1.0)
            region_score = 0.8 if reg in ("US", "EU", "UK") else 0.4
            base_score = type_weight * 0.4 + amount_score * 0.3 + retry_score * 0.2 + region_score * 0.1

        # Коефіцієнт тиску системи (backpressure)
        cpu = cpu_usages[i]
        mem = mem_usages[i]
        lag = lags[i]

        cpu_factor = 1.0 - (cpu / 100.0) * 0.3
        mem_factor = 1.0 - (mem / 100.0) * 0.2
        lag_factor = 1.0 - min(lag / 5000.0, 0.4)
        pressure = cpu_factor * mem_factor * lag_factor

        # Фінальний бал під тиском
        final_score = np.clip(base_score * pressure, 0.0, 1.0)

        # Класифікація в пріоритет (класи 0, 1, 2, 3)
        # При високому навантаженні (cpu/lag) пороги складніше подолати
        load_factor = (cpu + mem) / 200.0
        critical_t = 0.85 + load_factor * 0.1
        high_t = 0.60 + load_factor * 0.1
        std_t = 0.30 + load_factor * 0.05

        if final_score >= critical_t:
            priority = 3  # CRITICAL
        elif final_score >= high_t:
            priority = 2  # HIGH
        elif final_score >= std_t:
            priority = 1  # STANDARD
        else:
            priority = 0  # LOW

        data.append({
            "amount": amount,
            "type_code": TYPE_MAP[tx_type],
            "retry_count": retry,
            "region_code": REGION_MAP[reg],
            "cpu_usage": cpu,
            "memory_usage": mem,
            "consumer_lag": lag,
            "priority": priority
        })

    return pd.DataFrame(data)


def main():
    print("Generating synthetic transaction history for training...")
    df = generate_synthetic_data(15000)

    # Визначаємо фічі (X) та цільову мітку (y)
    feature_cols = ["amount", "type_code", "retry_count", "region_code", "cpu_usage", "memory_usage", "consumer_lag"]
    X = df[feature_cols]
    y = df["priority"]

    # Розбиваємо на навчальну та тестову вибірки (80% / 20%)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    print(f"Training DecisionTreeClassifier on {len(X_train)} samples...")
    # Обмежуємо глибину дерева (max_depth=6), щоб уникнути перенавчання (overfitting)
    # та зберегти швидкість інференсу
    model = DecisionTreeClassifier(max_depth=6, random_state=42)
    model.fit(X_train, y_train)

    # Оцінка якості
    y_pred = model.predict(X_test)
    print("\nModel Evaluation Report:")
    print(classification_report(y_test, y_pred, target_names=["LOW", "STANDARD", "HIGH", "CRITICAL"], labels=[0, 1, 2, 3]))

    # Збереження моделі
    models_dir = os.path.join(os.path.dirname(__file__), "..", "..", "models")
    os.makedirs(models_dir, exist_ok=True)
    model_path = os.path.join(models_dir, "priority_model.pkl")

    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    print(f"\nSUCCESS: ML model trained and saved to: {model_path}")


if __name__ == "__main__":
    main()
