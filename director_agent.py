#!/usr/bin/env python3
"""
DirectorAgent Core Implementation
================================

This module implements the DirectorAgent class, which serves as the Game Master AI
for the Warhammer 40k Multi-Agent Simulator. The DirectorAgent orchestrates the
entire simulation by managing PersonaAgent instances, coordinating their interactions,
and maintaining the campaign narrative through structured event logging.

The DirectorAgent acts as the central coordinator that:
1. Registers and manages multiple PersonaAgent instances
2. Executes simulation turns by calling each agent's decision_loop
3. Logs all events and actions to a persistent campaign log
4. Manages world state data (prepared for future integration)
5. Handles errors gracefully to maintain simulation stability

This implementation provides the Phase 1 foundation for multi-agent orchestration
that will later integrate with AI/LLM systems for advanced world state management
and dynamic narrative generation.

Architecture Reference: Architecture_Blueprint.md Section 2.1 DirectorAgent
Development Phase: Phase 1 - DirectorAgent Core Logic (Weeks 3-5)
"""

import json
import os
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path

# 引入PersonaAgent及相关类别，建立人格机灵与指挥中心的神圣连接...
from persona_agent import PersonaAgent, CharacterAction

# 引入配置系统圣典，获取指挥中心的运行参数...
from config_loader import get_config, get_campaign_log_filename


