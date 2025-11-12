// 神圣角色选择组件 - 供奉于机器之神的数字神庙
import { logger } from '../services/logging/LoggerFactory';
// Sacred Character Selection Component - Digital Temple Devoted to the the system
// 执行角色召唤仪式，连接至英灵殿数据库，祈求机器灵魂的指引...

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useCharactersQuery } from '../services/queries';
import { usePerformance } from '../hooks/usePerformance';
import { CharacterCard } from './CharacterCard';
import { SkeletonCard } from './loading';
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
  const [focusedCardIndex, setFocusedCardIndex] = useState<number>(0); // Current focused card for arrow key navigation
  
  // Refs for character cards to enable programmatic focus
  const characterCardRefs = useRef<(HTMLDivElement | null)[]>([]);

  // T052: Performance monitoring for CharacterSelection component
  // Track re-render counts and interaction latency
  usePerformance({
    onMetric: (metric) => {
      logger.info('CharacterSelection performance metric', {
        component: 'CharacterSelection',
        metric: metric.name,
        value: metric.value,
        rating: metric.rating,
      });
    },
    reportToAnalytics: import.meta.env.PROD,
  });

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

  /**
   * 角色选择状态验证函数 - Character selection validation function
   * 根据神圣戒律验证当前选择的角色数量
   */
  const validateSelection = useCallback((customCount = null) => {
    const count = customCount !== null ? customCount : selectedCharacters.length;
    
    logger.info('Validating selection:', { count, min: selectionConstraints.minSelection, max: selectionConstraints.maxSelection });
    
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
  }, [selectedCharacters.length, selectionConstraints.minSelection, selectionConstraints.maxSelection, t]);

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
   * 角色选择处理器 - Character selection handler
   * 执行角色选择的神圣仪式，管理选中状态的变化
   * 
   * Wrapped with useCallback to prevent function recreation on every render
   * This optimization prevents unnecessary re-renders of memoized child components
   */
  const handleCharacterSelection = useCallback((characterName: string) => {
    logger.info('Handling character selection:', characterName);
    logger.info('ARIA interaction: Character selection', { 
      character: characterName, 
      selectionCount: selectedCharacters.length,
      ariaPressed: !selectedCharacters.includes(characterName)
    });
    
    setSelectedCharacters(prev => {
      const isCurrentlySelected = prev.includes(characterName);
      
      if (isCurrentlySelected) {
        // Remove if already selected
        const newSelection = prev.filter(name => name !== characterName);
        logger.info('Selection changed from', prev, 'to', newSelection);
        return newSelection;
      } else {
        // Trying to add a new character
        if (prev.length < selectionConstraints.maxSelection) {
          // Can add - under limit
          const newSelection = [...prev, characterName];
          logger.info('Selection changed from', prev, 'to', newSelection);
          return newSelection;
        } else {
          // At max limit - show error and don't change selection
          logger.info('At max selection limit, cannot add more');
          logger.info('Showing max selection error');
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
  }, [selectionConstraints.maxSelection, t]);

  /**
   * Focus handler for character cards
   * Wrapped with useCallback for performance optimization
   */
  const handleCardFocus = useCallback((index: number) => {
    setFocusedCardIndex(index);
  }, []);

  /**
   * Arrow key navigation handlers for character grid
   * Allows keyboard users to navigate through character cards using arrow keys
   */
  const handleArrowNavigation = useCallback((direction: 'left' | 'right' | 'up' | 'down') => {
    const totalCards = charactersList.length;
    if (totalCards === 0) return;
    
    // Assume 3 columns for grid layout (adjust based on actual CSS grid)
    const columns = 3;
    const rows = Math.ceil(totalCards / columns);
    
    let newIndex = focusedCardIndex;
    
    switch (direction) {
      case 'left':
        newIndex = focusedCardIndex > 0 ? focusedCardIndex - 1 : totalCards - 1;
        break;
      case 'right':
        newIndex = focusedCardIndex < totalCards - 1 ? focusedCardIndex + 1 : 0;
        break;
      case 'up':
        newIndex = focusedCardIndex - columns;
        if (newIndex < 0) {
          // Wrap to bottom row
          const currentColumn = focusedCardIndex % columns;
          newIndex = Math.min(totalCards - 1, (rows - 1) * columns + currentColumn);
        }
        break;
      case 'down':
        newIndex = focusedCardIndex + columns;
        if (newIndex >= totalCards) {
          // Wrap to top row
          const currentColumn = focusedCardIndex % columns;
          newIndex = currentColumn;
        }
        break;
    }
    
    setFocusedCardIndex(newIndex);
    characterCardRefs.current[newIndex]?.focus();
    
    logger.info('Arrow key navigation:', { direction, oldIndex: focusedCardIndex, newIndex });
  }, [charactersList.length, focusedCardIndex]);

  /**
   * Keyboard event handler for character cards
   * Wrapped with useCallback to prevent recreation on every render
   * Uses event.currentTarget.dataset to get character name
   */
  const handleCardKeyDown = useCallback((e: React.KeyboardEvent<HTMLDivElement>) => {
    const character = e.currentTarget.dataset.character;
    if (!character) return;

    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      logger.info('Keyboard selection triggered', { key: e.key, character });
      handleCharacterSelection(character);
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault();
      handleArrowNavigation('left');
    } else if (e.key === 'ArrowRight') {
      e.preventDefault();
      handleArrowNavigation('right');
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      handleArrowNavigation('up');
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      handleArrowNavigation('down');
    }
  }, [handleCharacterSelection, handleArrowNavigation]);

  /**
   * 开启模拟仪式处理器 - Start simulation ritual handler
   * 验证选择并启动神圣模拟进程
   * Wrapped with useCallback for performance optimization
   */
  const handleStartSimulation = useCallback(() => {
    const count = selectedCharacters.length;
    
    // Temporary validation logic
    if (count >= selectionConstraints.minSelection && count <= selectionConstraints.maxSelection) {
      logger.info('Sacred Simulation initiated with characters:', selectedCharacters);
      alert(`${t('characterSelection.confirmButton')} - ${selectedCharacters.join(', ')}`);
    }
  }, [selectedCharacters, selectionConstraints.minSelection, selectionConstraints.maxSelection, t]);

  /**
   * 创建新角色处理器 - Create new character handler
   * 导航至角色创建圣殿
   * Wrapped with useCallback for performance optimization
   */
  const handleCreateNewCharacter = useCallback(() => {
    navigate('/character-creation');
  }, [navigate]);

  /**
   * 重试连接处理器 - Retry connection handler
   * 重新执行数据搜寻仪式
   * Wrapped with useCallback for performance optimization
   */
  const handleRetry = useCallback(() => {
    logger.info('Retrying character fetch...');
    setError(null);
    setCharactersList([]);
    setSelectedCharacters([]); // Clear any previous selections
    fetchCharacters();
  }, [fetchCharacters]);

  /**
   * Memoized Set for O(1) character selection lookup
   * Performance optimization: Converting array.includes() O(n) to Set.has() O(1)
   */
  const selectedCharactersSet = useMemo(() => {
    return new Set(selectedCharacters);
  }, [selectedCharacters]);

  /**
   * 判断角色是否被选中 - Check if character is selected
   * Optimized with Set for O(1) lookup performance
   */
  const isCharacterSelected = useCallback((characterName: string) => {
    return selectedCharactersSet.has(characterName);
  }, [selectedCharactersSet]);

  /**
   * 获取选择计数器颜色 - Get selection counter color based on validation
   * Memoized to prevent recalculation on every render
   */
  const counterColor = useMemo(() => {
    const count = selectedCharacters.length;
    if (count < selectionConstraints.minSelection) return 'var(--color-error)';
    if (count > selectionConstraints.maxSelection) return 'var(--color-error)';
    return 'var(--color-success)';
  }, [selectedCharacters.length, selectionConstraints.minSelection, selectionConstraints.maxSelection]);

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
          <div className="character-grid" data-testid="loading-skeleton-grid">
            {/* Show 6 skeleton cards during loading to match typical grid */}
            {Array.from({ length: 6 }).map((_, index) => (
              <SkeletonCard key={`skeleton-${index}`} />
            ))}
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
                style={{ color: counterColor }}
                data-testid="selection-counter"
                role="status"
                aria-live="polite"
                aria-atomic="true"
              >
                {t('characterSelection.counter', { 
                  count: selectedCharacters.length, 
                  max: selectionConstraints.maxSelection 
                })}
              </div>
            </div>

            {/* Character Grid */}
            <div className="character-grid" data-testid="character-grid">
              {charactersList.map((character, index) => (
                <CharacterCard
                  key={character}
                  character={character}
                  isSelected={isCharacterSelected(character)}
                  onSelect={handleCharacterSelection}
                  index={index}
                  isFocused={focusedCardIndex === index}
                  cardRef={(el) => (characterCardRefs.current[index] = el)}
                  onFocus={handleCardFocus}
                  onKeyDown={handleCardKeyDown}
                />
              ))}
            </div>

            {/* Validation Error Display */}
            {validationError && (
              <div 
                className="validation-error" 
                data-testid="validation-error"
                role="alert"
                aria-live="assertive"
                aria-atomic="true"
              >
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
