#!/usr/bin/env python3
import time
import json
import urllib.request

BURST_URL = "http://localhost:8080/api/v1/qos/test-burst"

def send_burst(count, tx_type="MIXED"):
    data = json.dumps({"count": count, "type": tx_type}).encode("utf-8")
    req = urllib.request.Request(BURST_URL, data=data, headers={"Content-Type": "application/json"})
    try:
        start = time.time()
        with urllib.request.urlopen(req, timeout=30) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            elapsed = time.time() - start
            print(f"[{time.strftime('%H:%M:%S')}] Sent {count:>4} txs | Mode: {res.get('modeUsed')} | "
                  f"Throughput: {res.get('throughputRps'):>8.1f} RPS | Avg Latency: {res.get('avgDecisionLatencyUs'):>6.1f} μs | "
                  f"P99: {res.get('p99LatencyUs'):>5} μs | Duration: {elapsed:.2f}s")
            print(f"             Distribution: {res.get('priorityDistribution')}")
    except Exception as e:
        print(f"Error sending burst: {e}")

def main():
    print("=" * 65)
    print("  GENERATING RICH LIVE TRAFFIC FOR GRAFANA MONITORING")
    print("=" * 65)
    print("Step 1: Baseline load (3 waves of 500 txs)...")
    for _ in range(3):
        send_burst(500)
        time.sleep(1.5)

    print("\nStep 2: Moderate surge (3 waves of 1,500 txs)...")
    for _ in range(3):
        send_burst(1500)
        time.sleep(2.0)

    print("\nStep 3: High-load PEAK SPIKE (3 waves of 3,000 txs)...")
    for _ in range(3):
        send_burst(3000)
        time.sleep(2.0)

    print("\nStep 4: Recovery & drain phase (2 waves of 800 txs)...")
    for _ in range(2):
        send_burst(800)
        time.sleep(1.5)

    print("\n" + "=" * 65)
    print("  ✅ Traffic generation complete! Total ~16,600 transactions sent.")
    print("  👉 Check Grafana at http://localhost:3000 (Set range to 'Last 5 minutes')")
    print("=" * 65)

if __name__ == "__main__":
    main()
