import os
import pickle
import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

TYPE_MAP = {
    "PAYMENT": 4,
    "REFUND": 3,
    "BALANCE_UPDATE": 2,
    "ADMIN_ACTION": 1,
    "HEALTH_CHECK": 0
}


def generate_paysim_workload(num_samples=15000):
    np.random.seed(42)

    types = np.random.choice(
        list(TYPE_MAP.keys()),
        size=num_samples,
        p=[0.55, 0.15, 0.15, 0.05, 0.10]
    )

    amounts = np.random.lognormal(mean=5.5, sigma=1.2, size=num_samples)
    amounts = np.clip(amounts, 1.0, 50000.0)

    retries = np.random.poisson(lam=0.2, size=num_samples)
    retries = np.clip(retries, 0, 5)

    worker_cpu = np.random.uniform(10.0, 95.0, size=num_samples)
    consumer_lag = np.random.negative_binomial(n=1, p=0.002, size=num_samples)
    consumer_lag = np.clip(consumer_lag, 0, 5000)

    lag_growth_rate = np.random.uniform(-5.0, 25.0, size=num_samples)

    db_pool_active = np.random.uniform(0.05, 0.95, size=num_samples)

    recent_p99_latency = 10.0 + (worker_cpu * 0.4) + (db_pool_active * 30.0) + np.random.uniform(0.0, 10.0, size=num_samples)

    data = []
    for i in range(num_samples):
        tx_type = types[i]
        type_val = TYPE_MAP[tx_type]
        amount = amounts[i]
        retry = retries[i]
        cpu = worker_cpu[i]
        lag = consumer_lag[i]
        growth = lag_growth_rate[i]
        db = db_pool_active[i]
        p99 = recent_p99_latency[i]

        if tx_type == "PAYMENT":
            amount_score = min(amount / 5000.0, 1.0)
            base_score = 0.65 + amount_score * 0.30
        elif tx_type == "REFUND":
            base_score = 0.70
        elif tx_type == "BALANCE_UPDATE":
            base_score = 0.45
        elif tx_type == "ADMIN_ACTION":
            base_score = 0.85
        else:  # HEALTH_CHECK
            base_score = 0.15

        pressure = (cpu / 100.0) * 0.3 + (lag / 5000.0) * 0.2 + (db * 0.3) + (p99 / 100.0) * 0.2
        if growth > 15.0:
            pressure += 0.1

        retry_boost = min(retry * 0.12, 0.36)

        final_score = np.clip(base_score - pressure * 0.25 + retry_boost, 0.0, 1.0)

        if final_score >= 0.82:
            priority = 3  # CRITICAL
        elif final_score >= 0.58:
            priority = 2  # HIGH
        elif final_score >= 0.32:
            priority = 1  # STANDARD
        else:
            priority = 0  # LOW

        data.append({
            "amount": amount,
            "type_code": type_val,
            "retry_count": retry,
            "consumer_lag": lag,
            "lag_growth_rate": growth,
            "worker_cpu": cpu,
            "db_pool_active": db,
            "recent_p99_latency": p99,
            "priority": priority
        })

    return pd.DataFrame(data)


def export_native_rules(tree, feature_names, output_path):
    left      = tree.tree_.children_left
    right     = tree.tree_.children_right
    threshold = tree.tree_.threshold
    value     = tree.tree_.value
    features  = tree.tree_.feature

    def recurse(node, depth):
        indent = "    " * depth
        if left[node] == -1:
            class_idx = int(np.argmax(value[node][0]))
            total = float(np.sum(value[node][0]))
            confidence = float(value[node][0][class_idx] / total) if total > 0 else 1.0
            return f"{indent}return {class_idx}, {confidence:.4f}\n"
        else:
            name = feature_names[features[node]]
            thresh = threshold[node]
            rule_str = f"{indent}if features['{name}'] <= {thresh:.4f}:\n"
            rule_str += recurse(left[node], depth + 1)
            rule_str += f"{indent}else:\n"
            rule_str += recurse(right[node], depth + 1)
            return rule_str

    with open(output_path, "w") as f:
        f.write("def predict_priority(features: dict) -> tuple:\n")
        f.write(recurse(0, 1))
    print(f"Exported native in-memory lookup rules to: {output_path}")


def main():
    print("Preparing transaction training dataset for policy distillation...")
    df = generate_paysim_workload(15000)

    feature_cols = [
        "amount",
        "type_code",
        "retry_count",
        "consumer_lag",
        "lag_growth_rate",
        "worker_cpu",
        "db_pool_active",
        "recent_p99_latency"
    ]
    X = df[feature_cols]
    y = df["priority"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"Training Decision Tree Classifier (max_depth=5, min_samples_leaf=20) on {len(X_train)} samples...")
    model = DecisionTreeClassifier(max_depth=5, min_samples_leaf=20, random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    print("\nSurrogate Model Evaluation Report:")
    print(classification_report(
        y_test, y_pred,
        target_names=["LOW", "STANDARD", "HIGH", "CRITICAL"],
        labels=[0, 1, 2, 3]
    ))

    print("\n=== Distilled Prioritization Policy Rules (Flowchart) ===")
    tree_rules = export_text(model, feature_names=feature_cols)
    print(tree_rules)
    print("=========================================================")

    src_dir = os.path.dirname(__file__)
    export_native_rules(model, feature_cols, os.path.join(src_dir, "lookup_rules.py"))

    models_dir = os.path.join(os.path.dirname(__file__), "..", "..", "models")
    os.makedirs(models_dir, exist_ok=True)
    model_path = os.path.join(models_dir, "priority_model.pkl")

    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    print(f"\nSUCCESS: ML surrogate model trained and saved to: {model_path}")


if __name__ == "__main__":
    main()
