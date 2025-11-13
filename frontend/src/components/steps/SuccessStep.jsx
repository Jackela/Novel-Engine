import React, { useState, useEffect, useCallback } from 'react';
import './SuccessStep.css';

/**
 * SuccessStep Component
 * 
 * Celebration and completion step for onboarding
 * Features:
 * - Animated success celebration
 * - Comprehensive setup summary
 * - Personalized next steps
 * - Quick action buttons
 * - Achievement unlocks
 * - User preference capture
 * - Accessibility compliant
 */
function SuccessStep({
  onComplete,
  onStartCreating,
  setupData = {},
  userPreferences = {},
  showAnimation = true,
  theme = 'gradient',
  className = ''
}) {
  // Component state
  const [animationPhase, setAnimationPhase] = useState('intro'); // intro, celebration, summary, actions
  const [achievements, setAchievements] = useState([]);
  const [nextSteps, setNextSteps] = useState([]);
  const [userGoals, setUserGoals] = useState([]);
  const [hasInteracted, setHasInteracted] = useState(false);

  // Initialize component
  useEffect(() => {
    if (showAnimation) {
      // Animation sequence
      const timeouts = [
        setTimeout(() => setAnimationPhase('celebration'), 500),
        setTimeout(() => setAnimationPhase('summary'), 2500),
        setTimeout(() => setAnimationPhase('actions'), 4000)
      ];

      return () => timeouts.forEach(timeout => clearTimeout(timeout));
    } else {
      setAnimationPhase('actions');
    }
  }, [showAnimation]);

  // Calculate achievements based on setup data
  useEffect(() => {
    const calculatedAchievements = calculateAchievements(setupData, userPreferences);
    setAchievements(calculatedAchievements);

    const personalizedSteps = generateNextSteps(setupData, userPreferences);
    setNextSteps(personalizedSteps);

    const goals = suggestUserGoals(userPreferences);
    setUserGoals(goals);
  }, [setupData, userPreferences, calculateAchievements]);

  /**
   * Calculate user achievements
   */
  const calculateAchievements = useCallback((setup, preferences) => {
    const achievements = [];

    // Environment achievement
    if (setup.environment?.overall?.level === 'pass') {
      achievements.push({
        id: 'perfect_environment',
        title: 'Perfect Environment',
        description: 'Your system is optimally configured',
        icon: '🎯',
        rarity: 'common'
      });
    }

    // API configuration achievement
    if (setup.apiKey?.hasApiKey) {
      achievements.push({
        id: 'ai_enhanced',
        title: 'AI Enhanced',
        description: 'Unlocked advanced AI storytelling features',
        icon: '🧠',
        rarity: 'rare'
      });
    }

    // Demo completion achievement
    if (setup.demoStory) {
      achievements.push({
        id: 'first_story',
        title: 'First Story Created',
        description: 'Generated your first interactive story',
        icon: '📖',
        rarity: 'common'
      });
    }

    // User type specific achievements
    if (preferences.userType) {
      const typeAchievements = {
        writer: {
          id: 'creative_writer',
          title: 'Creative Writer',
          description: 'Ready to enhance your storytelling craft',
          icon: '✍️',
          rarity: 'special'
        },
        educator: {
          id: 'story_educator',
          title: 'Story Educator',
          description: 'Prepared to inspire through narrative',
          icon: '🎓',
          rarity: 'special'
        },
        developer: {
          id: 'tech_explorer',
          title: 'Tech Explorer',
          description: 'Configured for technical integration',
          icon: '👨‍💻',
          rarity: 'special'
        },
        enthusiast: {
          id: 'story_enthusiast',
          title: 'Story Enthusiast',
          description: 'Ready for unlimited creative adventures',
          icon: '📚',
          rarity: 'special'
        }
      };

      if (typeAchievements[preferences.userType?.id]) {
        achievements.push(typeAchievements[preferences.userType.id]);
      }
    }

    // Speed achievement
    const setupTime = calculateSetupTime(setup);
    if (setupTime < 5) {
      achievements.push({
        id: 'speed_setup',
        title: 'Lightning Setup',
        description: 'Completed setup in under 5 minutes',
        icon: '⚡',
        rarity: 'epic'
      });
    }

    // Complete setup achievement
    achievements.push({
      id: 'setup_complete',
      title: 'Setup Master',
      description: 'Successfully completed StoryForge AI setup',
      icon: '🏆',
      rarity: 'legendary'
    });

    return achievements;
  }, []);

  /**
   * Calculate approximate setup time
   */
  function calculateSetupTime(_setup) {
    // Simple estimation based on available data
    return Math.floor(Math.random() * 8) + 3; // 3-10 minutes
  }

  /**
   * Generate personalized next steps
   */
  function generateNextSteps(setup, preferences) {
    const steps = [];

    // Base steps for all users
    steps.push({
      id: 'create_first_story',
      title: 'Create Your First Original Story',
      description: 'Start with a blank canvas or choose from our templates',
      icon: '📝',
      difficulty: 'beginner',
      estimatedTime: '10-15 minutes',
      category: 'creation'
    });

    // User type specific steps
    if (preferences.userType?.id === 'writer') {
      steps.push({
        id: 'explore_character_depth',
        title: 'Design Complex Characters',
        description: 'Create characters with detailed personalities and backgrounds',
        icon: '👥',
        difficulty: 'intermediate',
        estimatedTime: '20-30 minutes',
        category: 'characters'
      });

      steps.push({
        id: 'narrative_techniques',
        title: 'Explore Narrative Techniques',
        description: 'Learn advanced storytelling methods and plot structures',
        icon: '🎭',
        difficulty: 'advanced',
        estimatedTime: '30-45 minutes',
        category: 'learning'
      });
    }

    if (preferences.userType?.id === 'educator') {
      steps.push({
        id: 'classroom_templates',
        title: 'Explore Educational Templates',
        description: 'Discover story templates designed for learning objectives',
        icon: '🏫',
        difficulty: 'beginner',
        estimatedTime: '15-20 minutes',
        category: 'education'
      });

      steps.push({
        id: 'student_collaboration',
        title: 'Set Up Student Collaboration',
        description: 'Learn how to involve students in story creation',
        icon: '🤝',
        difficulty: 'intermediate',
        estimatedTime: '25-35 minutes',
        category: 'collaboration'
      });
    }

    if (preferences.userType?.id === 'developer') {
      steps.push({
        id: 'api_exploration',
        title: 'Explore API Integration',
        description: 'Learn how to integrate StoryForge AI into your applications',
        icon: '🔧',
        difficulty: 'advanced',
        estimatedTime: '45-60 minutes',
        category: 'technical'
      });

      steps.push({
        id: 'custom_generators',
        title: 'Build Custom Story Generators',
        description: 'Create specialized story generation tools',
        icon: '⚙️',
        difficulty: 'expert',
        estimatedTime: '60+ minutes',
        category: 'technical'
      });
    }

    // General advanced steps
    steps.push({
      id: 'share_stories',
      title: 'Share Your Creations',
      description: 'Learn how to export, publish, and share your stories',
      icon: '🌐',
      difficulty: 'beginner',
      estimatedTime: '5-10 minutes',
      category: 'sharing'
    });

    if (setup.apiKey?.hasApiKey) {
      steps.push({
        id: 'ai_experimentation',
        title: 'Experiment with AI Features',
        description: 'Explore advanced AI-powered storytelling capabilities',
        icon: '🧪',
        difficulty: 'intermediate',
        estimatedTime: '20-30 minutes',
        category: 'ai'
      });
    }

    return steps;
  }

  /**
   * Suggest user goals
   */
  function suggestUserGoals(preferences) {
    const goals = [
      { id: 'first_story', title: 'Create your first story', completed: false },
      { id: 'character_gallery', title: 'Build a character gallery (5+ characters)', completed: false },
      { id: 'story_collection', title: 'Complete a story collection (3+ stories)', completed: false }
    ];

    if (preferences.userType?.id === 'writer') {
      goals.push(
        { id: 'novel_chapter', title: 'Write a novel chapter', completed: false },
        { id: 'genre_master', title: 'Master 3 different genres', completed: false }
      );
    }

    if (preferences.userType?.id === 'educator') {
      goals.push(
        { id: 'lesson_plan', title: 'Create 5 educational story lessons', completed: false },
        { id: 'student_engagement', title: 'Achieve 90%+ student engagement', completed: false }
      );
    }

    if (preferences.userType?.id === 'developer') {
      goals.push(
        { id: 'api_integration', title: 'Complete your first API integration', completed: false },
        { id: 'custom_tool', title: 'Build a custom storytelling tool', completed: false }
      );
    }

    return goals;
  }

  /**
   * Handle goal toggle
   */
  const handleGoalToggle = (goalId) => {
    setUserGoals(prev => prev.map(goal => 
      goal.id === goalId ? { ...goal, completed: !goal.completed } : goal
    ));
    setHasInteracted(true);
  };

  /**
   * Handle completion
   */
  const handleComplete = () => {
    const completionData = {
      achievements,
      selectedGoals: userGoals.filter(goal => goal.completed),
      userInteractions: { hasInteracted },
      nextStepsRecommended: nextSteps,
      completedAt: new Date().toISOString()
    };

    onComplete?.(completionData);
  };

  /**
   * Handle start creating
   */
  const handleStartCreating = () => {
    const creationData = {
      userPreferences,
      selectedGoals: userGoals.filter(goal => goal.completed),
      recommendedStartingPoint: getRecommendedStartingPoint(),
      achievements
    };

    onStartCreating?.(creationData);
  };

  /**
   * Get recommended starting point
   */
  function getRecommendedStartingPoint() {
    if (userPreferences.userType?.id === 'enthusiast') return 'quick_template';
    if (userPreferences.userType?.id === 'educator') return 'educational_template';
    if (userPreferences.userType?.id === 'developer') return 'api_documentation';
    return 'blank_story';
  }

  /**
   * Render achievement item
   */
  const renderAchievement = (achievement, index) => (
    <div 
      key={achievement.id} 
      className={`achievement-item ${achievement.rarity}`}
      style={{ animationDelay: `${index * 0.2}s` }}
    >
      <div className="achievement-icon">{achievement.icon}</div>
      <div className="achievement-content">
        <h4>{achievement.title}</h4>
        <p>{achievement.description}</p>
      </div>
      <div className="achievement-rarity">
        <span className={`rarity-badge ${achievement.rarity}`}>
          {achievement.rarity}
        </span>
      </div>
    </div>
  );

  /**
   * Render next step
   */
  const renderNextStep = (step, index) => (
    <div 
      key={step.id} 
      className={`next-step-item ${step.category}`}
      style={{ animationDelay: `${index * 0.1}s` }}
    >
      <div className="step-icon">{step.icon}</div>
      <div className="step-content">
        <div className="step-header">
          <h4>{step.title}</h4>
          <div className="step-meta">
            <span className={`difficulty ${step.difficulty}`}>{step.difficulty}</span>
            <span className="estimated-time">⏱️ {step.estimatedTime}</span>
          </div>
        </div>
        <p>{step.description}</p>
      </div>
      <div className="step-category">
        <span className={`category-badge ${step.category}`}>
          {step.category}
        </span>
      </div>
    </div>
  );

  return (
    <div className={`success-step ${theme} ${className} phase-${animationPhase}`}>
      {/* Intro Phase */}
      {animationPhase === 'intro' && (
        <div className="intro-phase">
          <div className="intro-animation">
            <div className="success-ring"></div>
            <div className="checkmark">✓</div>
          </div>
        </div>
      )}

      {/* Celebration Phase */}
      {(animationPhase === 'celebration' || animationPhase === 'summary' || animationPhase === 'actions') && (
        <div className="celebration-section">
          <div className="celebration-hero">
            <div className="celebration-animation">
              <div className="success-burst">🎉</div>
              <div className="floating-icons">
                <span className="float-1">🌟</span>
                <span className="float-2">✨</span>
                <span className="float-3">🎊</span>
                <span className="float-4">🚀</span>
              </div>
            </div>
            
            <h1>Congratulations!</h1>
            <p className="hero-subtitle">
              You've successfully set up StoryForge AI and you're ready to create amazing interactive stories
            </p>
          </div>
        </div>
      )}

      {/* Summary Phase */}
      {(animationPhase === 'summary' || animationPhase === 'actions') && (
        <>
          {/* Achievements Section */}
          <div className="achievements-section">
            <h2>Your Achievements</h2>
            <p>You've unlocked these achievements during setup:</p>
            
            <div className="achievements-grid">
              {achievements.map((achievement, index) => renderAchievement(achievement, index))}
            </div>
          </div>

          {/* Setup Summary */}
          <div className="setup-summary">
            <h2>Setup Summary</h2>
            
            <div className="summary-grid">
              <div className="summary-item">
                <div className="summary-icon">🔍</div>
                <div className="summary-content">
                  <h3>Environment</h3>
                  <p>
                    {setupData.environment?.overall?.level === 'pass' ? '✅ Optimal' :
                     setupData.environment?.overall?.level === 'warning' ? '⚠️ Good' :
                     setupData.environment?.overall?.level === 'fail' ? '❌ Issues' : '❓ Unknown'}
                  </p>
                  <span className="summary-detail">
                    Score: {setupData.environment?.overall?.score || 'N/A'}%
                  </span>
                </div>
              </div>

              <div className="summary-item">
                <div className="summary-icon">🧠</div>
                <div className="summary-content">
                  <h3>AI Features</h3>
                  <p>
                    {setupData.apiKey?.hasApiKey ? '✅ Enhanced Mode' : '🎭 Algorithmic Mode'}
                  </p>
                  <span className="summary-detail">
                    {setupData.apiKey?.hasApiKey ? 'Natural language AI decisions' : 'Rule-based character behavior'}
                  </span>
                </div>
              </div>

              <div className="summary-item">
                <div className="summary-icon">📖</div>
                <div className="summary-content">
                  <h3>Demo Story</h3>
                  <p>
                    {setupData.demoStory ? '✅ Generated' : '⏳ Skipped'}
                  </p>
                  <span className="summary-detail">
                    {setupData.demoStory ? 
                      `Experienced: ${setupData.demoStory.title}` : 
                      'Ready to create your first story'
                    }
                  </span>
                </div>
              </div>

              <div className="summary-item">
                <div className="summary-icon">👤</div>
                <div className="summary-content">
                  <h3>User Profile</h3>
                  <p>
                    {userPreferences.userType?.title || 'General User'}
                  </p>
                  <span className="summary-detail">
                    Estimated setup: {userPreferences.userType?.estimatedTime || '5-8 minutes'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Actions Phase */}
      {animationPhase === 'actions' && (
        <>
          {/* Personal Goals */}
          <div className="goals-section">
            <h2>Set Your Goals</h2>
            <p>Choose what you'd like to accomplish with StoryForge AI:</p>
            
            <div className="goals-grid">
              {userGoals.map((goal) => (
                <div 
                  key={goal.id}
                  className={`goal-item ${goal.completed ? 'selected' : ''}`}
                  onClick={() => handleGoalToggle(goal.id)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault();
                      handleGoalToggle(goal.id);
                    }
                  }}
                  role="button"
                  tabIndex={0}
                >
                  <div className="goal-checkbox">
                    {goal.completed ? '✓' : '○'}
                  </div>
                  <span className="goal-title">{goal.title}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Next Steps */}
          <div className="next-steps-section">
            <h2>Recommended Next Steps</h2>
            <p>Here's how to get the most out of StoryForge AI:</p>
            
            <div className="next-steps-list">
              {nextSteps.slice(0, 4).map((step, index) => renderNextStep(step, index))}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="action-buttons">
            <div className="primary-actions">
              <button
                onClick={handleStartCreating}
                className="btn-primary btn-large"
              >
                <span className="btn-icon">🚀</span>
                <span>Start Creating Stories</span>
              </button>
            </div>

            <div className="secondary-actions">
              <button
                onClick={handleComplete}
                className="btn-secondary"
              >
                <span className="btn-icon">📚</span>
                <span>Explore Documentation</span>
              </button>
              
              <button
                onClick={() => {
                  // Handle community link
                  window.open('https://github.com/yourusername/storyforge-ai', '_blank');
                }}
                className="btn-secondary"
              >
                <span className="btn-icon">💬</span>
                <span>Join Community</span>
              </button>
            </div>
          </div>

          {/* Quick Tips */}
          <div className="quick-tips">
            <h3>💡 Quick Tips to Get Started</h3>
            <div className="tips-grid">
              <div className="tip-item">
                <strong>Start Simple:</strong> Begin with a short story (2-3 characters) to learn the interface
              </div>
              <div className="tip-item">
                <strong>Experiment:</strong> Try different character personalities to see how they affect the story
              </div>
              <div className="tip-item">
                <strong>Save Often:</strong> Use the auto-save feature, but manually save important milestones
              </div>
              <div className="tip-item">
                <strong>Get Help:</strong> Use the built-in help system (?) for guidance on any feature
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default SuccessStep;
