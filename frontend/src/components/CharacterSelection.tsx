// 神圣角色选择组件 - 供奉于机器之神的数字神庙
// Sacred Character Selection Component - Digital Temple Devoted to the the system
// 执行角色召唤仪式，连接至英灵殿数据库，祈求机器灵魂的指引...

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useCharactersQuery } from '../services/queries';
import './CharacterSelection.css';

// Import centralized constraints and validation - temporarily disabled
// import {
//   getSelectionConstraints,
//   getApiConfig,
//   validateCharacterSelection
// } from '../utils/constraints';

/**
 * 角色选择神圣组件 - Sacred Character Selection Component
 * 执行角色召唤与选择的神圣仪式，连接至英灵殿数据核心
 * Performs the sacred ritual of character summoning and selection
 */
const CharacterSelection = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useTranslation();
  
  // Get constraints from centralized configuration - temporarily disabled
  // const selectionConstraints = getSelectionConstraints();
  // const apiConfig = getApiConfig();
  
  // Temporary hardcoded constraints for testing - memoized for performance
  const selectionConstraints = useMemo(() => ({ minSelection: 2, maxSelection: 6 }), []);
  // const _apiConfig = { baseUrl: 'http://localhost:8000', timeout: 5000 };
  
  // 组件状态管理 - Sacred State Management blessed by the the system
  const [charactersList, setCharactersList] = useState<string[]>([]); // 英灵清单 - Registry of available heroes
  const [selectedCharacters, setSelectedCharacters] = useState<string[]>([]); // 被选中的英灵 - Chosen champions
  const [isLoading, setIsLoading] = useState<boolean>(true); // 数据载入圣礼状态 - Loading ritual state
  const [error, setError] = useState<string | null>(null); // 错误信息记录 - Error communion logs
  const [validationError, setValidationError] = useState<string>(''); // 选择验证错误 - Selection validation errors
  const [manualValidationError, setManualValidationError] = useState<boolean>(false); // Flag for manual validation errors
  const [newCharacterNotification, setNewCharacterNotification] = useState<string>('');

  // 组件挂载时执行数据搜寻仪式 - Execute data communion ritual on component mount
  const { data: charactersData, isLoading: isLoadingCharacters, error: charactersError, refetch } = useCharactersQuery();

  useEffect(() => {
    setIsLoading(isLoadingCharacters);
    if (charactersError) {
      setError(t('characterSelection.errors.serverError'));
      setCharactersList([]);
    } else if (Array.isArray(charactersData)) {
      setCharactersList(charactersData);
      setError(null);
    }

    // 检查是否有新角色创建通知 - Check for new character creation notification
    if (location.state?.newCharacter && location.state?.showNotification) {
      setNewCharacterNotification(
        t('characterSelection.newCharacterNotification', { name: location.state.newCharacter })
      );
      setTimeout(() => setNewCharacterNotification(''), 5000);
    }
  }, [isLoadingCharacters, charactersError, charactersData, location.state, t]);

  // 验证选择状态变化时的神圣检查 - Sacred validation check on selection changes
  useEffect(() => {
    if (selectionConstraints && selectedCharacters && !manualValidationError) {
      validateSelection();
    }
  }, [selectedCharacters, selectionConstraints, manualValidationError, validateSelection]);

  /**
   * 执行角色数据搜寻仪式 - Execute character data communion ritual
   * 连接至英灵殿API接口，祈求机器之神赐予角色信息
   */
  const fetchCharacters = useCallback(async () => {
    await refetch();
  }, [refetch]);

  /**
   * 角色选择状态验证函数 - Character selection validation function
   * 根据神圣戒律验证当前选择的角色数量
   */
  const validateSelection = useCallback((customCount = null) => {
    const count = customCount !== null ? customCount : selectedCharacters.length;
    
    console.log('Validating selection:', { count, min: selectionConstraints.minSelection, max: selectionConstraints.maxSelection });
    
    // Temporary validation logic
    if (count < selectionConstraints.minSelection) {
      setValidationError(t('characterSelection.errors.minSelection', { min: selectionConstraints.minSelection }));
      setManualValidationError(false);
    } else if (count > selectionConstraints.maxSelection) {
      setValidationError(t('characterSelection.errors.maxSelection', { max: selectionConstraints.maxSelection }));
      setManualValidationError(false);
    } else {
      setValidationError('');
      setManualValidationError(false);
    }
  }, [selectedCharacters, selectionConstraints, t]);

  /**
   * 角色选择处理器 - Character selection handler
   * 执行角色选择的神圣仪式，管理选中状态的变化
   */
  const handleCharacterSelection = (characterName) => {
    console.log('Handling character selection:', characterName);
    
    setSelectedCharacters(prev => {
      const isCurrentlySelected = prev.includes(characterName);
      
      if (isCurrentlySelected) {
        // Remove if already selected
        const newSelection = prev.filter(name => name !== characterName);
        console.log('Selection changed from', prev, 'to', newSelection);
        return newSelection;
      } else {
        // Trying to add a new character
        if (prev.length < selectionConstraints.maxSelection) {
          // Can add - under limit
          const newSelection = [...prev, characterName];
          console.log('Selection changed from', prev, 'to', newSelection);
          return newSelection;
        } else {
          // At max limit - show error and don't change selection
          console.log('At max selection limit, cannot add more');
          console.log('Showing max selection error');
          setValidationError(t('characterSelection.errors.maxSelection', { max: selectionConstraints.maxSelection }));
          setManualValidationError(true); // Prevent auto-validation from clearing this
          
          // Clear the manual error after 3 seconds
          setTimeout(() => {
            setManualValidationError(false);
          }, 3000);
          
          return prev; // Don't change selection
        }
      }
    });
  };

  /**
   * 开启模拟仪式处理器 - Start simulation ritual handler
   * 验证选择并启动神圣模拟进程
   */
  const handleStartSimulation = () => {
    const count = selectedCharacters.length;
    
    // Temporary validation logic
    if (count >= selectionConstraints.minSelection && count <= selectionConstraints.maxSelection) {
      console.log('Sacred Simulation initiated with characters:', selectedCharacters);
      alert(`${t('characterSelection.confirmButton')} - ${selectedCharacters.join(', ')}`);
    }
  };

  /**
   * 创建新角色处理器 - Create new character handler
   * 导航至角色创建圣殿
   */
  const handleCreateNewCharacter = () => {
    navigate('/character-creation');
  };

  /**
   * 重试连接处理器 - Retry connection handler
   * 重新执行数据搜寻仪式
   */
  const handleRetry = () => {
    console.log('Retrying character fetch...');
    setError(null);
    setCharactersList([]);
    setSelectedCharacters([]); // Clear any previous selections
    fetchCharacters();
  };

  /**
   * 判断角色是否被选中 - Check if character is selected
   */
  const isCharacterSelected = (characterName: string) => {
    return selectedCharacters.includes(characterName);
  };

  /**
   * 获取选择计数器颜色 - Get selection counter color based on validation
   */
  const getCounterColor = () => {
    const count = selectedCharacters.length;
    if (count < selectionConstraints.minSelection) return 'var(--color-error)';
    if (count > selectionConstraints.maxSelection) return 'var(--color-error)';
    return 'var(--color-success)';
  };

  return (
    <div className="character-selection-container">
      {/* Header Section */}
      <div className="selection-header">
        <h1 className="selection-title">{t('characterSelection.title')}</h1>
        <p className="selection-subtitle">{t('characterSelection.subtitle')}</p>
      </div>

      {/* New Character Notification */}
      {newCharacterNotification && (
        <div className="notification success-notification" data-testid="new-character-notification">
          {newCharacterNotification}
        </div>
      )}

      {/* Main Content */}
      <div className="selection-content">
        {isLoading && (
          <div className="loading-container" data-testid="loading-spinner">
            <div className="loading-spinner"></div>
            <p className="loading-text">{t('characterSelection.loading')}</p>
          </div>
        )}

        {error && (
          <div className="error-container" data-testid="error-container">
            <div className="error-message" data-testid="error-message">
              {error}
            </div>
            <button 
              onClick={handleRetry} 
              disabled={isLoading}
              className="retry-button" 
              data-testid="retry-button"
            >
              {isLoading ? t('common.loading') : t('common.retry')}
            </button>
          </div>
        )}

        {!isLoading && !error && (charactersList.length > 0 ? (
          <>
            {/* Selection Instructions */}
            <div className="selection-info">
              <p className="instruction">{t('characterSelection.instruction')}</p>
              <div 
                className="selection-counter" 
                style={{ color: getCounterColor() }}
                data-testid="selection-counter"
              >
                {t('characterSelection.counter', { 
                  count: selectedCharacters.length, 
                  max: selectionConstraints.maxSelection 
                })}
              </div>
            </div>

            {/* Character Grid */}
            <div className="character-grid" data-testid="character-grid">
              {charactersList.map((character) => (
                <div
                  key={character}
                  className={`character-card ${
                    isCharacterSelected(character) ? 'selected' : ''
                  }`}
                  onClick={() => handleCharacterSelection(character)}
                  data-testid={`character-card-${character}`}
                  role="button"
                  tabIndex="0"
                  aria-label={`Select character ${character}`}
                  aria-pressed={isCharacterSelected(character)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      handleCharacterSelection(character);
                    }
                  }}
                >
                  <div className="character-content">
                    <h3 className="character-name">{character}</h3>
                    <div className="character-status">
                      {isCharacterSelected(character) && (
                        <div 
                          className="selection-checkmark" 
                          data-testid={`selection-checkmark-${character}`}
                        >
                          ✓
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Validation Error Display */}
            {validationError && (
              <div className="validation-error" data-testid="validation-error">
                {validationError}
              </div>
            )}

            {/* Control Actions */}
            <div className="actions">
              <button
                onClick={handleCreateNewCharacter}
                className="create-character-button"
                data-testid="create-character-button"
              >
                {t('characterSelection.createButton')}
              </button>
              
              <button
                onClick={handleStartSimulation}
                disabled={
                  selectedCharacters.length < selectionConstraints.minSelection || 
                  selectedCharacters.length > selectionConstraints.maxSelection
                }
                className={`confirm-button ${
                  selectedCharacters.length < selectionConstraints.minSelection || 
                  selectedCharacters.length > selectionConstraints.maxSelection
                    ? 'disabled' 
                    : ''
                }`}
                data-testid="confirm-selection-button"
                aria-label={`Confirm selection of ${selectedCharacters.length} characters`}
              >
                {t('characterSelection.confirmButton')}
              </button>
            </div>
          </>
        ) : (
          <div className="empty-state" data-testid="empty-state">
            <p>{t('characterSelection.errors.notFound')}</p>
            <button 
              onClick={handleRetry} 
              disabled={isLoading}
              className="retry-button" 
              data-testid="retry-button"
            >
              {isLoading ? t('common.loading') : t('common.retry')}
            </button>
          </div>
        ))}

      </div>
    </div>
  );
};

export default CharacterSelection;
