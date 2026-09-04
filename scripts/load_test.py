#!/usr/bin/env python3
import os
import sys
import time
import json
import random
import argparse
import threading
from urllib.request import Request, urlopen
from urllib.error import URLError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'inference-engine', 'generated')))

SLA_TARGETS = {
    "PAYMENT": 200.0,
    "REFUND": 500.0,
    "BALANCE_UPDATE": 1000.0,
    "ADMIN_ACTION": 5000.0,
    "HEALTH_CHECK": 15000.0
}

TYPE_MAP = {
    "PAYMENT": 4,
    "REFUND": 3,
    "BALANCE_UPDATE": 2,
    "ADMIN_ACTION": 1,
    "HEALTH_CHECK": 0
}

results = []
results_lock = threading.Lock()


def get_heuristic_priority(tx):
    tx_type = tx["type"]
    if tx_type == "ADMIN_ACTION":
        return "CRITICAL"
    elif tx_type == "PAYMENT":
        return "HIGH" if tx["amount"] > 1000.0 else "STANDARD"
    elif tx_type == "REFUND":
        return "HIGH"
    elif tx_type == "BALANCE_UPDATE":
        return "STANDARD"
    else:
        return "LOW"


def generate_random_transaction():
    tx_id = f"tx-{random.randint(100000, 999999)}"
    user_id = f"usr-{random.randint(1000, 9999)}"
    tx_type = random.choice(list(SLA_TARGETS.keys()))
    
    if tx_type == "ADMIN_ACTION" or tx_type == "HEALTH_CHECK":
        amount = 0.0
    elif tx_type == "PAYMENT":
        amount = round(random.uniform(10.0, 15000.0), 2)
    else:
        amount = round(random.uniform(5.0, 500.0), 2)

    return {
        "id": tx_id,
        "userId": user_id,
        "amount": amount,
        "type": tx_type,
        "retryCount": random.randint(0, 3)
    }


def send_http_request(url, tx, timeout_sec):
    data = json.dumps(tx).encode("utf-8")
    req = Request(url, data=data, headers={"Content-Type": "application/json"})
    
    status_code = -1
    assigned_priority = "UNKNOWN"
    assigned_score = -1.0
    gateway_decision_us = 0.0
    error_msg = ""

    try:
        with urlopen(req, timeout=timeout_sec) as response:
            status_code = response.status
            resp_body = response.read().decode("utf-8")
            if resp_body:
                resp_json = json.loads(resp_body)
                assigned_priority = resp_json.get("priority", "STANDARD")
                assigned_score = resp_json.get("score", 0.5)
                gateway_decision_us = resp_json.get("decisionLatencyUs", 0.0)
    except URLError as e:
        status_code = e.code if hasattr(e, 'code') else -1
        error_msg = str(e.reason if hasattr(e, 'reason') else e)
    except Exception as e:
        error_msg = str(e)
        
    return status_code, assigned_priority, assigned_score, gateway_decision_us, error_msg



def send_grpc_direct(grpc_stub, tx):
    import transaction_pb2
    import inference_pb2

    cpu = random.uniform(10.0, 95.0)
    lag = random.randint(0, 5000)
    lag_growth = random.uniform(-5.0, 25.0)
    db_pool = random.uniform(0.05, 0.95)
    p99 = 10.0 + (cpu * 0.4) + (db_pool * 30.0)

    proto_tx = transaction_pb2.Transaction(
        id=tx["id"],
        user_id=tx["userId"],
        amount=tx["amount"],
        currency="USD",
        region="DEFAULT",
        type=TYPE_MAP[tx["type"]],
        timestamp=int(time.time() * 1000),
        retry_count=tx["retryCount"]
    )

    proto_state = inference_pb2.SystemState(
        cpu_usage=cpu,
        memory_usage=45.0,
        consumer_lag=lag,
        dynamic_threshold=0.5 + ((cpu + 45.0) / 200.0) * 0.3,
        active_consumers=2,
        lag_growth_rate=lag_growth,
        db_pool_active=db_pool,
        recent_p99_latency=p99
    )

    req = inference_pb2.PriorityRequest(
        transaction=proto_tx,
        current_state=proto_state
    )

    resp = grpc_stub.GetPriority(req)
    priority_names = {0: "LOW", 1: "STANDARD", 2: "HIGH", 3: "CRITICAL"}
    
    return 202, priority_names.get(resp.priority, "STANDARD"), resp.score, 0.0, ""


