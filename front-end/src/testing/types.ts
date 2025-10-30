export type TestStatus = 'pending' | 'running' | 'passed' | 'failed';

export interface TestResult {
  id: string;
  category: string;
  name: string;
  description: string;
  status: TestStatus;
  duration?: number;
  error?: string;
}

export interface TestReport {
  runId: string;
  timestamp: string;
  user?: string;
  summary: {
    total: number;
    passed: number;
    failed: number;
    duration: number;
  };
  results: TestResult[];
}

export interface Test {
  name: string;
  description: string;
  fn: () => Promise<void>;
}

export interface TestCategory {
  name: string;
  description: string;
  tests: Test[];
}
