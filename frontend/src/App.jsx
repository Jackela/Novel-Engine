import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import axios from 'axios';
import CharacterSelection from './components/CharacterSelection.jsx';
import CharacterCreation from './components/CharacterCreation.jsx';
import TestCharacterSelection from './components/TestCharacterSelection.jsx';
import SimpleCharacterSelection from './components/SimpleCharacterSelection.jsx';
import EmergentDashboard from './components/EmergentDashboard';
import './styles/design-system.css';
import './App.css';

// Home component - Application dashboard providing users with system status and navigation
function Home() {
  const [backendStatus, setBackendStatus] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchBackendHealth = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const response = await axios.get('http://localhost:8000/health', {
          timeout: 5000, // 5 second timeout protection for network requests
        });
        
        setBackendStatus(response.data.message || response.data.status || 'Backend is healthy');
        setLoading(false);
      } catch (err) {
        console.error('Error connecting to backend:', err);
        
        if (err.code === 'ECONNABORTED') {
          setError('Request timeout - Backend may be slow to respond');
        } else if (err.response) {
          setError(`Backend error: ${err.response.status} - ${err.response.statusText}`);
        } else if (err.request) {
          setError('Cannot connect to backend - Please ensure the server is running on http://localhost:8000');
        } else {
          setError('An unexpected error occurred');
        }
        
        setLoading(false);
      }
    };

    fetchBackendHealth();
  }, []);

  const refreshStatus = () => {
    setLoading(true);
    setError(null);
    
    const fetchHealth = async () => {
      try {
        const response = await axios.get('http://localhost:8000/health', {
          timeout: 5000,
        });
        
        setBackendStatus(response.data.message || response.data.status || 'Backend is healthy');
        setLoading(false);
      } catch (err) {
        console.error('Error connecting to backend:', err);
        
        if (err.code === 'ECONNABORTED') {
          setError('Request timeout - Backend may be slow to respond');
        } else if (err.response) {
          setError(`Backend error: ${err.response.status} - ${err.response.statusText}`);
        } else if (err.request) {
          setError('Cannot connect to backend - Please ensure the server is running on http://localhost:8000');
        } else {
          setError('An unexpected error occurred');
        }
        
        setLoading(false);
      }
    };

    fetchHealth();
  };

  return (
    <div className="App">
      {/* Skip Link for Accessibility */}
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      <header className="app-header">
        <h1>StoryForge AI - Interactive Story Engine</h1>
        <p className="app-subtitle">AI-Powered Narrative Generation Platform</p>
      </header>

      <main className="app-main" id="main-content">
        <div className="status-container">
          <h2>Backend Connection Status</h2>
          
          {loading && (
            <div className="status-loading">
              <div className="loading-spinner"></div>
              <p>Connecting to backend...</p>
            </div>
          )}

          {error && (
            <div className="status-error">
              <h3>Connection Error</h3>
              <p>{error}</p>
              <button onClick={refreshStatus} className="retry-button">
                Retry Connection
              </button>
            </div>
          )}

          {!loading && !error && backendStatus && (
            <div className="status-success">
              <h3>Backend Status: {backendStatus}</h3>
              <p className="connection-info">
                Successfully connected to FastAPI backend at http://localhost:8000
              </p>
              <button onClick={refreshStatus} className="refresh-button">
                Refresh Status
              </button>
            </div>
          )}
        </div>

        {!loading && !error && (
          <div className="simulator-info">
            <h2>Simulator Information</h2>
            <div className="info-grid">
              <div className="info-card">
                <h4>Frontend</h4>
                <p>React 19 with Vite</p>
                <p>Status: Active</p>
              </div>
              <div className="info-card">
                <h4>Backend</h4>
                <p>FastAPI Server</p>
                <p>Status: Connected</p>
              </div>
              <div className="info-card">
                <h4>Integration</h4>
                <p>REST API via Axios</p>
                <p>Status: Operational</p>
              </div>
            </div>
            
            <div style={{ textAlign: 'center', marginTop: '2rem' }}>
              <Link to="/character-selection" className="nav-button">
                Start Character Selection
              </Link>
            </div>
          </div>
        )}
      </main>

      <footer className="app-footer">
        <p>StoryForge AI Interactive Story Engine - Web Interface</p>
      </footer>
    </div>
  );
}

// Main App component with routing - Managing navigation paths and user interface flow
function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<EmergentDashboard />} />
        <Route path="/home-old" element={<Home />} />
        <Route path="/character-selection" element={<SimpleCharacterSelection />} />
        <Route path="/character-creation" element={<CharacterCreation />} />
      </Routes>
    </Router>
  );
}

export default App;
