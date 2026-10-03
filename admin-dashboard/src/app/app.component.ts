import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { switchMap, map } from 'rxjs';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { BadgeModule } from 'primeng/badge';
import { Select } from 'primeng/select';

export interface QosModeResponse {
  mode: string;
  status?: string;
}

export interface TransactionSample {
  id: string;
  priority: string;
  score: number;
  reason: string;
  status: string;
  decisionLatencyUs: number;
}

export interface TestBurstResponse {
  modeUsed: string;
  totalTransactions: number;
  durationSeconds?: number;
  throughputRps?: number;
  avgDecisionLatencyUs: number;
  p50LatencyUs?: number;
  p95LatencyUs?: number;
  p99LatencyUs?: number;
  priorityDistribution: { [key: string]: number };
  sampleResults: TransactionSample[];
}

export interface ComparisonBenchmark {
  batchSize: number;
  fifo: TestBurstResponse;
  static: TestBurstResponse;
  adaptive: TestBurstResponse;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ButtonModule,
    CardModule,
    TableModule,
    TagModule,
    BadgeModule,
    Select
  ],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss'
})
export class AppComponent implements OnInit {
  title = 'Adaptive QoS System Admin Panel';
  gatewayUrl = 'http://localhost:8080';

  currentMode = 'adaptive';
  connectionStatus: 'ONLINE' | 'OFFLINE' | 'CHECKING' = 'CHECKING';
  loadingMode = false;
  runningTest = false;
  runningComparison = false;

  // Test parameters - default to 50
  testCount = 50;
  testType = 'MIXED';

  countOptions = [
    { label: '50 Transactions (Quick Test)', value: 50 },
    { label: '500 Transactions (Small Burst)', value: 500 },
    { label: '1,000 Transactions (1k Load Test)', value: 1000 },
    { label: '5,000 Transactions (5k Stress Load)', value: 5000 },
    { label: '10,000 Transactions (10k High-Load)', value: 10000 },
    { label: '50,000 Transactions (50k Production Scale)', value: 50000 },
    { label: '100,000 Transactions (100k Ultra High-Load)', value: 100000 }
  ];

  typeOptions = [
    { label: 'MIXED (Realistic Multi-Workload)', value: 'MIXED' },
    { label: 'PAYMENT Only (High Value)', value: 'PAYMENT' },
    { label: 'REFUND Only', value: 'REFUND' },
    { label: 'BALANCE_UPDATE Only', value: 'BALANCE_UPDATE' },
    { label: 'HEALTH_CHECK Only', value: 'HEALTH_CHECK' }
  ];

  // Thesis charts gallery
  activeChart = 'p99';
  chartsList = [
    { id: 'p99', title: 'P99 Tail Latency Scaling (1k – 100k)', file: 'charts/chart_p99_latency_scaling.png', figure: 'Рисунок 4.1', desc: 'Деградація P99 затримки у FIFO (>912 мс при 100k) проти стійкої полиці 44.1 мс у запропонованій системі Adaptive ML (-95.2% хвостової затримки)' },
    { id: 'throughput', title: 'System Throughput (RPS)', file: 'charts/chart_throughput_scaling.png', figure: 'Рисунок 4.2', desc: 'Ефективна пропускна здатність комплексу досягає 3,100 RPS (+142% приросту відносно класичної черги FIFO)' },
    { id: 'drain', title: 'Total Queue Drainage Time', file: 'charts/chart_total_drainage_time.png', figure: 'Рисунок 4.3', desc: 'Прискорення розвантаження черги зі 100,000 транзакцій у 2.4 рази (32.2 с проти 78.1 с) завдяки диференційованій конкурентності консюмерів' },
    { id: 'inference', title: 'Tree-to-Code vs Scikit-Learn Microbenchmark', file: 'charts/chart_inference_microbenchmark.png', figure: 'Рисунок 4.4', desc: 'Прискорення ML-інференсу Tree-to-Code (0.301 мкс) у 28 000 разів відносно Scikit-Learn predict() (8,510 мкс) на 100,000 ітерацій' }
  ];

  get selectedChart() {
    return this.chartsList.find(c => c.id === this.activeChart) || this.chartsList[0];
  }