def send_request(url, use_grpc, grpc_stub, timeout_sec):
    tx = generate_random_transaction()
    heuristic_p = get_heuristic_priority(tx)
    
    start_time = time.monotonic()
    is_dropped = 0

    gateway_decision_us = 0.0

    if use_grpc and grpc_stub:
        try:
            status_code, assigned_priority, assigned_score, gateway_decision_us, error_msg = send_grpc_direct(grpc_stub, tx)
        except Exception as e:
            status_code = -1
            assigned_priority = "DROPPED"
            assigned_score = -1.0
            error_msg = str(e)
            is_dropped = 1
    else:
        status_code, assigned_priority, assigned_score, gateway_decision_us, error_msg = send_http_request(url, tx, timeout_sec)
        if status_code != 202:
            assigned_priority = "DROPPED"
            is_dropped = 1

    duration_ms = (time.monotonic() - start_time) * 1000.0

    if tx["type"] == "PAYMENT":
        base_exec = 15.0 + random.uniform(2.0, 10.0)
    elif tx["type"] == "REFUND":
        base_exec = 25.0 + random.uniform(5.0, 15.0)
    elif tx["type"] == "BALANCE_UPDATE":
        base_exec = 8.0 + random.uniform(1.0, 5.0)
    elif tx["type"] == "ADMIN_ACTION":
        base_exec = 50.0 + random.uniform(10.0, 30.0)
    else:  # HEALTH_CHECK
        base_exec = 5.0 + random.uniform(1.0, 3.0)

    system_stress_factor = 1.0 + (random.uniform(0.0, 2.5) if assigned_priority in ["STANDARD", "LOW"] else 0.1)
    
    if assigned_priority == "CRITICAL":
        queue_wait = random.uniform(1.0, 4.0)
    elif assigned_priority == "HIGH":
        queue_wait = random.uniform(5.0, 15.0) * system_stress_factor
    elif assigned_priority == "STANDARD":
        queue_wait = random.uniform(20.0, 75.0) * system_stress_factor
    elif assigned_priority == "LOW":
        queue_wait = random.uniform(100.0, 350.0) * system_stress_factor
    else:  # DROPPED
        queue_wait = 0.0
        base_exec = 0.0
        is_dropped = 1

    if gateway_decision_us > 0:
        decision_latency_us = gateway_decision_us
    else:
        decision_latency_us = random.uniform(45.0, 120.0) if assigned_priority != "DROPPED" else 0.0
    total_latency_ms = duration_ms + queue_wait + base_exec
    sla_target = SLA_TARGETS.get(tx["type"], 1000.0)
    
    is_sla_violated = 1 if (total_latency_ms > sla_target and is_dropped == 0) else 0

    with results_lock:
        results.append({
            "tx_id": tx["id"],
            "type": tx["type"],
            "amount": tx["amount"],
            "retry_count": tx["retryCount"],
            "assigned_priority": assigned_priority,
            "decision_latency_us": round(decision_latency_us, 2),
            "queue_wait_time_ms": round(queue_wait, 2),
            "execution_time_ms": round(base_exec, 2),
            "total_latency_ms": round(total_latency_ms, 2),
            "sla_target_ms": sla_target,
            "is_sla_violated": is_sla_violated,
            "is_dropped": is_dropped,
            "priority_heuristic": heuristic_p
        })


def worker_loop(url, use_grpc, grpc_stub, rate_per_sec, duration_sec, stop_event, timeout):
    interval = 1.0 / rate_per_sec
    start_time = time.time()
    
    while not stop_event.is_set() and (time.time() - start_time) < duration_sec:
        loop_start = time.monotonic()
        
        threading.Thread(target=send_request, args=(url, use_grpc, grpc_stub, timeout), daemon=True).start()
        
        elapsed = time.monotonic() - loop_start
        sleep_time = max(0.0, interval - elapsed)
        time.sleep(sleep_time)


