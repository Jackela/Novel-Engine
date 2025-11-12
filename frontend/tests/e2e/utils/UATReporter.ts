/**
 * UAT Reporter for Emergent Narrative Dashboard
 * 
 * Generates comprehensive User Acceptance Test reports with:
 * - Test execution summaries
 * - Performance metrics
 * - Compliance validation
 * - Visual evidence
 * - Recommendations
 */

import * as fs from 'fs';
import * as path from 'path';

export interface UATTestResult {
  testName: string;
  status: 'passed' | 'failed' | 'skipped';
  duration: number;
  phases: UATPhaseResult[];
  errors?: string[];
  screenshots: string[];
  metrics: Record<string, number>;
}

export interface UATPhaseResult {
  phase: string;
  status: 'passed' | 'failed' | 'skipped';
  duration: number;
  details: string;
  validations: UATValidation[];
}

export interface UATValidation {
  type: 'component' | 'layout' | 'performance' | 'api' | 'accessibility';
  name: string;
  status: 'passed' | 'failed' | 'warning';
  expected: any;
  actual: any;
  message?: string;
}

export interface UATEnvironmentInfo {
  browser: string;
  viewport: { width: number; height: number };
  userAgent: string;
  timestamp: string;
  testDuration: number;
  baseURL: string;
}

export interface UATSummary {
  totalTests: number;
  passedTests: number;
  failedTests: number;
  skippedTests: number;
  totalDuration: number;
  averageTestDuration: number;
  overallStatus: 'passed' | 'failed' | 'partial';
}

/**
 * Main UAT Reporter Class
 */
export class UATReporter {
  private results: UATTestResult[] = [];
  private environment: UATEnvironmentInfo | null = null;
  private startTime: number = Date.now();
  
  /**
   * Set environment information for the test run
   */
  setEnvironment(env: UATEnvironmentInfo): void {
    this.environment = env;
  }
  
  /**
   * Add test result to the report
   */
  addTestResult(result: UATTestResult): void {
    this.results.push(result);
  }
  
  /**
   * Generate summary statistics
   */
  generateSummary(): UATSummary {
    const totalTests = this.results.length;
    const passedTests = this.results.filter(r => r.status === 'passed').length;
    const failedTests = this.results.filter(r => r.status === 'failed').length;
    const skippedTests = this.results.filter(r => r.status === 'skipped').length;
    const totalDuration = Date.now() - this.startTime;
    const averageTestDuration = totalTests > 0 
      ? this.results.reduce((sum, r) => sum + r.duration, 0) / totalTests 
      : 0;
    
    let overallStatus: UATSummary['overallStatus'] = 'passed';
    if (failedTests > 0) {
      overallStatus = passedTests > 0 ? 'partial' : 'failed';
    }
    
    return {
      totalTests,
      passedTests,
      failedTests,
      skippedTests,
      totalDuration,
      averageTestDuration,
      overallStatus
    };
  }
  
  /**
   * Generate comprehensive HTML report
   */
  generateHTMLReport(): string {
    const summary = this.generateSummary();
    const timestamp = new Date().toISOString();
    
    return `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Emergent Narrative Dashboard - UAT Report</title>
    <style>
        ${this.getReportStyles()}
    </style>
</head>
<body>
    <header class="report-header">
        <h1>🎯 Emergent Narrative Dashboard - User Acceptance Test Report</h1>
        <div class="report-meta">
            <span class="timestamp">Generated: ${new Date(timestamp).toLocaleString()}</span>
            <span class="status status-${summary.overallStatus}">${summary.overallStatus.toUpperCase()}</span>
        </div>
    </header>

    <section class="executive-summary">
        <h2>📊 Executive Summary</h2>
        <div class="summary-grid">
            <div class="summary-card">
                <h3>Test Execution</h3>
                <div class="metric-large">${summary.totalTests}</div>
                <div class="metric-label">Total Tests</div>
            </div>
            <div class="summary-card success">
                <h3>Passed</h3>
                <div class="metric-large">${summary.passedTests}</div>
                <div class="metric-label">${((summary.passedTests / summary.totalTests) * 100).toFixed(1)}%</div>
            </div>
            <div class="summary-card ${summary.failedTests > 0 ? 'failure' : ''}">
                <h3>Failed</h3>
                <div class="metric-large">${summary.failedTests}</div>
                <div class="metric-label">${((summary.failedTests / summary.totalTests) * 100).toFixed(1)}%</div>
            </div>
            <div class="summary-card">
                <h3>Duration</h3>
                <div class="metric-large">${(summary.totalDuration / 1000).toFixed(1)}s</div>
                <div class="metric-label">Total Time</div>
            </div>
        </div>
    </section>

    <section class="environment-info">
        <h2>🖥️ Test Environment</h2>
        ${this.generateEnvironmentHTML()}
    </section>

    <section class="test-results">
        <h2>🧪 Test Results Detail</h2>
        ${this.generateTestResultsHTML()}
    </section>

    <section class="validation-summary">
        <h2>✅ Validation Summary</h2>
        ${this.generateValidationSummaryHTML()}
    </section>

    <section class="performance-metrics">
        <h2>⚡ Performance Metrics</h2>
        ${this.generatePerformanceMetricsHTML()}
    </section>

    <section class="recommendations">
        <h2>💡 Recommendations</h2>
        ${this.generateRecommendationsHTML(summary)}
    </section>

    <footer class="report-footer">
        <p>Generated by Emergent Narrative Dashboard UAT Suite</p>
        <p>Report ID: uat-${Date.now()}</p>
    </footer>
</body>
</html>`;
  }
  
