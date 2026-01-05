import React, { useState, useEffect } from 'react';
import './WelcomeStep.css';

/**
 * WelcomeStep Component
 * 
 * Enhanced welcome experience for StoryForge AI onboarding
 * Features:
 * - Interactive value proposition
 * - Animated feature showcase
 * - User type detection and personalization
 * - Quick start options
 * - Accessibility compliant
 */
function WelcomeStep({ 
  onContinue, 
  onQuickStart,
  theme = 'gradient',
  showAnimation = true,
  className = '' 
}) {
  const [selectedUserType, setSelectedUserType] = useState(null);
  const [currentFeature, setCurrentFeature] = useState(0);
  const [hasInteracted, setHasInteracted] = useState(false);

  const userTypes = [
    {
      id: 'writer',
      title: 'Creative Writer',
      description: 'Looking to enhance your storytelling with AI assistance',
      icon: '✍️',
      features: ['Character development', 'Plot assistance', 'Dialogue enhancement'],
      estimatedTime: '5-8 minutes'
    },
    {
      id: 'educator',
      title: 'Educator',
      description: 'Teaching creative writing or using stories for education',
      icon: '🎓',
      features: ['Educational templates', 'Student collaboration', 'Learning objectives'],
      estimatedTime: '3-5 minutes'
    },
    {
      id: 'developer',
      title: 'Developer',
      description: 'Exploring AI capabilities or integrating story generation',
      icon: '👨‍💻',
      features: ['API access', 'Technical documentation', 'Integration examples'],
      estimatedTime: '10-15 minutes'
    },
    {
      id: 'enthusiast',
      title: 'Story Enthusiast',
      description: 'Just want to create and enjoy interactive stories',
      icon: '📚',
      features: ['Quick start templates', 'Guided creation', 'Easy sharing'],
      estimatedTime: '2-4 minutes'
    }
  ];

  const features = [
    {
      icon: '🎭',
      title: 'Dynamic Characters',
      description: 'AI-powered characters with unique personalities, memories, and decision-making capabilities',
      highlight: 'Each character thinks independently and reacts authentically to story events'
    },
    {
      icon: '📖',
      title: 'Interactive Stories',
      description: 'Stories that evolve and adapt based on character choices and player interactions',
      highlight: 'No two playthroughs are exactly the same - stories grow organically'
    },
    {
      icon: '🎨',
      title: 'Rich Narratives',
      description: 'Professional-quality storytelling across multiple genres and themes',
      highlight: 'From sci-fi adventures to romantic comedies - unlimited creative possibilities'
    },
    {
      icon: '⚡',
      title: 'Real-Time Generation',
      description: 'Instant story generation and character responses powered by advanced AI',
      highlight: 'Watch your stories come to life in real-time with minimal waiting'
    }
  ];

  // Auto-rotate features for showcase
  useEffect(() => {
    if (!showAnimation) return;

    const interval = setInterval(() => {
      setCurrentFeature(prev => (prev + 1) % features.length);
    }, 4000);

    return () => clearInterval(interval);
  }, [features.length, showAnimation]);

  const handleUserTypeSelection = (userType) => {
    setSelectedUserType(userType);
    setHasInteracted(true);
  };

  const handleGetStarted = () => {
    const userPreferences = {
      userType: selectedUserType,
      estimatedTime: selectedUserType?.estimatedTime || '5-8 minutes',
      features: selectedUserType?.features || [],
      hasInteracted
    };

    onContinue?.(userPreferences);
  };

  const handleQuickStart = () => {
    const quickStartPreferences = {
      userType: { id: 'quick', title: 'Quick Start' },
      estimatedTime: '2-3 minutes',
      features: ['Demo story', 'Basic setup'],
      hasInteracted: true,
      quickStart: true
    };

    onQuickStart?.(quickStartPreferences);
  };

  return (
    <div className={`welcome-step ${theme} ${className}`}>
      {/* Hero Section */}
      <div className="welcome-hero">
        <div className="hero-content">
          <h1 className="hero-title">
            Welcome to <span className="brand-highlight">StoryForge AI</span>
          </h1>
          <p className="hero-subtitle">
            Create immersive, interactive stories where AI-powered characters 
            think, feel, and make decisions that shape your narrative
          </p>
        </div>
        
        <div className="hero-visual">
          <div className="floating-elements">
            <div className="floating-char char-1">🎭</div>
            <div className="floating-char char-2">📖</div>
            <div className="floating-char char-3">✨</div>
            <div className="floating-char char-4">🎨</div>
          </div>
        </div>
      </div>

      {/* Feature Showcase */}
      <div className="feature-showcase">
        <h2>What Makes StoryForge AI Special?</h2>
        
        <div className="features-container">
          <div className="feature-display">
            <div className="feature-icon">{features[currentFeature].icon}</div>
            <h3>{features[currentFeature].title}</h3>
            <p className="feature-description">
              {features[currentFeature].description}
            </p>
            <p className="feature-highlight">
              💡 {features[currentFeature].highlight}
            </p>
          </div>

          <div className="feature-indicators">
            {features.map((_, index) => (
              <button
                key={index}
                className={`feature-indicator ${index === currentFeature ? 'active' : ''}`}
                onClick={() => setCurrentFeature(index)}
                aria-label={`Show feature ${index + 1}`}
              />
            ))}
          </div>
        </div>
      </div>

      {/* User Type Selection */}
      <div className="user-type-section">
        <h2>Tell Us About Yourself</h2>
        <p>This helps us customize your experience and show you the most relevant features</p>
        
        <div className="user-types-grid">
          {userTypes.map((type) => (
            <button
              key={type.id}
              className={`user-type-card ${selectedUserType?.id === type.id ? 'selected' : ''}`}
              onClick={() => handleUserTypeSelection(type)}
            >
              <div className="type-icon">{type.icon}</div>
              <h3>{type.title}</h3>
              <p className="type-description">{type.description}</p>
              
              <div className="type-features">
                <h4>Perfect for:</h4>
                <ul>
                  {type.features.map((feature, index) => (
                    <li key={index}>{feature}</li>
                  ))}
                </ul>
              </div>
              
              <div className="type-meta">
                <span className="setup-time">
                  ⏱️ Setup: {type.estimatedTime}
                </span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* What to Expect */}
      <div className="expectations-section">
        <h2>What to Expect</h2>
        
        <div className="expectations-timeline">
          <div className="timeline-item">
            <div className="timeline-icon">1️⃣</div>
            <div className="timeline-content">
              <h3>System Check</h3>
              <p>We'll validate your environment for optimal performance</p>
              <span className="timeline-duration">~1 minute</span>
            </div>
          </div>
          
          <div className="timeline-item">
            <div className="timeline-icon">2️⃣</div>
            <div className="timeline-content">
              <h3>AI Configuration</h3>
              <p>Optionally set up your API key for enhanced AI features</p>
              <span className="timeline-duration">~2 minutes</span>
            </div>
          </div>
          
          <div className="timeline-item">
            <div className="timeline-icon">3️⃣</div>
            <div className="timeline-content">
              <h3>Try Your First Story</h3>
              <p>Experience the magic with a sample interactive story</p>
              <span className="timeline-duration">~3 minutes</span>
            </div>
          </div>
          
          <div className="timeline-item">
            <div className="timeline-icon">4️⃣</div>
            <div className="timeline-content">
              <h3>Start Creating</h3>
              <p>Begin crafting your own unique stories and characters</p>
              <span className="timeline-duration">Unlimited!</span>
            </div>
          </div>
        </div>
      </div>

      {/* Call to Action */}
      <div className="cta-section">
        <div className="cta-primary">
          <button
            onClick={handleGetStarted}
            className="btn-primary btn-large"
            disabled={!selectedUserType}
          >
            <span>Get Started</span>
            <span className="btn-arrow">→</span>
          </button>
          
          {selectedUserType && (
            <p className="cta-help-text">
              Estimated setup time: {selectedUserType.estimatedTime}
            </p>
          )}
        </div>

        <div className="cta-alternative">
          <p>In a hurry?</p>
          <button
            onClick={handleQuickStart}
            className="btn-secondary"
          >
            Quick Demo (2 min)
          </button>
        </div>
      </div>

      {/* Trust Indicators */}
      <div className="trust-section">
        <div className="trust-indicators">
          <div className="trust-item">
            <span className="trust-icon">🔒</span>
            <span>Your data stays private</span>
          </div>
          <div className="trust-item">
            <span className="trust-icon">⚡</span>
            <span>Works offline</span>
          </div>
          <div className="trust-item">
            <span className="trust-icon">🆓</span>
            <span>Free to use</span>
          </div>
          <div className="trust-item">
            <span className="trust-icon">🌐</span>
            <span>Open source</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default WelcomeStep;