# 配置指挥中心操作追踪的记录仪式，记录Game Master AI的每个决策...
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DirectorAgent:
    """
    Core implementation of the Game Master AI for the Warhammer 40k Multi-Agent Simulator.
    
    The DirectorAgent serves as the central orchestrator that manages the simulation by:
    - Registering and coordinating multiple PersonaAgent instances
    - Executing simulation turns and collecting agent decisions
    - Maintaining a comprehensive campaign log for narrative tracking
    - Preparing for future world state management and AI integration
    - Handling errors gracefully to ensure simulation stability
    
    Key Responsibilities:
    - Agent lifecycle management (registration, validation, coordination)
    - Turn-based simulation execution with structured event processing
    - Campaign narrative logging with timestamp and participant tracking
    - Error handling and recovery for robust simulation operation
    - Interface preparation for future world state database integration
    
    Architecture Notes:
    - Designed for easy integration with future AI/LLM systems
    - Maintains clear separation between agent coordination and world state management
    - Supports dynamic agent registration and deregistration during runtime
    - Provides hooks for future WorldState_DB.json integration
    - Implements comprehensive logging for debugging and narrative purposes
    """
    
    def __init__(self, world_state_file_path: Optional[str] = None, campaign_log_path: Optional[str] = None):
        """
        Initialize the DirectorAgent with optional world state file integration.
        
        Sets up the core director infrastructure including agent registry,
        campaign logging system, and world state management preparation.
        Handles file operations with comprehensive error checking.
        
        Args:
            world_state_file_path: Optional path to world state database file
                                  (prepared for future Phase 2 integration)
                                  If provided, attempts to load existing world state
                                  If None, uses configuration or defaults
            campaign_log_path: Optional path to campaign log file
                             If None, uses configuration value
                                  
        Raises:
            ValueError: If world_state_file_path is provided but file is malformed
            OSError: If file operations fail due to permissions or disk issues
        """
        logger.info("Initializing DirectorAgent - Game Master AI starting up")
        
        # 加载配置圣典，获取指挥中心的神圣参数...
        try:
            config = get_config()
            self._config = config
        except Exception as e:
            logger.warning(f"Failed to load configuration, using defaults: {e}")
            self._config = None
        
        # 核心代理管理系统，统管所有人格机灵的生命周期...
        self.registered_agents: List[PersonaAgent] = []
        """List of registered PersonaAgent instances managed by this director"""
        
        # 世界状态管理系统（为未来融合做准备），维护模拟世界的真实性...
        if world_state_file_path is None and self._config:
            world_state_file_path = self._config.director.world_state_file
        self.world_state_file_path = world_state_file_path
        """Path to world state database file for persistence"""
        
        self.world_state_data: Dict[str, Any] = {}
        """Current world state data (placeholder for future implementation)"""
        
        # 战役记录系统 - 如可用则使用配置，记录英雄传说的点点滴滴...
        if campaign_log_path is None:
            if self._config:
                campaign_log_path = self._config.paths.log_file_path
            else:
                campaign_log_path = "campaign_log.md"
        self.campaign_log_path = campaign_log_path
        """Path to the campaign log file for narrative tracking"""
        
        # 设置配置驱动的参数，遵循机械教条的指导...
        if self._config:
            self.max_turn_history = self._config.director.max_turn_history
            self.error_threshold = self._config.director.error_threshold
        else:
            self.max_turn_history = 100
            self.error_threshold = 10
        
        # 模拟状态追踪系统，监控虚拟战场的每个细节...
        self.current_turn_number = 0
        """Current simulation turn counter"""
        
        self.simulation_start_time = datetime.now()
        """Timestamp when the simulation was initialized"""
        
        self.total_actions_processed = 0
        """Counter for total actions processed across all turns"""
        
        # 错误追踪稳定性监控，诊断与修复模拟系统的创伤...
        self.error_count = 0
        """Count of errors encountered during simulation"""
        
        self.last_error_time: Optional[datetime] = None
        """Timestamp of the most recent error"""
        
        # 初始化指挥系统，唤醒Game Master AI的核心机器灵魂...
        try:
            self._initialize_campaign_log()
            self._load_world_state()
            
            logger.info(f"DirectorAgent initialized successfully")
            logger.info(f"Campaign log: {self.campaign_log_path}")
            logger.info(f"World state file: {self.world_state_file_path or 'None (using defaults)'}")
            logger.info(f"Registered agents: {len(self.registered_agents)}")
            
        except Exception as e:
            logger.error(f"Failed to initialize DirectorAgent: {str(e)}")
            raise ValueError(f"DirectorAgent initialization failed: {str(e)}")
    
    def _initialize_campaign_log(self) -> None:
        """
        Initialize the campaign log file with proper headers and initial entries.
        
        Creates a new campaign log if none exists, or validates the existing one.
        The log uses markdown format for human readability and tool compatibility.
        
        Raises:
            OSError: If file creation or writing fails
        """
        try:
            # 检查战役记录是否已存在，验证英雄传说的连续性...
            if os.path.exists(self.campaign_log_path):
                logger.info(f"Found existing campaign log: {self.campaign_log_path}")
                
                # 验证现有记录格式，确保英雄传说的正确编写...
                try:
                    with open(self.campaign_log_path, 'r', encoding='utf-8') as file:
                        content = file.read()
                        if not content.strip():
                            logger.warning("Campaign log exists but is empty, reinitializing")
                            self._create_new_campaign_log()
                        else:
                            logger.info("Campaign log validated successfully")
                except Exception as e:
                    logger.warning(f"Could not validate existing campaign log: {e}")
                    logger.info("Creating backup and initializing new log")
                    self._backup_existing_log()
                    self._create_new_campaign_log()
            else:
                logger.info("No existing campaign log found, creating new one")
                self._create_new_campaign_log()
                
        except Exception as e:
            logger.error(f"Failed to initialize campaign log: {str(e)}")
            raise OSError(f"Campaign log initialization failed: {str(e)}")
    
    def _create_new_campaign_log(self) -> None:
        """Create a new campaign log file with proper formatting and headers."""
        initial_content = f"""# Campaign Log

**Simulation Started:** {self.simulation_start_time.strftime('%Y-%m-%d %H:%M:%S')}  
**Director Agent:** DirectorAgent v1.0  
**Phase:** Phase 1 - Core Logic Implementation  

## Campaign Overview

This log tracks all events, decisions, and interactions in the Warhammer 40k Multi-Agent Simulator.
Each entry includes timestamps, participating agents, and detailed event descriptions.

---

## Campaign Events

### Simulation Initialization
**Time:** {self.simulation_start_time.strftime('%Y-%m-%d %H:%M:%S')}  
**Event:** DirectorAgent initialized and campaign log created  
**Participants:** System  
**Details:** Game Master AI successfully started, ready for agent registration and simulation execution

"""
        
        with open(self.campaign_log_path, 'w', encoding='utf-8') as file:
            file.write(initial_content)
        
        logger.info(f"New campaign log created: {self.campaign_log_path}")
    
    def _backup_existing_log(self) -> None:
        """Create a backup of existing campaign log before reinitializing."""
        backup_path = f"{self.campaign_log_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            import shutil
            shutil.copy2(self.campaign_log_path, backup_path)
            logger.info(f"Existing campaign log backed up to: {backup_path}")
        except Exception as e:
            logger.warning(f"Could not create backup of existing log: {e}")
    
    def _load_world_state(self) -> None:
        """
        Load world state data from file if provided.
        
        This method prepares for future Phase 2 integration with WorldState_DB.json.
        Currently implements placeholder logic for world state management.
        
        Raises:
            ValueError: If world state file exists but contains invalid data
            OSError: If file operations fail
        """
        if self.world_state_file_path is None:
            logger.info("No world state file specified, using default world state")
            self._initialize_default_world_state()
            return
        
        try:
            if os.path.exists(self.world_state_file_path):
                logger.info(f"Loading world state from: {self.world_state_file_path}")
                
                with open(self.world_state_file_path, 'r', encoding='utf-8') as file:
                    self.world_state_data = json.load(file)
                
                # 验证世界状态结构，确保模拟世界的数据完整性...
                self._validate_world_state_data()
                
                logger.info(f"World state loaded successfully")
                logger.info(f"World state contains {len(self.world_state_data)} top-level entries")
                
            else:
                logger.warning(f"World state file not found: {self.world_state_file_path}")
                logger.info("Initializing with default world state")
                self._initialize_default_world_state()
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in world state file: {str(e)}")
            raise ValueError(f"World state file contains invalid JSON: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to load world state: {str(e)}")
            raise OSError(f"World state loading failed: {str(e)}")
    
    def _initialize_default_world_state(self) -> None:
        """Initialize default world state for simulation operation."""
        self.world_state_data = {
            'simulation_info': {
                'phase': 'Phase 1 - Core Logic',
                'version': '1.0.0',
                'initialized_at': self.simulation_start_time.isoformat(),
            },
            'locations': {
                'default_location': {
                    'name': 'Simulation Space',
                    'description': 'Default location for Phase 1 testing',
                    'threat_level': 'low',
                    'faction_control': 'neutral',
                }
            },
            'factions': {
                'imperium': {'status': 'active', 'influence': 0.6},
                'chaos': {'status': 'active', 'influence': 0.3},
                'ork': {'status': 'active', 'influence': 0.1},
            },
            'global_events': [],
            'turn_history': [],
        }
        
        logger.info("Default world state initialized")
    
    def _validate_world_state_data(self) -> None:
        """
        Validate the structure and content of loaded world state data.
        
        Ensures that world state data contains required fields and valid values
        for proper simulation operation.
        
        Raises:
            ValueError: If world state data is missing required fields or has invalid structure
        """
        required_fields = ['simulation_info', 'locations', 'factions']
        
        for field in required_fields:
            if field not in self.world_state_data:
                logger.warning(f"World state missing required field: {field}")
                # 添加默认值而非失败，维持系统的稳定运行...
                if field == 'simulation_info':
                    self.world_state_data[field] = {'phase': 'Unknown', 'version': 'Unknown'}
                elif field == 'locations':
                    self.world_state_data[field] = {}
                elif field == 'factions':
                    self.world_state_data[field] = {}
        
        # 验证数据类型，确保数据圣物的纯洁性...
        if not isinstance(self.world_state_data['locations'], dict):
            raise ValueError("World state 'locations' must be a dictionary")
        
        if not isinstance(self.world_state_data['factions'], dict):
            raise ValueError("World state 'factions' must be a dictionary")
        
        logger.info("World state data validation completed")
    
    def register_agent(self, agent: PersonaAgent) -> bool:
        """
        Register a PersonaAgent instance with the DirectorAgent for simulation management.
        
        Validates the agent has required methods and adds it to the registered agents list.
        Includes comprehensive validation to ensure agent compatibility and prevent
        runtime errors during simulation execution.
        
        Args:
            agent: PersonaAgent instance to register
                  Must have decision_loop method and valid agent_id
                  
        Returns:
            bool: True if registration successful, False if validation failed
                  
        Example:
            >>> director = DirectorAgent()
            >>> agent = PersonaAgent("character_sheet.md")
            >>> success = director.register_agent(agent)
            >>> if success:
            ...     print("Agent registered successfully")
        """
        try:
            logger.info(f"Attempting to register agent for simulation management")
            
            # 验证代理实例，确认人格机灵的真实性...
            if not isinstance(agent, PersonaAgent):
                logger.error(f"Invalid agent type: {type(agent)}. Expected PersonaAgent instance")
                return False
            
            # 验证必需方法是否存在，确保人格机灵具备必要能力...
            if not hasattr(agent, 'decision_loop'):
                logger.error(f"Agent missing required 'decision_loop' method")
                return False
            
            if not callable(getattr(agent, 'decision_loop')):
                logger.error(f"Agent 'decision_loop' is not callable")
                return False
            
            # 验证代理具有有效ID，给予人格机灵独特的识别符...
            if not hasattr(agent, 'agent_id') or not agent.agent_id:
                logger.error(f"Agent missing valid agent_id")
                return False
            
            # 检查重复注册，防止人格机灵的身份冲突...
            existing_ids = [existing_agent.agent_id for existing_agent in self.registered_agents]
            if agent.agent_id in existing_ids:
                logger.warning(f"Agent with ID '{agent.agent_id}' already registered")
                return False
            
            # 验证代理已正确初始化，确保人格机灵的完整性...
            if not hasattr(agent, 'character_data') or not isinstance(agent.character_data, dict):
                logger.error(f"Agent character_data not properly initialized")
                return False
            
            # 注册代理，将人格机灵纳入指挥系统...
            self.registered_agents.append(agent)
            
            # 记录成功注册，存档人格机灵的加入仪式...
            character_name = agent.character_data.get('name', 'Unknown')
            faction = agent.subjective_worldview.get('primary_faction', 'Unknown')
            
            logger.info(f"Agent registered successfully:")
            logger.info(f"  - Agent ID: {agent.agent_id}")
            logger.info(f"  - Character: {character_name}")
            logger.info(f"  - Faction: {faction}")
            logger.info(f"  - Total registered agents: {len(self.registered_agents)}")
            
            # 将注册事件记录到战役日志，留下英雄加入的历史记录...
            registration_event = (
                f"**Agent Registration:** {character_name} ({agent.agent_id}) joined the simulation\\n"
                f"**Faction:** {faction}\\n"
                f"**Registration Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n"
                f"**Total Active Agents:** {len(self.registered_agents)}"
            )
            
            self.log_event(registration_event)
            
            return True
            
        except Exception as e:
            logger.error(f"Exception during agent registration: {str(e)}")
            self.error_count += 1
            self.last_error_time = datetime.now()
            return False
    
    def log_event(self, event_description: str) -> None:
        """
        Append an event description to the campaign log with timestamp and formatting.
        
        Creates properly formatted log entries with timestamps and handles file
        operations safely. Ensures campaign log remains readable and well-structured
        for both human review and potential future AI processing.
        
        Args:
            event_description: Human-readable description of the event to log
                             Can include markdown formatting for better presentation
                             Should describe what happened, who was involved, and the outcome
                             
        Example:
            >>> director.log_event("Brother Marcus engaged ork raiders in sector 7")
            >>> director.log_event("**Combat Result:** Imperial forces victorious")
        """
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 检查战役记录是否存在，不存在则创建，开启英雄传说的第一页...
            if not os.path.exists(self.campaign_log_path):
                self._create_new_campaign_log()
            
            # 使用正确的markdown结构格式化事件条目，给予英雄传说优雅的形式...
            log_entry = f"\n### Turn {self.current_turn_number + 1} Event\n"
            log_entry += f"**Time:** {timestamp}  \n"
            log_entry += f"**Event:** {event_description}  \n"
            log_entry += f"**Turn:** {self.current_turn_number + 1}  \n"
            log_entry += f"**Active Agents:** {len(self.registered_agents)}  \n"
            log_entry += "\n---\n"
            
            # 附加到战役记录文件，书写英雄传说的新章节...
            with open(self.campaign_log_path, 'a', encoding='utf-8') as file:
                file.write(log_entry)
            
            logger.info(f"Event logged to campaign: {event_description[:50]}...")
            
        except Exception as e:
            logger.error(f"Failed to log event to campaign file: {str(e)}")
            self.error_count += 1
            self.last_error_time = datetime.now()
            
            # 尝试记录到控制台作为后备，确保英雄事迹不被遮蒻...
            fallback_log = f"[{timestamp}] CAMPAIGN EVENT: {event_description}"
            logger.warning(f"Fallback logging: {fallback_log}")
    
    def run_turn(self) -> Dict[str, Any]:
        """
        Execute a single simulation turn by calling each registered agent's decision_loop.
        
        Orchestrates the turn-based simulation by:
        1. Incrementing turn counter and logging turn start
        2. Iterating through all registered agents in order
        3. Calling each agent's decision_loop with current world state
        4. Collecting and logging all agent actions and decisions
        5. Handling individual agent errors gracefully
        6. Returning comprehensive turn summary for analysis
        
        The method ensures simulation stability by isolating agent errors and
        continuing execution even if individual agents fail. All actions and
        errors are logged for debugging and narrative purposes.
        
        Returns:
            Dict[str, Any]: Comprehensive turn summary containing:
                - turn_number: Current turn number
                - timestamp: When the turn was executed
                - participating_agents: List of agent IDs that participated
                - agent_actions: Dictionary mapping agent_id to their actions
                - errors: List of any errors encountered during the turn
                - turn_duration: Time taken to execute the turn
                - total_actions: Number of actions generated this turn
                
        Example:
            >>> director = DirectorAgent()
            >>> director.register_agent(agent1)
            >>> director.register_agent(agent2)
            >>> turn_result = director.run_turn()
            >>> print(f"Turn {turn_result['turn_number']} completed with {turn_result['total_actions']} actions")
        """
        turn_start_time = datetime.now()
        self.current_turn_number += 1
        
        logger.info(f"=== STARTING TURN {self.current_turn_number} ===")
        logger.info(f"Active agents: {len(self.registered_agents)}")
        
        # 初始化回合追踪数据，开始新一轮的神圣决策循环...
        turn_summary = {
            'turn_number': self.current_turn_number,
            'timestamp': turn_start_time.isoformat(),
            'participating_agents': [],
            'agent_actions': {},
            'errors': [],
            'turn_duration': 0.0,
            'total_actions': 0,
        }
        
        # 将回合开始记录到战役日志，宣告新章节的开启...
        turn_start_event = f"TURN {self.current_turn_number} BEGINS"
        self.log_event(turn_start_event)
        
        # 检查是否有已注册的代理，确认参战英雄的存在...
        if not self.registered_agents:
            logger.warning("No registered agents found - turn will be empty")
            empty_turn_event = f"TURN {self.current_turn_number} COMPLETED"
            self.log_event(empty_turn_event)
            
            turn_summary['turn_duration'] = (datetime.now() - turn_start_time).total_seconds()
            return turn_summary
        
        # 遍历所有已注册的代理，让每个人格机灵参与决策...
        for agent_index, agent in enumerate(self.registered_agents):
            agent_start_time = datetime.now()
            
            try:
                logger.info(f"Processing agent {agent_index + 1}/{len(self.registered_agents)}: {agent.agent_id}")
                
                # 为代理准备世界状态更新，向人格机灵提供最新情报...
                # 目前使用占位数据 - 第二阶段将实现复杂的世界状态管理...
                world_state_update = self._prepare_world_state_for_agent(agent)
                
                # 调用代理的决策循环，启动人格机灵的思考仪式...
                agent_action = agent.decision_loop(world_state_update)
                
                # 记录代理参与，留下人格机灵的行动足迹...
                turn_summary['participating_agents'].append(agent.agent_id)
                
                # 处理代理的行动决定，将人格机灵的意志转化为现实行为...
                if agent_action is not None:
                    # 记录成功执行的行动，书写英雄传说的新章节...
                    character_name = agent.character_data.get('name', 'Unknown')
                    action_description = f"{character_name} ({agent.agent_id}) decided to {agent_action.action_type}"
                    
                    if agent_action.reasoning:
                        action_description += f": {agent_action.reasoning}"
                    
                    logger.info(f"Agent {agent.agent_id} action: {action_description}")
                    
                    # 将行动存储至回合摘要，保存战术决策的详细记录...
                    turn_summary['agent_actions'][agent.agent_id] = {
                        'action_type': agent_action.action_type,
                        'target': agent_action.target,
                        'priority': agent_action.priority.value if agent_action.priority else 'normal',
                        'reasoning': agent_action.reasoning,
                        'parameters': agent_action.parameters,
                        'processing_time': (datetime.now() - agent_start_time).total_seconds(),
                    }
                    
                    # 记录到战役日志，书写英雄传说的新章...
                    self.log_event(action_description)
                    
                    turn_summary['total_actions'] += 1
                    self.total_actions_processed += 1
                    
                else:
                    # 代理选择等待与观察，显示谨慎的战术智慧...
                    character_name = agent.character_data.get('name', 'Unknown')
                    wait_description = f"{character_name} ({agent.agent_id}) chose to wait and observe"
                    
                    logger.info(f"Agent {agent.agent_id} waiting: {wait_description}")
                    
                    # 将等待行动存储至回合摘要，记录谨慎的战术选择...
                    turn_summary['agent_actions'][agent.agent_id] = {
                        'action_type': 'wait',
                        'target': None,
                        'priority': 'low',
                        'reasoning': 'Agent chose to wait and observe the situation',
                        'parameters': {},
                        'processing_time': (datetime.now() - agent_start_time).total_seconds(),
                    }
                    
                    # 记入战役日志，书写英雄的谨慎与智慧...
                    self.log_event(wait_description)
                
            except Exception as e:
                # 优雅地处理代理错误，防止机器灵魂的损伤扩散...
                error_message = f"Error processing agent {agent.agent_id}: {str(e)}"
                logger.error(error_message)
                
                # 将错误记录在回合摘要中，保存机械故障的证据...
                turn_summary['errors'].append({
                    'agent_id': agent.agent_id,
                    'error_message': str(e),
                    'error_type': type(e).__name__,
                    'timestamp': datetime.now().isoformat(),
                })
                
                # 将错误记入战役日志，记录机器灵魂的痛苦与挑战...
                error_event = f"**ERROR:** Agent {agent.agent_id} encountered an error: {str(e)}"
                self.log_event(error_event)
                
                # 更新指挥官错误追踪，监控指挥中心的健康状态...
                self.error_count += 1
                self.last_error_time = datetime.now()
                
                # 继续处理下一个代理 - 不让单个机器灵魂的故障摧毁整个回合...
                continue
        
        # 计算回合完成指标，衡量指挥中心的效率...
        turn_end_time = datetime.now()
        turn_duration = (turn_end_time - turn_start_time).total_seconds()
        turn_summary['turn_duration'] = turn_duration
        
        # 记录回合完成，宣告一个战术周期的结束...
        logger.info(f"=== TURN {self.current_turn_number} COMPLETED ===")
        logger.info(f"Duration: {turn_duration:.2f} seconds")
        logger.info(f"Actions generated: {turn_summary['total_actions']}")
        logger.info(f"Errors encountered: {len(turn_summary['errors'])}")
        
        # 将回合摘要记入战役日志，书写战术历史的新章...
        turn_end_event = f"TURN {self.current_turn_number} COMPLETED"
        self.log_event(turn_end_event)
        
        # 将回合存储在世界状态历史中，为未来的策略分析提供参考...
        self._store_turn_in_history(turn_summary)
        
        return turn_summary
    
    def _prepare_world_state_for_agent(self, agent: PersonaAgent) -> Dict[str, Any]:
        """
        Prepare world state information for a specific agent's decision-making.
        
        This method creates a customized world state update tailored to what the
        specific agent would know and perceive. Currently implements placeholder
        logic for Phase 1 - Phase 2 will include sophisticated information filtering
        based on agent location, capabilities, and knowledge networks.
        
        Args:
            agent: PersonaAgent instance to prepare world state for
            
        Returns:
            Dict containing world state information relevant to the agent
        """
        # 占位世界状态圣典 - 第二阶段将实现复杂的世界状态管理系统...
        world_state_update = {
            # 在根级添加回合编号，保证测试兼容性的神圣统一...
            'turn_number': self.current_turn_number,
            'world_state': {
                'current_turn': self.current_turn_number,
                'total_agents': len(self.registered_agents),
                'simulation_time': datetime.now().isoformat(),
            },
            'location_updates': {
                'current_area': {
                    'threat_level': 'moderate',
                    'faction_presence': 'mixed',
                    'resources_available': True,
                    'strategic_importance': 'normal',
                }
            },
            'entity_updates': {
                # 关于其他代理/实体的信息，代理可能知晓的情报网络...
            },
            'faction_updates': {
                'imperium': {'activity': 'normal', 'influence': 0.6},
                'chaos': {'activity': 'low', 'influence': 0.2},
                'ork': {'activity': 'moderate', 'influence': 0.2},
            },
            'recent_events': [
                {
                    'id': f'event_{self.current_turn_number}',
                    'type': 'world_update',
                    'description': 'The world is calm, but tensions remain',
                    'scope': 'local',
                    'location': 'simulation_space',
                }
            ],
            'turn_info': {
                'current_turn': self.current_turn_number,
                'total_agents': len(self.registered_agents),
                'simulation_time': datetime.now().isoformat(),
            }
        }
        
        # 添加其他已注册代理的信息（如果他们会知晓的话），构建情报网络...
        other_agents = {}
        for other_agent in self.registered_agents:
            if other_agent.agent_id != agent.agent_id:
                other_agents[other_agent.agent_id] = {
                    'name': other_agent.character_data.get('name', 'Unknown'),
                    'faction': other_agent.subjective_worldview.get('primary_faction', 'Unknown'),
                    'status': other_agent.current_status,
                    'last_seen': 'recently',
                }
        
        world_state_update['entity_updates'] = other_agents
        
        return world_state_update
    
    def _store_turn_in_history(self, turn_summary: Dict[str, Any]) -> None:
        """
        Store turn summary in world state history for future reference.
        
        Maintains a history of all turns for analysis and potential AI integration.
        Implements memory management to prevent unbounded growth.
        
        Args:
            turn_summary: Complete turn summary data to store
        """
        try:
            # 初始化回合历史数据库（如果不存在），建立战术记忆檔案...
            if 'turn_history' not in self.world_state_data:
                self.world_state_data['turn_history'] = []
            
            # 将回合数据添加到历史记录，积累战术智慧与经验...
            self.world_state_data['turn_history'].append(turn_summary)
            
            # Implement memory management - keep only configured number of turns
            max_history_length = self.max_turn_history
            if len(self.world_state_data['turn_history']) > max_history_length:
                self.world_state_data['turn_history'] = self.world_state_data['turn_history'][-max_history_length:]
                logger.info(f"Turn history trimmed to last {max_history_length} turns")
            
            logger.debug(f"Turn {turn_summary['turn_number']} stored in history")
            
        except Exception as e:
            logger.error(f"Failed to store turn in history: {str(e)}")
    
    # Utility methods for director management and debugging
    
    def get_simulation_status(self) -> Dict[str, Any]:
        """
        Get comprehensive status information about the current simulation state.
        
        Returns:
            Dict containing detailed simulation status information
        """
        current_time = datetime.now()
        simulation_duration = (current_time - self.simulation_start_time).total_seconds()
        
        # Calculate agent statistics
        agent_stats = {}
        for agent in self.registered_agents:
            character_name = agent.character_data.get('name', 'Unknown')
            faction = agent.subjective_worldview.get('primary_faction', 'Unknown')
            agent_stats[agent.agent_id] = {
                'name': character_name,
                'faction': faction,
                'status': agent.current_status,
                'morale': agent.morale_level,
            }
        
        return {
            'simulation_info': {
                'start_time': self.simulation_start_time.isoformat(),
                'current_time': current_time.isoformat(),
                'duration_seconds': simulation_duration,
                'current_turn': self.current_turn_number,
                'total_actions_processed': self.total_actions_processed,
            },
            'agents': {
                'total_registered': len(self.registered_agents),
                'agent_details': agent_stats,
            },
            'system_health': {
                'error_count': self.error_count,
                'last_error_time': self.last_error_time.isoformat() if self.last_error_time else None,
                'campaign_log_path': self.campaign_log_path,
                'world_state_file': self.world_state_file_path,
            },
            'world_state': {
                'locations_tracked': len(self.world_state_data.get('locations', {})),
                'factions_tracked': len(self.world_state_data.get('factions', {})),
                'turn_history_length': len(self.world_state_data.get('turn_history', [])),
            }
        }
    
    def get_agent_list(self) -> List[Dict[str, str]]:
        """
        Get a list of all registered agents with basic information.
        
        Returns:
            List of dictionaries containing agent information
        """
        agent_list = []
        for agent in self.registered_agents:
            character_name = agent.character_data.get('name', 'Unknown')
            faction = agent.subjective_worldview.get('primary_faction', 'Unknown')
            
            agent_list.append({
                'agent_id': agent.agent_id,
                'character_name': character_name,
                'faction': faction,
                'status': agent.current_status,
            })
        
        return agent_list
    
    def remove_agent(self, agent_id: str) -> bool:
        """
        Remove an agent from the simulation.
        
        Args:
            agent_id: ID of the agent to remove
            
        Returns:
            bool: True if agent was found and removed, False otherwise
        """
        try:
            for i, agent in enumerate(self.registered_agents):
                if agent.agent_id == agent_id:
                    removed_agent = self.registered_agents.pop(i)
                    character_name = removed_agent.character_data.get('name', 'Unknown')
                    
                    logger.info(f"Agent removed: {agent_id} ({character_name})")
                    
                    # Log removal event
                    removal_event = (
                        f"**Agent Departure:** {character_name} ({agent_id}) left the simulation\\n"
                        f"**Departure Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n"
                        f"**Remaining Agents:** {len(self.registered_agents)}"
                    )
                    self.log_event(removal_event)
                    
                    return True
            
            logger.warning(f"Agent not found for removal: {agent_id}")
            return False
            
        except Exception as e:
            logger.error(f"Error removing agent {agent_id}: {str(e)}")
            return False
    
    def save_world_state(self, file_path: Optional[str] = None) -> bool:
        """
        Save current world state to file.
        
        Args:
            file_path: Optional path to save to (uses default if None)
            
        Returns:
            bool: True if save successful, False otherwise
        """
        try:
            save_path = file_path or self.world_state_file_path or "world_state_backup.json"
            
            # Add current timestamp to world state
            self.world_state_data['last_saved'] = datetime.now().isoformat()
            self.world_state_data['save_info'] = {
                'turn_number': self.current_turn_number,
                'total_agents': len(self.registered_agents),
                'total_actions': self.total_actions_processed,
            }
            
            with open(save_path, 'w', encoding='utf-8') as file:
                json.dump(self.world_state_data, file, indent=2, ensure_ascii=False)
            
            logger.info(f"World state saved to: {save_path}")
            self.log_event(f"World state saved to {save_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save world state: {str(e)}")
            return False
    
    def close_campaign_log(self) -> None:
        """
        Properly close the campaign log with summary information.
        
        Adds final summary statistics and closing information to the campaign log.
        Should be called when simulation ends or director is being shut down.
        """
        try:
            end_time = datetime.now()
            simulation_duration = (end_time - self.simulation_start_time).total_seconds()
            
            closing_summary = f"""

## Campaign Summary

**Simulation End Time:** {end_time.strftime('%Y-%m-%d %H:%M:%S')}  
**Total Duration:** {simulation_duration:.2f} seconds ({simulation_duration/60:.1f} minutes)  
**Turns Executed:** {self.current_turn_number}  
**Total Actions Processed:** {self.total_actions_processed}  
**Agents Participated:** {len(self.registered_agents)}  
**System Errors:** {self.error_count}  

### Final Agent Roster

"""
            
            for agent in self.registered_agents:
                character_name = agent.character_data.get('name', 'Unknown')
                faction = agent.subjective_worldview.get('primary_faction', 'Unknown')
                closing_summary += f"- **{character_name}** ({agent.agent_id}) - {faction}\\n"
            
            closing_summary += """

**Campaign Status:** Simulation completed successfully  
**Log Generated By:** DirectorAgent v1.0 - Warhammer 40k Multi-Agent Simulator  

---

*For the Emperor! In the grim darkness of the far future, there is only war...*
"""
            
            with open(self.campaign_log_path, 'a', encoding='utf-8') as file:
                file.write(closing_summary)
            
            logger.info("Campaign log closed with summary")
            
        except Exception as e:
            logger.error(f"Failed to close campaign log properly: {str(e)}")


