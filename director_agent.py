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
from persona_agent import PersonaAgent
from shared_types import CharacterAction

# 引入配置系统圣典，获取指挥中心的运行参数...
from config_loader import get_config, get_campaign_log_filename

# 引入叙事引擎组件，将史诗传说融入模拟系统...
from campaign_brief import CampaignBrief, CampaignBriefLoader, NarrativeEvent
from narrative_actions import NarrativeActionResolver, NarrativeOutcome


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
    
    def __init__(self, world_state_file_path: Optional[str] = None, campaign_log_path: Optional[str] = None, campaign_brief_path: Optional[str] = None):
        """
        Initialize the DirectorAgent with optional world state file integration and narrative campaign brief.
        
        Sets up the core director infrastructure including agent registry,
        campaign logging system, world state management preparation, and narrative engine.
        Handles file operations with comprehensive error checking.
        
        Args:
            world_state_file_path: Optional path to world state database file
                                  (prepared for future Phase 2 integration)
                                  If provided, attempts to load existing world state
                                  If None, uses configuration or defaults
            campaign_log_path: Optional path to campaign log file
                             If None, uses configuration value
            campaign_brief_path: Optional path to campaign brief YAML/Markdown file
                               Defines narrative context for story-driven simulation
                               If None, simulation runs in basic combat mode
                                  
        Raises:
            ValueError: If files are provided but malformed
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
        
        # 叙事引擎组件初始化，启动史诗传说生成系统...
        self.campaign_brief_path = campaign_brief_path
        """Path to campaign brief file for narrative context"""
        
        self.campaign_brief: Optional[CampaignBrief] = None
        """Loaded campaign brief defining narrative context"""
        
        self.narrative_resolver = NarrativeActionResolver()
        """Resolver for story-driven actions and outcomes"""
        
        self.story_state = {
            'current_phase': 'initialization',
            'triggered_events': [],
            'story_progression': [],
            'investigation_count': 0,
            'dialogue_count': 0,
            'character_relationships': {}
        }
        """Current narrative state tracking"""
        
        # 世界之心系统 - 动态世界状态追踪器，记录代理行动对世界的影响...
        self.world_state_tracker = {
            'discovered_clues': {},  # agent_id -> list of discovered clues
            'environmental_changes': {},  # location -> list of changes
            'agent_discoveries': {},  # turn_number -> {agent_id: discoveries}
            'temporal_markers': {},  # timestamp -> events
            'investigation_history': []  # chronological list of all investigations
        }
        """Dynamic world state tracker - Heart of the World system"""
        
        # 初始化指挥系统，唤醒Game Master AI的核心机器灵魂...
        try:
            self._initialize_campaign_log()
            self._load_world_state()
            self._load_campaign_brief()
            
            logger.info(f"DirectorAgent initialized successfully")
            logger.info(f"Campaign log: {self.campaign_log_path}")
            logger.info(f"World state file: {self.world_state_file_path or 'None (using defaults)'}")
            logger.info(f"Campaign brief: {self.campaign_brief_path or 'None (combat mode)'}")
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
    
    def _load_campaign_brief(self) -> None:
        """
        Load campaign brief file to define narrative context for story-driven simulation.
        
        Campaign briefs transform the simulation from basic combat mechanics to rich
        story-driven character interactions. If no brief is provided, simulation
        runs in traditional combat-focused mode.
        
        Raises:
            ValueError: If campaign brief file exists but contains invalid data
            OSError: If file operations fail
        """
        if self.campaign_brief_path is None:
            logger.info("No campaign brief specified - running in combat mode")
            self.narrative_resolver = NarrativeActionResolver(None)
            return
        
        try:
            campaign_brief_path = Path(self.campaign_brief_path)
            
            if not campaign_brief_path.exists():
                logger.warning(f"Campaign brief file not found: {self.campaign_brief_path}")
                logger.info("Running in combat mode without narrative context")
                self.narrative_resolver = NarrativeActionResolver(None)
                return
            
            # 加载战役背景圣典，获取史诗传说的叙事指导...
            logger.info(f"Loading campaign brief from: {self.campaign_brief_path}")
            
            brief_loader = CampaignBriefLoader()
            self.campaign_brief = brief_loader.load_from_file(campaign_brief_path)
            
            # 验证战役背景完整性，确保史诗传说的神圣结构...
            brief_loader.validate_campaign_brief(self.campaign_brief)
            
            # 初始化叙事解析器，连接史诗传说与模拟现实...
            self.narrative_resolver = NarrativeActionResolver(self.campaign_brief)
            
            # 更新故事状态，开启叙事引擎的神圣仪式...
            self.story_state['current_phase'] = 'campaign_loaded'
            
            logger.info(f"Campaign brief loaded successfully: {self.campaign_brief.title}")
            logger.info(f"Setting: {self.campaign_brief.setting[:100]}...")
            logger.info(f"Narrative events available: {len(self.campaign_brief.key_events)}")
            
            # 触发初始化叙事事件，启动史诗传说的开端...
            self._trigger_initial_narrative_events()
            
        except Exception as e:
            logger.error(f"Failed to load campaign brief: {str(e)}")
            logger.warning("Falling back to combat mode")
            self.campaign_brief = None
            self.narrative_resolver = NarrativeActionResolver(None)
    
    def _trigger_initial_narrative_events(self) -> None:
        """
        Trigger initial narrative events marked for simulation start.
        
        Processes campaign brief events with 'simulation_start' trigger condition
        to establish the initial story context for all agents.
        """
        if not self.campaign_brief:
            return
        
        for event in self.campaign_brief.key_events:
            if event.trigger_condition == "simulation_start":
                logger.info(f"Triggering initial narrative event: {event.description}")
                
                # 将事件添加到故事状态，记录史诗传说的重要时刻...
                self.story_state['triggered_events'].append({
                    'event': event,
                    'turn_triggered': 0,
                    'timestamp': datetime.now().isoformat()
                })
                
                # 将叙事事件记录到战役日志，书写史诗传说的新章节...
                event_description = f"**NARRATIVE EVENT:** {event.description}"
                self.log_event(event_description)
    
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
                    
                    # 处理叙事行动结果，生成故事驱动的后果...
                    narrative_outcome = self._process_narrative_action(agent_action, agent)
                    if narrative_outcome:
                        turn_summary['agent_actions'][agent.agent_id]['narrative_outcome'] = {
                            'success': narrative_outcome.success,
                            'description': narrative_outcome.description,
                            'story_advancement': narrative_outcome.story_advancement,
                            'relationship_changes': narrative_outcome.relationship_changes,
                            'discovered_information': narrative_outcome.discovered_information
                        }
                        
                        # 记录叙事结果到战役日志
                        self.log_event(f"NARRATIVE OUTCOME: {narrative_outcome.description}")
                        
                        # 更新故事状态
                        self._update_story_state(narrative_outcome)
                    
                    # 世界之心系统 - 处理行动对世界状态的影响...
                    self._process_action_world_impact(agent_action, agent)
                    
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
        
        This method creates a customized world state update that includes both tactical
        information and rich narrative context when a campaign brief is loaded. The
        agent receives character-specific story elements alongside traditional simulation data.
        
        Args:
            agent: PersonaAgent instance to prepare world state for
            
        Returns:
            Dict containing world state information and narrative context relevant to the agent
        """
        # 基础世界状态更新，维持战术模拟的核心功能...
        world_state_update = {
            # 在根级添加回合编号，保证测试兼容性的神圣统一...
            'current_turn': self.current_turn_number,
            'simulation_time': datetime.now().isoformat(),
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
        
        # 世界之心系统 - 添加动态世界状态反馈...
        world_state_feedback = self._generate_world_state_feedback(agent.agent_id)
        if world_state_feedback:
            world_state_update['world_state_feedback'] = world_state_feedback
            logger.debug(f"Added dynamic world state feedback for agent {agent.agent_id}")
        
        # 生成叙事上下文更新，注入史诗传说的故事元素...
        narrative_context = self.generate_narrative_context(agent.agent_id)
        if narrative_context:
            world_state_update['narrative_context'] = narrative_context
            logger.debug(f"Added narrative context for agent {agent.agent_id}")
        
        return world_state_update
    
    def _generate_world_state_feedback(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Generate dynamic world state feedback based on agent discoveries and world changes.
        
        This method creates the feedback that agents receive about the consequences of
        their previous actions and the evolving state of the world. It's the core
        implementation of the "Heart of the World" feedback loop.
        
        Args:
            agent_id: ID of the agent to generate feedback for
            
        Returns:
            Dictionary containing world state feedback or None if no feedback available
        """
        feedback = {}
        has_feedback = False
        
        try:
            # 生成个人发现反馈 - "你发现了一条新的线索"
            personal_discoveries = self._get_agent_discoveries_feedback(agent_id)
            if personal_discoveries:
                feedback['personal_discoveries'] = personal_discoveries
                has_feedback = True
            
            # 生成环境变化反馈
            environmental_changes = self._get_environmental_changes_feedback(agent_id)
            if environmental_changes:
                feedback['environmental_changes'] = environmental_changes
                has_feedback = True
            
            # 生成其他代理活动反馈
            other_agent_activities = self._get_other_agents_activities_feedback(agent_id)
            if other_agent_activities:
                feedback['other_agent_activities'] = other_agent_activities
                has_feedback = True
            
            # 生成世界状态总览
            world_state_summary = self._get_world_state_summary()
            if world_state_summary:
                feedback['world_state_summary'] = world_state_summary
                has_feedback = True
            
            return feedback if has_feedback else None
            
        except Exception as e:
            logger.error(f"Error generating world state feedback for {agent_id}: {str(e)}")
            return None
    
    def _get_agent_discoveries_feedback(self, agent_id: str) -> List[str]:
        """
        Get feedback about the agent's recent discoveries.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            List of discovery feedback messages
        """
        feedback_messages = []
        
        # 检查该代理最近的发现
        if agent_id in self.world_state_tracker['discovered_clues']:
            agent_clues = self.world_state_tracker['discovered_clues'][agent_id]
            
            # 获取本回合或上回合的发现
            recent_clues = [
                clue for clue in agent_clues 
                if clue['turn_discovered'] >= self.current_turn_number - 1
            ]
            
            for clue in recent_clues:
                if clue['turn_discovered'] == self.current_turn_number - 1:
                    # 上一回合的发现 - 满足神圣验证标准
                    feedback_messages.append(f"你发现了一条新的线索：{clue['content']}")
                elif clue['turn_discovered'] == self.current_turn_number:
                    # 本回合的发现 - 即时反馈
                    feedback_messages.append(f"你刚刚发现：{clue['content']}")
        
        return feedback_messages
    
    def _get_environmental_changes_feedback(self, agent_id: str) -> List[str]:
        """
        Get feedback about environmental changes visible to the agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            List of environmental change messages
        """
        feedback_messages = []
        
        # 检查环境变化
        for location, changes_list in self.world_state_tracker['environmental_changes'].items():
            recent_changes = [
                change for change in changes_list 
                if change['turn'] >= self.current_turn_number - 2  # 看到过去2回合的变化
            ]
            
            for change in recent_changes:
                if change['agent'] != agent_id:  # 不显示自己造成的变化
                    feedback_messages.append(f"在{location}，{change['change']}")
                else:
                    # 显示自己行动的持续影响
                    if change['turn'] < self.current_turn_number:
                        feedback_messages.append(f"你之前在{location}的调查留下了明显痕迹")
        
        return feedback_messages
    
    def _get_other_agents_activities_feedback(self, agent_id: str) -> List[str]:
        """
        Get feedback about other agents' activities and discoveries.
        
        Args:
            agent_id: ID of the requesting agent
            
        Returns:
            List of other agents' activity messages
        """
        feedback_messages = []
        
        # 检查其他代理的最近发现
        current_turn = self.current_turn_number
        for turn_num in range(max(1, current_turn - 2), current_turn + 1):
            if turn_num in self.world_state_tracker['agent_discoveries']:
                turn_discoveries = self.world_state_tracker['agent_discoveries'][turn_num]
                
                for other_agent_id, discoveries in turn_discoveries.items():
                    if other_agent_id != agent_id:  # 不包括自己
                        # 查找代理名称
                        other_agent_name = "另一名代理"
                        for agent in self.registered_agents:
                            if agent.agent_id == other_agent_id:
                                other_agent_name = agent.character_data.get('name', '未知代理')
                                break
                        
                        for discovery in discoveries:
                            if turn_num == current_turn - 1:
                                feedback_messages.append(f"{other_agent_name} 最近发现了：{discovery}")
                            elif turn_num == current_turn:
                                feedback_messages.append(f"{other_agent_name} 刚刚发现了：{discovery}")
        
        return feedback_messages
    
    def _get_world_state_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current world state.
        
        Returns:
            Dictionary containing world state summary information
        """
        total_clues = sum(len(clues) for clues in self.world_state_tracker['discovered_clues'].values())
        total_investigations = len(self.world_state_tracker['investigation_history'])
        total_locations_investigated = len(self.world_state_tracker['environmental_changes'])
        
        return {
            'total_clues_discovered': total_clues,
            'total_investigations': total_investigations,
            'locations_with_activity': total_locations_investigated,
            'current_phase': self.story_state.get('current_phase', 'unknown'),
            'world_activity_level': 'active' if total_investigations > 0 else 'quiet'
        }
    
    def generate_narrative_context(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Generate narrative context for a specific agent based on current story state.
        
        Creates rich story elements that transform basic simulation updates into
        compelling narrative situations. Character-specific context is tailored
        to their faction, personality, and relationship to the ongoing story.
        
        Args:
            agent_id: ID of the agent to generate context for
            
        Returns:
            Dict containing narrative context or None if no campaign brief loaded
        """
        if not self.campaign_brief:
            return None
        
        try:
            # 查找对应的代理以获取角色数据，连接叙事与人格机灵...
            target_agent = None
            for agent in self.registered_agents:
                if agent.agent_id == agent_id:
                    target_agent = agent
                    break
            
            if not target_agent:
                logger.warning(f"Could not find agent {agent_id} for narrative context generation")
                return None
            
            # 基础叙事上下文结构，包含史诗传说的核心元素...
            narrative_context = {
                'campaign_title': self.campaign_brief.title,
                'setting_description': self.campaign_brief.setting,
                'atmosphere': self.campaign_brief.atmosphere,
                'current_phase': self.story_state['current_phase'],
                'environmental_elements': [],
                'character_specific_context': '',
                'active_story_threads': [],
                'available_narrative_actions': []
            }
            
            # 添加环境叙事元素，构建故事的物理背景...
            if self.campaign_brief.environmental_elements:
                # 选择相关的环境元素（最多3个以避免信息过载）
                selected_elements = self.campaign_brief.environmental_elements[:3]
                narrative_context['environmental_elements'] = selected_elements
            
            # 生成角色特定的叙事上下文，定制史诗传说的个人体验...
            character_context = self._generate_character_specific_context(target_agent)
            narrative_context['character_specific_context'] = character_context
            
            # 检查触发的叙事事件，激活史诗传说的关键时刻...
            active_events = self._check_narrative_event_triggers(target_agent)
            if active_events:
                narrative_context['active_story_threads'] = active_events
            
            # 添加可用的叙事行动选项，为角色提供故事选择...
            narrative_actions = self._identify_available_narrative_actions(target_agent)
            narrative_context['available_narrative_actions'] = narrative_actions
            
            return narrative_context
            
        except Exception as e:
            logger.error(f"Failed to generate narrative context for agent {agent_id}: {str(e)}")
            return None
    
    def _generate_character_specific_context(self, agent: PersonaAgent) -> str:
        """
        Generate character-specific narrative context based on their faction and traits.
        
        Args:
            agent: PersonaAgent to generate context for
            
        Returns:
            String containing personalized narrative context
        """
        character_name = agent.character_data.get('name', 'Unknown')
        faction = agent.subjective_worldview.get('primary_faction', 'Unknown')
        
        # 基础角色情境描述...
        base_context = f"As {character_name} of {faction}, you find yourself in this unfolding story."
        
        # 根据派系添加特定的叙事视角...
        if 'imperial' in faction.lower():
            imperial_context = " Your duty to the Emperor guides your perception of these events."
            base_context += imperial_context
        elif 'ork' in faction.lower():
            ork_context = " Your ork instincts tell you there's a good fight brewing here."
            base_context += ork_context
        elif 'mechanicus' in faction.lower():
            mechanicus_context = " Your augmetic senses detect deeper mysteries in the machine spirits here."
            base_context += mechanicus_context
        
        # 添加当前故事阶段的角色体验...
        if self.story_state['current_phase'] == 'investigation':
            base_context += " The mysteries here call for careful investigation."
        elif self.story_state['current_phase'] == 'revelation':
            base_context += " The truth begins to reveal itself through your actions."
        
        return base_context
    
    def _check_narrative_event_triggers(self, agent: PersonaAgent) -> List[Dict[str, Any]]:
        """
        Check which narrative events should trigger for the current turn and agent.
        
        Args:
            agent: Agent to check event triggers for
            
        Returns:
            List of active narrative events
        """
        active_events = []
        
        for event in self.campaign_brief.key_events:
            should_trigger = False
            
            # 检查基于回合的触发条件...
            if 'turn >=' in event.trigger_condition:
                try:
                    required_turn = int(event.trigger_condition.split('>=')[1].strip())
                    if self.current_turn_number >= required_turn:
                        should_trigger = True
                except ValueError:
                    logger.warning(f"Invalid turn trigger condition: {event.trigger_condition}")
            
            # 检查基于调查数量的触发条件...
            elif 'investigation_count >=' in event.trigger_condition:
                try:
                    required_count = int(event.trigger_condition.split('>=')[1].strip())
                    if self.story_state['investigation_count'] >= required_count:
                        should_trigger = True
                except ValueError:
                    logger.warning(f"Invalid investigation trigger condition: {event.trigger_condition}")
            
            # 如果事件应该触发且尚未触发过...
            if should_trigger:
                # 检查是否已经触发过此事件
                already_triggered = any(
                    triggered['event'].description == event.description 
                    for triggered in self.story_state['triggered_events']
                )
                
                if not already_triggered:
                    # 添加到已触发事件列表
                    self.story_state['triggered_events'].append({
                        'event': event,
                        'turn_triggered': self.current_turn_number,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    # 创建活跃事件描述
                    active_event = {
                        'description': event.description,
                        'character_impact': event.character_impact.get(agent.agent_id, 
                                          event.character_impact.get('all', '')),
                        'environmental_change': event.environmental_change
                    }
                    active_events.append(active_event)
        
        return active_events
    
    def _identify_available_narrative_actions(self, agent: PersonaAgent) -> List[str]:
        """
        Identify narrative actions available to the character in current context.
        
        Args:
            agent: Agent to identify actions for
            
        Returns:
            List of available narrative action names
        """
        available_actions = ['investigate', 'observe_environment']  # Always available
        
        # 添加基于故事状态的行动选项...
        if self.story_state['investigation_count'] > 0:
            available_actions.append('analyze_data')
        
        if len(self.registered_agents) > 1:
            available_actions.extend(['dialogue', 'communicate_faction'])
        
        # 添加基于角色特征的行动选项...
        personality_traits = agent.personality_traits
        decision_weights = agent.decision_weights
        
        if decision_weights.get('personal_relationships', 0) > 0.6:
            available_actions.append('diplomacy')
        
        if personality_traits.get('aggressive', 0) < 0.3 and personality_traits.get('cautious', 0) > 0.6:
            available_actions.append('search_area')
        
        # 移除重复项并返回
        return list(set(available_actions))
    
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
    
    def _process_narrative_action(self, action: 'CharacterAction', agent: 'PersonaAgent') -> Optional['NarrativeOutcome']:
        """
        Process narrative actions and generate story-driven outcomes.
        
        This method handles story actions like investigation, dialogue, diplomacy, and betrayal
        by using the narrative action resolver to create meaningful story consequences.
        
        Args:
            action: The character action to process
            agent: The agent who performed the action
            
        Returns:
            NarrativeOutcome if the action is narrative-based, None otherwise
        """
        if not hasattr(action, 'action_type'):
            return None
        
        # Check if this is a narrative action
        narrative_action_types = ['investigate', 'dialogue', 'diplomacy', 'betrayal', 
                                 'observe_environment', 'communicate_faction']
        
        if action.action_type not in narrative_action_types:
            return None
        
        logger.info(f"Processing narrative action: {action.action_type} by {agent.agent_id}")
        
        # Get character data for narrative processing
        character_data = {
            'agent_id': agent.agent_id,
            'name': agent.character_data.get('name', 'Unknown'),
            'faction': agent.character_data.get('faction', 'Unknown'),
            'personality_traits': agent.personality_traits,
            'decision_weights': agent.decision_weights
        }
        
        # Get current world state for context
        world_state = {
            'current_turn': self.current_turn_number,
            'story_state': self.story_state,
            'campaign_brief': self.campaign_brief
        }
        
        # Use narrative resolver to process the action
        try:
            if action.action_type == 'investigate':
                outcome = self.narrative_resolver.resolve_investigate_action(action, character_data, world_state)
            elif action.action_type == 'dialogue':
                outcome = self.narrative_resolver.resolve_dialogue_action(action, character_data, world_state)
            elif action.action_type == 'diplomacy':
                outcome = self.narrative_resolver.resolve_diplomacy_action(action, character_data, world_state)
            elif action.action_type == 'betrayal':
                outcome = self.narrative_resolver.resolve_betrayal_action(action, character_data, world_state)
            else:
                # Handle other narrative actions as investigation-type
                outcome = self.narrative_resolver.resolve_investigate_action(action, character_data, world_state)
            
            return outcome
            
        except Exception as e:
            logger.error(f"Error processing narrative action {action.action_type}: {str(e)}")
            return None
    
    def _update_story_state(self, narrative_outcome: 'NarrativeOutcome') -> None:
        """
        Update the story state based on narrative action outcomes.
        
        This method processes the consequences of narrative actions and updates
        the ongoing story progression markers and character relationships.
        
        Args:
            narrative_outcome: The outcome of a narrative action to process
        """
        try:
            # Update story progression markers
            for advancement in narrative_outcome.story_advancement:
                if advancement not in self.story_state['story_progression']:
                    self.story_state['story_progression'].append(advancement)
                    logger.info(f"Story advancement: {advancement}")
            
            # Update character relationships
            for character, change in narrative_outcome.relationship_changes.items():
                if character not in self.story_state['character_relationships']:
                    self.story_state['character_relationships'][character] = 0.0
                
                self.story_state['character_relationships'][character] += change
                logger.info(f"Relationship change: {character} {change:+.2f} (now {self.story_state['character_relationships'][character]:.2f})")
            
            # Track investigation count for event triggers
            if 'investigation' in str(narrative_outcome.description).lower():
                self.story_state['investigation_count'] += 1
            
            # Track dialogue count for event triggers
            if 'dialogue' in str(narrative_outcome.description).lower() or 'communication' in str(narrative_outcome.description).lower():
                self.story_state['dialogue_count'] += 1
            
            # Update story phase based on progression
            total_investigations = self.story_state['investigation_count']
            total_dialogues = self.story_state['dialogue_count']
            
            if total_investigations >= 3 and self.story_state['current_phase'] == 'initialization':
                self.story_state['current_phase'] = 'investigation_phase'
                logger.info("Story phase advanced to: investigation_phase")
            
            if total_dialogues >= 2 and total_investigations >= 2:
                self.story_state['current_phase'] = 'interaction_phase'
                logger.info("Story phase advanced to: interaction_phase")
                
        except Exception as e:
            logger.error(f"Error updating story state: {str(e)}")
    
    def _process_action_world_impact(self, action: 'CharacterAction', agent: 'PersonaAgent') -> None:
        """
        Process Agent action and update world state tracker accordingly.
        
        This method analyzes PersonaAgent actions and updates the world_state_tracker
        to reflect the impact of actions on the world. Creates discoverable content
        for investigation actions and tracks environmental changes.
        
        Args:
            action: The character action being processed
            agent: The agent who performed the action
        """
        if not hasattr(action, 'action_type'):
            return
        
        try:
            action_type = action.action_type.lower()
            agent_id = agent.agent_id
            character_name = agent.character_data.get('name', 'Unknown')
            current_turn = self.current_turn_number
            timestamp = datetime.now().isoformat()
            
            # 处理调查类行动 - 生成可发现的线索
            if action_type in ['investigate', 'search', 'analyze', 'explore']:
                self._process_investigation_impact(action, agent_id, character_name, current_turn, timestamp)
            
            # 记录所有行动到历史记录
            self._record_action_to_history(action, agent_id, character_name, current_turn, timestamp)
            
            logger.info(f"World state updated for {action_type} action by {character_name}")
            
        except Exception as e:
            logger.error(f"Error processing action world impact: {str(e)}")
    
    def _process_investigation_impact(self, action: 'CharacterAction', agent_id: str, 
                                    character_name: str, turn_number: int, timestamp: str) -> None:
        """
        Process investigation-type actions and generate discoverable clues.
        
        Args:
            action: The investigation action
            agent_id: ID of the investigating agent
            character_name: Name of the investigating character
            turn_number: Current turn number
            timestamp: Action timestamp
        """
        target = action.target or 'unknown_area'
        
        # 生成基于目标的线索内容
        clue_content = self._generate_clue_content(target, character_name, action.action_type)
        
        # 更新发现的线索
        if agent_id not in self.world_state_tracker['discovered_clues']:
            self.world_state_tracker['discovered_clues'][agent_id] = []
        
        clue_entry = {
            'content': clue_content,
            'target': target,
            'turn_discovered': turn_number,
            'timestamp': timestamp,
            'discoverer': character_name
        }
        
        self.world_state_tracker['discovered_clues'][agent_id].append(clue_entry)
        
        # 更新代理发现记录
        if turn_number not in self.world_state_tracker['agent_discoveries']:
            self.world_state_tracker['agent_discoveries'][turn_number] = {}
        
        if agent_id not in self.world_state_tracker['agent_discoveries'][turn_number]:
            self.world_state_tracker['agent_discoveries'][turn_number][agent_id] = []
        
        self.world_state_tracker['agent_discoveries'][turn_number][agent_id].append(clue_content)
        
        # 更新环境变化
        location = target
        if location not in self.world_state_tracker['environmental_changes']:
            self.world_state_tracker['environmental_changes'][location] = []
        
        environmental_change = f"Signs of {character_name}'s investigation are visible"
        self.world_state_tracker['environmental_changes'][location].append({
            'change': environmental_change,
            'turn': turn_number,
            'agent': character_name,
            'timestamp': timestamp
        })
        
        logger.info(f"Generated clue for {character_name}: {clue_content}")
    
    def _generate_clue_content(self, target: str, character_name: str, action_type: str) -> str:
        """
        Generate contextual clue content based on investigation target and character.
        
        Args:
            target: The target being investigated
            character_name: Name of the investigating character  
            action_type: Type of investigation action
            
        Returns:
            Generated clue content string
        """
        # 基础线索模板
        clue_templates = [
            f"Strange markings found on {target}",
            f"Hidden compartment discovered within {target}",
            f"Unusual energy readings detected from {target}",
            f"Fragmentary data logs recovered from {target}",
            f"Traces of recent activity around {target}",
            f"Concealed passage revealed behind {target}",
            f"Mysterious symbols etched into {target}",
            f"Evidence of tampering discovered on {target}"
        ]
        
        # 根据行动类型调整线索
        if action_type == 'analyze':
            analysis_clues = [
                f"Pattern analysis reveals {target} was modified recently",
                f"Chemical residue on {target} suggests Imperial presence",
                f"Structural damage to {target} indicates forced entry",
                f"Data corruption in {target} appears to be intentional"
            ]
            clue_templates.extend(analysis_clues)
        
        elif action_type == 'search':
            search_clues = [
                f"Careful search of {target} reveals hidden cache",
                f"Thorough examination of {target} uncovers secret mechanism",
                f"Methodical search discovers concealed items in {target}",
                f"Detailed search reveals unauthorized modifications to {target}"
            ]
            clue_templates.extend(search_clues)
        
        # 随机选择一个线索模板
        import random
        selected_clue = random.choice(clue_templates)
        
        return selected_clue
    
    def _record_action_to_history(self, action: 'CharacterAction', agent_id: str,
                                character_name: str, turn_number: int, timestamp: str) -> None:
        """
        Record action to investigation history for tracking.
        
        Args:
            action: The action being recorded
            agent_id: ID of the acting agent
            character_name: Name of the acting character
            turn_number: Current turn number
            timestamp: Action timestamp
        """
        history_entry = {
            'agent_id': agent_id,
            'character_name': character_name,
            'action_type': action.action_type,
            'target': action.target,
            'turn': turn_number,
            'timestamp': timestamp,
            'reasoning': action.reasoning or 'No reasoning provided'
        }
        
        self.world_state_tracker['investigation_history'].append(history_entry)
        
        # 更新时间标记
        self.world_state_tracker['temporal_markers'][timestamp] = {
            'turn': turn_number,
            'agent': character_name,
            'action': action.action_type,
            'description': f"{character_name} performed {action.action_type} on {action.target or 'unknown'}"
        }


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