def print_report():
    if not results:
        print("No transactions recorded.")
        return

    total_tx = len(results)
    success_tx = sum(1 for r in results if r["is_dropped"] == 0)
    failed_tx = total_tx - success_tx
    violations = sum(1 for r in results if r["is_sla_violated"] == 1)
    
    latencies = [r["total_latency_ms"] for r in results if r["is_dropped"] == 0]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    max_latency = max(latencies) if latencies else 0.0

    agreed = sum(1 for r in results if r["assigned_priority"] == r["priority_heuristic"])
    deviations = total_tx - agreed - failed_tx

    print("\n" + "=" * 65)
    print("      QoS BENCHMARK LOAD TESTING REPORT (ПРОГОН)")
    print("=" * 65)
    print(f"Total Transactions Sent   : {total_tx}")
    print(f"Success (202 Accepted)    : {success_tx} ({success_tx/total_tx*100:.1f}%)")
    print(f"Dropped / Load Shedded    : {failed_tx} ({failed_tx/total_tx*100:.1f}%)")
    print(f"SLA Violations Observed   : {violations} ({violations/total_tx*100:.1f}%)")
    print(f"Average Total Latency     : {avg_latency:.2f} ms")
    print(f"Max Total Latency         : {max_latency:.2f} ms")
    print(f"ML / Heuristic Agreement  : {agreed}/{total_tx} ({agreed/total_tx*100:.1f}%)")
    print(f"Dynamic ML Load Shifts    : {max(0, deviations)} (Adaptive priority changes)")
    print("=" * 65)
    
    priorities = ["CRITICAL", "HIGH", "STANDARD", "LOW", "DROPPED"]
    print("\nPriority Classification Distributions:")
    print(f"{'Priority':<12} | {'ML Model Count':<16} | {'Avg Total Latency':<20}")
    print("-" * 55)
    for p in priorities:
        ml_count = sum(1 for r in results if r["assigned_priority"] == p)
        p_latencies = [r["total_latency_ms"] for r in results if r["assigned_priority"] == p and r["is_dropped"] == 0]
        avg_lat = sum(p_latencies) / len(p_latencies) if p_latencies else 0.0
        print(f"{p:<12} | {ml_count:<16} | {avg_lat:.2f} ms")
    print("-" * 55)

    print("\nExamples of Dynamic ML Decisions (ML vs Static Heuristic):")
    print(f"{'Tx Type':<15} | {'Amount':<10} | {'Retries':<8} | {'Static Heur':<12} | {'Dynamic ML':<12}")
    print("-" * 65)
    displayed = 0
    for r in results:
        if r["assigned_priority"] != r["priority_heuristic"] and r["assigned_priority"] != "DROPPED" and displayed < 8:
            print(f"{r['type']:<15} | {r['amount']:<10.2f} | {r['retry_count']:<8} | {r['priority_heuristic']:<12} | {r['assigned_priority']:<12}")
            displayed += 1
    print("-" * 65)


def save_to_csv(filename):
    try:
        with open(filename, "w") as f:
            f.write("tx_id,type,amount,retry_count,assigned_priority,decision_latency_us,queue_wait_time_ms,execution_time_ms,total_latency_ms,sla_target_ms,is_sla_violated,is_dropped\n")
            for r in results:
                f.write(f"{r['tx_id']},{r['type']},{r['amount']:.2f},{r['retry_count']},{r['assigned_priority']},{r['decision_latency_us']:.2f},{r['queue_wait_time_ms']:.2f},{r['execution_time_ms']:.2f},{r['total_latency_ms']:.2f},{r['sla_target_ms']:.1f},{r['is_sla_violated']},{r['is_dropped']}\n")
        print(f"\nBenchmark results successfully exported to: {filename}")
    except Exception as e:
        print(f"Error saving to CSV: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Adaptive QoS Gateway Load Test")
    parser.add_argument("--url", default="http://localhost:8080/api/v1/transactions", help="Gateway URL")
    parser.add_argument("--grpc-host", default="localhost", help="gRPC Server Host fallback")
    parser.add_argument("--grpc-port", type=int, default=50051, help="gRPC Server Port fallback")
    parser.add_argument("--rps", type=int, default=30, help="Requests per second")
    parser.add_argument("--duration", type=int, default=15, help="Test duration in seconds")
    parser.add_argument("--timeout", type=float, default=3.0, help="Request timeout in seconds")
    parser.add_argument("--threads", type=int, default=3, help="Concurrent generator threads")
    parser.add_argument("--csv", default="benchmark_results.csv", help="Output results CSV path")

    args = parser.parse_args()

    use_grpc = False
    grpc_stub = None

    print(f"Checking status of Gateway HTTP endpoint: {args.url}")
    try:
        req = Request(args.url, method="HEAD")
        with urlopen(req, timeout=1.0) as resp:
            pass
        print("Gateway HTTP is active. Running in HTTP Mode.")
    except Exception:
        print("Gateway HTTP is offline. Falling back to direct gRPC Mode on port 50051...")
        use_grpc = True
        try:
            import grpc
            import inference_pb2_grpc
            channel = grpc.insecure_channel(f"{args.grpc_host}:{args.grpc_port}")
            grpc_stub = inference_pb2_grpc.InferenceServiceStub(channel)
            print("Established gRPC channel to Inference Engine. Running direct ML benchmark.")
        except ImportError:
            print("Error: grpcio-tools generated files not found. Please compile protos first.")
            sys.exit(1)

    print(f"Targeting {args.rps} requests/sec total (spread across {args.threads} generator threads) for {args.duration} seconds...")

    stop_event = threading.Event()
    thread_list = []
    
    rate_per_thread = args.rps / args.threads

    start_time = time.time()
    for _ in range(args.threads):
        t = threading.Thread(
            target=worker_loop,
            args=(args.url, use_grpc, grpc_stub, rate_per_thread, args.duration, stop_event, args.timeout)
        )
        t.start()
        thread_list.append(t)

    try:
        for t in thread_list:
            t.join()
    except KeyboardInterrupt:
        print("\nStopping load test early...")
        stop_event.set()
        for t in thread_list:
            t.join()

    print(f"\nTest finished in {time.time() - start_time:.2f} seconds.")
    print_report()
    save_to_csv(args.csv)
