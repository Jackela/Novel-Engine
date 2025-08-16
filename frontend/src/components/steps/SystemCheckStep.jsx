import React, { useState, useEffect, useCallback } from 'react';
import { useEnvironmentValidator } from '../../utils/EnvironmentValidator';
import { useHealthMonitor } from '../../utils/HealthMonitor';
import { usePortDetection } from '../../utils/PortDetector';
import './SystemCheckStep.css';

/**
 * SystemCheckStep Component
 * 
 * Comprehensive system validation with real-time monitoring
 * Features:
 * - Progressive validation stages
 * - Real-time health monitoring
 * - Interactive troubleshooting
 * - Performance optimization suggestions
 * - Accessibility compliant
 */
function SystemCheckStep({
  onValidationComplete,
  onValidationProgress,
  autoStart = true,
  showDetailedResults = true,
  theme = 'gradient',
  className = ''
}) {
  // Validation hooks
  const { validationData, validateEnvironment } = useEnvironmentValidator();
  const { healthData, startMonitoring, performHealthCheck } = useHealthMonitor();
  const { config: portConfig, detectConfig, isDetecting } = usePortDetection();

  // Component state
  const [currentStage, setCurrentStage] = useState(0);
  const [validationProgress, setValidationProgress] = useState(0);
  const [stageResults, setStageResults] = useState({});
  const [overallStatus, setOverallStatus] = useState('pending');
  const [isRetrying, setIsRetrying] = useState(false);
  const [showTroubleshooting, setShowTroubleshooting] = useState(false);

  // Validation stages
  const validationStages = [
    {
      id: 'browser',
      title: 'Browser Compatibility',
      description: 'Checking browser features and version compatibility',
      icon: '🌐',
      estimatedTime: 2000,
      weight: 25
    },
    {
      id: 'environment',
      title: 'System Environment',
      description: 'Validating system requirements and capabilities',
      icon: '💻',
      estimatedTime: 3000,
      weight: 30
    },
    {
      id: 'connectivity',
      title: 'Network & Backend',
      description: 'Testing backend connectivity and network performance',
      icon: '🔗',
      estimatedTime: 4000,
      weight: 25
    },
    {
      id: 'performance',
      title: 'Performance Assessment',
      description: 'Measuring system performance and optimization potential',
      icon: '⚡',
      estimatedTime: 3000,
      weight: 20
    }
  ];

  // Auto-start validation
  useEffect(() => {
    if (autoStart && currentStage === 0 && overallStatus === 'pending') {
      startValidation();
    }
  }, [autoStart, currentStage, overallStatus, startValidation]);

  // Update progress when stage changes
  useEffect(() => {
    if (currentStage > 0) {
      const completedWeight = validationStages
        .slice(0, currentStage)
        .reduce((total, stage) => total + stage.weight, 0);
      setValidationProgress(completedWeight);
      onValidationProgress?.(completedWeight);
    }
  }, [currentStage, onValidationProgress, validationStages]);

  /**
   * Start the validation process
   */
  const startValidation = useCallback(async () => {
    setOverallStatus('running');
    setCurrentStage(0);
    setValidationProgress(0);
    setStageResults({});

    try {
      // Stage 1: Browser Compatibility
      await runValidationStage(0, async () => {
        const envResult = await validateEnvironment();
        return {
          level: envResult.validation.browser.level,
          score: envResult.validation.browser.score,
          details: envResult.validation.browser,
          recommendations: envResult.validation.browser.issues || []
        };
      });

      // Stage 2: System Environment
      await runValidationStage(1, async () => {
        const envResult = validationData || await validateEnvironment();
        const systemValidation = {
          features: envResult.validation.features,
          performance: envResult.validation.performance,
          storage: envResult.validation.storage
        };

        const avgScore = Object.values(systemValidation)
          .reduce((sum, val) => sum + val.score, 0) / 3;

        return {
          level: avgScore >= 80 ? 'pass' : avgScore >= 60 ? 'warning' : 'fail',
          score: Math.round(avgScore),
          details: systemValidation,
          recommendations: []
        };
      });

      // Stage 3: Network & Backend Connectivity
      await runValidationStage(2, async () => {
        try {
          // Detect backend configuration
          if (!portConfig) {
            await detectConfig();
          }

          // Perform health check
          const healthResult = await performHealthCheck();
          
          return {
            level: healthResult.overall.level === 'critical' ? 'fail' :
                  healthResult.overall.level === 'warning' ? 'warning' : 'pass',
            score: healthResult.overall.score,
            details: {
              connectivity: healthResult.details.connectivity,
              backend: portConfig,
              health: healthResult.overall
            },
            recommendations: healthResult.recommendations || []
          };
        } catch (error) {
          return {
            level: 'fail',
            score: 0,
            details: { error: error.message },
            recommendations: [
              'Check that the StoryForge backend server is running',
              'Verify network connectivity',
              'Try refreshing the page'
            ]
          };
        }
      });

      // Stage 4: Performance Assessment
      await runValidationStage(3, async () => {
        const perfResult = await runPerformanceTests();
        return {
          level: perfResult.score >= 80 ? 'pass' : 
                perfResult.score >= 60 ? 'warning' : 'fail',
          score: perfResult.score,
          details: perfResult.details,
          recommendations: perfResult.recommendations
        };
      });

      // Complete validation
      completeValidation();

    } catch (error) {
      console.error('Validation failed:', error);
      setOverallStatus('error');
    }
  }, [validateEnvironment, validationData, portConfig, detectConfig, performHealthCheck, completeValidation, runPerformanceTests, runValidationStage]);

  /**
   * Run a specific validation stage
   */
  const runValidationStage = async (stageIndex, validationFunction) => {
    setCurrentStage(stageIndex);
    
    const stage = validationStages[stageIndex];
    const startTime = Date.now();

    try {
      // Simulate minimum time for better UX
      const [result] = await Promise.all([
        validationFunction(),
        new Promise(resolve => setTimeout(resolve, Math.min(stage.estimatedTime, 1500)))
      ]);

      const duration = Date.now() - startTime;
      
      setStageResults(prev => ({
        ...prev,
        [stage.id]: {
          ...result,
          duration,
          timestamp: new Date().toISOString()
        }
      }));

      setCurrentStage(stageIndex + 1);
      
    } catch (error) {
      console.error(`Stage ${stage.id} failed:`, error);
      
      setStageResults(prev => ({
        ...prev,
        [stage.id]: {
          level: 'fail',
          score: 0,
          details: { error: error.message },
          recommendations: ['An unexpected error occurred during validation'],
          duration: Date.now() - startTime,
          timestamp: new Date().toISOString()
        }
      }));

      setCurrentStage(stageIndex + 1);
    }
  };

  /**
   * Complete the validation process
   */
  const completeValidation = () => {
    const results = Object.values(stageResults);
    const avgScore = results.reduce((sum, result) => sum + result.score, 0) / results.length;
    const criticalFailures = results.filter(r => r.level === 'fail').length;
    const warnings = results.filter(r => r.level === 'warning').length;

    let status;
    if (criticalFailures > 0) {
      status = 'failed';
    } else if (warnings > 1) {
      status = 'warnings';
    } else {
      status = 'passed';
    }

    setOverallStatus(status);
    setValidationProgress(100);

    // Start health monitoring if validation passed
    if (status === 'passed') {
      startMonitoring(30000);
    }

    // Notify parent component
    onValidationComplete?.({
      status,
      score: Math.round(avgScore),
      results: stageResults,
      criticalFailures,
      warnings,
      timestamp: new Date().toISOString()
    });
  };

  /**
   * Run performance tests
   */
  const runPerformanceTests = async () => {
    const tests = {
      memoryUsage: testMemoryUsage(),
      renderPerformance: await testRenderPerformance(),
      networkLatency: await testNetworkLatency(),
      storageSpeed: await testStorageSpeed()
    };

    const scores = Object.values(tests);
    const avgScore = scores.reduce((sum, score) => sum + score, 0) / scores.length;

    const recommendations = [];
    if (tests.memoryUsage < 70) recommendations.push('Consider closing other browser tabs to free memory');
    if (tests.renderPerformance < 70) recommendations.push('Graphics performance may affect user experience');
    if (tests.networkLatency < 70) recommendations.push('Network latency may impact story generation speed');
    if (tests.storageSpeed < 70) recommendations.push('Storage performance may affect loading times');

    return {
      score: Math.round(avgScore),
      details: tests,
      recommendations
    };
  };

  /**
   * Performance test utilities
   */
  const testMemoryUsage = () => {
    if (performance.memory) {
      const used = performance.memory.usedJSHeapSize / 1024 / 1024; // MB
      const total = performance.memory.totalJSHeapSize / 1024 / 1024; // MB
      const usage = (used / total) * 100;
      return Math.max(0, 100 - usage);
    }
    return 75; // Default score
  };

  const testRenderPerformance = async () => {
    return new Promise(resolve => {
      const startTime = performance.now();
      
      // Create a complex DOM manipulation task
      const testElement = document.createElement('div');
      testElement.style.position = 'absolute';
      testElement.style.visibility = 'hidden';
      document.body.appendChild(testElement);

      for (let i = 0; i < 1000; i++) {
        const child = document.createElement('div');
        child.textContent = `Test ${i}`;
        testElement.appendChild(child);
      }

      requestAnimationFrame(() => {
        const endTime = performance.now();
        const duration = endTime - startTime;
        document.body.removeChild(testElement);
        
        // Score based on render time (lower is better)
        const score = Math.max(0, 100 - (duration / 10));
        resolve(Math.round(score));
      });
    });
  };

  const testNetworkLatency = async () => {
    try {
      const startTime = performance.now();
      const response = await fetch(window.location.origin, { 
        method: 'HEAD',
        cache: 'no-cache'
      });
      const endTime = performance.now();
      
      if (response.ok) {
        const latency = endTime - startTime;
        return Math.max(0, 100 - (latency / 20));
      }
      return 50;
    } catch (error) {
      return 30;
    }
  };

  const testStorageSpeed = async () => {
    try {
      const testData = 'x'.repeat(10000); // 10KB test data
      const startTime = performance.now();
      
      localStorage.setItem('storyforge_speed_test', testData);
      const data = localStorage.getItem('storyforge_speed_test');
      localStorage.removeItem('storyforge_speed_test');
      
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      return data === testData ? Math.max(0, 100 - duration) : 0;
    } catch (error) {
      return 50;
    }
  };

  /**
   * Retry validation
   */
  const retryValidation = async () => {
    setIsRetrying(true);
    await startValidation();
    setIsRetrying(false);
  };

  /**
   * Get status color for UI
   */
  const getStatusColor = (level) => {
    switch (level) {
      case 'pass': return '#28a745';
      case 'warning': return '#ffc107';
      case 'fail': return '#dc3545';
      default: return '#6c757d';
    }
  };

  /**
   * Get status icon for UI
   */
  const getStatusIcon = (level) => {
    switch (level) {
      case 'pass': return '✅';
      case 'warning': return '⚠️';
      case 'fail': return '❌';
      default: return '🔄';
    }
  };

  return (
    <div className={`system-check-step ${theme} ${className}`}>
      {/* Header */}
      <div className="check-header">
        <h2>System Validation</h2>
        <p>Ensuring optimal performance for your StoryForge AI experience</p>
      </div>

      {/* Progress Overview */}
      <div className="validation-progress">
        <div className="progress-header">
          <span className="progress-label">Validation Progress</span>
          <span className="progress-percentage">{validationProgress}%</span>
        </div>
        <div className="progress-bar">
          <div 
            className="progress-fill"
            style={{ 
              width: `${validationProgress}%`,
              backgroundColor: overallStatus === 'failed' ? '#dc3545' : 
                              overallStatus === 'warnings' ? '#ffc107' : '#28a745'
            }}
          />
        </div>
      </div>

      {/* Validation Stages */}
      <div className="validation-stages">
        {validationStages.map((stage, index) => {
          const result = stageResults[stage.id];
          const isActive = index === currentStage && overallStatus === 'running';
          const isCompleted = !!result;
          const isPending = index > currentStage;

          return (
            <div
              key={stage.id}
              className={`validation-stage ${
                isActive ? 'active' : 
                isCompleted ? 'completed' : 
                isPending ? 'pending' : ''
              }`}
            >
              <div className="stage-indicator">
                <div className="stage-icon">
                  {isActive ? (
                    <div className="loading-spinner" />
                  ) : isCompleted ? (
                    getStatusIcon(result.level)
                  ) : (
                    stage.icon
                  )}
                </div>
                {isCompleted && (
                  <div 
                    className="stage-score"
                    style={{ color: getStatusColor(result.level) }}
                  >
                    {result.score}%
                  </div>
                )}
              </div>

              <div className="stage-content">
                <h3>{stage.title}</h3>
                <p className="stage-description">{stage.description}</p>
                
                {isActive && (
                  <div className="stage-activity">
                    <div className="activity-dots">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                    <span>Checking...</span>
                  </div>
                )}

                {isCompleted && result.recommendations?.length > 0 && (
                  <div className="stage-recommendations">
                    <details>
                      <summary>View recommendations</summary>
                      <ul>
                        {result.recommendations.map((rec, i) => (
                          <li key={i}>{rec}</li>
                        ))}
                      </ul>
                    </details>
                  </div>
                )}
              </div>

              <div className="stage-status">
                {isCompleted && (
                  <span 
                    className={`status-badge ${result.level}`}
                    style={{ backgroundColor: getStatusColor(result.level) }}
                  >
                    {result.level.toUpperCase()}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Results Summary */}
      {overallStatus !== 'pending' && overallStatus !== 'running' && (
        <div className={`results-summary ${overallStatus}`}>
          <div className="summary-header">
            <div className="summary-icon">
              {overallStatus === 'passed' ? '🎉' :
               overallStatus === 'warnings' ? '⚠️' : '❌'}
            </div>
            <div className="summary-content">
              <h3>
                {overallStatus === 'passed' ? 'System Ready!' :
                 overallStatus === 'warnings' ? 'System Ready with Warnings' :
                 'System Issues Detected'}
              </h3>
              <p>
                {overallStatus === 'passed' ? 'Your system is optimally configured for StoryForge AI' :
                 overallStatus === 'warnings' ? 'Your system will work, but some features may be limited' :
                 'Some critical issues need to be addressed for optimal performance'}
              </p>
            </div>
          </div>

          {showDetailedResults && (
            <div className="detailed-results">
              <button
                onClick={() => setShowTroubleshooting(!showTroubleshooting)}
                className="toggle-details"
              >
                {showTroubleshooting ? 'Hide' : 'Show'} detailed results
              </button>

              {showTroubleshooting && (
                <div className="troubleshooting-section">
                  <h4>Detailed Validation Results</h4>
                  
                  {validationStages.map(stage => {
                    const result = stageResults[stage.id];
                    if (!result) return null;

                    return (
                      <div key={stage.id} className="result-detail">
                        <div className="detail-header">
                          <span className="detail-icon">{stage.icon}</span>
                          <span className="detail-title">{stage.title}</span>
                          <span className="detail-score">{result.score}%</span>
                        </div>
                        
                        {result.details && (
                          <div className="detail-content">
                            <pre>{JSON.stringify(result.details, null, 2)}</pre>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          <div className="summary-actions">
            {overallStatus === 'failed' && (
              <button
                onClick={retryValidation}
                className="btn-retry"
                disabled={isRetrying}
              >
                {isRetrying ? 'Retrying...' : 'Retry Validation'}
              </button>
            )}
            
            <button
              onClick={() => onValidationComplete?.({
                status: overallStatus,
                results: stageResults,
                canProceed: overallStatus !== 'failed'
              })}
              className="btn-continue"
              disabled={overallStatus === 'failed'}
            >
              {overallStatus === 'failed' ? 'Fix Issues First' : 'Continue Setup'}
            </button>
          </div>
        </div>
      )}

      {/* Manual Start */}
      {!autoStart && overallStatus === 'pending' && (
        <div className="manual-start">
          <button onClick={startValidation} className="btn-primary">
            Start System Check
          </button>
        </div>
      )}
    </div>
  );
}

export default SystemCheckStep;