  // Test results
  testResult: TestBurstResponse | null = null;
  comparisonResult: ComparisonBenchmark | null = null;
  errorMessage = '';

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.checkHealthAndFetchMode();
  }

  checkHealthAndFetchMode(): void {
    this.connectionStatus = 'CHECKING';
    this.http.get<{ mode: string }>(`${this.gatewayUrl}/api/v1/qos/mode`).subscribe({
      next: (res) => {
        this.currentMode = res.mode;
        this.connectionStatus = 'ONLINE';
        this.errorMessage = '';
      },
      error: () => {
        this.connectionStatus = 'OFFLINE';
        this.errorMessage = 'Could not connect to Gateway Service at ' + this.gatewayUrl;
      }
    });
  }

  setQosMode(mode: string): void {
    this.loadingMode = true;
    this.http.post<QosModeResponse>(`${this.gatewayUrl}/api/v1/qos/mode`, { mode }).subscribe({
      next: (res) => {
        this.currentMode = res.mode;
        this.loadingMode = false;
        this.errorMessage = '';
      },
      error: (err) => {
        this.loadingMode = false;
        this.errorMessage = 'Failed to update QoS mode: ' + (err.message || 'Network error');
      }
    });
  }

  runTestBurst(): void {
    this.runningTest = true;
    this.errorMessage = '';
    const body = {
      count: this.testCount,
      type: this.testType
    };

    this.http.post<TestBurstResponse>(`${this.gatewayUrl}/api/v1/qos/test-burst`, body).subscribe({
      next: (res) => {
        this.testResult = res;
        this.runningTest = false;
      },
      error: (err) => {
        this.runningTest = false;
        this.errorMessage = 'Failed to execute test burst: ' + (err.message || 'Network error');
      }
    });
  }

  runComparativeBenchmark(): void {
    this.runningComparison = true;
    this.errorMessage = '';
    const count = this.testCount;
    const type = this.testType;

    // Step 1: Run FIFO
    this.http.post<QosModeResponse>(`${this.gatewayUrl}/api/v1/qos/mode`, { mode: 'fifo' }).pipe(
      switchMap(() => this.http.post<TestBurstResponse>(`${this.gatewayUrl}/api/v1/qos/test-burst`, { count, type })),
      switchMap((fifoRes) => {
        // Step 2: Run STATIC
        return this.http.post<QosModeResponse>(`${this.gatewayUrl}/api/v1/qos/mode`, { mode: 'static' }).pipe(
          switchMap(() => this.http.post<TestBurstResponse>(`${this.gatewayUrl}/api/v1/qos/test-burst`, { count, type })),
          switchMap((staticRes) => {
            // Step 3: Run ADAPTIVE
            return this.http.post<QosModeResponse>(`${this.gatewayUrl}/api/v1/qos/mode`, { mode: 'adaptive' }).pipe(
              switchMap(() => this.http.post<TestBurstResponse>(`${this.gatewayUrl}/api/v1/qos/test-burst`, { count, type })),
              map((adaptiveRes) => ({ fifoRes, staticRes, adaptiveRes }))
            );
          })
        );
      })
    ).subscribe({
      next: ({ fifoRes, staticRes, adaptiveRes }) => {
        this.comparisonResult = {
          batchSize: count,
          fifo: fifoRes,
          static: staticRes,
          adaptive: adaptiveRes
        };
        this.currentMode = 'adaptive';
        this.runningComparison = false;
      },
      error: (err) => {
        this.runningComparison = false;
        this.errorMessage = 'Comparative benchmark failed: ' + (err.message || 'Network error');
      }
    });
  }

  getPercent(count: number | undefined, total: number): number {
    if (!count || !total) return 0;
    return Math.round((count / total) * 100);
  }

  getPrioritySeverity(priority: string): 'danger' | 'warn' | 'info' | 'secondary' {
    switch (priority.toUpperCase()) {
      case 'CRITICAL': return 'danger';
      case 'HIGH': return 'warn';
      case 'STANDARD': return 'info';
      case 'LOW':
      default: return 'secondary';
    }
  }
}
