import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';

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
  avgDecisionLatencyUs: number;
  priorityDistribution: { [key: string]: number };
  sampleResults: TransactionSample[];
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss'
})
export class AppComponent implements OnInit {
  title = 'Adaptive QoS System Admin Dashboard';
  gatewayUrl = 'http://localhost:8080';

  currentMode = 'adaptive';
  connectionStatus: 'ONLINE' | 'OFFLINE' | 'CHECKING' = 'CHECKING';
  loadingMode = false;
  runningTest = false;

  // Test parameters
  testCount = 20;
  testType = 'MIXED';

  // Test results
  testResult: TestBurstResponse | null = null;
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
      error: (err) => {
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

  getPriorityClass(priority: string): string {
    switch (priority.toUpperCase()) {
      case 'CRITICAL': return 'badge-critical';
      case 'HIGH': return 'badge-high';
      case 'STANDARD': return 'badge-standard';
      case 'LOW': return 'badge-low';
      default: return 'badge-secondary';
    }
  }
}
