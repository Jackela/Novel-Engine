// 简化版角色选择组件 - 逐步修复问题
import React, { useState, useEffect } from 'react';
import { useCharactersQuery } from '../services/queries';
import './CharacterSelection.css';

const SimpleCharacterSelection = () => {
  console.log('SimpleCharacterSelection component mounted');
  
  const [characters, setCharacters] = useState<string[]>([]);
  const [selectedCharacters, setSelectedCharacters] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [validationError, setValidationError] = useState('');
  const [simulationResult, setSimulationResult] = useState(null);
  const [isSimulating, setIsSimulating] = useState(false);
  
  // 新增交互模拟状态
  const [interactiveMode, setInteractiveMode] = useState(false);
  const [currentTurn, setCurrentTurn] = useState(0);
  const [maxTurns] = useState(10);
  const [turnHistory, setTurnHistory] = useState([]);
  const [simulationStatus, setSimulationStatus] = useState('idle'); // idle, running, paused, completed
  const [interventionOptions, setInterventionOptions] = useState(null);
  const [showInterventionModal, setShowInterventionModal] = useState(false);

  const { data: charactersData, isLoading, error: charactersError } = useCharactersQuery();

  useEffect(() => {
    if (Array.isArray(charactersData)) setCharacters(charactersData);
    setLoading(isLoading);
    if (charactersError) setError('Failed to load characters');
  }, [charactersData, isLoading, charactersError]);

  const handleCharacterSelection = (character: string) => {
    console.log('Character selected:', character);
    
    setSelectedCharacters(prev => {
      if (prev.includes(character)) {
        // Remove character if already selected
        const newSelection = prev.filter(c => c !== character);
        
        // Show validation error for minimum when dropping below 2
        if (newSelection.length === 1) {
          setValidationError('Please select at least 2 characters to start simulation');
        } else {
          setValidationError('');
        }
        return newSelection;
      } else {
        // Trying to add a character
        if (prev.length >= 6) {
          // At maximum limit
          setValidationError('Maximum 6 characters allowed');
          return prev; // Don't change selection
        } else {
          // Can add character
          const newSelection = [...prev, character];
          
          // Show validation error if still below minimum
          if (newSelection.length === 1) {
            setValidationError('Please select at least 2 characters to start simulation');
          } else {
            setValidationError('');
          }
          
          return newSelection;
        }
      }
    });
  };

  const isCharacterSelected = (character: string) => {
    return selectedCharacters.includes(character);
  };

  // 推进一回合的逻辑
  const advanceOneTurn = async () => {
    if (simulationStatus === 'completed' || isSimulating) return;
    
    setIsSimulating(true);
    setSimulationStatus('running');
    
    try {
      // 模拟API调用延迟
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      const newTurn = currentTurn + 1;
      
      // 生成模拟的回合事件
      const turnEvents = generateMockTurnEvents(selectedCharacters, newTurn);
      
      const newTurnData = {
        turnNumber: newTurn,
        timestamp: new Date().toISOString(),
        events: turnEvents
      };
      
      setTurnHistory(prev => [...prev, newTurnData]);
      setCurrentTurn(newTurn);
      
      // 检查是否需要用户干预 (每3回合一次)
      if (newTurn % 3 === 0 && newTurn < maxTurns) {
        triggerUserIntervention(newTurn);
      }
      
      // 检查是否达到最大回合数
      if (newTurn >= maxTurns) {
        setSimulationStatus('completed');
      }
      
    } catch (error) {
      console.error('Error advancing turn:', error);
      setError('推进回合失败: ' + error.message);
    } finally {
      setIsSimulating(false);
    }
  };

  // 生成模拟回合事件
  const generateMockTurnEvents = (characters, turnNumber) => {
    const actionTypes = [
      '发起猛烈攻击',
      '进行战术移动',
      '寻找掩护',
      '装填弹药',
      '呼叫支援',
      '投掷手雷',
      '瞄准射击',
      '近战冲锋',
      '防御姿态',
      '观察敌情'
    ];
    
    const events = [];
    const numEvents = Math.min(characters.length * 2, 6); // 每个角色最多2个动作
    
    for (let i = 0; i < numEvents; i++) {
      const character = characters[Math.floor(Math.random() * characters.length)];
      const action = actionTypes[Math.floor(Math.random() * actionTypes.length)];
      
      events.push({
        agent: character,
        action: `${action} - 在第${turnNumber}回合展现战术技巧`
      });
    }
    
    return events;
  };

  // 生成最终战役故事
  const generateFinalStory = async () => {
    if (turnHistory.length === 0) return;
    
    setIsSimulating(true);
    
    try {
      // 将所有回合记录整合成完整的故事请求
      const storyRequest = {
        character_names: selectedCharacters,
        turns: turnHistory.length,
        narrative_style: 'epic',
        turn_history: turnHistory
      };
      
      console.log('Generating final story with data:', storyRequest);
      
      // 模拟故事生成过程
      await new Promise(resolve => setTimeout(resolve, 3000));
      
      // 生成基于交互历史的模拟故事
      const compiledStory = compileInteractiveStory(turnHistory, selectedCharacters);
      
      const finalResult = {
        story: compiledStory,
        participants: selectedCharacters,
        turns_executed: turnHistory.length,
        duration_seconds: turnHistory.length * 2.5,
        interaction_based: true
      };
      
      // 切换到结果显示界面
      setInteractiveMode(false);
      setSimulationResult(finalResult);
      
    } catch (error) {
      console.error('Error generating final story:', error);
      setError('生成故事失败: ' + error.message);
    } finally {
      setIsSimulating(false);
    }
  };

  // 编译交互式故事
  const compileInteractiveStory = (history, participants) => {
    let story = `🛡️ **Novel Engine 交互式战役记录** 🛡️\n\n`;
    story += `参与英雄: ${participants.join(', ')}\n`;
    story += `总回合数: ${history.length}\n`;
    story += `战斗类型: 交互式指挥战斗\n\n`;
    
    story += `📜 **战斗序章**\n`;
    story += `在这片被战火吞噬的战场上，${participants.join('、')} 这些英勇的战士们展开了一场史诗般的冲突。每一个决策都由指挥官亲自下达，每一回合都见证着战术的较量与命运的转折。\n\n`;
    
    history.forEach((turn, index) => {
      story += `⚔️ **第 ${turn.turnNumber} 回合** - ${new Date(turn.timestamp).toLocaleString()}\n`;
      
      turn.events.forEach(event => {
        story += `• **${event.agent}**: ${event.action}\n`;
      });
      
      // 添加回合间的叙事连接
      if (index < history.length - 1) {
        story += `\n战况激烈，双方都在寻找致胜的机会...\n\n`;
      }
    });
    
    story += `\n🏆 **战役结语**\n`;
    story += `经过 ${history.length} 个回合的激烈交锋，这场由指挥官亲自指挥的战斗展现了战略智慧与战术执行的完美结合。每个参与者都在这场神圣的冲突中证明了自己的价值，这将是一个被永远铭记的传奇战役。\n\n`;
    story += `愿机械之神庇佑所有勇敢的战士！`;
    
    return story;
  };

  // 触发用户干预
  const triggerUserIntervention = (turnNumber) => {
    const interventionTypes = [
      {
        title: '战术决策时刻',
        question: `第 ${turnNumber} 回合结束，指挥官需要做出战术决策：`,
        options: [
          { id: 'aggressive', text: '🗡️ 发起全面攻势', effect: '增强攻击力，提高风险' },
          { id: 'defensive', text: '🛡️ 采取防御策略', effect: '提高防御力，减少伤亡' },
          { id: 'tactical', text: '📋 执行战术机动', effect: '获得位置优势，下回合优先行动' }
        ]
      },
      {
        title: '增援决策',
        question: `战况激烈！是否调动增援支持前线？`,
        options: [
          { id: 'reinforcements', text: '📞 呼叫增援部队', effect: '下回合获得额外支援单位' },
          { id: 'equipment', text: '📦 申请装备补给', effect: '提升所有单位装备等级' },
          { id: 'continue', text: '⚔️ 以现有力量继续', effect: '保持当前状态，节约资源' }
        ]
      },
      {
        title: '环境利用',
        question: `发现战场环境可以利用，如何行动？`,
        options: [
          { id: 'terrain', text: '🏔️ 利用地形优势', effect: '获得掩体加成，提高生存率' },
          { id: 'weather', text: '🌩️ 等待天气变化', effect: '延迟一回合，获得环境加成' },
          { id: 'ignore', text: '🏃 忽略环境因素', effect: '快速推进，保持攻击节奏' }
        ]
      }
    ];
    
    const randomIntervention = interventionTypes[Math.floor(Math.random() * interventionTypes.length)];
    
    setInterventionOptions(randomIntervention);
    setShowInterventionModal(true);
    setSimulationStatus('paused');
  };

  // 处理用户干预选择
  const handleInterventionChoice = (choice) => {
    console.log('User intervention choice:', choice);
    
    // 添加干预事件到历史记录
    const interventionEvent = {
      turnNumber: currentTurn,
      timestamp: new Date().toISOString(),
      events: [{
        agent: '指挥官',
        action: `${choice.text} - ${choice.effect}`
      }]
    };
    
    setTurnHistory(prev => [...prev, interventionEvent]);
    
    // 关闭干预模态框
    setShowInterventionModal(false);
    setInterventionOptions(null);
    setSimulationStatus('running');
  };

  console.log('Rendering component - loading:', loading, 'error:', error, 'characters:', characters);

  if (loading) {
    return (
      <div className="character-selection-container">
        <div className="selection-header">
          <h1 className="selection-title">Character Selection Sanctum</h1>
          <p className="selection-subtitle">Sacred Character Arsenal - Choose Your Champions</p>
        </div>
        <div className="loading-container" data-testid="loading-spinner">
          <div className="loading-spinner"></div>
          <p className="loading-text">Communing with the Machine God to retrieve character souls...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="character-selection-container">
        <div className="selection-header">
          <h1 className="selection-title">Character Selection Sanctum</h1>
          <p className="selection-subtitle">Sacred Character Arsenal - Choose Your Champions</p>
        </div>
        <div className="error-container" data-testid="error-container">
          <div className="error-message" data-testid="error-message">
            {error.includes('404') ? 'No characters found - Please ensure character data is available' :
             error.includes('500') ? 'Server error - Please try again later' :
             error.includes('Network Error') || error.includes('ECONNREFUSED') ? 'Cannot connect to server - Please ensure the backend is running' :
             error}
          </div>
          <button 
            onClick={() => window.location.reload()} 
            className="retry-button" 
            data-testid="retry-button"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  // 显示交互式模拟界面
  if (interactiveMode) {
    return (
      <div className="character-selection-container">
        <div className="selection-header">
          <h1 className="selection-title">Interactive Battle Simulation</h1>
          <p className="selection-subtitle">Witness the Sacred Conflict Unfold - Turn by Turn</p>
        </div>
        
        <div className="interactive-simulation">
          {/* 模拟状态面板 */}
          <div className="simulation-status-panel">
            <div className="status-info">
              <span className="current-turn">回合 {currentTurn}/{maxTurns}</span>
              <span className={`status-badge ${simulationStatus}`}>
                {simulationStatus === 'idle' && '待启动'}
                {simulationStatus === 'running' && '进行中'}
                {simulationStatus === 'paused' && '已暂停'}
                {simulationStatus === 'completed' && '已完成'}
              </span>
              <span className="participants">参与者: {selectedCharacters.join(', ')}</span>
            </div>
            
            <div className="control-buttons-panel">
              <button 
                className="advance-button"
                disabled={simulationStatus === 'completed' || isSimulating}
                onClick={advanceOneTurn}
              >
                {isSimulating ? '执行中...' : '推进一回合'}
              </button>
              
              <button 
                className="pause-button"
                disabled={simulationStatus !== 'running'}
                onClick={() => setSimulationStatus('paused')}
              >
                暂停
              </button>
              
              <button 
                className="resume-button"
                disabled={simulationStatus !== 'paused'}
                onClick={() => setSimulationStatus('running')}
              >
                继续
              </button>
              
              <button 
                className="finish-button"
                disabled={turnHistory.length === 0}
                onClick={generateFinalStory}
              >
                生成战役故事
              </button>
            </div>
          </div>
          
          {/* 交互历史显示 */}
          <div className="interaction-history">
            <h3>战斗记录 (Battle Log)</h3>
            <div className="history-content">
              {turnHistory.length === 0 ? (
                <div className="no-history">
                  <p>战斗尚未开始...</p>
                  <p>点击"推进一回合"开始神圣的冲突</p>
                </div>
              ) : (
                turnHistory.map((turn, index) => (
                  <div key={index} className="turn-entry">
                    <div className="turn-header">
                      <span className="turn-number">第 {turn.turnNumber} 回合</span>
                      <span className="turn-time">{new Date(turn.timestamp).toLocaleTimeString()}</span>
                    </div>
                    <div className="turn-content">
                      {turn.events.map((event, eventIndex) => (
                        <div key={eventIndex} className="event-entry">
                          <span className="agent-name">{event.agent}</span>
                          <span className="event-action">{event.action}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
          
          {/* 返回按钮 */}
          <div className="back-controls">
            <button 
              onClick={() => {
                setInteractiveMode(false);
                setCurrentTurn(0);
                setTurnHistory([]);
                setSimulationStatus('idle');
                setSelectedCharacters([]);
                setShowInterventionModal(false);
                setInterventionOptions(null);
              }}
              className="back-button"
            >
              返回角色选择
            </button>
          </div>
          
          {/* 用户干预模态框 */}
          {showInterventionModal && interventionOptions && (
            <div className="intervention-modal-overlay">
              <div className="intervention-modal">
                <div className="modal-header">
                  <h3>{interventionOptions.title}</h3>
                  <div className="modal-badge">⚠️ 指挥决策</div>
                </div>
                
                <div className="modal-content">
                  <p className="intervention-question">{interventionOptions.question}</p>
                  
                  <div className="intervention-options">
                    {interventionOptions.options.map((option) => (
                      <button
                        key={option.id}
                        className="intervention-option"
                        onClick={() => handleInterventionChoice(option)}
                      >
                        <div className="option-text">{option.text}</div>
                        <div className="option-effect">{option.effect}</div>
                      </button>
                    ))}
                  </div>
                </div>
                
                <div className="modal-footer">
                  <p className="modal-hint">💡 你的选择将影响战斗的进程和最终故事</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // 显示模拟结果
  if (simulationResult) {
    return (
      <div className="character-selection-container">
        <div className="selection-header">
          <h1 className="selection-title">Sacred Simulation Complete</h1>
          <p className="selection-subtitle">The Machine God Has Spoken - Witness the Chronicle</p>
        </div>
        
        <div className="simulation-result" data-testid="simulation-result">
          <div className="result-header">
            <h2>Epic Battle Chronicle</h2>
            <div className="simulation-stats">
              <span>参与者 (Participants): {simulationResult.participants.join(', ')}</span>
              <span>回合数 (Turns): {simulationResult.turns_executed}</span>
              <span>用时 (Duration): {simulationResult.duration_seconds.toFixed(1)}秒</span>
            </div>
          </div>
          
          <div className="story-content">
            <div className="story-text">
              {simulationResult.story.split('\n\n').map((paragraph, index) => (
                <p key={index} className="story-paragraph">
                  {paragraph}
                </p>
              ))}
            </div>
          </div>
          
          <div className="result-actions">
            <button 
              onClick={() => {
                setSimulationResult(null);
                setSelectedCharacters([]);
              }}
              className="new-simulation-button"
            >
              🔄 开始新模拟 (New Simulation)
            </button>
            <button 
              onClick={() => {
                const blob = new Blob([simulationResult.story], { type: 'text/plain' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `Novel Engine-40k-simulation-${Date.now()}.txt`;
                a.click();
                URL.revokeObjectURL(url);
              }}
              className="download-story-button"
            >
              💾 下载故事 (Download Story)
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="character-selection-container">
      <div className="selection-header">
        <h1 className="selection-title">Character Selection Sanctum</h1>
        <p className="selection-subtitle">Sacred Character Arsenal - Choose Your Champions</p>
      </div>
      
      <div className="selection-content">
        {characters.length > 0 ? (
          <>
            <div className="selection-info">
              <p className="instruction">Select 2-6 characters to forge the perfect warband for your simulation.</p>
              <div 
                className="selection-counter" 
                data-testid="selection-counter"
                style={{ 
                  color: selectedCharacters.length < 2 ? 'var(--color-error)' : 
                         selectedCharacters.length > 6 ? 'var(--color-error)' : 'var(--color-success)'
                }}
              >
                {selectedCharacters.length} of 6 characters selected
              </div>
            </div>

            <div className="character-grid" data-testid="character-grid">
              {characters.map((character) => (
                <div
                  key={character}
                  className={`character-card ${isCharacterSelected(character) ? 'selected' : ''}`}
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
                  <div className="character-header">
                    <h3 className="character-name">{character}</h3>
                    {isCharacterSelected(character) && (
                      <div 
                        className="selection-checkmark" 
                        data-testid={`selection-checkmark-${character}`}
                      >
                        ✓
                      </div>
                    )}
                  </div>
                  <div className="character-info">
                    <div className="character-description">
                      {character === 'bastion_guardian' && 'Bastion Cohort - Fearless Alliance Guard'}
                      {character === 'freewind_raider' && 'Freewind Collective - Unpredictable Raider'}
                      {character === 'isabella_varr' && 'Alliance Network Noble - Tactical Commander'}
                      {character === 'cors_test_char' && 'Test Character - Development Unit'}
                      {character === 'test' && 'Experimental Subject - Combat Testing'}
                    </div>
                    <div className="character-status">
                      {isCharacterSelected(character) ? 'SELECTED' : 'AVAILABLE'}
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

            <div className="actions">
              <button
                className="create-character-button"
                data-testid="create-character-button"
                onClick={() => alert('Create new character functionality')}
              >
                Forge New Character Soul
              </button>
              
              {/* 交互式模拟按钮 */}
              <button
                disabled={selectedCharacters.length < 2 || selectedCharacters.length > 6}
                className={`interactive-button ${
                  selectedCharacters.length < 2 || selectedCharacters.length > 6 ? 'disabled' : ''
                }`}
                data-testid="interactive-simulation-button"
                onClick={() => {
                  console.log('Starting interactive simulation with characters:', selectedCharacters);
                  setInteractiveMode(true);
                  setSimulationStatus('idle');
                  setCurrentTurn(0);
                  setTurnHistory([]);
                }}
              >
                🎮 交互式战斗 (Interactive Battle)
              </button>
              
              {/* 经典模拟按钮 */}
              <button
                disabled={selectedCharacters.length < 2 || selectedCharacters.length > 6 || isSimulating}
                className={`confirm-button ${
                  selectedCharacters.length < 2 || selectedCharacters.length > 6 || isSimulating ? 'disabled' : ''
                }`}
                data-testid="confirm-selection-button"
                aria-label={`Confirm selection of ${selectedCharacters.length} characters`}
                onClick={() => {
                  console.log('Starting simulation with characters:', selectedCharacters);
                  setIsSimulating(true);
                  setError(null);
                  setSimulationResult(null);
                  
                  // 使用正确的API端点
                  fetch('http://localhost:8000/simulations', {
                    method: 'POST',
                    headers: {
                      'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                      character_names: selectedCharacters,
                      turns: 3,
                      narrative_style: 'epic'
                    })
                  })
                  .then(response => {
                    if (!response.ok) {
                      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    return response.json();
                  })
                  .then(data => {
                    console.log('Simulation completed:', data);
                    setIsSimulating(false);
                    // 显示结果界面而不是alert
                    setSimulationResult(data);
                  })
                  .catch(error => {
                    console.error('Error starting simulation:', error);
                    setIsSimulating(false);
                    setError(`模拟启动失败: ${error.message}`);
                  });
                }}
              >
                {isSimulating ? (
                  <>
                    <div className="loading-spinner" style={{width: '20px', height: '20px', marginBottom: '5px'}}></div>
                    正在进行神圣模拟... (Sacred Simulation in Progress...)
                  </>
                ) : (
                  '📖 经典模拟 (Classic Simulation)'
                )}
              </button>
            </div>
          </>
        ) : (
          <div className="empty-state" data-testid="empty-state">
            <p>No characters found - Please ensure character data is available</p>
            <button 
              onClick={() => window.location.reload()} 
              className="retry-button" 
              data-testid="retry-button"
            >
              Retry
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default SimpleCharacterSelection;
