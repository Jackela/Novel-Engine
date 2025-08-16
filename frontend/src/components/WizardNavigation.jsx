import React, { useState, useEffect } from 'react';
import './WizardNavigation.css';

/**
 * WizardNavigation Component
 * 
 * Advanced navigation controls for multi-step wizards
 * Features:
 * - Flexible navigation patterns (linear, non-linear, conditional)
 * - Keyboard navigation support
 * - Progress persistence
 * - Validation gates
 * - Accessibility compliance
 * - Mobile-responsive design
 */
function WizardNavigation({
  steps = [],
  currentStep = 0,
  completedSteps = [],
  onStepChange,
  onComplete,
  onCancel,
  validateStep,
  allowSkip = false,
  allowBacktrack = true,
  showStepList = true,
  navigationStyle = 'buttons', // 'buttons', 'breadcrumb', 'tabs', 'minimal'
  variant = 'horizontal', // 'horizontal', 'vertical'
  size = 'medium', // 'small', 'medium', 'large'
  className = ''
}) {
  const [isValidating, setIsValidating] = useState(false);
  const [validationErrors, setValidationErrors] = useState({});
  const [navigationHistory, setNavigationHistory] = useState([0]);

  const totalSteps = steps.length;
  const isFirstStep = currentStep === 0;
  const isLastStep = currentStep === totalSteps - 1;
  const canProceed = completedSteps.includes(currentStep) || !validationErrors[currentStep];

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.ctrlKey || event.metaKey) {
        switch (event.key) {
          case 'ArrowLeft':
            event.preventDefault();
            handlePrevious();
            break;
          case 'ArrowRight':
            event.preventDefault();
            handleNext();
            break;
          case 'Enter':
            if (event.shiftKey) {
              event.preventDefault();
              handleComplete();
            } else {
              event.preventDefault();
              handleNext();
            }
            break;
          case 'Escape':
            event.preventDefault();
            handleCancel();
            break;
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [currentStep, canProceed, handleCancel, handleComplete, handleNext, handlePrevious]);

  /**
   * Handle navigation to next step
   */
  const handleNext = async () => {
    if (isValidating) return;

    // Validate current step if validator provided
    if (validateStep) {
      setIsValidating(true);
      try {
        const validation = await validateStep(currentStep, steps[currentStep]);
        if (!validation.isValid) {
          setValidationErrors(prev => ({
            ...prev,
            [currentStep]: validation.errors
          }));
          setIsValidating(false);
          return;
        } else {
          // Clear any previous errors
          setValidationErrors(prev => {
            const newErrors = { ...prev };
            delete newErrors[currentStep];
            return newErrors;
          });
        }
      } catch (error) {
        console.error('Validation error:', error);
        setValidationErrors(prev => ({
          ...prev,
          [currentStep]: ['Validation failed. Please try again.']
        }));
        setIsValidating(false);
        return;
      }
      setIsValidating(false);
    }

    // Move to next step
    if (currentStep < totalSteps - 1) {
      const nextStep = currentStep + 1;
      setNavigationHistory(prev => [...prev, nextStep]);
      onStepChange?.(nextStep, 'next');
    } else {
      handleComplete();
    }
  };

  /**
   * Handle navigation to previous step
   */
  const handlePrevious = () => {
    if (isFirstStep || !allowBacktrack) return;

    const previousStep = currentStep - 1;
    setNavigationHistory(prev => [...prev, previousStep]);
    onStepChange?.(previousStep, 'previous');
  };

  /**
   * Handle direct step navigation
   */
  const handleStepClick = (stepIndex) => {
    if (stepIndex === currentStep) return;

    // Check if step is accessible
    const isAccessible = allowBacktrack || 
                        stepIndex <= Math.max(...completedSteps) + 1 ||
                        completedSteps.includes(stepIndex);

    if (!isAccessible) return;

    setNavigationHistory(prev => [...prev, stepIndex]);
    onStepChange?.(stepIndex, stepIndex > currentStep ? 'jump_forward' : 'jump_backward');
  };

  /**
   * Handle skip current step
   */
  const handleSkip = () => {
    if (!allowSkip || isLastStep) return;

    const nextStep = currentStep + 1;
    setNavigationHistory(prev => [...prev, nextStep]);
    onStepChange?.(nextStep, 'skip');
  };

  /**
   * Handle wizard completion
   */
  const handleComplete = () => {
    onComplete?.({
      completedSteps,
      navigationHistory,
      totalSteps,
      timestamp: new Date().toISOString()
    });
  };

  /**
   * Handle wizard cancellation
   */
  const handleCancel = () => {
    onCancel?.({
      currentStep,
      completedSteps,
      navigationHistory,
      timestamp: new Date().toISOString()
    });
  };

  if (navigationStyle === 'breadcrumb') {
    return <BreadcrumbNavigation {...{ steps, currentStep, completedSteps, onStepClick: handleStepClick, variant, size, className }} />;
  }

  if (navigationStyle === 'tabs') {
    return <TabNavigation {...{ steps, currentStep, completedSteps, onStepClick: handleStepClick, variant, size, className }} />;
  }

  if (navigationStyle === 'minimal') {
    return <MinimalNavigation {...{ currentStep, totalSteps, onNext: handleNext, onPrevious: handlePrevious, canProceed, isFirstStep, isLastStep, size, className }} />;
  }

  // Default button navigation
  return (
    <div className={`wizard-navigation ${navigationStyle} ${variant} ${size} ${className}`}>
      {/* Step List */}
      {showStepList && (
        <div className="navigation-step-list">
          <StepList 
            steps={steps}
            currentStep={currentStep}
            completedSteps={completedSteps}
            onStepClick={handleStepClick}
            allowBacktrack={allowBacktrack}
          />
        </div>
      )}

      {/* Validation Errors */}
      {validationErrors[currentStep] && (
        <div className="navigation-errors">
          <div className="error-list">
            {validationErrors[currentStep].map((error, index) => (
              <div key={index} className="error-item">
                <span className="error-icon">⚠️</span>
                <span className="error-message">{error}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Navigation Controls */}
      <div className="navigation-controls">
        <div className="nav-left">
          {!isFirstStep && allowBacktrack && (
            <button
              onClick={handlePrevious}
              className="nav-button btn-secondary"
              disabled={isValidating}
            >
              ← Previous
            </button>
          )}
          
          {onCancel && (
            <button
              onClick={handleCancel}
              className="nav-button btn-cancel"
              disabled={isValidating}
            >
              Cancel
            </button>
          )}
        </div>

        <div className="nav-center">
          {allowSkip && !isLastStep && (
            <button
              onClick={handleSkip}
              className="nav-button btn-link"
              disabled={isValidating}
            >
              Skip this step
            </button>
          )}
        </div>

        <div className="nav-right">
          <button
            onClick={isLastStep ? handleComplete : handleNext}
            className="nav-button btn-primary"
            disabled={!canProceed || isValidating}
          >
            {isValidating ? (
              <>
                <span className="spinner"></span>
                Validating...
              </>
            ) : isLastStep ? (
              'Complete Setup'
            ) : (
              'Continue →'
            )}
          </button>
        </div>
      </div>

      {/* Keyboard Shortcuts Help */}
      <div className="navigation-shortcuts">
        <details>
          <summary>Keyboard shortcuts</summary>
          <div className="shortcuts-list">
            <div className="shortcut-item">
              <kbd>Ctrl</kbd> + <kbd>→</kbd> Next step
            </div>
            <div className="shortcut-item">
              <kbd>Ctrl</kbd> + <kbd>←</kbd> Previous step
            </div>
            <div className="shortcut-item">
              <kbd>Ctrl</kbd> + <kbd>Enter</kbd> Continue
            </div>
            <div className="shortcut-item">
              <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>Enter</kbd> Complete
            </div>
            <div className="shortcut-item">
              <kbd>Esc</kbd> Cancel
            </div>
          </div>
        </details>
      </div>
    </div>
  );
}

/**
 * StepList Component
 */
function StepList({ steps, currentStep, completedSteps, onStepClick, allowBacktrack }) {
  return (
    <div className="step-list">
      {steps.map((step, index) => {
        const isCompleted = completedSteps.includes(index);
        const isCurrent = index === currentStep;
        const isAccessible = allowBacktrack || 
                           index <= Math.max(...completedSteps, currentStep) + 1 ||
                           isCompleted;

        return (
          <button
            key={step.id || index}
            onClick={() => isAccessible && onStepClick(index)}
            className={`step-list-item ${
              isCompleted ? 'completed' : 
              isCurrent ? 'current' : 
              isAccessible ? 'accessible' : 'locked'
            }`}
            disabled={!isAccessible}
            aria-current={isCurrent ? 'step' : undefined}
          >
            <div className="step-indicator">
              {isCompleted ? '✓' : index + 1}
            </div>
            <div className="step-info">
              <span className="step-title">{step.title || `Step ${index + 1}`}</span>
              {step.description && (
                <span className="step-description">{step.description}</span>
              )}
            </div>
            {!isAccessible && (
              <div className="step-lock">🔒</div>
            )}
          </button>
        );
      })}
    </div>
  );
}

/**
 * BreadcrumbNavigation Component
 */
function BreadcrumbNavigation({ steps, currentStep, completedSteps, onStepClick, variant, size, className }) {
  return (
    <nav className={`breadcrumb-navigation ${variant} ${size} ${className}`} aria-label="Setup progress">
      <ol className="breadcrumb-list">
        {steps.map((step, index) => {
          const isCompleted = completedSteps.includes(index);
          const isCurrent = index === currentStep;

          return (
            <li 
              key={step.id || index}
              className={`breadcrumb-item ${
                isCompleted ? 'completed' : 
                isCurrent ? 'current' : 'pending'
              }`}
            >
              <button
                onClick={() => onStepClick(index)}
                className="breadcrumb-link"
                aria-current={isCurrent ? 'step' : undefined}
              >
                <span className="breadcrumb-icon">
                  {isCompleted ? '✓' : index + 1}
                </span>
                <span className="breadcrumb-text">
                  {step.title || `Step ${index + 1}`}
                </span>
              </button>
              {index < steps.length - 1 && (
                <span className="breadcrumb-separator">→</span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

/**
 * TabNavigation Component
 */
function TabNavigation({ steps, currentStep, completedSteps, onStepClick, variant, size, className }) {
  return (
    <div className={`tab-navigation ${variant} ${size} ${className}`}>
      <div className="tab-list" role="tablist">
        {steps.map((step, index) => {
          const isCompleted = completedSteps.includes(index);
          const isCurrent = index === currentStep;

          return (
            <button
              key={step.id || index}
              onClick={() => onStepClick(index)}
              className={`tab-item ${
                isCompleted ? 'completed' : 
                isCurrent ? 'current' : 'pending'
              }`}
              role="tab"
              aria-selected={isCurrent}
              aria-controls={`step-panel-${index}`}
            >
              <span className="tab-icon">
                {isCompleted ? '✓' : index + 1}
              </span>
              <span className="tab-text">
                {step.title || `Step ${index + 1}`}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

/**
 * MinimalNavigation Component
 */
function MinimalNavigation({ currentStep, totalSteps, onNext, onPrevious, canProceed, isFirstStep, isLastStep, size, className }) {
  return (
    <div className={`minimal-navigation ${size} ${className}`}>
      <div className="minimal-controls">
        <button
          onClick={onPrevious}
          className="minimal-button"
          disabled={isFirstStep}
          aria-label="Previous step"
        >
          ←
        </button>
        
        <span className="step-indicator">
          {currentStep + 1} / {totalSteps}
        </span>
        
        <button
          onClick={onNext}
          className="minimal-button"
          disabled={!canProceed}
          aria-label={isLastStep ? "Complete setup" : "Next step"}
        >
          {isLastStep ? '✓' : '→'}
        </button>
      </div>
    </div>
  );
}

// Navigation Hook commented out to fix Fast Refresh issues
// Move to separate hooks file if needed
/*
export function useWizardNavigation(initialStep = 0, totalSteps = 0) {
  const [currentStep, setCurrentStep] = useState(initialStep);
  const [completedSteps, setCompletedSteps] = useState([]);
  const [navigationHistory, setNavigationHistory] = useState([initialStep]);

  const goToStep = (stepIndex, reason = 'manual') => {
    if (stepIndex >= 0 && stepIndex < totalSteps) {
      setCurrentStep(stepIndex);
      setNavigationHistory(prev => [...prev, { step: stepIndex, reason, timestamp: Date.now() }]);
    }
  };

  const markStepCompleted = (stepIndex) => {
    setCompletedSteps(prev => 
      prev.includes(stepIndex) ? prev : [...prev, stepIndex]
    );
  };

  const goNext = () => {
    if (currentStep < totalSteps - 1) {
      goToStep(currentStep + 1, 'next');
    }
  };

  const goPrevious = () => {
    if (currentStep > 0) {
      goToStep(currentStep - 1, 'previous');
    }
  };

  const reset = () => {
    setCurrentStep(initialStep);
    setCompletedSteps([]);
    setNavigationHistory([initialStep]);
  };

  return {
    currentStep,
    completedSteps,
    navigationHistory,
    goToStep,
    goNext,
    goPrevious,
    markStepCompleted,
    reset,
    isFirstStep: currentStep === 0,
    isLastStep: currentStep === totalSteps - 1,
    progress: totalSteps > 0 ? (currentStep + 1) / totalSteps : 0
  };
}
*/

export default WizardNavigation;