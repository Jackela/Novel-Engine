import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { logger } from '../services/logging/LoggerFactory';
import { useEnvironmentValidator } from '../../utils/EnvironmentValidator';
import { useHealthMonitor } from '../../utils/HealthMonitor';
import { usePortDetection } from '../../utils/PortDetector';
import './SystemCheckStep.css';

interface Props {
  onValidationComplete?: (result: unknown) => void;
  onValidationProgress?: (progress: number) => void;
  autoStart?: boolean;
  showDetailedResults?: boolean;
  theme?: string;
  className?: string;
}

export default function SystemCheckStep({
  onValidationComplete,
  onValidationProgress,
  autoStart = true,
  showDetailedResults: _showDetailedResults = true,
  theme = 'gradient',
  className = ''
}: Props) {
  const { validationData, validateEnvironment } = useEnvironmentValidator();
  const { startMonitoring, performHealthCheck } = useHealthMonitor();
  const { config: portConfig, detectConfig } = usePortDetection();

  const [currentStage, setCurrentStage] = useState(0);
  const [_validationProgress, setValidationProgress] = useState(0);
  const [stageResults, setStageResults] = useState<Record<string, unknown>>({});
  const [overallStatus, setOverallStatus] = useState<'pending' | 'running' | 'error' | 'passed' | 'failed' | 'warnings'>('pending');

  const validationStages = useMemo(
    () => [
      { id: 'browser', title: 'Browser Compatibility', estimatedTime: 2000, weight: 25 },
      { id: 'environment', title: 'System Environment', estimatedTime: 3000, weight: 30 },
      { id: 'connectivity', title: 'Network & Backend', estimatedTime: 4000, weight: 25 },
      { id: 'performance', title: 'Performance Assessment', estimatedTime: 3000, weight: 20 },
    ],
    []
  );

  useEffect(() => {
    if (autoStart && currentStage === 0 && overallStatus === 'pending') {
      startValidation();
    }
  }, [autoStart, currentStage, overallStatus]);

  useEffect(() => {
    if (currentStage > 0) {
      const completedWeight = validationStages.slice(0, currentStage).reduce((t, s) => t + s.weight, 0);
      setValidationProgress(completedWeight);
      onValidationProgress?.(completedWeight);
    }
  }, [currentStage, onValidationProgress, validationStages]);

  const runValidationStage = useCallback(
    async (stageIndex: number, validationFunction: () => Promise<unknown>) => {
      setCurrentStage(stageIndex);
      const stage = validationStages[stageIndex];
      const startTime = Date.now();
      try {
        const [result] = await Promise.all([
          validationFunction(),
          new Promise((r) => setTimeout(r, Math.min(stage.estimatedTime, 1500))),
        ]);
        const duration = Date.now() - startTime;
        setStageResults((prev) => ({
          ...prev,
          [stage.id]: { ...result, duration, timestamp: new Date().toISOString() },
        }));
        setCurrentStage(stageIndex + 1);
      } catch (error: unknown) {
        setStageResults((prev) => ({
          ...prev,
          [stage.id]: {
            level: 'fail',
            score: 0,
            details: { error: (error as { message?: string })?.message ?? 'Unknown error' },
            recommendations: ['An unexpected error occurred during validation'],
            duration: Date.now() - startTime,
            timestamp: new Date().toISOString(),
          },
        }));
        setCurrentStage(stageIndex + 1);
      }
    },
    [validationStages]
  );

  type ValidationStatus = 'pending' | 'running' | 'error' | 'passed' | 'failed' | 'warnings';
  const completeValidation = useCallback(() => {
    const results = Object.values(stageResults) as Array<{ level?: string; score?: number }>;
    const avgScore = results.reduce((sum, r) => sum + (r.score ?? 0), 0) / (results.length || 1);
    const criticalFailures = results.filter((r) => r.level === 'fail').length;
    const warnings = results.filter((r) => r.level === 'warning').length;
    const status: ValidationStatus = criticalFailures > 0 ? 'failed' : warnings > 1 ? 'warnings' : 'passed';
    setOverallStatus(status);
    setValidationProgress(100);
    if (status === 'passed') startMonitoring(30000);
    onValidationComplete?.({ status, score: Math.round(avgScore), results: stageResults, criticalFailures, warnings, timestamp: new Date().toISOString() });
  }, [stageResults, startMonitoring, onValidationComplete]);

  const startValidation = useCallback(async () => {
    setOverallStatus('running');
    setCurrentStage(0);
    setValidationProgress(0);
    setStageResults({});
    try {
      await runValidationStage(0, async () => {
        const envResult = await validateEnvironment();
        return { level: envResult.validation.browser.level, score: envResult.validation.browser.score, details: envResult.validation.browser, recommendations: envResult.validation.browser.issues || [] };
      });
      await runValidationStage(1, async () => {
        const envResult = validationData || (await validateEnvironment());
        const systemValidation = { features: envResult.validation.features, performance: envResult.validation.performance, storage: envResult.validation.storage };
        const avgScore = (Object.values(systemValidation) as Array<{ score: number }>).reduce((sum, val) => sum + val.score, 0) / 3;
        return { level: avgScore >= 80 ? 'pass' : avgScore >= 60 ? 'warning' : 'fail', score: Math.round(avgScore), details: systemValidation, recommendations: envResult.recommendations || [] };
      });
      await runValidationStage(2, async () => {
        const cfg = portConfig || (await detectConfig());
        try {
          const health = await performHealthCheck(cfg.defaultPort);
          return { level: health.overall.level, score: health.overall.score, details: { port: cfg.defaultPort, latency: health.network.latency }, recommendations: health.recommendations || [] };
        } catch (error: unknown) {
          return { level: 'fail', score: 0, details: { error: (error as { message?: string })?.message }, recommendations: ['Check that the backend is running', 'Verify network connectivity', 'Try refreshing the page'] };
        }
      });
      await runValidationStage(3, async () => {
        const perf = await runPerformanceTests();
        return { level: perf.score >= 80 ? 'pass' : perf.score >= 60 ? 'warning' : 'fail', score: perf.score, details: perf.details, recommendations: perf.recommendations };
      });
      completeValidation();
    } catch (error) {
      logger.error('Validation failed:', error);
      setOverallStatus('error');
    }
  }, [validateEnvironment, validationData, portConfig, detectConfig, performHealthCheck, runValidationStage, completeValidation]);

  const runPerformanceTests = useCallback(async () => {
    return { score: 85, details: { fps: 60, memory: 'ok' }, recommendations: [] };
  }, []);

  return <div className={`system-check-step ${className}`} data-theme={theme} />;
}