# Utility functions for DirectorAgent management

def create_director_with_agents(world_state_path: Optional[str] = None, 
                               character_sheet_paths: Optional[List[str]] = None) -> Tuple[DirectorAgent, List[bool]]:
    """
    Utility function to create a DirectorAgent and register multiple agents at once.
    
    Args:
        world_state_path: Optional path to world state file
        character_sheet_paths: List of paths to character sheet files
        
    Returns:
        Tuple of (DirectorAgent instance, list of registration success booleans)
    """
    director = DirectorAgent(world_state_path)
    registration_results = []
    
    if character_sheet_paths:
        for sheet_path in character_sheet_paths:
            try:
                agent = PersonaAgent(sheet_path)
                success = director.register_agent(agent)
                registration_results.append(success)
            except Exception as e:
                logger.error(f"Failed to create agent from {sheet_path}: {e}")
                registration_results.append(False)
    
    return director, registration_results


def run_simulation_batch(director: DirectorAgent, num_turns: int) -> List[Dict[str, Any]]:
    """
    Utility function to run multiple simulation turns in batch.
    
    Args:
        director: DirectorAgent instance to run
        num_turns: Number of turns to execute
        
    Returns:
        List of turn summary dictionaries
    """
    turn_results = []
    
    logger.info(f"Starting batch simulation: {num_turns} turns")
    
    for turn_num in range(num_turns):
        try:
            turn_result = director.run_turn()
            turn_results.append(turn_result)
            
            logger.info(f"Batch turn {turn_num + 1}/{num_turns} completed")
            
        except Exception as e:
            logger.error(f"Batch simulation failed at turn {turn_num + 1}: {e}")
            break
    
    logger.info(f"Batch simulation completed: {len(turn_results)} turns executed")
    
    return turn_results


