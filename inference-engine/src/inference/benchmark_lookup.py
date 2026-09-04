import time
import random
import statistics
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from lookup_rules import predict_priority
except ImportError:
    print("ERROR: lookup_rules.py not found. Run train.py first to generate it.")
    sys.exit(1)


def generate_random_features():
    return {
        "amount": random.uniform(1.0, 50000.0),
        "type_code": random.choice([0, 1, 2, 3, 4]),
        "retry_count": random.randint(0, 5),
        "consumer_lag": random.randint(0, 5000),
        "lag_growth_rate": random.uniform(-5.0, 25.0),
        "worker_cpu": random.uniform(10.0, 95.0),
        "db_pool_active": random.uniform(0.05, 0.95),
        "recent_p99_latency": random.uniform(15.0, 80.0)
    }


def run_benchmark(num_iterations=100_000):
    print(f"Benchmarking lookup_rules.predict_priority() over {num_iterations:,} iterations...")
    print("Warming up (1,000 iterations)...")

    for _ in range(1000):
        features = generate_random_features()
        predict_priority(features)

    latencies_us = []
    for _ in range(num_iterations):
        features = generate_random_features()
        start = time.perf_counter()
        predict_priority(features)
        elapsed_us = (time.perf_counter() - start) * 1_000_000
        latencies_us.append(elapsed_us)

    latencies_us.sort()
    mean_us = statistics.mean(latencies_us)
    median_us = statistics.median(latencies_us)
    p99_idx = int(len(latencies_us) * 0.99)
    p99_us = latencies_us[p99_idx]
    min_us = latencies_us[0]
    max_us = latencies_us[-1]

    print("\n" + "=" * 55)
    print("  NATIVE LOOKUP RULES MICRO-BENCHMARK RESULTS")
    print("=" * 55)
    print(f"  Iterations      : {num_iterations:>12,}")
    print(f"  Mean latency    : {mean_us:>12.3f} μs")
    print(f"  Median (p50)    : {median_us:>12.3f} μs")
    print(f"  Tail (p99)      : {p99_us:>12.3f} μs")
    print(f"  Min             : {min_us:>12.3f} μs")
    print(f"  Max             : {max_us:>12.3f} μs")
    print("=" * 55)

    if p99_us < 100.0:
        print("  ✅ PASS: p99 < 100μs (0.1ms) — sub-millisecond target met")
    else:
        print("  ⚠️  WARN: p99 >= 100μs — review lookup_rules complexity")
    print()


if __name__ == "__main__":
    run_benchmark()
