import React from 'react';
import type { ReactNode } from 'react';
import './WizardStep.css';

/**
 * WizardStep Component
 * 
 * Reusable foundation component for onboarding wizard steps
 * Features:
 * - Consistent step layout and styling
 * - Progress indication and navigation
 * - Flexible content areas
 * - Accessibility support
 * - Animation transitions
 */
interface WizardStepProps {
  stepId: number;
  title: string;
  description?: string;
  icon?: ReactNode;
  children?: ReactNode;
  currentStep: number;
  totalSteps: number;
  onNext: () => void;
  onPrevious: () => void;
  onSkip?: () => void;
  nextText?: string;
  previousText?: string;
  skipText?: string;
  canProceed?: boolean;
  canSkip?: boolean;
  isLoading?: boolean;
  className?: string;
}

function WizardStep({ 
  stepId,
  title,
  description,
  icon,
  children,
  currentStep,
  totalSteps,
  onNext,
  onPrevious,
  onSkip,
  nextText = "Continue",
  previousText = "Back",
  skipText = "Skip",
  canProceed = true,
  canSkip = false,
  isLoading = false,
  className = ''
}: WizardStepProps) {
  const stepNumber = currentStep + 1;
  const isActive = stepId === currentStep;
  const progress = ((currentStep + 1) / totalSteps) * 100;

  return (
    <div className={`wizard-step ${isActive ? 'active' : ''} ${className}`}>
      {/* Step Header */}
      <div className="step-header">
        <div className="step-indicator">
          <div className="step-icon">
            {icon || stepNumber}
          </div>
          <div className="step-info">
            <h2 className="step-title">{title}</h2>
            {description && (
              <p className="step-description">{description}</p>
            )}
          </div>
        </div>
        
        <div className="step-progress">
          <span className="step-counter">
            Step {stepNumber} of {totalSteps}
          </span>
          <div className="progress-bar">
            <div 
              className="progress-fill"
              style={{ width: `${progress}%` }}
              role="progressbar"
              aria-valuenow={progress}
              aria-valuemin="0"
              aria-valuemax="100"
              aria-label={`Setup progress: ${Math.round(progress)}% complete`}
            />
          </div>
        </div>
      </div>

      {/* Step Content */}
      <div className="step-content">
        {children}
      </div>

      {/* Step Navigation */}
      <div className="step-navigation">
        <div className="nav-left">
          {currentStep > 0 && (
            <button
              onClick={onPrevious}
              className="btn-secondary nav-button"
              disabled={isLoading}
            >
              ← {previousText}
            </button>
          )}
        </div>

        <div className="nav-center">
          {canSkip && (
            <button
              onClick={onSkip}
              className="btn-link skip-button"
              disabled={isLoading}
            >
              {skipText}
            </button>
          )}
        </div>

        <div className="nav-right">
          <button
            onClick={onNext}
            className="btn-primary nav-button"
            disabled={!canProceed || isLoading}
          >
            {isLoading ? (
              <>
                <span className="spinner"></span>
                Processing...
              </>
            ) : (
              <>
                {nextText} →
              </>
            )}
          </button>
        </div>
      </div>

      {/* Loading Overlay */}
      {isLoading && (
        <div className="step-loading-overlay">
          <div className="loading-content">
            <div className="loading-spinner"></div>
            <p>Please wait while we set up your experience...</p>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * WizardStepContainer Component
 * 
 * Container for managing multiple wizard steps with animation
 */
export function WizardStepContainer({ 
  steps, 
  currentStep, 
  onStepChange, 
  className = '' 
}: { steps: React.ReactElement[]; currentStep: number; onStepChange: (idx: number) => void; className?: string }) {
  const activeStep = steps[currentStep];

  if (!activeStep) {
    return (
      <div className="wizard-error">
        <h3>Setup Error</h3>
        <p>Invalid step configuration. Please refresh and try again.</p>
      </div>
    );
  }

  return (
    <div className={`wizard-step-container ${className}`}>
      <div className="step-transition-wrapper">
        {React.cloneElement(activeStep, {
          currentStep,
          totalSteps: steps.length,
          onNext: () => {
            if (currentStep < steps.length - 1) {
              onStepChange(currentStep + 1);
            }
          },
          onPrevious: () => {
            if (currentStep > 0) {
              onStepChange(currentStep - 1);
            }
          }
        })}
      </div>
    </div>
  );
}

/**
 * Step Status Component
 * 
 * Shows completion status for wizard steps
 */
export function StepStatus({ steps, currentStep, completedSteps = [] }: { steps: { id?: string | number; title: string }[]; currentStep: number; completedSteps?: number[] }) {
  return (
    <div className="step-status-list">
      {steps.map((step, index) => {
        const isCompleted = completedSteps.includes(index);
        const isCurrent = index === currentStep;
        const isUpcoming = index > currentStep;

        return (
          <div 
            key={step.id || index}
            className={`step-status-item ${
              isCompleted ? 'completed' : 
              isCurrent ? 'current' : 
              isUpcoming ? 'upcoming' : ''
            }`}
          >
            <div className="status-indicator">
              {isCompleted ? '✅' : 
               isCurrent ? '🔄' : 
               '⏳'}
            </div>
            <span className="status-label">{step.title}</span>
          </div>
        );
      })}
    </div>
  );
}

export default WizardStep;
