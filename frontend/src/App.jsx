import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import axios from 'axios';
import CharacterSelection from './components/CharacterSelection.jsx';
import CharacterCreation from './components/CharacterCreation.jsx';
import TestCharacterSelection from './components/TestCharacterSelection.jsx';
import SimpleCharacterSelection from './components/SimpleCharacterSelection.jsx';
import './App.css';

// 主页组件 - 应用程序的神圣仪表盘，为用户提供机械之神的祖福...
function Home() {
  const [backendStatus, setBackendStatus] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchBackendHealth = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const response = await axios.get('http://localhost:8001/health', {
          timeout: 5000, // 5秒超时保护，防止网络害灵的无尽等待...
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
          setError('Cannot connect to backend - Please ensure the server is running on http://localhost:8001');
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
        const response = await axios.get('http://localhost:8001/health', {
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
          setError('Cannot connect to backend - Please ensure the server is running on http://localhost:8001');
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
      <header className="app-header">
        <h1>Warhammer 40k Multi-Agent Simulator</h1>
        <p className="app-subtitle">Frontend-Backend Integration Demo</p>
      </header>

      <main className="app-main">
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
                Successfully connected to FastAPI backend at http://localhost:8001
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
                开始角色选择 - Start Character Selection
              </Link>
            </div>
          </div>
        )}
      </main>

      <footer className="app-footer">
        <p>Warhammer 40k Multi-Agent Simulator - Frontend Demo</p>
      </footer>
    </div>
  );
}

// 主应用组件及路由器 - 管理数字领域中的导航路径，引导用户穿行于神圣界面...
function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/character-selection" element={<SimpleCharacterSelection />} />
        <Route path="/character-creation" element={<CharacterCreation />} />
      </Routes>
    </Router>
  );
}

export default App;