  /**
   * Generate environment information HTML
   */
  private generateEnvironmentHTML(): string {
    if (!this.environment) return '<p>Environment information not available</p>';
    
    return `
    <div class="env-grid">
        <div class="env-item">
            <strong>Browser:</strong> ${this.environment.browser}
        </div>
        <div class="env-item">
            <strong>Viewport:</strong> ${this.environment.viewport.width}x${this.environment.viewport.height}
        </div>
        <div class="env-item">
            <strong>Base URL:</strong> ${this.environment.baseURL}
        </div>
        <div class="env-item">
            <strong>Test Duration:</strong> ${(this.environment.testDuration / 1000).toFixed(1)}s
        </div>
    </div>`;
  }
  
  /**
   * Generate test results HTML
   */
  private generateTestResultsHTML(): string {
    return this.results.map(result => `
    <div class="test-result ${result.status}">
        <div class="test-header">
            <h3>${result.testName}</h3>
            <span class="test-status status-${result.status}">${result.status}</span>
            <span class="test-duration">${(result.duration / 1000).toFixed(1)}s</span>
        </div>
        
        <div class="test-phases">
            <h4>Test Phases</h4>
            ${result.phases.map(phase => `
            <div class="phase ${phase.status}">
                <strong>${phase.phase}</strong> 
                <span class="phase-status">${phase.status}</span>
                <span class="phase-duration">(${(phase.duration / 1000).toFixed(1)}s)</span>
                <p>${phase.details}</p>
                ${phase.validations.length > 0 ? `
                <div class="validations">
                    ${phase.validations.map(v => `
                    <div class="validation ${v.status}">
                        <span class="validation-type">[${v.type}]</span>
                        <span class="validation-name">${v.name}</span>
                        <span class="validation-status">${v.status}</span>
                        ${v.message ? `<p class="validation-message">${v.message}</p>` : ''}
                    </div>`).join('')}
                </div>` : ''}
            </div>`).join('')}
        </div>
        
        ${result.errors && result.errors.length > 0 ? `
        <div class="test-errors">
            <h4>Errors</h4>
            ${result.errors.map(error => `<div class="error">${error}</div>`).join('')}
        </div>` : ''}
        
        ${result.screenshots.length > 0 ? `
        <div class="test-screenshots">
            <h4>Screenshots</h4>
            ${result.screenshots.map(screenshot => `
            <div class="screenshot">
                <img src="${screenshot}" alt="Test Screenshot" style="max-width: 300px; margin: 5px;">
            </div>`).join('')}
        </div>` : ''}
    </div>`).join('');
  }
  
  /**
   * Generate validation summary HTML
   */
  private generateValidationSummaryHTML(): string {
    const allValidations = this.results.flatMap(r => r.phases.flatMap(p => p.validations));
    const byType = allValidations.reduce((acc, v) => {
      acc[v.type] = acc[v.type] || { passed: 0, failed: 0, warning: 0 };
      acc[v.type][v.status]++;
      return acc;
    }, {} as Record<string, Record<string, number>>);
    
    return `
    <div class="validation-grid">
        ${Object.entries(byType).map(([type, counts]) => `
        <div class="validation-type-summary">
            <h4>${type.charAt(0).toUpperCase() + type.slice(1)} Validations</h4>
            <div class="validation-counts">
                <span class="count success">✅ ${counts.passed || 0}</span>
                <span class="count warning">⚠️ ${counts.warning || 0}</span>
                <span class="count failure">❌ ${counts.failed || 0}</span>
            </div>
        </div>`).join('')}
    </div>`;
  }
  
