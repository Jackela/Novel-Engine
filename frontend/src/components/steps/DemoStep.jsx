import React, { useState, useEffect, useCallback } from 'react';
import { SAMPLE_STORIES, STORY_UTILS } from '../../data/sampleStories';
import './DemoStep.css';

/**
 * DemoStep Component - Enhanced
 * 
 * Interactive story demonstration with enhanced UX
 * Features:
 * - Rich story selection interface
 * - Real-time story generation preview
 * - Character interaction simulation
 * - Progressive story revelation
 * - API vs algorithmic mode comparison
 * - Interactive story timeline
 * - Accessibility compliant
 */
function DemoStep({
  onStoryGenerated,
  onContinue,
  apiUrl,
  hasApiKey = false,
  autoSelectStory = false,
  showComparison = true,
  theme = 'gradient',
  className = ''
}) {
  // Component state
  const [currentPhase, setCurrentPhase] = useState('selection'); // selection, generation, preview, completed
  const [selectedStory, setSelectedStory] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedStory, setGeneratedStory] = useState(null);
  const [currentTurn, setCurrentTurn] = useState(0);
  const [showFullStory, setShowFullStory] = useState(false);
  const [generationProgress, setGenerationProgress] = useState(0);
  const [storyMode, setStoryMode] = useState(hasApiKey ? 'ai_enhanced' : 'algorithmic');
  const [hasInteracted, setHasInteracted] = useState(false);

  // Sample stories with enhanced metadata
  const enhancedStories = Object.values(SAMPLE_STORIES).map(story => ({
    ...story,
    difficulty: getDifficultyLevel(story),
    features: getStoryFeatures(story),
    estimatedPlayTime: getEstimatedPlayTime(story)
  }));

  // Auto-select first story if requested
  useEffect(() => {
    if (autoSelectStory && enhancedStories.length > 0) {
      handleStorySelection(enhancedStories[0]);
    }
  }, [autoSelectStory, enhancedStories]);

  // Auto-advance turns during preview
  useEffect(() => {
    if (currentPhase === 'preview' && generatedStory && !showFullStory) {
      const maxTurns = Math.min(3, generatedStory.sampleTurns.length);
      if (currentTurn < maxTurns - 1) {
        const timer = setTimeout(() => {
          setCurrentTurn(prev => prev + 1);
        }, 3000);
        return () => clearTimeout(timer);
      }
    }
  }, [currentTurn, currentPhase, generatedStory, showFullStory]);

  /**
   * Get difficulty level for story
   */
  function getDifficultyLevel(story) {
    const factors = {
      characterCount: story.characters.length,
      complexity: story.complexity === 'High' ? 3 : story.complexity === 'Medium' ? 2 : 1,
      genreComplexity: ['Science Fiction', 'Fantasy'].includes(story.genre) ? 2 : 1
    };
    
    const totalScore = factors.characterCount + factors.complexity + factors.genreComplexity;
    return totalScore >= 8 ? 'Advanced' : totalScore >= 5 ? 'Intermediate' : 'Beginner';
  }

  /**
   * Get story features
   */
  function getStoryFeatures(story) {
    const features = ['Interactive Characters'];
    
    if (story.characters.length >= 3) features.push('Multi-Character');
    if (story.complexity === 'High') features.push('Complex Plot');
    if (['Science Fiction', 'Fantasy'].includes(story.genre)) features.push('World Building');
    if (story.characters.some(c => c.personality?.includes('mysterious'))) features.push('Mystery Elements');
    
    return features;
  }

  /**
   * Get estimated play time
   */
  function getEstimatedPlayTime(story) {
    const baseTime = 5; // minutes
    const characterModifier = story.characters.length * 2;
    const complexityModifier = story.complexity === 'High' ? 5 : story.complexity === 'Medium' ? 3 : 0;
    
    return Math.max(3, baseTime + characterModifier + complexityModifier);
  }

  /**
   * Handle story selection
   */
  const handleStorySelection = useCallback((story) => {
    setSelectedStory(story);
    setCurrentPhase('generation');
    setHasInteracted(true);
    
    // Auto-start generation after brief delay
    setTimeout(() => {
      generateStory(story);
    }, 1000);
  }, []);

  /**
   * Generate story with realistic progression
   */
  const generateStory = async (story) => {
    setIsGenerating(true);
    setGenerationProgress(0);
    
    try {
      // Simulate realistic generation phases
      const phases = [
        { name: 'Initializing characters...', duration: 800, progress: 20 },
        { name: 'Building story world...', duration: 1200, progress: 45 },
        { name: 'Generating narrative...', duration: 1000, progress: 70 },
        { name: 'Optimizing interactions...', duration: 800, progress: 90 },
        { name: 'Finalizing story...', duration: 500, progress: 100 }
      ];

      for (const phase of phases) {
        await new Promise(resolve => setTimeout(resolve, phase.duration));
        setGenerationProgress(phase.progress);
      }

      // Create enhanced story data
      const enhancedStory = {
        ...story,
        generatedAt: new Date().toISOString(),
        mode: storyMode,
        sessionId: generateSessionId(),
        metadata: {
          generationTime: phases.reduce((total, phase) => total + phase.duration, 0),
          apiEnhanced: hasApiKey,
          userSelections: { storyId: story.id, mode: storyMode }
        },
        interactiveElements: generateInteractiveElements(story),
        progressiveReveal: true
      };

      setGeneratedStory(enhancedStory);
      setCurrentPhase('preview');
      setCurrentTurn(0);
      
      // Notify parent component
      onStoryGenerated?.(enhancedStory);

    } catch (error) {
      console.error('Story generation failed:', error);
      // Handle error state
    } finally {
      setIsGenerating(false);
    }
  };

  /**
   * Generate session ID
   */
  const generateSessionId = () => {
    return 'demo_' + Date.now().toString(36) + Math.random().toString(36).substr(2);
  };

  /**
   * Generate interactive elements
   */
  const generateInteractiveElements = (story) => {
    return {
      choicePoints: [
        {
          turn: 1,
          question: "How should the characters proceed?",
          options: ["Investigate cautiously", "Take immediate action", "Seek more information"]
        },
        {
          turn: 3,
          question: "What's the group's priority?",
          options: ["Safety first", "Mission completion", "Character relationships"]
        }
      ],
      characterDecisions: story.characters.map(char => ({
        name: char.name,
        personality: char.personality || 'balanced',
        decisionStyle: getDecisionStyle(char)
      }))
    };
  };

  /**
   * Get character decision style
   */
  const getDecisionStyle = (character) => {
    const styles = ['analytical', 'intuitive', 'cautious', 'bold', 'diplomatic'];
    return styles[Math.floor(Math.random() * styles.length)];
  };

  /**
   * Handle mode change
   */
  const handleModeChange = (newMode) => {
    setStoryMode(newMode);
    if (selectedStory && currentPhase === 'generation') {
      generateStory(selectedStory);
    }
  };

  /**
   * Handle continue to next step
   */
  const handleContinue = () => {
    setCurrentPhase('completed');
    onContinue?.({
      storyData: generatedStory,
      userInteractions: {
        hasInteracted,
        selectedStory: selectedStory?.id,
        viewedFullStory: showFullStory,
        currentTurn: currentTurn
      }
    });
  };

  /**
   * Render story selection phase
   */
  const renderStorySelection = () => (
    <div className="story-selection-phase">
      <div className="selection-header">
        <h2>Choose Your Adventure</h2>
        <p>Select a story to experience the magic of AI-powered narrative generation</p>
      </div>

      {showComparison && (
        <div className="mode-selector">
          <h3>Generation Mode</h3>
          <div className="mode-options">
            <button
              className={`mode-option ${storyMode === 'algorithmic' ? 'active' : ''}`}
              onClick={() => handleModeChange('algorithmic')}
            >
              <div className="mode-icon">🎭</div>
              <div className="mode-content">
                <strong>Algorithmic Mode</strong>
                <p>Rule-based character decisions</p>
              </div>
            </button>
            
            <button
              className={`mode-option ${storyMode === 'ai_enhanced' ? 'active' : ''} ${!hasApiKey ? 'disabled' : ''}`}
              onClick={() => hasApiKey && handleModeChange('ai_enhanced')}
              disabled={!hasApiKey}
            >
              <div className="mode-icon">🧠</div>
              <div className="mode-content">
                <strong>AI Enhanced</strong>
                <p>{hasApiKey ? 'Natural language decisions' : 'Requires API key'}</p>
              </div>
            </button>
          </div>
        </div>
      )}

      <div className="stories-grid">
        {enhancedStories.map((story) => (
          <div
            key={story.id}
            className="story-card enhanced"
            onClick={() => handleStorySelection(story)}
          >
            <div className="card-header">
              <div className="story-title">
                <h3>{story.title}</h3>
                <span className="genre-badge">{story.genre}</span>
              </div>
              <div className="difficulty-indicator">
                <span className={`difficulty ${story.difficulty.toLowerCase()}`}>
                  {story.difficulty}
                </span>
              </div>
            </div>

            <div className="story-description">
              <p>{story.description}</p>
            </div>

            <div className="story-features">
              <h4>Features</h4>
              <div className="features-list">
                {story.features.map((feature, index) => (
                  <span key={index} className="feature-tag">{feature}</span>
                ))}
              </div>
            </div>

            <div className="story-characters">
              <h4>Characters ({story.characters.length})</h4>
              <div className="characters-preview">
                {story.characters.slice(0, 3).map((character, index) => (
                  <div key={index} className="character-avatar">
                    <span className="avatar-icon">👤</span>
                    <span className="character-name">{character.name.split(' ')[0]}</span>
                  </div>
                ))}
                {story.characters.length > 3 && (
                  <div className="more-characters">+{story.characters.length - 3}</div>
                )}
              </div>
            </div>

            <div className="story-meta">
              <div className="meta-item">
                <span className="meta-icon">⏱️</span>
                <span>~{story.estimatedPlayTime} min</span>
              </div>
              <div className="meta-item">
                <span className="meta-icon">📊</span>
                <span>{story.complexity}</span>
              </div>
            </div>

            <div className="selection-overlay">
              <div className="selection-content">
                <span className="selection-icon">▶️</span>
                <span>Start This Story</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  /**
   * Render story generation phase
   */
  const renderStoryGeneration = () => (
    <div className="story-generation-phase">
      <div className="generation-header">
        <h2>Generating Your Story</h2>
        <p>Creating an interactive narrative experience with AI-powered characters</p>
      </div>

      <div className="selected-story-preview">
        <div className="preview-header">
          <h3>{selectedStory.title}</h3>
          <span className="generation-mode">{storyMode === 'ai_enhanced' ? '🧠 AI Enhanced' : '🎭 Algorithmic'}</span>
        </div>
        
        <div className="story-summary">
          <p>{selectedStory.description}</p>
        </div>
      </div>

      <div className="generation-progress">
        <div className="progress-header">
          <span className="progress-label">Generation Progress</span>
          <span className="progress-percentage">{generationProgress}%</span>
        </div>
        
        <div className="progress-bar">
          <div 
            className="progress-fill"
            style={{ width: `${generationProgress}%` }}
          />
        </div>
        
        <div className="generation-status">
          <div className="status-indicator">
            <div className="spinner" />
          </div>
          <span>Building your interactive story...</span>
        </div>
      </div>

      <div className="characters-initializing">
        <h4>Initializing Characters</h4>
        <div className="character-grid">
          {selectedStory.characters.map((character, index) => (
            <div key={index} className="character-initializing">
              <div className="character-avatar">
                <span className="avatar-icon">👤</span>
                <div className="initialization-pulse" />
              </div>
              <div className="character-info">
                <strong>{character.name}</strong>
                <span>{character.profession}</span>
              </div>
              <div className="initialization-status">
                <span className="status-icon">⚡</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  /**
   * Render story preview phase
   */
  const renderStoryPreview = () => (
    <div className="story-preview-phase">
      <div className="preview-header">
        <h2>Your Story is Ready!</h2>
        <p>Experience how AI-powered characters make decisions and drive the narrative</p>
      </div>

      <div className="story-info">
        <div className="info-header">
          <h3>{generatedStory.title}</h3>
          <div className="story-badges">
            <span className="mode-badge">{storyMode === 'ai_enhanced' ? '🧠 AI Enhanced' : '🎭 Algorithmic'}</span>
            <span className="status-badge">✨ Generated</span>
          </div>
        </div>
      </div>

      <div className="narrative-preview">
        <div className="preview-controls">
          <button
            className={`preview-mode ${!showFullStory ? 'active' : ''}`}
            onClick={() => setShowFullStory(false)}
          >
            Progressive View
          </button>
          <button
            className={`preview-mode ${showFullStory ? 'active' : ''}`}
            onClick={() => setShowFullStory(true)}
          >
            Full Story
          </button>
        </div>

        <div className="story-content">
          {!showFullStory ? (
            <div className="progressive-narrative">
              <div className="turn-indicator">
                <span>Turn {currentTurn + 1} of {Math.min(3, generatedStory.sampleTurns.length)}</span>
                <div className="turn-progress">
                  {Array.from({ length: Math.min(3, generatedStory.sampleTurns.length) }, (_, i) => (
                    <div key={i} className={`turn-dot ${i <= currentTurn ? 'active' : ''}`} />
                  ))}
                </div>
              </div>

              <div className="current-turn">
                {renderStoryTurn(generatedStory.sampleTurns[currentTurn], currentTurn)}
              </div>

              <div className="turn-controls">
                <button
                  onClick={() => setCurrentTurn(Math.max(0, currentTurn - 1))}
                  disabled={currentTurn === 0}
                  className="turn-nav prev"
                >
                  ← Previous
                </button>
                <button
                  onClick={() => setCurrentTurn(Math.min(generatedStory.sampleTurns.length - 1, currentTurn + 1))}
                  disabled={currentTurn >= Math.min(3, generatedStory.sampleTurns.length) - 1}
                  className="turn-nav next"
                >
                  Next →
                </button>
              </div>
            </div>
          ) : (
            <div className="full-narrative">
              {generatedStory.sampleTurns.slice(0, 3).map((turn, index) => (
                <div key={index} className="story-turn">
                  {renderStoryTurn(turn, index)}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="story-actions">
        <button
          onClick={() => {
            setSelectedStory(null);
            setGeneratedStory(null);
            setCurrentPhase('selection');
            setCurrentTurn(0);
          }}
          className="btn-secondary"
        >
          Try Different Story
        </button>
        
        <button
          onClick={handleContinue}
          className="btn-primary"
        >
          Continue Setup
        </button>
      </div>
    </div>
  );

  /**
   * Render individual story turn
   */
  const renderStoryTurn = (turn, index) => (
    <div className="story-turn-content">
      <div className="narrator-section">
        <div className="narrator-header">
          <span className="narrator-icon">📖</span>
          <span className="narrator-label">Narrator</span>
        </div>
        <p className="narrator-text">{turn.narrator}</p>
      </div>

      <div className="characters-section">
        {Object.entries(turn.characters).map(([characterName, character]) => (
          <div key={characterName} className="character-turn">
            <div className="character-header">
              <div className="character-avatar">
                <span className="avatar-icon">👤</span>
              </div>
              <div className="character-info">
                <strong className="character-name">{characterName}</strong>
                <span className="decision-style">{character.decisionReasoning ? '🧠 AI Decision' : '🎭 Algorithmic'}</span>
              </div>
            </div>
            
            <div className="character-content">
              <div className="dialogue">
                <span className="quote-icon">"</span>
                <p>{character.dialogue}</p>
                <span className="quote-icon">"</span>
              </div>
              
              <div className="action">
                <span className="action-icon">→</span>
                <p><em>{character.action}</em></p>
              </div>

              {character.decisionReasoning && (
                <div className="decision-reasoning">
                  <details>
                    <summary>View AI Reasoning</summary>
                    <p>{character.decisionReasoning}</p>
                  </details>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {generatedStory.interactiveElements?.choicePoints?.find(cp => cp.turn === index) && (
        <div className="choice-point">
          <h4>Story Choice Point</h4>
          <p>{generatedStory.interactiveElements.choicePoints.find(cp => cp.turn === index).question}</p>
          <div className="choice-options">
            {generatedStory.interactiveElements.choicePoints.find(cp => cp.turn === index).options.map((option, i) => (
              <button key={i} className="choice-option" disabled>
                {option}
              </button>
            ))}
          </div>
          <p className="choice-note">
            <em>In the full version, these choices would influence the story direction</em>
          </p>
        </div>
      )}
    </div>
  );

  return (
    <div className={`demo-step ${theme} ${className}`}>
      {currentPhase === 'selection' && renderStorySelection()}
      {currentPhase === 'generation' && renderStoryGeneration()}
      {currentPhase === 'preview' && renderStoryPreview()}
    </div>
  );
}

export default DemoStep;