def predict_priority(features: dict) -> tuple:
    type_code = features.get('type_code', 4)
    amount = features.get('amount', 0.0)
    retry_count = features.get('retry_count', 0)
    recent_p99 = features.get('recent_p99_latency', 20.0)
    db_pool = features.get('db_pool_active', 0.15)
    worker_cpu = features.get('worker_cpu', 30.0)
    lag_growth = features.get('lag_growth_rate', 0.0)

    # 1. Background batch / system health pings -> strictly LOW
    if type_code <= 0.5:  # HEALTH_CHECK (0)
        return 0, 0.9850  # LOW
    if type_code <= 1.5:  # ADMIN_ACTION (1)
        if retry_count >= 3:
            return 1, 0.8500  # STANDARD (prevent eternal starvation)
        return 0, 0.9600  # LOW

    # 2. Anti-starvation promotion for repeated retries
    if retry_count >= 2:
        if amount >= 1000.0 or type_code >= 3.5:
            return 3, 0.9200  # CRITICAL
        return 2, 0.8800  # HIGH

    # 3. Dynamic system stress detection (CPU > 80% or DB pool > 75% or tail latency > 45ms)
    system_stress = (worker_cpu > 80.0) or (db_pool > 0.75) or (recent_p99 > 45.0)

    # 4. BALANCE_UPDATE (2) -> fast micro-operations
    if type_code <= 2.5:
        if system_stress and lag_growth > 10.0:
            return 0, 0.8000  # Demote to LOW under extreme overload
        if amount > 5000.0:
            return 2, 0.8500  # HIGH
        return 1, 0.9100  # STANDARD

    # 5. REFUND (3) -> high priority customer care
    if type_code <= 3.5:
        if system_stress:
            return 1, 0.8200  # STANDARD under stress
        if amount > 2500.0:
            return 3, 0.8900  # CRITICAL
        return 2, 0.8700  # HIGH

    # 6. PAYMENT (4) -> core business transactions
    if amount >= 1200.0:
        if system_stress and amount < 3500.0:
            return 2, 0.8400  # HIGH under stress
        return 3, 0.9400  # CRITICAL (VIP transaction)
    elif amount >= 300.0:
        if system_stress:
            return 1, 0.8500  # Demote to STANDARD under stress
        return 2, 0.8800  # HIGH
    else:
        # Micro-payments (< $300)
        return 1, 0.9200  # STANDARD
