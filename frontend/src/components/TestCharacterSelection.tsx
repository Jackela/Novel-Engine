// 简化的角色选择组件用于问题诊断
import { logger } from '../../services/logging/LoggerFactory';
import React, { useState, useEffect } from 'react';
import { useCharactersQuery } from '../services/queries';

const TestCharacterSelection = () => {
  logger.info('TestCharacterSelection component mounted');
  
  const [characters, setCharacters] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const { data: charactersData, isLoading, error: charactersError } = useCharactersQuery();

  useEffect(() => {
    if (Array.isArray(charactersData)) setCharacters(charactersData);
    setLoading(isLoading);
    if (charactersError) setError(String(charactersError));
  }, [charactersData, isLoading, charactersError]);

  logger.info('Rendering component - loading:', loading, 'error:', error, 'characters:', characters);

  if (loading) {
    return (
      <div style={{ padding: '20px', color: 'var(--color-text-primary)', backgroundColor: 'var(--color-bg-tertiary)' }}>
        <h1>Loading characters...</h1>
        <p>Please wait while we fetch character data from the API.</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '20px', color: 'var(--color-error)', backgroundColor: 'var(--color-bg-tertiary)' }}>
        <h1>Error occurred</h1>
        <p>Error: {error}</p>
        <button onClick={() => window.location.reload()}>Reload Page</button>
      </div>
    );
  }

  return (
    <div style={{ padding: '20px', color: 'var(--color-text-primary)', backgroundColor: 'var(--color-bg-tertiary)', minHeight: '100vh' }}>
      <h1>Test Character Selection</h1>
      <p>Successfully loaded {characters.length} characters:</p>
      
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '20px', marginTop: '20px' }}>
        {characters.map((character, index) => (
          <div 
            key={character} 
            style={{ 
              border: '2px solid var(--color-primary-500)', 
              borderRadius: '8px', 
              padding: '15px', 
              backgroundColor: 'var(--color-bg-elevated)',
              cursor: 'pointer'
            }}
          >
            <h3 style={{ margin: '0 0 10px 0', color: 'var(--color-primary-500)' }}>
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
            backgroundColor: 'var(--color-primary-500)', 
            color: 'var(--color-bg-primary)', 
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