  /**
   * Generate performance metrics HTML
   */
  private generatePerformanceMetricsHTML(): string {
    const allMetrics = this.results.reduce((acc, r) => {
      Object.entries(r.metrics).forEach(([key, value]) => {
        acc[key] = acc[key] || [];
        acc[key].push(value);
      });
      return acc;
    }, {} as Record<string, number[]>);
    
    return `
    <div class="performance-grid">
        ${Object.entries(allMetrics).map(([metric, values]) => {
          const avg = values.reduce((a, b) => a + b, 0) / values.length;
          const min = Math.min(...values);
          const max = Math.max(...values);
          
          return `
          <div class="performance-metric">
              <h4>${metric}</h4>
              <div class="metric-stats">
                  <div>Avg: ${avg.toFixed(1)}ms</div>
                  <div>Min: ${min.toFixed(1)}ms</div>
                  <div>Max: ${max.toFixed(1)}ms</div>
              </div>
          </div>`;
        }).join('')}
    </div>`;
  }
  
  /**
   * Generate recommendations HTML
   */
  private generateRecommendationsHTML(summary: UATSummary): string {
    const recommendations: string[] = [];
    
    if (summary.failedTests > 0) {
      recommendations.push('🔧 Address failed test cases to improve system reliability');
    }
    
    if (summary.averageTestDuration > 30000) {
      recommendations.push('⚡ Optimize performance - average test duration exceeds 30 seconds');
    }
    
    const componentValidations = this.results
      .flatMap(r => r.phases.flatMap(p => p.validations))
      .filter(v => v.type === 'component' && v.status === 'failed');
    
    if (componentValidations.length > 0) {
      recommendations.push('🎨 Review UI component implementations for compliance');
    }
    
    if (summary.passedTests === summary.totalTests) {
      recommendations.push('✨ All tests passed! Consider expanding test coverage for edge cases');
    }
    
    return recommendations.length > 0 
      ? `<ul>${recommendations.map(r => `<li>${r}</li>`).join('')}</ul>`
      : '<p>✅ No specific recommendations - system performing well!</p>';
  }
  
  /**
   * Get CSS styles for the report
   */
  private getReportStyles(): string {
    return `
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .report-header { background: white; padding: 30px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .report-header h1 { margin: 0 0 10px 0; color: #2c3e50; }
        .report-meta { display: flex; justify-content: space-between; align-items: center; }
        .timestamp { color: #666; }
        .status { padding: 4px 12px; border-radius: 4px; font-weight: bold; }
        .status-passed { background: #d4edda; color: #155724; }
        .status-failed { background: #f8d7da; color: #721c24; }
        .status-partial { background: #fff3cd; color: #856404; }
        
        section { background: white; margin: 20px 0; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h2 { margin: 0 0 20px 0; color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        
        .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
        .summary-card { text-align: center; padding: 20px; border-radius: 6px; border: 1px solid #ddd; }
        .summary-card.success { border-color: #28a745; background: #f8fff9; }
        .summary-card.failure { border-color: #dc3545; background: #fff8f8; }
        .metric-large { font-size: 2.5em; font-weight: bold; margin: 10px 0; }
        .metric-label { color: #666; }
        
        .env-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; }
        .env-item { padding: 10px; background: #f8f9fa; border-radius: 4px; }
        
        .test-result { border: 1px solid #ddd; border-radius: 6px; margin: 15px 0; }
        .test-result.passed { border-left: 4px solid #28a745; }
        .test-result.failed { border-left: 4px solid #dc3545; }
        .test-header { display: flex; justify-content: space-between; align-items: center; padding: 15px; background: #f8f9fa; }
        
        .test-phases { padding: 15px; }
        .phase { margin: 10px 0; padding: 10px; border-radius: 4px; }
        .phase.passed { background: #f8fff9; border-left: 3px solid #28a745; }
        .phase.failed { background: #fff8f8; border-left: 3px solid #dc3545; }
        
        .validation { display: flex; align-items: center; gap: 10px; padding: 5px; }
        .validation.passed { color: #28a745; }
        .validation.failed { color: #dc3545; }
        .validation.warning { color: #ffc107; }
        
        .performance-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
        .performance-metric { padding: 15px; border: 1px solid #ddd; border-radius: 6px; }
        
        .report-footer { text-align: center; padding: 20px; color: #666; }
    `;
  }
  
  /**
   * Save report to file
   */
  async saveReport(filePath: string): Promise<void> {
    const htmlContent = this.generateHTMLReport();
    const dir = path.dirname(filePath);
    
    // Ensure directory exists
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    
    fs.writeFileSync(filePath, htmlContent, 'utf8');
    console.log(`📊 UAT Report saved to: ${filePath}`);
  }
  
  /**
   * Save JSON summary for programmatic access
   */
  async saveJSONReport(filePath: string): Promise<void> {
    const jsonReport = {
      summary: this.generateSummary(),
      environment: this.environment,
      results: this.results,
      generatedAt: new Date().toISOString()
    };
    
    const dir = path.dirname(filePath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    
    fs.writeFileSync(filePath, JSON.stringify(jsonReport, null, 2), 'utf8');
    console.log(`📊 JSON Report saved to: ${filePath}`);
  }
}