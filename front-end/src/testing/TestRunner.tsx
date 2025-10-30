import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  Alert,
  IconButton,
  Collapse,
  Divider,
  Card,
  CardContent,
} from '@mui/material';
import {
  PlayArrow,
  Stop,
  CheckCircle,
  Error,
  Pending,
  ExpandMore,
  ExpandLess,
  Download,
  ContentCopy,
} from '@mui/icons-material';
import { TestExecutor } from './utils/testExecutor';
import { TestResult, TestReport, TestStatus } from './types';
import { allTests } from './tests';

const TestRunner: React.FC = () => {
  const [isRunning, setIsRunning] = useState(false);
  const [results, setResults] = useState<TestResult[]>([]);
  const [report, setReport] = useState<TestReport | null>(null);
  const [executor, setExecutor] = useState<TestExecutor | null>(null);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(['Authentication', 'Catalogs & Schemas']));

  const totalTests = allTests.reduce((sum, cat) => sum + cat.tests.length, 0);
  const completedTests = results.filter(r => r.status !== 'pending' && r.status !== 'running').length;
  const passedTests = results.filter(r => r.status === 'passed').length;
  const failedTests = results.filter(r => r.status === 'failed').length;

  const handleRunTests = () => {
    setIsRunning(true);
    setResults([]);
    setReport(null);

    const newExecutor = new TestExecutor(allTests, {
      onProgress: (result) => {
        setResults((prev) => [...prev, result]);
      },
      onComplete: (finalReport) => {
        setReport(finalReport);
        setIsRunning(false);
      },
    });

    setExecutor(newExecutor);
    newExecutor.runAll();
  };

  const handleStopTests = () => {
    if (executor) {
      executor.stop();
      setIsRunning(false);
    }
  };

  const toggleCategory = (category: string) => {
    setExpandedCategories((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(category)) {
        newSet.delete(category);
      } else {
        newSet.add(category);
      }
      return newSet;
    });
  };

  const getStatusIcon = (status: TestStatus) => {
    switch (status) {
      case 'passed':
        return <CheckCircle color="success" />;
      case 'failed':
        return <Error color="error" />;
      case 'running':
        return <Pending color="info" />;
      default:
        return <Pending color="disabled" />;
    }
  };

  const getStatusColor = (status: TestStatus) => {
    switch (status) {
      case 'passed':
        return 'success';
      case 'failed':
        return 'error';
      case 'running':
        return 'info';
      default:
        return 'default';
    }
  };

  const exportReport = () => {
    if (!report) return;

    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `test-report-${report.runId}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const copyResultsToClipboard = async () => {
    if (!report) return;

    try {
      const jsonString = JSON.stringify(report, null, 2);
      await navigator.clipboard.writeText(jsonString);
      alert('Test results copied to clipboard! Paste into Claude Code for analysis.');
    } catch (error) {
      console.error('Failed to copy to clipboard:', error);
      alert('Failed to copy to clipboard. Please try the Export button instead.');
    }
  };

  const groupedResults = allTests.map((category) => ({
    ...category,
    results: results.filter((r) => r.category === category.name),
  }));

  const progress = totalTests > 0 ? (completedTests / totalTests) * 100 : 0;

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: 'auto' }}>
      <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h4" component="h1">
            🧪 Metadata Manager - Test Runner
          </Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            {!isRunning ? (
              <Button
                variant="contained"
                color="primary"
                startIcon={<PlayArrow />}
                onClick={handleRunTests}
                disabled={isRunning}
              >
                Run All Tests
              </Button>
            ) : (
              <Button
                variant="contained"
                color="error"
                startIcon={<Stop />}
                onClick={handleStopTests}
              >
                Stop
              </Button>
            )}
            {report && (
              <>
                <Button
                  variant="outlined"
                  startIcon={<ContentCopy />}
                  onClick={copyResultsToClipboard}
                >
                  Copy Results
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<Download />}
                  onClick={exportReport}
                >
                  Export Report
                </Button>
              </>
            )}
          </Box>
        </Box>

        <Alert severity="info" sx={{ mb: 2 }}>
          <Typography variant="body2">
            <strong>Running inside Databricks SSO boundary</strong> - Tests authenticate against Neon PostgreSQL database
          </Typography>
        </Alert>

        {isRunning && (
          <Box sx={{ mt: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <Typography variant="body2" sx={{ flexGrow: 1 }}>
                Running tests... ({completedTests}/{totalTests})
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {progress.toFixed(0)}%
              </Typography>
            </Box>
            <LinearProgress variant="determinate" value={progress} />
          </Box>
        )}

        {report && (
          <Alert
            severity={report.summary.failed === 0 ? 'success' : 'warning'}
            sx={{ mt: 2 }}
          >
            <Typography variant="body2">
              <strong>Test Run Complete!</strong> {report.summary.passed}/{report.summary.total} tests passed
              in {(report.summary.duration / 1000).toFixed(2)}s
            </Typography>
          </Alert>
        )}
      </Paper>

      {/* Summary Cards */}
      {results.length > 0 && (
        <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 2, mb: 3 }}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Total Tests
              </Typography>
              <Typography variant="h4">{totalTests}</Typography>
            </CardContent>
          </Card>
          <Card>
            <CardContent>
              <Typography color="success.main" gutterBottom>
                Passed
              </Typography>
              <Typography variant="h4" color="success.main">
                {passedTests}
              </Typography>
            </CardContent>
          </Card>
          <Card>
            <CardContent>
              <Typography color="error.main" gutterBottom>
                Failed
              </Typography>
              <Typography variant="h4" color="error.main">
                {failedTests}
              </Typography>
            </CardContent>
          </Card>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Completion
              </Typography>
              <Typography variant="h4">{progress.toFixed(0)}%</Typography>
            </CardContent>
          </Card>
        </Box>
      )}

      {/* Test Results by Category */}
      {groupedResults.map((category) => {
        const categoryPassed = category.results.filter(r => r.status === 'passed').length;
        const categoryFailed = category.results.filter(r => r.status === 'failed').length;
        const categoryTotal = category.tests.length;
        const isExpanded = expandedCategories.has(category.name);

        return (
          <Paper key={category.name} elevation={2} sx={{ mb: 2 }}>
            <Box
              sx={{
                p: 2,
                display: 'flex',
                alignItems: 'center',
                cursor: 'pointer',
                '&:hover': { bgcolor: 'action.hover' },
              }}
              onClick={() => toggleCategory(category.name)}
            >
              <Typography variant="h6" sx={{ flexGrow: 1 }}>
                {category.name}
              </Typography>
              <Chip
                label={`${categoryPassed}/${categoryTotal}`}
                color={categoryFailed > 0 ? 'error' : 'success'}
                size="small"
                sx={{ mr: 1 }}
              />
              <IconButton size="small">
                {isExpanded ? <ExpandLess /> : <ExpandMore />}
              </IconButton>
            </Box>

            <Collapse in={isExpanded}>
              <Divider />
              <List dense>
                {category.results.map((result) => (
                  <React.Fragment key={result.id}>
                    <ListItem>
                      <ListItemIcon>{getStatusIcon(result.status)}</ListItemIcon>
                      <ListItemText
                        primary={result.name}
                        secondary={
                          <>
                            {result.description}
                            {result.duration && ` • ${result.duration}ms`}
                            {result.error && (
                              <Typography
                                component="div"
                                variant="caption"
                                color="error"
                                sx={{ mt: 0.5, fontFamily: 'monospace' }}
                              >
                                {result.error}
                              </Typography>
                            )}
                          </>
                        }
                      />
                      <Chip
                        label={result.status}
                        color={getStatusColor(result.status)}
                        size="small"
                      />
                    </ListItem>
                    <Divider />
                  </React.Fragment>
                ))}
              </List>
            </Collapse>
          </Paper>
        );
      })}

      {results.length === 0 && !isRunning && (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No tests run yet
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Click "Run All Tests" to start testing database authentication
          </Typography>
        </Paper>
      )}
    </Box>
  );
};

export default TestRunner;
