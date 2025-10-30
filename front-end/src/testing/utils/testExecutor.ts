// Test execution engine

import { TestResult, TestCategory, TestStatus, TestReport } from '../types';
import api from '../../services/api';

export class TestExecutor {
  private results: TestResult[] = [];
  private onProgress?: (result: TestResult) => void;
  private onComplete?: (report: TestReport) => void;
  private startTime: number = 0;
  private shouldStop: boolean = false;
  private runId: string = '';

  constructor(
    private categories: TestCategory[],
    callbacks?: {
      onProgress?: (result: TestResult) => void;
      onComplete?: (report: TestReport) => void;
    }
  ) {
    this.onProgress = callbacks?.onProgress;
    this.onComplete = callbacks?.onComplete;
  }

  async runAll(): Promise<TestReport> {
    this.results = [];
    this.shouldStop = false;
    this.startTime = Date.now();
    this.runId = `test-run-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

    // Create initial test run record in database (TEMPORARILY DISABLED)
    // try {
    //   await api.post('/test-runs', {
    //     run_id: this.runId,
    //     status: 'running',
    //     total_tests: this.categories.reduce((sum, cat) => sum + cat.tests.length, 0),
    //     passed_tests: 0,
    //     failed_tests: 0,
    //     duration_ms: 0,
    //     results: [],
    //     summary: {},
    //     browser_info: navigator.userAgent,
    //     app_url: window.location.origin,
    //     });
    // } catch (error) {
    //   console.warn('Failed to create test run record:', error);
    // }

    for (const category of this.categories) {
      if (this.shouldStop) break;

      for (const test of category.tests) {
        if (this.shouldStop) break;

        const result = await this.runTest(category.name, test.name, test.description, test.fn);
        this.results.push(result);

        if (this.onProgress) {
          this.onProgress(result);
        }
      }
    }

    const report = this.generateReport();

    // Save final results to database (TEMPORARILY DISABLED)
    // try {
    //   await api.put(`/test-runs/${this.runId}`, {
    //     status: 'completed',
    //     passed_tests: report.summary.passed,
    //     failed_tests: report.summary.failed,
    //     duration_ms: report.summary.duration,
    //     results: this.results.map(r => ({
    //       id: r.id,
    //       name: r.name,
    //       description: r.description,
    //       category: r.category,
    //       status: r.status,
    //       duration: r.duration,
    //       error: r.error,
    //     })),
    //     summary: report.summary,
    //     completed_at: new Date().toISOString(),
    //   });
    // } catch (error) {
    //   console.warn('Failed to save test run results:', error);
    // }

    if (this.onComplete) {
      this.onComplete(report);
    }

    return report;
  }

  async runTest(
    category: string,
    name: string,
    description: string,
    testFn: () => Promise<void>
  ): Promise<TestResult> {
    const testId = `${category}-${name}`.toLowerCase().replace(/\s+/g, '-');
    const testStartTime = Date.now();

    const result: TestResult = {
      id: testId,
      category,
      name,
      description,
      status: 'running',
    };

    try {
      await testFn();
      result.status = 'passed';
      result.duration = Date.now() - testStartTime;
    } catch (error: any) {
      result.status = 'failed';
      result.duration = Date.now() - testStartTime;
      result.error = error.message || String(error);
      result.details = error.stack;
    }

    return result;
  }

  stop(): void {
    this.shouldStop = true;
  }

  private generateReport(): TestReport {
    const totalDuration = Date.now() - this.startTime;
    const passed = this.results.filter(r => r.status === 'passed').length;
    const failed = this.results.filter(r => r.status === 'failed').length;
    const skipped = this.results.filter(r => r.status === 'skipped').length;

    return {
      runId: this.runId || `test-run-${Date.now()}`,
      timestamp: new Date().toISOString(),
      environment: window.location.hostname.includes('databricks') ? 'databricks_production' : 'development',
      user: 'current_user', // Will be replaced with actual user
      summary: {
        total: this.results.length,
        passed,
        failed,
        skipped,
        duration: totalDuration,
      },
      results: this.results,
    };
  }

  getResults(): TestResult[] {
    return this.results;
  }
}
