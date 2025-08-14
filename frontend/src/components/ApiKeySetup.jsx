import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './ApiKeySetup.css';

/**
 * ApiKeySetup Component
 * 
 * Provides a user-friendly interface for configuring Gemini API keys
 * Features:
 * - Visual API key validation
 * - Step-by-step setup guidance  
 * - Secure local storage
 * - Demo mode fallback
 * - Clear error messaging
 */
function ApiKeySetup({ onConfigured, allowSkip = true }) {
  const [apiKey, setApiKey] = useState('');
  const [status, setStatus] = useState('unconfigured'); // unconfigured, testing, valid, invalid, demo
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showInstructions, setShowInstructions] = useState(false);

  // Load existing API key from localStorage on component mount
  useEffect(() => {
    const savedKey = localStorage.getItem('storyforge_api_key');
    if (savedKey) {
      setApiKey(savedKey);
      setStatus('configured');
    }
  }, []);

  /**
   * Test API key validity with backend
   */
  const testApiKey = async (keyToTest) => {
    try {
      setIsLoading(true);
      setError('');
      
      const response = await axios.post('/api/test-gemini-key', {
        apiKey: keyToTest
      }, {
        timeout: 10000 // 10 second timeout
      });

      if (response.data.valid) {
        return { valid: true, model: response.data.model || 'gemini-pro' };
      } else {
        return { valid: false, error: response.data.error || 'Invalid API key' };
      }
    } catch (error) {
      console.error('API key test failed:', error);
      
      if (error.code === 'ECONNABORTED') {
        return { valid: false, error: 'Request timeout - please try again' };
      } else if (error.response?.status === 401) {
        return { valid: false, error: 'Invalid API key' };
      } else if (error.response?.status === 429) {
        return { valid: false, error: 'Rate limit exceeded - please wait and try again' };
      } else {
        return { valid: false, error: 'Unable to validate API key - backend may be unavailable' };
      }
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Save and validate API key
   */
  const handleSaveKey = async () => {
    if (!apiKey || apiKey.trim().length < 10) {
      setError('Please enter a valid API key');
      setStatus('invalid');
      return;
    }

    setStatus('testing');
    const result = await testApiKey(apiKey.trim());
    
    if (result.valid) {
      localStorage.setItem('storyforge_api_key', apiKey.trim());
      setStatus('valid');
      setError('');
      
      // Notify parent component
      if (onConfigured) {
        onConfigured({ 
          hasApiKey: true, 
          model: result.model,
          source: 'user_configured'
        });
      }
    } else {
      setStatus('invalid');
      setError(result.error);
    }
  };

  /**
   * Clear saved API key
   */
  const handleClearKey = () => {
    setApiKey('');
    setStatus('unconfigured');
    setError('');
    localStorage.removeItem('storyforge_api_key');
  };

  /**
   * Continue without API key (demo mode)
   */
  const handleSkip = () => {
    setStatus('demo');
    if (onConfigured) {
      onConfigured({ 
        hasApiKey: false, 
        mode: 'demo',
        source: 'user_skipped'
      });
    }
  };

  /**
   * Handle paste event for better UX
   */
  const handlePaste = (e) => {
    // Clear any existing errors when user pastes
    if (error) {
      setError('');
      setStatus('unconfigured');
    }
  };

  return (
    <div className="api-key-setup">
      <div className="setup-header">
        <h3>🔑 Configure AI Features</h3>
        <p className="setup-description">
          Add your Gemini API key to enable advanced character AI and enhanced storytelling.
          {allowSkip && " This step is optional - you can try the system without it."}
        </p>
      </div>

      {status === 'valid' && (
        <div className="status-card success">
          <div className="status-icon">✅</div>
          <div className="status-content">
            <h4>API Key Configured</h4>
            <p>Your Gemini API key is working correctly. Enhanced AI features are enabled.</p>
            <button onClick={handleClearKey} className="btn-secondary">
              Change API Key
            </button>
          </div>
        </div>
      )}

      {status === 'demo' && (
        <div className="status-card info">
          <div className="status-icon">🎭</div>
          <div className="status-content">
            <h4>Demo Mode Active</h4>
            <p>You're using StoryForge with algorithmic character decisions. Add an API key anytime for AI-enhanced features.</p>
          </div>
        </div>
      )}

      {(status === 'unconfigured' || status === 'invalid' || status === 'testing') && (
        <div className="setup-form">
          <div className="input-group">
            <label htmlFor="api-key-input">Gemini API Key</label>
            <div className="input-container">
              <input
                id="api-key-input"
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                onPaste={handlePaste}
                placeholder="AIzaSy... (paste your Gemini API key here)"
                className={`api-key-input ${status === 'invalid' ? 'error' : ''}`}
                disabled={isLoading}
              />
              <button
                onClick={handleSaveKey}
                disabled={!apiKey || isLoading}
                className="btn-primary"
              >
                {isLoading ? (
                  <>
                    <span className="spinner"></span>
                    Testing...
                  </>
                ) : status === 'testing' ? (
                  'Validating...'
                ) : (
                  'Test & Save'
                )}
              </button>
            </div>
          </div>

          {error && (
            <div className="error-message">
              <span className="error-icon">⚠️</span>
              {error}
            </div>
          )}

          {status === 'testing' && (
            <div className="testing-status">
              <div className="progress-bar">
                <div className="progress-fill"></div>
              </div>
              <p>Validating your API key with Google's servers...</p>
            </div>
          )}
        </div>
      )}

      <div className="setup-instructions">
        <button
          onClick={() => setShowInstructions(!showInstructions)}
          className="instructions-toggle"
        >
          {showInstructions ? '👆 Hide' : '📖 Show'} setup instructions
        </button>

        {showInstructions && (
          <div className="instructions-content">
            <h4>How to get your Gemini API key:</h4>
            <ol>
              <li>
                <strong>Visit Google AI Studio:</strong>
                <br />
                <a href="https://aistudio.google.com/" target="_blank" rel="noopener noreferrer">
                  https://aistudio.google.com/
                </a>
              </li>
              <li><strong>Sign in</strong> with your Google account (or create one)</li>
              <li><strong>Click "Get API Key"</strong> in the sidebar</li>
              <li><strong>Create new API key</strong> (or use an existing one)</li>
              <li><strong>Copy the key</strong> (it starts with "AIzaSy...")</li>
              <li><strong>Paste it above</strong> and click "Test & Save"</li>
            </ol>

            <div className="tips">
              <h4>💡 Tips:</h4>
              <ul>
                <li>API keys are <strong>free</strong> for typical usage</li>
                <li>Your key is stored locally and never shared</li>
                <li>You can change or remove it anytime</li>
                <li>Without an API key, characters use algorithmic decisions</li>
              </ul>
            </div>

            <div className="security-note">
              <h4>🔒 Security:</h4>
              <p>
                Your API key is stored securely in your browser and sent only to Google's servers
                for story generation. We never store or transmit your key to other services.
              </p>
            </div>
          </div>
        )}
      </div>

      {allowSkip && status !== 'valid' && status !== 'demo' && (
        <div className="skip-section">
          <button onClick={handleSkip} className="btn-secondary skip-btn">
            Skip for now - Try without AI enhancement
          </button>
          <p className="skip-note">
            You can add your API key later from the settings menu
          </p>
        </div>
      )}
    </div>
  );
}

export default ApiKeySetup;