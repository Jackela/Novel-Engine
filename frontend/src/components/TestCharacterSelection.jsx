// 简化的角色选择组件用于问题诊断
import React, { useState, useEffect } from 'react';
import axios from 'axios';

const TestCharacterSelection = () => {
  console.log('TestCharacterSelection component mounted');
  
  const [characters, setCharacters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    console.log('useEffect triggered - fetching characters');
    
    const fetchCharacters = async () => {
      try {
        console.log('Making API call to http://localhost:8000/characters');
        const response = await axios.get('http://localhost:8000/characters');
        console.log('API response received:', response.data);
        
        if (response.data && response.data.characters) {
          setCharacters(response.data.characters);
        } else {
          console.error('Unexpected API response format:', response.data);
          setError('Unexpected API response format');
        }
      } catch (err) {
        console.error('Error fetching characters:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchCharacters();
  }, []);

  console.log('Rendering component - loading:', loading, 'error:', error, 'characters:', characters);

  if (loading) {
    return (
      <div style={{ padding: '20px', color: 'white', backgroundColor: '#1a1a2e' }}>
        <h1>Loading characters...</h1>
        <p>Please wait while we fetch character data from the API.</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '20px', color: 'red', backgroundColor: '#1a1a2e' }}>
        <h1>Error occurred</h1>
        <p>Error: {error}</p>
        <button onClick={() => window.location.reload()}>Reload Page</button>
      </div>
    );
  }

  return (
    <div style={{ padding: '20px', color: 'white', backgroundColor: '#1a1a2e', minHeight: '100vh' }}>
      <h1>Test Character Selection</h1>
      <p>Successfully loaded {characters.length} characters:</p>
      
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '20px', marginTop: '20px' }}>
        {characters.map((character, index) => (
          <div 
            key={character} 
            style={{ 
              border: '2px solid #ffd700', 
              borderRadius: '8px', 
              padding: '15px', 
              backgroundColor: 'rgba(0,0,0,0.3)',
              cursor: 'pointer'
            }}
          >
            <h3 style={{ margin: '0 0 10px 0', color: '#ffd700' }}>
              Character {index + 1}
            </h3>
            <p style={{ margin: '0', fontSize: '18px' }}>{character}</p>
          </div>
        ))}
      </div>
      
      <div style={{ marginTop: '30px' }}>
        <button 
          style={{ 
            padding: '10px 20px', 
            backgroundColor: '#ffd700', 
            color: '#1a1a2e', 
            border: 'none', 
            borderRadius: '5px',
            fontSize: '16px',
            fontWeight: 'bold',
            cursor: 'pointer'
          }}
          onClick={() => alert('Test button clicked!')}
        >
          Test Button
        </button>
      </div>
    </div>
  );
};

export default TestCharacterSelection;