# Example usage and testing functions

def example_usage():
    """
    Example usage of the DirectorAgent class.
    
    Demonstrates how to create and use DirectorAgent for orchestrating
    multi-agent simulations.
    """
    print("DirectorAgent Example Usage:")
    print("============================")
    
    try:
        # Create DirectorAgent
        director = DirectorAgent()
        print(f"✓ DirectorAgent created successfully")
        print(f"  Campaign log: {director.campaign_log_path}")
        
        # Example agent registration (would need actual character sheet file)
        # agent = PersonaAgent("test_character.md")
        # success = director.register_agent(agent)
        # print(f"✓ Agent registration: {'Success' if success else 'Failed'}")
        
        # Example turn execution
        # turn_result = director.run_turn()
        # print(f"✓ Turn executed: {turn_result['total_actions']} actions generated")
        
        # Get simulation status
        status = director.get_simulation_status()
        print(f"✓ Simulation status: {status['agents']['total_registered']} agents registered")
        
        # Close campaign log
        director.close_campaign_log()
        print(f"✓ Campaign log closed successfully")
        
        print("\nDirectorAgent is ready for multi-agent orchestration!")
        
    except Exception as e:
        print(f"✗ Example failed: {e}")


if __name__ == "__main__":
    # Run example usage when script is executed directly
    example_usage()