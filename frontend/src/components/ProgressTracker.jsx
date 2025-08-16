import React, { useState, useEffect } from 'react';
import './ProgressTracker.css';

/**
 * ProgressTracker Component
 * 
 * Advanced progress visualization for onboarding wizard
 * Features:
 * - Multi-step progress indication
 * - Real-time updates and animations
 * - Estimated completion times
 * - Step validation states
 * - Accessibility support
 * - Mobile-responsive design
 */
function ProgressTracker({
  steps = [],
  currentStep = 0,
  completedSteps = [],
  estimatedTimeRemaining = null,
  showStepLabels = true,
  showTimeEstimate = true,
  variant = 'horizontal', // 'horizontal', 'vertical', 'circular'
  size = 'medium', // 'small', 'medium', 'large'
  theme = 'gradient', // 'gradient', 'solid', 'minimal'
  className = ''
}) {
  const [animatedProgress, setAnimatedProgress] = useState(0);
  const totalSteps = steps.length;
  const progressPercentage = totalSteps > 0 ? ((currentStep + 1) / totalSteps) * 100 : 0;

  // Animate progress changes
  useEffect(() => {
    const timer = setTimeout(() => {
      setAnimatedProgress(progressPercentage);
    }, 100);

    return () => clearTimeout(timer);
  }, [progressPercentage]);

  // Calculate estimated time
  const formatTimeEstimate = (minutes) => {
    if (!minutes) return null;
    if (minutes < 1) return 'Less than 1 minute';
    if (minutes < 60) return `${Math.round(minutes)} minutes`;
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = Math.round(minutes % 60);
    return `${hours}h ${remainingMinutes}m`;
  };

  if (variant === 'circular') {
    return <CircularProgressTracker {...{ steps, currentStep, completedSteps, progressPercentage, size, theme, className }} />;
  }

  if (variant === 'vertical') {
    return <VerticalProgressTracker {...{ steps, currentStep, completedSteps, showStepLabels, size, theme, className }} />;
  }

  // Horizontal progress tracker (default)
  return (
    <div className={`progress-tracker horizontal ${size} ${theme} ${className}`}>
      {/* Progress Header */}
      <div className="progress-header">
        <div className="progress-info">
          <h3 className="progress-title">Setup Progress</h3>
          <div className="progress-stats">
            <span className="step-counter">
              Step {currentStep + 1} of {totalSteps}
            </span>
            {showTimeEstimate && estimatedTimeRemaining && (
              <span className="time-estimate">
                {formatTimeEstimate(estimatedTimeRemaining)} remaining
              </span>
            )}
          </div>
        </div>
        <div className="progress-percentage">
          {Math.round(animatedProgress)}%
        </div>
      </div>

      {/* Progress Bar */}
      <div className="progress-bar-container">
        <div className="progress-bar-track">
          <div 
            className="progress-bar-fill"
            style={{ width: `${animatedProgress}%` }}
            role="progressbar"
            aria-valuenow={animatedProgress}
            aria-valuemin="0"
            aria-valuemax="100"
            aria-label={`Setup progress: ${Math.round(animatedProgress)}% complete`}
          />
          <div className="progress-bar-glow" />
        </div>
      </div>

      {/* Step Indicators */}
      {showStepLabels && (
        <div className="step-indicators">
          {steps.map((step, index) => {
            const isCompleted = completedSteps.includes(index);
            const isCurrent = index === currentStep;
            const isUpcoming = index > currentStep;

            return (
              <div 
                key={step.id || index}
                className={`step-indicator ${
                  isCompleted ? 'completed' : 
                  isCurrent ? 'current' : 
                  isUpcoming ? 'upcoming' : ''
                }`}
              >
                <div className="step-marker">
                  <div className="step-icon">
                    {isCompleted ? '✓' : 
                     isCurrent ? index + 1 : 
                     index + 1}
                  </div>
                </div>
                <div className="step-label">
                  <span className="step-title">{step.title || `Step ${index + 1}`}</span>
                  {step.description && (
                    <span className="step-description">{step.description}</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Current Step Details */}
      {steps[currentStep] && (
        <div className="current-step-details">
          <div className="current-step-content">
            <h4>{steps[currentStep].title}</h4>
            {steps[currentStep].description && (
              <p>{steps[currentStep].description}</p>
            )}
          </div>
          {steps[currentStep].estimatedTime && (
            <div className="step-time-estimate">
              <span>≈ {steps[currentStep].estimatedTime}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Circular Progress Tracker Component
 */
function CircularProgressTracker({ 
  steps, 
  currentStep, 
  completedSteps: _completedSteps, 
  progressPercentage, 
  size, 
  theme, 
  className 
}) {
  const radius = size === 'small' ? 40 : size === 'large' ? 80 : 60;
  const strokeWidth = size === 'small' ? 4 : size === 'large' ? 8 : 6;
  const circumference = 2 * Math.PI * radius;
  const strokeDasharray = circumference;
  const strokeDashoffset = circumference - (progressPercentage / 100) * circumference;

  return (
    <div className={`progress-tracker circular ${size} ${theme} ${className}`}>
      <div className="circular-progress-container">
        <svg 
          className="circular-progress-svg"
          width={(radius + strokeWidth) * 2}
          height={(radius + strokeWidth) * 2}
        >
          {/* Background circle */}
          <circle
            className="progress-circle-bg"
            cx={radius + strokeWidth}
            cy={radius + strokeWidth}
            r={radius}
            strokeWidth={strokeWidth}
            fill="transparent"
          />
          
          {/* Progress circle */}
          <circle
            className="progress-circle-fill"
            cx={radius + strokeWidth}
            cy={radius + strokeWidth}
            r={radius}
            strokeWidth={strokeWidth}
            fill="transparent"
            strokeDasharray={strokeDasharray}
            strokeDashoffset={strokeDashoffset}
            transform={`rotate(-90 ${radius + strokeWidth} ${radius + strokeWidth})`}
          />
        </svg>
        
        <div className="circular-progress-content">
          <div className="progress-percentage">
            {Math.round(progressPercentage)}%
          </div>
          <div className="progress-label">
            Step {currentStep + 1} of {steps.length}
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Vertical Progress Tracker Component
 */
function VerticalProgressTracker({ 
  steps, 
  currentStep, 
  completedSteps, 
  showStepLabels, 
  size, 
  theme, 
  className 
}) {
  return (
    <div className={`progress-tracker vertical ${size} ${theme} ${className}`}>
      <div className="vertical-steps">
        {steps.map((step, index) => {
          const isCompleted = completedSteps.includes(index);
          const isCurrent = index === currentStep;
          const isUpcoming = index > currentStep;

          return (
            <div 
              key={step.id || index}
              className={`vertical-step ${
                isCompleted ? 'completed' : 
                isCurrent ? 'current' : 
                isUpcoming ? 'upcoming' : ''
              }`}
            >
              <div className="step-marker">
                <div className="step-icon">
                  {isCompleted ? '✓' : 
                   isCurrent ? '●' : 
                   '○'}
                </div>
                {index < steps.length - 1 && (
                  <div className="step-connector" />
                )}
              </div>
              
              {showStepLabels && (
                <div className="step-content">
                  <h4 className="step-title">{step.title || `Step ${index + 1}`}</h4>
                  {step.description && (
                    <p className="step-description">{step.description}</p>
                  )}
                  {step.estimatedTime && (
                    <span className="step-time">≈ {step.estimatedTime}</span>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/**
 * Real-time Progress Monitor Component
 */
export function ProgressMonitor({ 
  onProgress, 
  autoUpdate = true, 
  updateInterval = 1000 
}) {
  const [currentProgress, setCurrentProgress] = useState(0);
  const [isTracking, setIsTracking] = useState(false);

  useEffect(() => {
    if (!autoUpdate || !isTracking) return;

    const interval = setInterval(() => {
      // Simulate progress tracking
      setCurrentProgress(prev => {
        const newProgress = Math.min(prev + Math.random() * 10, 100);
        if (onProgress) onProgress(newProgress);
        return newProgress;
      });
    }, updateInterval);

    return () => clearInterval(interval);
  }, [autoUpdate, isTracking, updateInterval, onProgress]);

  return {
    currentProgress,
    isTracking,
    startTracking: () => setIsTracking(true),
    stopTracking: () => setIsTracking(false),
    resetProgress: () => setCurrentProgress(0)
  };
}

/**
 * Progress Analytics Component
 */
export function ProgressAnalytics({ steps, currentStep, startTime }) {
  const [analytics, setAnalytics] = useState({
    averageStepTime: 0,
    estimatedCompletion: null,
    efficiency: 100
  });

  useEffect(() => {
    if (!startTime) return;

    const elapsed = (Date.now() - startTime) / 1000 / 60; // minutes
    const completedSteps = currentStep + 1;
    const averageStepTime = elapsed / completedSteps;
    const remainingSteps = Math.max(0, steps.length - completedSteps);
    const estimatedCompletion = averageStepTime * remainingSteps;

    setAnalytics({
      averageStepTime,
      estimatedCompletion,
      efficiency: Math.max(0, 100 - (elapsed / steps.length) * 10)
    });
  }, [currentStep, startTime, steps.length]);

  return analytics;
}

export default ProgressTracker;