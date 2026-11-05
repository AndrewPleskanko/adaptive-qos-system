import random

def predict_priority(features: dict) -> tuple:
    type_code = features.get("type_code", 4)
    amount = features.get("amount", 0.0)
    retry_count = features.get("retry_count", 0)
    recent_p99 = features.get("recent_p99_latency", 20.0)
    db_pool = features.get("db_pool_active", 0.15)
    worker_cpu = features.get("worker_cpu", 30.0)
    lag_growth = features.get("lag_growth_rate", 0.0)

    if type_code <= 0.5:
        return 0, 0.9850
    if type_code <= 1.5:
        if retry_count >= 3:
            return 1, 0.8500
        return 0, 0.9600

    if retry_count >= 2:
        if amount >= 1000.0 or type_code >= 3.5:
            return 3, 0.9200
        return 2, 0.8800

    system_stress = (worker_cpu > 80.0) or (db_pool > 0.75) or (recent_p99 > 45.0)

    if type_code <= 2.5:
        if system_stress and lag_growth > 10.0:
            return 0, 0.8000
        if amount > 5000.0:
            return 2, 0.8500
        return 1, 0.9100

    if type_code <= 3.5:
        if system_stress:
            return 1, 0.8200
        if amount > 2500.0:
            return 3, 0.8900
        return 2, 0.8700

    if amount >= 1200.0:
        if system_stress and amount < 3500.0:
            return 2, 0.8400
        return 3, 0.9400
    elif amount >= 300.0:
        if system_stress:
            return 1, 0.8500
        return 2, 0.8800
    else:
        return 1, 0.9200

random.seed(42)
types_pool = ["PAYMENT"] * 55 + ["REFUND"] * 15 + ["BALANCE_UPDATE"] * 15 + ["ADMIN_ACTION"] * 5 + ["HEALTH_CHECK"] * 10
type_map = {"HEALTH_CHECK": 0, "ADMIN_ACTION": 1, "BALANCE_UPDATE": 2, "REFUND": 3, "PAYMENT": 4}
priority_names = {0: "LOW", 1: "STANDARD", 2: "HIGH", 3: "CRITICAL"}

matrix = {t: {"CRITICAL": 0, "HIGH": 0, "STANDARD": 0, "LOW": 0, "total": 0} for t in type_map}
totals = {"CRITICAL": 0, "HIGH": 0, "STANDARD": 0, "LOW": 0}

for _ in range(5000):
    t_name = random.choice(types_pool)
    t_code = type_map[t_name]
    amt = random.lognormvariate(5.5, 1.2)
    amt = max(1.0, min(amt, 50000.0))
    ret = random.choice([0]*80 + [1]*12 + [2]*5 + [3]*2 + [4]*1)
    cpu = random.uniform(15.0, 85.0)
    lag = random.randint(0, 3000)
    growth = random.uniform(-5.0, 20.0)
    db = random.uniform(0.1, 0.7)
    p99 = 15.0 + cpu * 0.3 + db * 20.0

    feat = {
        "type_code": t_code, "amount": amt, "retry_count": ret,
        "worker_cpu": cpu, "consumer_lag": lag, "lag_growth_rate": growth,
        "db_pool_active": db, "recent_p99_latency": p99
    }
    p_code, _ = predict_priority(feat)
    p_name = priority_names[p_code]

    matrix[t_name][p_name] += 1
    matrix[t_name]["total"] += 1
    totals[p_name] += 1

print(f"{'TYPE':<15} | {'CRIT':<6} | {'HIGH':<6} | {'STD':<6} | {'LOW':<6} | {'TOTAL':<6}")
print("-" * 55)
for t_name, c in matrix.items():
    print(f"{t_name:<15} | {c['CRITICAL']:<6} | {c['HIGH']:<6} | {c['STANDARD']:<6} | {c['LOW']:<6} | {c['total']:<6}")
print("-" * 55)
print(f"{'TOTAL':<15} | {totals['CRITICAL']:<6} | {totals['HIGH']:<6} | {totals['STANDARD']:<6} | {totals['LOW']:<6} | 5000")
print()
for p in ["CRITICAL", "HIGH", "STANDARD", "LOW"]:
    pct = totals[p] / 5000.0 * 100
    print(f"{p}: {totals[p]} ({pct:.2f}%)")
