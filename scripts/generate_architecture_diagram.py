#!/usr/bin/env python3
"""
Generates a publication-grade 300-DPI Architecture Diagram (Рисунок 1)
for the MCETI-2026 conference paper and thesis.
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUTPUT_PATH = os.path.join(PROJECT_ROOT, 'thesis', 'images', 'architecture_diagram.png')
DASHBOARD_PATH = os.path.join(PROJECT_ROOT, 'admin-dashboard', 'public', 'charts', 'architecture_diagram.png')

def draw_architecture():
    fig, ax = plt.subplots(figsize=(11, 6.2), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # Color Palette - Professional Engineering
    c_client = "#e0f2fe"       # Light Sky
    c_client_b = "#0284c7"
    c_gw = "#fef3c7"           # Amber
    c_gw_b = "#d97706"
    c_ml = "#dcfce7"           # Emerald
    c_ml_b = "#16a34a"
    c_kafka = "#fee2e2"        # Rose / Red
    c_kafka_b = "#dc2626"
    c_proc = "#f3e8ff"         # Purple
    c_proc_b = "#9333ea"
    c_db = "#f1f5f9"           # Slate
    c_db_b = "#475569"

    # 1. CLIENT TIER
    rect_client = patches.FancyBboxPatch((3, 62), 22, 32, boxstyle="round,pad=0.5",
                                         facecolor=c_client, edgecolor=c_client_b, linewidth=1.5)
    ax.add_patch(rect_client)
    ax.text(14, 90, "1. Client Layer", ha='center', va='center', fontsize=11, fontweight='bold', color='#0369a1')
    ax.text(14, 78, "Admin Dashboard\n(Angular 21 UI)\n──────────────────\n• Traffic Burst Generator\n• 3-Way Benchmark Runner\n• Real-time Telemetry",
            ha='center', va='center', fontsize=8.5, color='#0f172a')

    # 2. API GATEWAY
    rect_gw = patches.FancyBboxPatch((32, 62), 26, 32, boxstyle="round,pad=0.5",
                                     facecolor=c_gw, edgecolor=c_gw_b, linewidth=1.5)
    ax.add_patch(rect_gw)
    ax.text(45, 90, "2. API Gateway Service", ha='center', va='center', fontsize=11, fontweight='bold', color='#b45309')
    ax.text(45, 78, "Spring Boot 3 (Java 21 LTS)\n─────────────────────\n• Ingress Filter & 8D Vector\n• Dynamic Threshold θ(t)\n• QoS Mode Switcher\n• Partition Key Dispatch",
            ha='center', va='center', fontsize=9, color='#0f172a')

    # 3. INFERENCE ENGINE
    rect_ml = patches.FancyBboxPatch((66, 62), 31, 32, boxstyle="round,pad=0.5",
                                     facecolor=c_ml, edgecolor=c_ml_b, linewidth=1.5)
    ax.add_patch(rect_ml)
    ax.text(81.5, 90, "3. Sub-ms Inference Engine", ha='center', va='center', fontsize=11, fontweight='bold', color='#15803d')
    ax.text(81.5, 77, "Python 3.12 (gRPC Service :50051)\n────────────────────────\n• Native Tree-to-Code (0.301 μs)\n• CART Decision Tree (Depth ≤ 5)\n• Hierarchical 4-Tier Cutoff\n• 1ms Rule-Based Fallback",
            ha='center', va='center', fontsize=9, color='#0f172a')

    # 4. KAFKA BROKER & REDIS
    rect_kafka = patches.FancyBboxPatch((8, 12), 40, 38, boxstyle="round,pad=0.5",
                                        facecolor=c_kafka, edgecolor=c_kafka_b, linewidth=1.5)
    ax.add_patch(rect_kafka)
    ax.text(28, 45, "4. Message Broker (Apache Kafka)", ha='center', va='center', fontsize=11, fontweight='bold', color='#b91c1c')

    # 4 Topics sub-boxes
    topic_colors = [('#ef4444', 'tx.priority.critical (P0)'),
                    ('#f59e0b', 'tx.priority.high (P1)'),
                    ('#3b82f6', 'tx.priority.standard (P2)'),
                    ('#64748b', 'tx.priority.low (P3)')]
    for i, (tc, tname) in enumerate(topic_colors):
        y_pos = 36 - i * 6.5
        t_box = patches.FancyBboxPatch((11, y_pos - 2.2), 34, 4.8, boxstyle="round,pad=0.2",
                                       facecolor='#ffffff', edgecolor=tc, linewidth=1.2)
        ax.add_patch(t_box)
        ax.text(28, y_pos, tname, ha='center', va='center', fontsize=8.5, fontweight='bold', color=tc)

    # 5. CORE PROCESSOR (Tiered Concurrency)
    rect_proc = patches.FancyBboxPatch((55, 12), 42, 38, boxstyle="round,pad=0.5",
                                       facecolor=c_proc, edgecolor=c_proc_b, linewidth=1.5)
    ax.add_patch(rect_proc)
    ax.text(76, 45, "5. Core Processor (Tiered Concurrency)", ha='center', va='center', fontsize=11, fontweight='bold', color='#7e22ce')

    workers_info = [
        ('CRITICAL: 4 parallel workers (40% CPU)', '#b91c1c'),
        ('HIGH: 3 parallel workers (30% CPU)', '#b45309'),
        ('STANDARD: 2 parallel workers (20% CPU)', '#0369a1'),
        ('LOW: 1 background worker (10% CPU)', '#475569')
    ]
    for i, (winfo, wc) in enumerate(workers_info):
        y_pos = 36 - i * 6.5
        w_box = patches.FancyBboxPatch((58, y_pos - 2.2), 36, 4.8, boxstyle="round,pad=0.2",
                                       facecolor='#ffffff', edgecolor=wc, linewidth=1.2)
        ax.add_patch(w_box)
        ax.text(76, y_pos, winfo, ha='center', va='center', fontsize=8.5, fontweight='bold', color=wc)

    # 6. PERSISTENCE & TELEMETRY STRIP (Bottom)
    rect_db = patches.FancyBboxPatch((3, 1), 94, 7.5, boxstyle="round,pad=0.3",
                                     facecolor=c_db, edgecolor=c_db_b, linewidth=1.2)
    ax.add_patch(rect_db)
    ax.text(50, 4.8, "State & Persistence:  PostgreSQL 17 (Audit & Transactions)   •   Redis 7 (In-Memory Telemetry & Metrics Store)   •   Prometheus & Grafana",
            ha='center', va='center', fontsize=8.5, fontweight='bold', color='#334155')

    # ARROWS & CONNECTORS
    # Client -> Gateway
    ax.annotate("", xy=(32, 78), xytext=(25, 78),
                arrowprops=dict(arrowstyle="->", color="#0284c7", lw=2))
    ax.text(28.5, 80.5, "HTTP/REST", ha='center', fontsize=8, color="#0284c7", fontweight='bold')

    # Gateway <-> Inference (gRPC)
    ax.annotate("", xy=(66, 80), xytext=(58, 80),
                arrowprops=dict(arrowstyle="<->", color="#16a34a", lw=2))
    ax.text(62, 82.5, "gRPC\n(Protobuf)", ha='center', fontsize=8, color="#16a34a", fontweight='bold')

    # Gateway -> Kafka
    ax.annotate("", xy=(28, 50), xytext=(40, 62),
                arrowprops=dict(arrowstyle="->", color="#d97706", lw=2))
    ax.text(32, 56, "KafkaProducer\n(Partition Key)", ha='center', fontsize=7.5, color="#b45309", fontweight='bold')

    # Kafka -> Core Processor
    ax.annotate("", xy=(55, 30), xytext=(48, 30),
                arrowprops=dict(arrowstyle="->", color="#dc2626", lw=2.2))
    ax.text(51.5, 32.5, "QoS\nPoll", ha='center', fontsize=8, color="#dc2626", fontweight='bold')

    # Core Processor -> DB/Redis
    ax.annotate("", xy=(76, 8.5), xytext=(76, 12),
                arrowprops=dict(arrowstyle="->", color="#475569", lw=1.5))

    plt.tight_layout()
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(DASHBOARD_PATH), exist_ok=True)
    fig.savefig(OUTPUT_PATH, dpi=300, bbox_inches='tight')
    fig.savefig(DASHBOARD_PATH, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"Architecture diagram generated: {OUTPUT_PATH}")

if __name__ == '__main__':
    draw_architecture()
