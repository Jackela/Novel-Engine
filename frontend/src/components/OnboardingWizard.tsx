import React, { useState, useEffect, useCallback, useMemo } from 'react';
import WizardStep from './WizardStep';
import WizardNavigation, { useWizardNavigation } from './WizardNavigation';
import ProgressTracker from './ProgressTracker';
import ApiKeySetup from './ApiKeySetup';
import ErrorDisplay from './ErrorDisplay';
import { usePortDetection } from '../utils/PortDetector';
import { useHealthMonitor } from '../utils/HealthMonitor';
import { useEnvironmentValidator } from '../utils/EnvironmentValidator';
import { SAMPLE_STORIES, STORY_UTILS } from '../data/sampleStories';
import './OnboardingWizard.css';
import DemoStep from './steps/DemoStep';

/**
 * OnboardingWizard Component
 * 
 * Comprehensive onboarding experience for StoryForge AI
 * Features:
 * - Multi-step guided setup
 * - Environment validation
 * - API key configuration
 * - Demo story generation
 * - Health monitoring integration
 * - Accessibility compliant
 * - Mobile responsive
 */
type WizardTheme = 'gradient' | 'solid' | 'minimal';

interface OnboardingWizardProps {
  onComplete?: (data?: unknown) => void;
  onCancel?: (data?: unknown) => void;
  allowSkip?: boolean;
  showProgress?: boolean;
  theme?: WizardTheme;
  className?: string;
}

function OnboardingWizard({
  onComplete,
  onCancel,
  allowSkip = true,
  showProgress = true,
  theme = 'gradient',
  className = ''
}: OnboardingWizardProps) {
  // Wizard navigation state
  const navigation = useWizardNavigation(0, 5);
  
  // System integration hooks
  const { config: portConfig, isDetecting, detectConfig, getApiUrl } = usePortDetection();
  const { healthData, startMonitoring: startHealthMonitoring } = useHealthMonitor();
  const { validationData, validateEnvironment } = useEnvironmentValidator();

  // Component state
  const [setupData, setSetupData] = useState({
    environment: null,
    apiKey: null,
    demoStory: null,
    healthStatus: null
  });
  const [currentError, setCurrentError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [estimatedTimeRemaining, setEstimatedTimeRemaining] = useState(8); // minutes

  // Step definitions
  type StepMeta = { id: string; title: string; description?: string; icon?: string; estimatedTime?: string };

  const steps = useMemo<StepMeta[]>(() => [
    {
      id: 'welcome',
      title: 'Welcome to StoryForge AI',
      description: 'Your journey into AI-powered storytelling begins here',
      icon: '🚀',
      estimatedTime: '1 minute'
    },
    {
      id: 'environment',
      title: 'System Check',
      description: 'Validate your environment for optimal performance',
      icon: '🔍',
      estimatedTime: '2 minutes'
    },
    {
      id: 'configuration',
      title: 'AI Configuration',
      description: 'Set up your Gemini API key for enhanced features',
      icon: '🔑',
      estimatedTime: '3 minutes'
    },
    {
      id: 'demo',
      title: 'Try Your First Story',
      description: 'Experience the magic of AI-powered storytelling',
      icon: '✨',
      estimatedTime: '2 minutes'
    },
    {
      id: 'completion',
      title: 'Setup Complete!',
      description: 'You\'re ready to create amazing stories',
      icon: '🎉',
      estimatedTime: '30 seconds'
    }
  ], []);

  // Update time estimate based on current step
  const updateTimeEstimate = useCallback(() => {
    const remainingSteps = steps.slice(navigation.currentStep + 1);
    const timeInMinutes = remainingSteps.reduce((total, step) => {
      const minutes = parseInt(step.estimatedTime.match(/\d+/)?.[0] || '1');
      return total + minutes;
    }, 0);
    setEstimatedTimeRemaining(timeInMinutes);
  }, [navigation.currentStep, steps]);

  // Initialize onboarding
  useEffect(() => {
    const initializeOnboarding = async () => {
      try {
        setIsLoading(true);

        // In test environments, skip long-running detection/monitoring to keep tests fast
        const isTestEnv = typeof process !== 'undefined' && !!(process.env?.VITEST || process.env?.VITEST_WORKER_ID);
        if (!isTestEnv) {
          // Start health monitoring
          startHealthMonitoring(30000);
        }
        
        // Update time estimate based on current step
        updateTimeEstimate();
        
      } catch (error) {
        setCurrentError({
          title: 'Initialization Error',
          message: 'Failed to initialize onboarding wizard.',
          suggestions: ['Refresh the page and try again', 'Check your internet connection'],
          severity: 'error',
          originalError: error
        });
      } finally {
        setIsLoading(false);
      }
    };

    initializeOnboarding();
  }, [startHealthMonitoring, updateTimeEstimate]);

  // Update time estimate when step changes
  useEffect(() => {
    updateTimeEstimate();
  }, [navigation.currentStep, updateTimeEstimate]);

  /**
   * Step validation function
   */
  const validateStep = async (stepIndex: number, step: StepMeta) => {
    try {
      switch (step.id) {
        case 'welcome':
          return { isValid: true };
          
        case 'environment':
          if (!validationData) {
            throw new Error('Environment validation not completed');
          }
          return { 
            isValid: validationData.overall.level !== 'fail',
            errors: validationData.overall.level === 'fail' ? 
              ['Environment validation failed. Please address critical issues.'] : []
          };
          
        case 'configuration':
          // API key is optional, so always valid
          return { isValid: true };
          
        case 'demo':
          if (!setupData.demoStory) {
            throw new Error('Demo story not generated');
          }
          return { isValid: true };
          
        case 'completion':
          return { isValid: true };
          
        default:
          return { isValid: true };
      }
    } catch (error) {
      return {
        isValid: false,
        errors: [error.message]
      };
    }
  };

  /**
   * Handle step changes
   */
  const handleStepChange = (newStep: number, reason: string) => {
    navigation.goToStep(newStep, reason);
    setCurrentError(null);
  };

  /**
   * Handle wizard completion
   */
  const handleComplete = () => {
    const completionData = {
      setupData,
      navigationHistory: navigation.navigationHistory,
      completedAt: new Date().toISOString(),
      healthStatus: healthData,
      environment: validationData
    };

    onComplete?.(completionData);
  };

  /**
   * Handle wizard cancellation
   */
  const handleCancel = () => {
    const cancellationData = {
      currentStep: navigation.currentStep,
      setupData,
      canceledAt: new Date().toISOString()
    };

    onCancel?.(cancellationData);
  };

  /**
   * Render step content
   */
  const renderStepContent = () => {
    const safeIndex = Math.min(Math.max(navigation.currentStep, 0), steps.length - 1);
    const currentStepData = steps[safeIndex];

    switch (currentStepData.id) {
      case 'welcome':
        return <WelcomeStep onContinue={() => navigation.goNext()} />;

      case 'environment':
        return (
          <EnvironmentStep
            validationData={validationData}
            onValidate={validateEnvironment}
            onValidationComplete={(data) => {
              setSetupData(prev => ({ ...prev, environment: data }));
              if (data.overall.level !== 'fail') {
                navigation.markStepCompleted(navigation.currentStep);
              }
            }}
          />
        );

      case 'configuration':
        return (
          <ConfigurationStep
            portConfig={portConfig}
            isDetecting={isDetecting}
            onDetectConfig={detectConfig}
            onConfigured={(config) => {
              setSetupData(prev => ({ ...prev, apiKey: config }));
              navigation.markStepCompleted(navigation.currentStep);
            }}
            allowSkip={allowSkip}
          />
        );

      case 'demo':
        return (
          <DemoStep
            apiUrl={getApiUrl}
            hasApiKey={!!setupData.apiKey?.hasApiKey}
            onStoryGenerated={(story) => {
              setSetupData(prev => ({ ...prev, demoStory: story }));
              navigation.markStepCompleted(navigation.currentStep);
            }}
          />
        );

      case 'completion':
        return (
          <CompletionStep
            setupData={setupData}
            healthData={healthData}
            onComplete={handleComplete}
          />
        );

      default:
        return <div>Step not found</div>;
    }
  };

  const displayIndex = Math.min(Math.max(navigation.currentStep, 0), steps.length - 1);

  return (
    <div className={`onboarding-wizard ${theme} ${className}`}>
      {/* Progress Tracker */}
      {showProgress && (
        <div className="wizard-progress">
          <ProgressTracker
            steps={steps}
            currentStep={navigation.currentStep}
            completedSteps={navigation.completedSteps}
            estimatedTimeRemaining={estimatedTimeRemaining}
            theme={theme}
            size="medium"
          />
        </div>
      )}

      {/* Current Step */}
      <div className="wizard-content">
        <WizardStep
          stepId={navigation.currentStep}
          title={steps[displayIndex]?.title}
          description={steps[displayIndex]?.description}
          icon={steps[displayIndex]?.icon}
          currentStep={navigation.currentStep}
          totalSteps={steps.length}
          isLoading={isLoading}
        >
          {renderStepContent()}
        </WizardStep>
      </div>

      {/* Error Display */}
      {currentError && (
        <div className="wizard-error">
          <ErrorDisplay
            error={currentError}
            onDismiss={() => setCurrentError(null)}
            showTechnicalDetails={true}
          />
        </div>
      )}

      {/* Navigation */}
      <div className="wizard-navigation">
        <WizardNavigation
          steps={steps}
          currentStep={navigation.currentStep}
          completedSteps={navigation.completedSteps}
          onStepChange={handleStepChange}
          onComplete={handleComplete}
          onCancel={handleCancel}
          validateStep={validateStep}
          allowSkip={allowSkip}
          allowBacktrack={true}
          showStepList={false}
          navigationStyle="buttons"
          size="medium"
        />
      </div>
    </div>
  );
}

/**
 * Welcome Step Component
 */
function WelcomeStep({ onContinue: _onContinue }) {
  return (
    <div className="welcome-step">
      <div className="welcome-hero">
        <h1>Welcome to StoryForge AI</h1>
        <p className="welcome-subtitle">
          Create immersive, interactive stories powered by advanced AI
        </p>
      </div>

      <div className="welcome-features">
        <div className="feature-card">
          <div className="feature-icon">🎭</div>
          <h3>Dynamic Characters</h3>
          <p>AI-powered characters with unique personalities and decision-making</p>
        </div>
        
        <div className="feature-card">
          <div className="feature-icon">📖</div>
          <h3>Interactive Stories</h3>
          <p>Stories that adapt and evolve based on character choices and interactions</p>
        </div>
        
        <div className="feature-card">
          <div className="feature-icon">🎨</div>
          <h3>Rich Narratives</h3>
          <p>Professional-quality storytelling with multiple genres and themes</p>
        </div>
      </div>

      <div className="welcome-getting-started">
        <p>Let's get you set up in just a few quick steps!</p>
      </div>
    </div>
  );
}

/**
 * Environment Step Component
 */
function EnvironmentStep({ validationData, onValidate, onValidationComplete }) {
  const [isValidating, setIsValidating] = useState(false);

  const handleValidation = async () => {
    setIsValidating(true);
    try {
      const result = await onValidate();
      onValidationComplete(result);
    } finally {
      setIsValidating(false);
    }
  };

  useEffect(() => {
    if (!validationData) {
      handleValidation();
    }
  }, [handleValidation, validationData]);

  if (isValidating) {
    return (
      <div className="environment-step validating">
        <div className="validation-progress">
          <div className="spinner"></div>
          <h3>Checking Your Environment</h3>
          <p>We're validating your system for optimal StoryForge AI performance...</p>
        </div>
      </div>
    );
  }

  if (!validationData) {
    return (
      <div className="environment-step">
        <button onClick={handleValidation} className="btn-primary">
          Start Environment Check
        </button>
      </div>
    );
  }

  const { overall, validation } = validationData;

  return (
    <div className="environment-step">
      <div className={`validation-summary ${overall.level}`}>
        <div className="summary-header">
          <div className="summary-icon">
            {overall.level === 'pass' ? '✅' : 
             overall.level === 'warning' ? '⚠️' : '❌'}
          </div>
          <div className="summary-content">
            <h3>{overall.summary}</h3>
            <div className="score-bar">
              <div 
                className="score-fill"
                style={{ width: `${overall.score}%` }}
              />
              <span className="score-text">{overall.score}%</span>
            </div>
          </div>
        </div>
      </div>

      <div className="validation-details">
        {Object.entries(validation).map(([category, result]) => (
          <div key={category} className={`validation-item ${result.level}`}>
            <div className="item-header">
              <span className="item-icon">
                {result.level === 'pass' ? '✅' : 
                 result.level === 'warning' ? '⚠️' : '❌'}
              </span>
              <span className="item-title">{category.replace('_', ' ').toUpperCase()}</span>
              <span className="item-score">{result.score}%</span>
            </div>
            
            {(result.issues?.length > 0 || result.warnings?.length > 0) && (
              <div className="item-details">
                {result.issues?.map((issue, index) => (
                  <div key={index} className="issue error">❌ {issue}</div>
                ))}
                {result.warnings?.map((warning, index) => (
                  <div key={index} className="issue warning">⚠️ {warning}</div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {overall.level === 'fail' && (
        <div className="validation-actions">
          <button onClick={handleValidation} className="btn-secondary">
            Retry Validation
          </button>
        </div>
      )}
    </div>
  );
}

/**
 * Configuration Step Component
 */
function ConfigurationStep({ portConfig, isDetecting, onDetectConfig, onConfigured, allowSkip }) {
  const [configStatus, setConfigStatus] = useState('pending');

  useEffect(() => {
    if (!portConfig && !isDetecting) {
      onDetectConfig();
    }
  }, [portConfig, isDetecting, onDetectConfig]);

  useEffect(() => {
    if (portConfig) {
      setConfigStatus('detected');
    }
  }, [portConfig]);

  return (
    <div className="configuration-step">
      {isDetecting && (
        <div className="detecting-backend">
          <div className="spinner"></div>
          <h3>Detecting Backend Configuration</h3>
          <p>Automatically configuring connection to StoryForge AI backend...</p>
        </div>
      )}

      {configStatus === 'detected' && (
        <div className="backend-detected">
          <div className="detection-success">
            <span className="success-icon">✅</span>
            <h3>Backend Connected Successfully</h3>
            <p>StoryForge AI backend is running at {portConfig ? `port ${portConfig.defaultPort}` : 'unknown port'}</p>
          </div>
        </div>
      )}

      <div className="api-configuration">
        <ApiKeySetup
          onConfigured={onConfigured}
          allowSkip={allowSkip}
        />
      </div>
    </div>
  );
}


/**
 * Completion Step Component
 */
// Completion Step Component
type SetupData = {
  environment?: { overall: { level?: string } };
  apiKey?: { hasApiKey?: boolean };
  demoStory?: unknown;
};

function CompletionStep({ setupData, healthData, onComplete }: { setupData: SetupData; healthData?: unknown; onComplete: () => void }) {
  return (
    <div className="completion-step">
      <div className="completion-hero">
        <div className="success-animation">🎉</div>
        <h1>Setup Complete!</h1>
        <p>You're ready to create amazing stories with StoryForge AI</p>
      </div>

      <div className="setup-summary">
        <h3>Your Configuration</h3>
        
        <div className="summary-grid">
          <div className="summary-item">
            <span className="item-label">Environment</span>
            <span className={`item-status ${setupData.environment?.overall.level || 'unknown'}`}>
              {setupData.environment?.overall.level === 'pass' ? '✅ Optimal' :
               setupData.environment?.overall.level === 'warning' ? '⚠️ Good' :
               setupData.environment?.overall.level === 'fail' ? '❌ Issues' :
               '❓ Unknown'}
            </span>
          </div>

          <div className="summary-item">
            <span className="item-label">AI Features</span>
            <span className={`item-status ${setupData.apiKey?.hasApiKey ? 'enabled' : 'disabled'}`}>
              {setupData.apiKey?.hasApiKey ? '✅ Enhanced' : '🎭 Algorithmic'}
            </span>
          </div>

          <div className="summary-item">
            <span className="item-label">Demo Story</span>
            <span className="item-status enabled">
              {setupData.demoStory ? '✅ Completed' : '⏳ Pending'}
            </span>
          </div>

          <div className="summary-item">
            <span className="item-label">System Health</span>
            <span className={`item-status ${healthData?.overall.level || 'unknown'}`}>
              {healthData?.overall.level === 'excellent' ? '✅ Excellent' :
               healthData?.overall.level === 'good' ? '✅ Good' :
               healthData?.overall.level === 'warning' ? '⚠️ Warning' :
               healthData?.overall.level === 'critical' ? '❌ Critical' :
               '❓ Unknown'}
            </span>
          </div>
        </div>
      </div>

      <div className="next-steps">
        <h3>What's Next?</h3>
        <div className="next-steps-list">
          <div className="next-step">
            <span className="step-icon">📝</span>
            <div className="step-content">
              <strong>Create Your First Story</strong>
              <p>Start with a blank canvas or use one of our templates</p>
            </div>
          </div>
          
          <div className="next-step">
            <span className="step-icon">👥</span>
            <div className="step-content">
              <strong>Design Custom Characters</strong>
              <p>Create unique characters with distinct personalities</p>
            </div>
          </div>
          
          <div className="next-step">
            <span className="step-icon">🌟</span>
            <div className="step-content">
              <strong>Explore Advanced Features</strong>
              <p>Discover story templates, export options, and sharing</p>
            </div>
          </div>
        </div>
      </div>

      <div className="completion-actions">
        <button onClick={onComplete} className="btn-primary btn-large">
          Start Creating Stories
        </button>
      </div>
    </div>
  );
}

export default OnboardingWizard;
