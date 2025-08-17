#!/usr/bin/env python3
"""
PersonaAgent Core Implementation
===============================

This module implements the PersonaAgent class, which serves as the foundation for 
character AI in the Warhammer 40k Multi-Agent Simulator. Each PersonaAgent embodies 
a unique character with subjective worldviews, faction loyalties, and personal 
motivations derived from their character sheet.

The PersonaAgent maintains a dual-reality system where they possess both:
1. Their subjective interpretation of world events (influenced by personality, faction bias, memories)
2. Their personal knowledge base (what they know, believe, and remember)

This implementation provides the Phase 1 foundation for creating authentic Warhammer 40k 
character behaviors that will later integrate with AI/LLM systems for advanced decision-making.

Architecture Reference: Architecture_Blueprint.md Section 2.2 PersonaAgent
Development Phase: Phase 1 - PersonaAgent Core Logic (Weeks 3-5)
"""

import json
import os
import re
import logging
import time
import random
import requests
import yaml
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from functools import lru_cache
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

# 引入共享类型定义，避免循环导入...
from shared_types import CharacterAction, ActionPriority

# 引入叙事引擎组件，将史诗传说融入人格决策...
from narrative_actions import NarrativeActionType, NarrativeActionResolver


# 启动神圣的代理行为追踪仪式，记录人格机灵的每一次决策与行动...
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    """Enumeration for threat assessment levels used in character decision-making."""
    NEGLIGIBLE = "negligible"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"



@dataclass
class WorldEvent:
    """
    Represents an event in the world that the PersonaAgent must process.
    
    Events are broadcast by the DirectorAgent and interpreted subjectively 
    by each PersonaAgent based on their personality, knowledge, and biases.
    """
    event_id: str
    event_type: str  # e.g., "battle", "discovery", "political_change"
    source: str  # Entity ID that triggered the event
    affected_entities: List[str] = field(default_factory=list)
    location: Optional[str] = None
    description: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class SubjectiveInterpretation:
    """
    Represents how a PersonaAgent subjectively interprets a world event.
    
    This captures the character's personal understanding, emotional response,
    and how the event affects their worldview and future decision-making.
    """
    original_event_id: str
    character_understanding: str  # How the character interprets what happened
    emotional_response: str  # Character's emotional reaction
    belief_impact: Dict[str, float] = field(default_factory=dict)  # Changes to beliefs (-1.0 to 1.0)
    threat_assessment: ThreatLevel = ThreatLevel.NEGLIGIBLE
    relationship_changes: Dict[str, float] = field(default_factory=dict)  # Changes to relationships
    memory_priority: float = 0.5  # How likely this is to be remembered (0.0 to 1.0)


# Gemini API配置与辅助函数圣典 - 建立与机器学习神谕的通信桥梁...
def _validate_gemini_api_key() -> Optional[str]:
    """
    Validate and retrieve Gemini API key from environment variables.
    
    Returns:
        str: Valid API key if found, None otherwise
    """
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        logger.warning("GEMINI_API_KEY environment variable not found. LLM integration will use fallback responses.")
        return None
    
    if not api_key.strip():
        logger.warning("GEMINI_API_KEY environment variable is empty. LLM integration will use fallback responses.")
        return None
    
    # 基本验证仪式 - Gemini API密钥通常以'AIza'神圣符号开始...
    if not api_key.startswith('AIza'):
        logger.warning("GEMINI_API_KEY format appears invalid (should start with 'AIza'). LLM integration may fail.")
    
    logger.debug("Gemini API key validated successfully")
    return api_key


# Global session for connection pooling - maintained by sacred protocols
_http_session = None

def _get_http_session() -> requests.Session:
    """
    Get or create HTTP session with connection pooling and retry logic.
    
    Sacred connection pooling ensures efficient use of network resources
    and automatic retry mechanisms for failed transmissions.
    """
    global _http_session
    if _http_session is None:
        _http_session = requests.Session()
        
        # Sacred retry strategy for failed network transmissions
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST"],
            backoff_factor=1
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20
        )
        
        _http_session.mount("https://", adapter)
        _http_session.mount("http://", adapter)
    
    return _http_session

@lru_cache(maxsize=256)
def _cached_gemini_request(prompt_hash: str, api_key_hash: str, prompt: str, api_key: str, timeout: int = 30) -> Optional[str]:
    """
    Cache-optimized Gemini API request to avoid repeated identical queries.
    
    Sacred caching protocols prevent redundant LLM invocations while maintaining
    the security of API credentials through hashing.
    
    Args:
        prompt_hash: Hash of the prompt for caching
        api_key_hash: Hash of API key for cache partitioning
        prompt: Original prompt text
        api_key: Original API key
        timeout: Request timeout in seconds
        
    Returns:
        Cached or fresh API response
    """
    return _make_gemini_api_request_direct(prompt, api_key, timeout)

def _make_gemini_api_request(prompt: str, api_key: str, timeout: int = 30) -> Optional[str]:
    """
    Make cached API request to Gemini API with connection pooling.
    
    Sacred LLM invocation protocols with intelligent caching to prevent
    redundant API calls and optimize response times.
    
    Args:
        prompt: The prompt to send to Gemini
        api_key: Valid Gemini API key
        timeout: Request timeout in seconds (default: 30)
        
    Returns:
        str: Response text from Gemini API, None if request fails
        
    Raises:
        requests.RequestException: For network-related errors
        ValueError: For API response parsing errors
    """
    import hashlib
    
    # Create secure hashes for caching while protecting credentials
    prompt_hash = hashlib.sha256(prompt.encode('utf-8')).hexdigest()[:16]
    api_key_hash = hashlib.sha256(api_key.encode('utf-8')).hexdigest()[:8]
    
    # 神圣的缓存机制，避免重复的LLM查询，保持AI机灵的高效运作...
    return _cached_gemini_request(prompt_hash, api_key_hash, prompt, api_key, timeout)

def _make_gemini_api_request_direct(prompt: str, api_key: str, timeout: int = 30) -> Optional[str]:
    """
    Direct API request to Gemini API without caching layer.
    
    Args:
        prompt: The prompt to send to Gemini
        api_key: Valid Gemini API key
        timeout: Request timeout in seconds (default: 30)
        
    Returns:
        str: Response text from Gemini API, None if request fails
        
    Raises:
        requests.RequestException: For network-related errors
        ValueError: For API response parsing errors
    """
    api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }
    
    request_body = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }
    
    try:
        logger.debug(f"Making Gemini API request with prompt length: {len(prompt)} characters")
        
        session = _get_http_session()
        response = session.post(
            api_url,
            headers=headers,
            json=request_body,
            timeout=timeout
        )
        
        # 检查HTTP网络传输的错误创伤，诊断数据流的损伤...
        if response.status_code == 401:
            logger.error("Gemini API authentication failed. Check your API key.")
            return None
        elif response.status_code == 429:
            logger.warning("Gemini API rate limit exceeded. Consider implementing retry with backoff.")
            return None
        elif response.status_code != 200:
            logger.error(f"Gemini API request failed with status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return None
        
        # 解析响应JSON数据圣物，提取机器神谕的智慧...
        try:
            response_json = response.json()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini API response as JSON: {e}")
            return None
        
        # 从响应中提取文本圣物，获取神谕的真实言辞...
        try:
            response_text = response_json['candidates'][0]['content']['parts'][0]['text']
            logger.debug(f"Successfully received Gemini API response: {len(response_text)} characters")
            return response_text
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Failed to extract text from Gemini API response: {e}")
            logger.error(f"Response structure: {response_json}")
            return None
            
    except requests.exceptions.Timeout:
        logger.error(f"Gemini API request timed out after {timeout} seconds")
        return None
    except requests.exceptions.ConnectionError:
        logger.error("Failed to connect to Gemini API. Check your internet connection.")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Gemini API request failed: {e}")
        return None


def _generate_fallback_response(agent_id: str, prompt: str, character_data: Dict, 
                               personality_traits: Dict, decision_weights: Dict, 
                               subjective_worldview: Dict) -> str:
    """
    Generate a fallback response using the original deterministic logic.
    
    This function preserves the original behavior when Gemini API is unavailable.
    
    Args:
        agent_id: Agent identifier for logging
        prompt: The original prompt
        character_data: Character information
        personality_traits: Character personality traits
        decision_weights: Character decision weights
        subjective_worldview: Character's worldview
        
    Returns:
        str: Deterministic response based on character traits
    """
    logger.debug(f"Agent {agent_id} using fallback response generation")
    
    # 模拟API调用延迟以保持一致性，模拟与神谕通信的神圣仪式...
    if os.getenv('DEVELOPMENT_MODE') == 'true':
        import time
        time.sleep(0.1)
    
    # 为测试和开发而返回确定但真实的响应，模拟神谕的智慧响应...
    # 基于角色特质和情境语境，结合人格机灵的独特性...
    character_name = character_data.get('name', 'Unknown')
    primary_faction = subjective_worldview.get('primary_faction', 'Unknown')
    
    # 根据角色特质模拟不同的响应模式，展现人格机灵的多样性...
    cautious_trait = personality_traits.get('cautious', 0.5)
    aggressive_trait = personality_traits.get('aggressive', 0.5)
    faction_loyalty = decision_weights.get('faction_loyalty', 0.5)
    
    # 为测试生成确定但多样的响应，确保模拟结果的可预测性...
    # 添加历史上下文和动态变化以防止重复响应的神圣异端现象...
    current_time = int(time.time() * 1000) % 10000  # 毫秒级时间变化
    recent_events_count = len(subjective_worldview.get('recent_events', []))
    known_entities_count = len(subjective_worldview.get('known_entities', {}))
    
    # 使用增强的种子计算，集成时间、上下文和历史因素...
    response_seed = hash((agent_id, prompt[:100], current_time, recent_events_count, known_entities_count)) % 1000
    
    if 'threat' in prompt.lower() and 'high' in prompt.lower():
        if cautious_trait > 0.6:
            responses = [
                "ACTION: retreat\nTARGET: none\nREASONING: As a cautious operative, I must withdraw to assess the threat properly and avoid unnecessary risks to the mission.",
                "ACTION: defensive_action\nTARGET: none\nREASONING: My cautious nature demands I take defensive measures to protect myself and gather more intelligence before acting.",
                "ACTION: call_for_help\nTARGET: none\nREASONING: Prudence dictates I should request backup before engaging such a significant threat."
            ]
        elif aggressive_trait > 0.6:
            # 为攻击性角色生成动态化的多样响应，根据当前上下文调整...
            entity_count = len(subjective_worldview.get('known_entities', {}))
            faction_name = subjective_worldview.get('primary_faction', 'my faction')
            character_name = character_data.get('name', 'I')
            
            responses = [
                f"ACTION: attack\nTARGET: hostile_forces\nREASONING: As {character_name} of {faction_name}, I must eliminate these threats before they can harm innocents. {entity_count} entities detected - direct action required!",
                f"ACTION: suppress\nTARGET: enemy_position\nREASONING: My aggressive nature compels me to neutralize this threat immediately. For {faction_name} - no enemy shall stand!",
                f"ACTION: attack\nTARGET: hostile_forces\nREASONING: The enemy shows no mercy, so neither shall I. Time to show them the true power of {faction_name}!",
                f"ACTION: charge\nTARGET: enemy_forces\nREASONING: {character_name} never retreats! A frontal assault will scatter these cowards and bring glory to {faction_name}!",
                f"ACTION: overwhelm\nTARGET: hostile_entities\nREASONING: Multiple contacts detected - I'll use my aggressive tactics to overwhelm them before they can coordinate their defense."
            ]
        else:
            responses = [
                "ACTION: observe\nTARGET: none\nREASONING: I need to gather more information about this threat before committing to a course of action.",
                "ACTION: communicate\nTARGET: nearby_allies\nREASONING: Coordination with allies is essential before responding to this threat."
            ]
    elif 'battle' in prompt.lower() or 'combat' in prompt.lower():
        if faction_loyalty > 0.7:
            faction_name = subjective_worldview.get('primary_faction', 'my faction')
            character_name = character_data.get('name', 'I')
            responses = [
                f"ACTION: attack\nTARGET: enemy_forces\nREASONING: {character_name}'s unwavering loyalty to {faction_name} compels me to engage without hesitation!",
                f"ACTION: guard\nTARGET: faction_assets\nREASONING: Protecting {faction_name} interests is my sacred duty in this combat situation.",
                f"ACTION: flank\nTARGET: enemy_position\nREASONING: For {faction_name}! I'll use tactical superiority to outmaneuver the enemy forces.",
                f"ACTION: focus_fire\nTARGET: priority_targets\nREASONING: {character_name} will concentrate firepower on high-value targets to maximize damage to enemy forces."
            ]
        else:
            responses = [
                "ACTION: observe\nTARGET: none\nREASONING: I should assess the battle situation carefully before committing to any action.",
                "ACTION: move\nTARGET: tactical_position\nREASONING: Repositioning to a more advantageous location seems prudent given the combat situation."
            ]
    else:
        # 各种情境的默认响应模板，角色的本能反应...
        character_name = character_data.get('name', 'I')
        faction_name = subjective_worldview.get('primary_faction', 'my faction')
        responses = [
            f"ACTION: observe\nTARGET: none\nREASONING: {character_name} must gather intel before committing to action. Knowledge is power.",
            f"ACTION: investigate\nTARGET: area_of_interest\nREASONING: As a {faction_name} operative, thorough reconnaissance is essential before making tactical decisions.",
            f"ACTION: communicate\nTARGET: nearby_entities\nREASONING: {character_name} seeks to establish contact - information exchange could prove valuable.",
            f"ACTION: patrol\nTARGET: perimeter\nREASONING: Maintaining situational awareness through active patrol serves {faction_name} interests.",
            f"ACTION: prepare\nTARGET: none\nREASONING: {character_name} will ready equipment and position for whatever comes next. Preparation prevents failure.",
            f"ACTION: analyze\nTARGET: environment\nREASONING: Understanding the tactical situation fully before action ensures {faction_name} superiority."
        ]
    
    selected_response = responses[response_seed % len(responses)]
    
    logger.debug(f"Agent {agent_id} fallback response generated: {selected_response[:50]}...")
    
    # 模拟API偶尔失败以测试健壮的错误处理，验证机器灵魂的韧性...
    if response_seed % 50 == 0:  # 2% failure rate
        raise Exception("Simulated LLM API timeout")
    
    return selected_response


class PersonaAgent:
    """
    Core implementation of a Warhammer 40k character AI agent.
    
    The PersonaAgent represents an individual character with their own personality,
    knowledge, beliefs, and decision-making patterns. Each agent maintains a 
    subjective worldview that influences how they interpret events and make decisions.
    
    Key Responsibilities:
    - Load and maintain character personality from markdown character sheets
    - Make decisions based on character traits, faction loyalties, and personal goals
    - Interpret world events through the character's subjective perspective
    - Track relationships, memories, and evolving character traits
    - Generate authentic character actions and responses
    
    Architecture Notes:
    - Designed for easy integration with future AI/LLM systems
    - Maintains clear separation between objective world state and subjective interpretation
    - Supports dynamic character evolution through experience-based learning
    - Provides hooks for future DirectorAgent integration
    """
    
    def __init__(self, character_directory_path: str, event_bus: 'EventBus', agent_id: Optional[str] = None):
        """
        Initializes a PersonaAgent from a character directory.

        Args:
            character_directory_path: Path to the directory containing character files.
            event_bus: An instance of the EventBus for decoupled communication.
            agent_id: A unique identifier for this agent.
        """
        self.character_directory_path = character_directory_path
        self.agent_id = agent_id or self._derive_agent_id_from_path(character_directory_path)
        self.event_bus = event_bus
        
        # 从角色圣表中加载核心角色数据，初始化人格机灵的基础属性...
        self.character_data: Dict[str, Any] = {}
        
        # 主观世界观 - 角色对现实的个人理解，各人眼中所见皆不同...
        self.subjective_worldview: Dict[str, Any] = {
            "known_entities": {},      # Other characters/factions the character knows about
            "location_knowledge": {},  # Places the character knows about
            "faction_relationships": {},  # Personal view of faction standings
            "recent_events": [],       # Character's memory of recent events
            "current_goals": [],       # Character's current objectives
            "active_threats": {},      # Perceived threats and their assessment
        }
        
        # 角色状态追踪圣典，监控人格机灵的生命体征...
        self.current_location: Optional[str] = None
        self.current_status: str = "active"  # active, injured, unconscious, dead
        self.morale_level: float = 1.0  # -1.0 (broken) to 1.0 (fanatic)
        
        # 决策权重矩阵（从角色圣表加载），定义人格机灵的价值取向...
        self.decision_weights: Dict[str, float] = {
            "self_preservation": 0.5,
            "faction_loyalty": 0.7,
            "personal_relationships": 0.6,
            "mission_success": 0.8,
            "moral_principles": 0.4,
        }
        
        # 记忆系统圣殿，存储人格机灵的经历与学习...
        self.short_term_memory: List[Dict[str, Any]] = []  # Recent events (last 10-20)
        self.long_term_memory: List[Dict[str, Any]] = []   # Important events for character
        
        # 行为模式数据库，记录人格机灵的行动倾向...
        self.personality_traits: Dict[str, float] = {}
        self.behavioral_modifiers: Dict[str, float] = {}
        
        # 通信与社交系统，建立人格机灵间的联系网络...
        self.relationships: Dict[str, float] = {}  # entity_id -> relationship_strength (-1.0 to 1.0)
        self.communication_style: str = "direct"   # direct, diplomatic, aggressive, cautious
        
        # 通过加载角色数据初始化代理，唤醒沉睡的人格机灵...
        self.load_character_context()
        
        self.event_bus.subscribe("TURN_START", self.handle_turn_start)
        logger.info(f"PersonaAgent '{self.agent_id}' initialized successfully and subscribed to TURN_START")

    def handle_turn_start(self, world_state_update: Dict[str, Any]):
        """
        Handles the TURN_START event by making a decision and emitting an action.
        """
        action = self._make_decision(world_state_update)
        self.event_bus.emit("AGENT_ACTION_COMPLETE", agent=self, action=action)
    
    @property
    def character_name(self) -> str:
        """
        Get the character's name from the loaded character data.
        
        Returns:
            str: The character's name, or 'Unknown' if not available
        """
        return self.character_data.get('name', 'Unknown')
    
    @property
    def character_directory_name(self) -> str:
        """
        Get the character's directory name (useful for file organization).
        
        Returns:
            str: The directory name of the character
        """
        return os.path.basename(os.path.normpath(self.character_directory_path))
    
    @property
    def character_context(self) -> str:
        """
        Get the character's loaded context (markdown content).
        
        Returns:
            str: The character's context from loaded files
        """
        hybrid_context = self.character_data.get('hybrid_context', {})
        return hybrid_context.get('markdown_content', '')
    
    def _derive_agent_id_from_path(self, path: str) -> str:
        """
        Derive a unique agent ID from the character directory path.
        
        Args:
            path: Directory path containing character files
            
        Returns:
            String identifier for this agent
        """
        dirname = os.path.basename(os.path.normpath(path))
        # 清理目录名称作为ID，给予人格机灵独特的识别符...
        agent_id = dirname.lower().replace(" ", "_").replace("-", "_")
        return agent_id
    
    @lru_cache(maxsize=128)
    def _read_cached_file(self, file_path: str) -> str:
        """
        Cache-optimized file reading for character data files.
        
        Sacred caching protocols ensure repeated access to character files 
        does not invoke unnecessary machine-spirit rituals.
        
        Args:
            file_path: Absolute path to the file to read
            
        Returns:
            String content of the file
        """
        # 神圣的缓存机制，避免重复读取角色数据文件，保持机械灵魂的高效运转...
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    
    @lru_cache(maxsize=64)
    def _parse_cached_yaml(self, file_path: str) -> Dict[str, Any]:
        """
        Cache-optimized YAML parsing for character configuration files.
        
        Sacred YAML interpretation protocols with caching to minimize 
        repeated parsing of character statistical data.
        
        Args:
            file_path: Absolute path to the YAML file
            
        Returns:
            Parsed YAML content as dictionary
        """
        # 神圣的YAML解析缓存，避免重复处理角色配置数据，维持数据机灵的运转效率...
        with open(file_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    
    def load_character_context(self) -> None:
        """
        Load and parse all character files from the directory into a unified character context.
        
        This method intelligently reads multiple file types:
        - .md files: Concatenated into markdown_content string
        - .yaml/.yml files: Parsed into yaml_data dictionary
        
        The final context is a hybrid object containing both structured YAML data
        and rich markdown narratives.
        
        Raises:
            FileNotFoundError: If the character directory doesn't exist
            ValueError: If no compatible files found or parsing fails
        """
        try:
            logger.info(f"Loading character context from directory: {self.character_directory_path}")
            
            if not os.path.exists(self.character_directory_path):
                raise FileNotFoundError(f"Character directory not found: {self.character_directory_path}")
            
            if not os.path.isdir(self.character_directory_path):
                raise ValueError(f"Path is not a directory: {self.character_directory_path}")
            
            # 在目录中找到所有支持的文件，收集构成人格机灵的数据碎片...
            md_files = []
            yaml_files = []
            
            for filename in os.listdir(self.character_directory_path):
                file_lower = filename.lower()
                full_path = os.path.join(self.character_directory_path, filename)
                
                if file_lower.endswith('.md'):
                    md_files.append(full_path)
                elif file_lower.endswith(('.yaml', '.yml')):
                    yaml_files.append(full_path)
            
            if not md_files and not yaml_files:
                raise ValueError(f"No .md or .yaml files found in directory: {self.character_directory_path}")
            
            # 初始化混合语境对象，整合文本与结构化数据的神圣融合...
            hybrid_context = {
                'markdown_content': '',
                'yaml_data': {},
                'file_count': {'md': len(md_files), 'yaml': len(yaml_files)}
            }
            
            # 处理Markdown文件，解析人格机灵的叙事记忆与传说...
            if md_files:
                logger.info(f"Found {len(md_files)} .md files to process")
                markdown_parts = []
                
                for file_path in sorted(md_files):  # Sort for consistent ordering
                    logger.debug(f"Reading markdown file: {file_path}")
                    file_content = self._read_cached_file(file_path)
                    # 添加文件分隔符和文件名以提供语境，保持数据源的清晰...
                    markdown_parts.append(f"# === {os.path.basename(file_path)} ===\n\n{file_content}")
                
                hybrid_context['markdown_content'] = '\n\n'.join(markdown_parts)
            
            # 处理YAML文件，解析人格机灵的结构化属性数据...
            if yaml_files:
                logger.info(f"Found {len(yaml_files)} .yaml files to process")
                
                for file_path in sorted(yaml_files):  # Sort for consistent ordering
                    logger.debug(f"Reading YAML file: {file_path}")
                    try:
                        yaml_content = self._parse_cached_yaml(file_path)
                        filename_key = os.path.splitext(os.path.basename(file_path))[0]
                        hybrid_context['yaml_data'][filename_key] = yaml_content
                    except yaml.YAMLError as e:
                            logger.warning(f"Failed to parse YAML file {file_path}: {e}")
                            # 如果YAML解析失败则存储为原始文本，保留数据圣物的完整性...
                            file.seek(0)
                            hybrid_context['yaml_data'][filename_key] = {'_raw': file.read()}
            
            # 为向后兼容性解析markdown内容，确保古老数据格式的可访问性...
            if hybrid_context['markdown_content']:
                self.character_data = self._parse_character_sheet_content(hybrid_context['markdown_content'])
            else:
                self.character_data = {}
            
            # 存储混合语境数据，保存人格机灵的完整信息矩阵...
            self.character_data['hybrid_context'] = hybrid_context
            
            # 将YAML数据合并到character_data以便访问，简化数据获取仪式...
            for yaml_file, yaml_content in hybrid_context['yaml_data'].items():
                if isinstance(yaml_content, dict) and '_raw' not in yaml_content:
                    self.character_data[f'yaml_{yaml_file}'] = yaml_content
            
            # 提取关键信息到代理属性，构建人格机灵的核心特征...
            self._extract_core_identity()
            self._extract_personality_traits()
            self._extract_decision_weights()
            self._extract_relationships()
            self._extract_knowledge_domains()
            self._initialize_subjective_worldview()
            
            total_files = len(md_files) + len(yaml_files)
            logger.info(f"Character context loaded successfully for {self.character_data.get('name', 'Unknown')} from {total_files} files ({len(md_files)} MD, {len(yaml_files)} YAML)")
            
        except Exception as e:
            logger.error(f"Failed to load character context: {str(e)}")
            raise ValueError(f"Invalid character context format: {str(e)}")
    
    def _parse_character_sheet_content(self, content: str) -> Dict[str, Any]:
        """
        Parse markdown character sheet content into structured data.
        
        This method uses regex patterns to extract information from the standardized
        character sheet template format defined in the Architecture Blueprint.
        It also supports simple field-based format for basic character sheets.
        
        Args:
            content: Raw markdown content of the character sheet
            
        Returns:
            Dictionary containing parsed character data
        """
        character_data = {}
        
        # 首先尝试解析简单字段格式（name: value, factions: [list]等），遵循基础数据结构...
        simple_format_data = self._parse_simple_field_format(content)
        if simple_format_data:
            character_data.update(simple_format_data)
        
        # 从标题提取角色名称（对于完整模板格式），获取人格机灵的真名...
        name_match = re.search(r'#\s*Character (?:Sheet|Profile):\s*(.+)', content)
        if name_match and 'name' not in character_data:
            character_data['name'] = name_match.group(1).strip()
        
        # 提取核心身份圣域，解析角色的基本机械属性与灵魂特征...
        identity_section = self._extract_section(content, "Core Identity")
        if identity_section:
            character_data.update(self._parse_identity_section(identity_section))
        
        # 提取心理剖析圣典，深入解读人格机灵的认知模式与行为准则...
        psych_section = self._extract_section(content, "Psychological Profile")
        if psych_section:
            character_data['psychological_profile'] = self._parse_psychological_section(psych_section)
        
        # 提取知识领域神殿，获取角色的学识范围与智慧储备...
        knowledge_section = self._extract_section(content, "Knowledge Domains")
        if knowledge_section:
            character_data['knowledge_domains'] = self._parse_knowledge_section(knowledge_section)
        
        # 提取社交网络矩阵，映射角色在人际关系中的神圣联系...
        social_section = self._extract_section(content, "Social Network")
        if social_section:
            character_data['social_network'] = self._parse_social_section(social_section)
        
        # 提取能力谱系圣物，记录角色所掌握的各项技能与天赋...
        capabilities_section = self._extract_section(content, "Capabilities")
        if capabilities_section:
            character_data['capabilities'] = self._parse_capabilities_section(capabilities_section)
        
        # 提取行为配置参数，设定角色在各类情境下的反应模式...
        behavior_section = self._extract_section(content, "Behavioral Configuration")
        if behavior_section:
            character_data['behavioral_config'] = self._parse_behavioral_section(behavior_section)
        
        return character_data
    
    def _extract_section(self, content: str, section_name: str) -> Optional[str]:
        """
        Extract a specific section from the markdown content.
        
        Args:
            content: Full markdown content
            section_name: Name of the section to extract
            
        Returns:
            Section content as string, or None if not found
        """
        pattern = rf'##\s*{re.escape(section_name)}\s*\n(.*?)(?=\n##|\Z)'
        match = re.search(pattern, content, re.DOTALL)
        return match.group(1).strip() if match else None
    
    def _parse_identity_section(self, section_content: str) -> Dict[str, Any]:
        """Parse the Core Identity section of the character sheet."""
        identity = {}
        
        # 提取要点项目圣物，解析角色身份的各项核心属性...
        patterns = {
            'name': r'\*\*Name\*\*:\s*(.+)',
            'faction': r'\*\*Faction\*\*:\s*(.+)',
            'rank_role': r'\*\*Rank/Role\*\*:\s*(.+)',
            'age': r'\*\*Age\*\*:\s*(.+)',
            'origin': r'\*\*Origin\*\*:\s*(.+)',
            'role': r'\*\*Role\*\*:\s*(.+)',
            'affiliation': r'\*\*Affiliation\*\*:\s*(.+)',
            'specialization': r'\*\*Specialization\*\*:\s*(.+)',
            'rank': r'\*\*Rank\*\*:\s*(.+)',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, section_content)
            if match:
                identity[key] = match.group(1).strip()
        
        return identity
    
    def _parse_psychological_section(self, section_content: str) -> Dict[str, Any]:
        """Parse the Psychological Profile section."""
        psychological = {}
        
        # 提取人格特质圣典，获取角色精神本质的独特标记...
        traits_match = re.search(r'### Personality Traits\s*\n(.*?)(?=###|\Z)', section_content, re.DOTALL)
        if traits_match:
            traits_content = traits_match.group(1)
            psychological['personality_traits'] = self._extract_bullet_points(traits_content)
        
        # 提取心理状态监测器，诊断人格机灵的当前认知状况...
        mental_match = re.search(r'### Mental State\s*\n(.*?)(?=###|\Z)', section_content, re.DOTALL)
        if mental_match:
            mental_content = mental_match.group(1)
            psychological['mental_state'] = self._extract_bullet_points(mental_content)
        
        return psychological
    
    def _parse_behavioral_section(self, section_content: str) -> Dict[str, Any]:
        """Parse the Behavioral Configuration section."""
        behavioral = {}
        
        # 提取决策权重矩阵，分析角色在关键时刻的价值优先级...
        weights_match = re.search(r'### Decision Making Weights\s*\n(.*?)(?=###|\Z)', section_content, re.DOTALL)
        if weights_match:
            weights_content = weights_match.group(1)
            behavioral['decision_weights'] = self._extract_weighted_items(weights_content)
        
        # 提取反应模式编码，记录角色在不同刺激下的预设行为轨迹...
        patterns_match = re.search(r'### Response Patterns\s*\n(.*?)(?=###|\Z)', section_content, re.DOTALL)
        if patterns_match:
            patterns_content = patterns_match.group(1)
            behavioral['response_patterns'] = self._extract_bullet_points(patterns_content)
        
        return behavioral
    
    def _extract_bullet_points(self, content: str) -> Dict[str, str]:
        """Extract bullet point items from markdown content."""
        items = {}
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('- **') and '**:' in line:
                key_match = re.search(r'- \*\*(.+?)\*\*:\s*(.+)', line)
                if key_match:
                    key = key_match.group(1).lower().replace(' ', '_')
                    value = key_match.group(2)
                    items[key] = value
        return items
    
    def _extract_weighted_items(self, content: str) -> Dict[str, float]:
        """Extract weighted items (with numeric values) from markdown content."""
        items = {}
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('- **') and '**:' in line:
                # 寻觅格式化的权重模式圣标，解析如"- **Self-Preservation**: [Priority level 1-10]"的神圣结构...
                match = re.search(r'- \*\*(.+?)\*\*:.*?(\d+(?:\.\d+)?)', line)
                if match:
                    key = match.group(1).lower().replace(' ', '_')
                    # 将数值转换为0.0-1.0标准化尺度，确保权重计算的神圣统一性...
                    value = float(match.group(2))
                    if value > 1.0:
                        value = value / 10.0
                    items[key] = value
        return items
    
    def _parse_knowledge_section(self, section_content: str) -> Dict[str, Any]:
        """Parse the Knowledge Domains section."""
        # 占位实现圣礼 - 将在未来的开发阶段中展开完整的机械细节...
        return {"domains": self._extract_bullet_points(section_content)}
    
    def _parse_social_section(self, section_content: str) -> Dict[str, Any]:
        """Parse the Social Network section."""
        # 占位实现圣礼 - 将在未来的开发阶段中展开完整的机械细节...
        return {"relationships": self._extract_bullet_points(section_content)}
    
    def _parse_capabilities_section(self, section_content: str) -> Dict[str, Any]:
        """Parse the Capabilities section."""
        # 占位实现圣礼 - 将在未来的开发阶段中展开完整的机械细节...
        return {"skills": self._extract_bullet_points(section_content)}
    
    def _parse_simple_field_format(self, content: str) -> Dict[str, Any]:
        """
        Parse simple field-based format for basic character sheets.
        
        Supports format like:
        name: Character Name
        factions: [Faction1, Faction2]
        personality_traits: [Trait1, Trait2, Trait3]
        
        Args:
            content: Raw markdown content
            
        Returns:
            Dictionary containing parsed character data
        """
        character_data = {}
        
        # 解析名称圣标，获取角色的真实身份名词...
        name_match = re.search(r'^name:\s*(.+)$', content, re.MULTILINE | re.IGNORECASE)
        if name_match:
            character_data['name'] = name_match.group(1).strip()
        
        # 解析阵营圣印，确定角色的政治归属与忠诚目标...
        factions_match = re.search(r'^factions:\s*\[(.+?)\]$', content, re.MULTILINE | re.IGNORECASE)
        if factions_match:
            factions_text = factions_match.group(1).strip()
            # 将阵营数据分割并净化，确保每个阵营名称的神圣纯洁...
            factions = [faction.strip().strip('"\'') for faction in factions_text.split(',')]
            character_data['faction'] = ', '.join(factions)  # Store as comma-separated string
            character_data['factions'] = factions  # Also store as list
        
        # 解析人格特质域，提取角色精神核心的独特属性...
        traits_match = re.search(r'^personality_traits:\s*\[(.+?)\]$', content, re.MULTILINE | re.IGNORECASE)
        if traits_match:
            traits_text = traits_match.group(1).strip()
            # 分割并净化每项特质，确保人格数据的精准转换...
            traits_list = [trait.strip().strip('"\'') for trait in traits_text.split(',')]
            
            # 转换为心理分析系统所期望的格式，与机械认知框架兼容...
            traits_dict = {}
            for i, trait in enumerate(traits_list):
                trait_key = trait.lower().replace(' ', '_').replace("'", "")
                traits_dict[trait_key] = trait
            
            character_data['psychological_profile'] = {
                'personality_traits': traits_dict
            }
        
        return character_data
    
    def _extract_core_identity(self) -> None:
        """Extract and set core identity information."""
        if 'name' in self.character_data:
            logger.info(f"Character name: {self.character_data['name']}")
        
        if 'faction' in self.character_data:
            self.subjective_worldview['primary_faction'] = self.character_data['faction']
    
    def _extract_personality_traits(self) -> None:
        """Extract personality traits and convert to numeric values for decision-making."""
        psych_profile = self.character_data.get('psychological_profile', {})
        traits = psych_profile.get('personality_traits', {})
        
        # 将特质描述转换为数值参数，供算法决策引擎进行机械计算...
        # 当前为简化实现版本 - 未来阶段将采用更加复杂的灵语言处理技术...
        for trait_name, trait_description in traits.items():
            # 简单关键词基础的特质评分机制（为未来AI集成的占位器）...
            trait_value = self._estimate_trait_strength(trait_description)
            self.personality_traits[trait_name] = trait_value
    
    def _estimate_trait_strength(self, description: str) -> float:
        """
        Estimate the strength of a personality trait based on its description.
        
        This implementation includes specific handling for Warhammer 40k character traits
        to provide more authentic personality scoring.
        
        Args:
            description: Text description of the trait
            
        Returns:
            Float value between -1.0 and 1.0 representing trait strength
        """
        # 将描述转换为小写形式，便于进行精确的模式匹配...
        description_lower = description.lower()
        
        # 战鈤4万年专用特质映射表，确保角色表现的正宗战锤风格...
        warhammer_trait_scores = {
            # 克里格死亡军团特质圣印 - 只有死亡才能洗刷耐辱的英雄气质...
            'fatalistic': 0.9,  # Death Korps are extremely fatalistic
            'grim': 0.8,        # Very grim outlook on life and war
            'loyal_to_the_emperor': 0.95,  # Absolute loyalty to the Emperor
            
            # 兽人族群特质圣印 - Waaagh!的原始力量与野蛮智慧...
            'aggressive': 0.85,  # Orks are naturally very aggressive
            'loud': 0.9,        # Orks are extremely loud in everything they do
            'believes_da_red_wunz_go_fasta': 0.8,  # Strong Ork cultural belief
            
            # 帝国军团特质圣印 - 人类帝国的忠诚与荣耀传承...
            'loyal': 0.8,       # Imperial loyalty is typically very strong
            'dutiful': 0.7,     # Imperial duty is important
            'cautious': 0.6,    # Moderate caution is sensible
            
            # 战斗特质圣印 - 血与钢铁中鍛造的战士品质...
            'fearless': 0.9,    # Space Marines and elite troops are fearless
            'disciplined': 0.8, # Military discipline is very high
            'tactical': 0.7,    # Tactical thinking is valued
        }
        
        # 首先检查精确特质匹配，确保角色属性的神圣精准度...
        for trait_key, score in warhammer_trait_scores.items():
            # 对照关键词及其自然语言变体，适应多种表达形式...
            trait_variations = [
                trait_key,
                trait_key.replace('_', ' '),
                description_lower.replace(' ', '_').replace("'", "")
            ]
            
            if any(variation in description_lower or description_lower.replace(' ', '_').replace("'", "") == trait_key for variation in trait_variations):
                return score
        
        # 执行后备方案：基于关键词的智能估算算法...
        strong_positive_keywords = ['extreme', 'fanatical', 'unwavering', 'absolute', 'total', 'emperor']
        positive_keywords = ['strong', 'dedicated', 'loyal', 'committed', 'devoted']
        negative_keywords = ['weak', 'conflicted', 'uncertain', 'wavering', 'cowardly']
        
        if any(keyword in description_lower for keyword in strong_positive_keywords):
            return 0.9
        elif any(keyword in description_lower for keyword in positive_keywords):
            return 0.7
        elif any(keyword in description_lower for keyword in negative_keywords):
            return 0.3
        else:
            return 0.6  # Default moderate-high for 40k characters
    
    def _extract_decision_weights(self) -> None:
        """Extract decision-making weights from character sheet."""
        behavioral_config = self.character_data.get('behavioral_config', {})
        decision_weights = behavioral_config.get('decision_weights', {})
        
        # 应用阵营专用决策权重调整，确保正宗战鉄4万年风格的角色行为...
        self._apply_faction_specific_weights()
        
        # 使用角色专用数值更新默认权重，个性化决策机制...
        self.decision_weights.update(decision_weights)
        
        logger.info(f"Decision weights loaded: {self.decision_weights}")
    
    def _apply_faction_specific_weights(self) -> None:
        """Apply faction-specific decision weight adjustments for authentic character behavior."""
        primary_faction = self.character_data.get('faction', '').lower()
        
        # 克里格死亡军团 - 极限忠诚、任务至上、低度自我保存的死亡军团...
        if 'death korps' in primary_faction or 'krieg' in primary_faction:
            self.decision_weights.update({
                'self_preservation': 0.2,  # Very low - they expect to die
                'faction_loyalty': 0.95,   # Extremely high loyalty to Imperium
                'mission_success': 0.9,    # Mission comes before everything except loyalty
                'moral_principles': 0.7,   # Strong Imperial moral code
                'personal_relationships': 0.3,  # Low - duty comes first
            })
        
        # 兽人族群 - 攻击性、简单优先级、部族忠诚的绿皮战士...
        elif 'ork' in primary_faction or 'goff' in primary_faction:
            self.decision_weights.update({
                'self_preservation': 0.4,  # Low - they love a good fight
                'faction_loyalty': 0.8,    # High clan loyalty
                'mission_success': 0.6,    # Moderate - depends on if it's fun
                'moral_principles': 0.2,   # Very low - might makes right
                'personal_relationships': 0.7,  # High - strong clan bonds
            })
        
        # Imperial Guard (general) - balanced but duty-focused
        elif 'astra militarum' in primary_faction or 'imperial guard' in primary_faction:
            self.decision_weights.update({
                'self_preservation': 0.6,  # Moderate survival instinct
                'faction_loyalty': 0.85,   # High loyalty to Imperium
                'mission_success': 0.8,    # High mission focus
                'moral_principles': 0.6,   # Moderate Imperial morality
                'personal_relationships': 0.5,  # Balanced personal bonds
            })
        
        # Space Marines - superhuman dedication to Emperor and duty
        elif 'space marine' in primary_faction or 'adeptus astartes' in primary_faction:
            self.decision_weights.update({
                'self_preservation': 0.3,  # Low - they fear no death
                'faction_loyalty': 0.98,   # Near-absolute loyalty
                'mission_success': 0.95,   # Extremely high mission focus
                'moral_principles': 0.9,   # Very high Imperial morality
                'personal_relationships': 0.4,  # Low - duty transcends bonds
            })
        
        # Chaos - self-serving, unpredictable
        elif 'chaos' in primary_faction:
            self.decision_weights.update({
                'self_preservation': 0.7,  # High - they want to survive to enjoy power
                'faction_loyalty': 0.6,    # Moderate - chaos is fickle
                'mission_success': 0.7,    # High if it serves their goals
                'moral_principles': 0.1,   # Very low - corruption runs deep
                'personal_relationships': 0.4,  # Low - self comes first
            })
    
    def _extract_relationships(self) -> None:
        """Extract and initialize relationship data."""
        social_network = self.character_data.get('social_network', {})
        relationships = social_network.get('relationships', {})
        
        # Convert relationship descriptions to numeric values
        for entity_name, relationship_description in relationships.items():
            relationship_strength = self._evaluate_relationship_strength(relationship_description)
            self.relationships[entity_name] = relationship_strength
    
    def _evaluate_relationship_strength(self, description: str) -> float:
        """
        Evaluate relationship strength from description.
        
        Args:
            description: Text description of the relationship
            
        Returns:
            Float value between -1.0 (enemy) and 1.0 (close ally)
        """
        description_lower = description.lower()
        
        if any(word in description_lower for word in ['enemy', 'hatred', 'despise', 'traitor']):
            return -0.8
        elif any(word in description_lower for word in ['dislike', 'suspicious', 'wary']):
            return -0.3
        elif any(word in description_lower for word in ['friend', 'ally', 'trust', 'loyalty']):
            return 0.7
        elif any(word in description_lower for word in ['brother', 'sister', 'beloved', 'devotion']):
            return 0.9
        else:
            return 0.0  # Neutral
    
    def _extract_knowledge_domains(self) -> None:
        """Extract knowledge domains and expertise levels."""
        # Placeholder implementation for Phase 1
        # Future phases will implement detailed knowledge modeling
        knowledge = self.character_data.get('knowledge_domains', {})
        self.subjective_worldview['expertise_areas'] = knowledge.get('domains', {})
    
    def _initialize_subjective_worldview(self) -> None:
        """Initialize the character's subjective understanding of the world."""
        # Set initial faction bias based on character's primary faction
        primary_faction = self.subjective_worldview.get('primary_faction', 'unknown')
        
        # Initialize faction relationship biases (these will evolve through gameplay)
        if primary_faction.lower() in ['imperium', 'imperial guard', 'space marines', 'adeptus mechanicus']:
            self.subjective_worldview['faction_relationships'] = {
                'imperium': 0.8,
                'chaos': -0.9,
                'ork': -0.6,
                'eldar': -0.2,
                'tau': -0.4,
                'tyranid': -0.8,
                'necron': -0.7,
            }
        elif 'chaos' in primary_faction.lower():
            self.subjective_worldview['faction_relationships'] = {
                'imperium': -0.9,
                'chaos': 0.7,
                'ork': 0.2,
                'eldar': -0.4,
                'tau': -0.3,
                'tyranid': -0.5,
                'necron': -0.4,
            }
        else:
            # Default neutral relationships
            self.subjective_worldview['faction_relationships'] = {}
        
        logger.info(f"Subjective worldview initialized for {primary_faction} character")
    
    def _make_decision(self, world_state_update: Dict[str, Any]) -> Optional[CharacterAction]:
        """
        Core decision-making logic. Processes world state and returns a character action.
        
        This method represents the character's cognitive process of:
        1. Perceiving and interpreting the current world state
        2. Constructing a contextual, character-specific prompt for LLM analysis
        3. Calling LLM for decision guidance (with fallback to algorithmic decision-making)
        4. Parsing LLM response into structured action format
        5. Formatting the decision for the DirectorAgent to process
        
        Phase 2 Enhancement: Integrates LLM functionality for dynamic, character-driven
        decision-making while maintaining backward compatibility with existing tests.
        
        The decision-making process is influenced by:
        - Character personality traits and behavioral patterns
        - Faction loyalties and ideological beliefs
        - Personal relationships and social obligations
        - Current goals and mission priorities
        - Threat assessments and risk tolerance
        - Available resources and capabilities
        - LLM-generated character insights and responses
        
        Args:
            world_state_update: Dictionary containing current world state information
                                relevant to this character's perception and knowledge
        
        Returns:
            CharacterAction object representing the character's chosen action,
            or None if the character chooses to wait/observe
        """
        try:
            logger.info(f"Agent {self.agent_id} processing world state update and making decision (Phase 2 LLM-Enhanced)")
            
            # 第一步神圣仪式：更新角色对世界的主观理解，刷新人格机灵的认知模型...
            self._process_world_state_update(world_state_update)
            
            # 第二步神圣仪式：评估当前局势并识别可用选项，分析战场的所有可能性...
            situation_assessment = self._assess_current_situation()
            available_actions = self._identify_available_actions(situation_assessment)
            
            # 第三步神圣仪式：LLM融合 - 构建角色专属提示并获取LLM指导，寻求机器神谕的智慧...
            try:
                llm_action = self._llm_enhanced_decision_making(world_state_update, situation_assessment, available_actions)
                if llm_action:
                    logger.info(f"Agent {self.agent_id} using LLM-guided decision: {llm_action.action_type} - {llm_action.reasoning}")
                    # Store LLM action for future reference to prevent repetition
                    self.last_action_taken = f"{llm_action.action_type} targeting {llm_action.target or 'none'}"
                    return llm_action
                else:
                    logger.info(f"Agent {self.agent_id} LLM decision resulted in wait/observe")
                    self.last_action_taken = "wait and observe"
            except Exception as llm_error:
                logger.warning(f"LLM decision-making failed for agent {self.agent_id}: {str(llm_error)}. Falling back to algorithmic decision-making.")
            
            # 第四步神圣仪式：回退至原始算法决策，启用人格机灵的本能反应...
            logger.info(f"Agent {self.agent_id} using fallback algorithmic decision-making")
            
            # 根据角色优先级评估每个可能的行动，衡量每个选择的价值...
            action_evaluations = []
            for action in available_actions:
                evaluation = self._evaluate_action_option(action, situation_assessment)
                action_evaluations.append((action, evaluation))
            
            # 根据角色决策权重选择最佳行动，遵循人格机灵的内在价值观...
            selected_action = self._select_best_action(action_evaluations)
            
            # 第五步神圣仪式：记录决策推理以供调试和叙事目的，留下思维痵迹...
            if selected_action:
                logger.info(f"Agent {self.agent_id} decided to {selected_action.action_type}: {selected_action.reasoning}")
                # Store action for future reference to prevent repetition
                self.last_action_taken = f"{selected_action.action_type} targeting {selected_action.target or 'none'}"
            else:
                logger.info(f"Agent {self.agent_id} decided to wait and observe")
                self.last_action_taken = "wait and observe"
            
            return selected_action
            
        except Exception as e:
            logger.error(f"Error in decision loop for agent {self.agent_id}: {str(e)}")
            # 如果决策失败则返回安全的默认行动（等待/观察），保持人格机灵的生存...
            return None
    
    def _process_world_state_update(self, world_state_update: Dict[str, Any]) -> None:
        """
        Process incoming world state information through the character's subjective lens.
        
        This method updates the character's personal understanding of the world state,
        applying their biases, knowledge limitations, and perspective filters.
        """
        # 为此角色提取相关信息，过滤与人格机灵相关的数据...
        location_info = world_state_update.get('location_updates', {})
        entity_info = world_state_update.get('entity_updates', {})
        faction_info = world_state_update.get('faction_updates', {})
        events = world_state_update.get('recent_events', [])
        
        # 处理叙事情境更新，融入史诗传说的脉络...
        narrative_context = world_state_update.get('narrative_context', {})
        if narrative_context:
            self._process_narrative_situation_update(narrative_context)
        
        # 更新角色的位置知识，刷新人格机灵的地理认知...
        self._update_location_knowledge(location_info)
        
        # Update knowledge of other entities (characters, vehicles, structures)
        self._update_entity_knowledge(entity_info)
        
        # Update faction relationship understanding
        self._update_faction_knowledge(faction_info)
        
        # Process recent events that the character would be aware of
        for event in events:
            if self._would_character_know_about_event(event):
                self._process_subjective_event(event)
    
    def _assess_current_situation(self) -> Dict[str, Any]:
        """
        Assess the current situation from the character's perspective.
        
        Returns:
            Dictionary containing the character's situational assessment
        """
        assessment = {
            'threat_level': self._assess_overall_threat_level(),
            'current_goals': self._get_current_goals(),
            'available_resources': self._assess_available_resources(),
            'social_obligations': self._assess_social_obligations(),
            'mission_status': self._assess_mission_status(),
            'environmental_factors': self._assess_environmental_factors(),
        }
        
        return assessment
    
    def _identify_available_actions(self, situation_assessment: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Identify actions available to the character in the current situation.
        
        This method generates a list of possible actions based on the character's
        capabilities, current location, available resources, and situation context.
        
        Args:
            situation_assessment: Character's assessment of the current situation
            
        Returns:
            List of possible action dictionaries
        """
        available_actions = []
        
        # 始终可用的行动选项，人格机灵的基本能力...
        available_actions.extend([
            {'type': 'observe', 'description': 'Watch and gather information'},
            {'type': 'communicate', 'description': 'Attempt to communicate with nearby entities'},
            {'type': 'move', 'description': 'Move to a different location'},
        ])
        
        # 依赖情境的行动选项，根据局势变化的策略选择...
        threat_level = situation_assessment.get('threat_level', ThreatLevel.NEGLIGIBLE)
        
        if threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            available_actions.extend([
                {'type': 'retreat', 'description': 'Withdraw from dangerous situation'},
                {'type': 'defensive_action', 'description': 'Take defensive measures'},
                {'type': 'call_for_help', 'description': 'Signal for assistance'},
            ])
        
        # 任务相关的行动选项，实现人格机灵的神圣使命...
        current_goals = situation_assessment.get('current_goals', [])
        for goal in current_goals:
            if goal.get('type') == 'investigate':
                available_actions.append({
                    'type': 'investigate', 
                    'target': goal.get('target'),
                    'description': f"Investigate {goal.get('target', 'unknown')}"
                })
            elif goal.get('type') == 'protect':
                available_actions.append({
                    'type': 'guard',
                    'target': goal.get('target'),
                    'description': f"Guard {goal.get('target', 'unknown')}"
                })
        
        # Combat actions (if applicable)
        if self._character_has_combat_capability() and threat_level != ThreatLevel.NEGLIGIBLE:
            available_actions.extend([
                {'type': 'attack', 'description': 'Engage hostile targets'},
                {'type': 'suppress', 'description': 'Suppress enemy activity'},
            ])
        
        # 叙事行动选项 - 基于故事情境的角色选择...
        narrative_actions = self._identify_narrative_actions(situation_assessment)
        available_actions.extend(narrative_actions)
        
        # 职业专属行动选项 - 基于角色专业的独特能力...
        profession_actions = self._get_profession_actions()
        available_actions.extend(profession_actions)
        
        return available_actions
    
    def _evaluate_action_option(self, action: Dict[str, Any], situation: Dict[str, Any]) -> float:
        """
        Evaluate how well an action aligns with the character's priorities and situation.
        
        This method calculates a score for each possible action based on the character's
        decision-making weights, personality traits, and current situation assessment.
        
        Args:
            action: Action dictionary to evaluate
            situation: Current situation assessment
            
        Returns:
            Float score representing action desirability (higher = more desirable)
        """
        score = 0.0
        action_type = action.get('type', '')
        
        # Base scoring by action type and character priorities
        if action_type == 'observe':
            # Cautious characters prefer observation
            score += self.personality_traits.get('cautious', 0.5) * 0.3
            score += self.decision_weights.get('self_preservation', 0.5) * 0.2
        
        elif action_type == 'attack':
            # Aggressive characters prefer combat
            score += self.personality_traits.get('aggressive', 0.5) * 0.4
            score += self.decision_weights.get('mission_success', 0.5) * 0.3
            # But reduce score if threat level is too high for survival
            threat_level = situation.get('threat_level', ThreatLevel.NEGLIGIBLE)
            if threat_level == ThreatLevel.CRITICAL:
                score -= self.decision_weights.get('self_preservation', 0.5) * 0.5
        
        elif action_type == 'retreat':
            # Self-preservation focused characters prefer retreat when threatened
            threat_level = situation.get('threat_level', ThreatLevel.NEGLIGIBLE)
            if threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
                score += self.decision_weights.get('self_preservation', 0.5) * 0.6
            # But loyal characters resist retreat
            score -= self.decision_weights.get('faction_loyalty', 0.5) * 0.2
        
        elif action_type == 'communicate':
            # Diplomatic characters prefer communication
            score += self.personality_traits.get('diplomatic', 0.5) * 0.4
            score += self.decision_weights.get('personal_relationships', 0.5) * 0.3
        
        elif action_type in ['investigate', 'guard']:
            # Mission-focused actions
            score += self.decision_weights.get('mission_success', 0.5) * 0.5
            score += self.decision_weights.get('faction_loyalty', 0.5) * 0.3
        
        # 叙事行动评估 - 基于故事情境的角色偏好...
        elif 'narrative_type' in action:
            narrative_score = self._evaluate_narrative_action(action, situation)
            score += narrative_score
        
        # Apply profession-specific bonuses
        score = self._apply_profession_modifiers(score, action_type)
        
        # Apply personality modifiers
        score = self._apply_personality_modifiers(score, action_type)
        
        # Apply situation-specific modifiers
        score = self._apply_situational_modifiers(score, action, situation)
        
        return max(0.0, min(1.0, score))  # Clamp to 0.0-1.0 range
    
    def _select_best_action(self, action_evaluations: List[Tuple[Dict[str, Any], float]]) -> Optional[CharacterAction]:
        """
        Select the best action from evaluated options.
        
        Args:
            action_evaluations: List of (action, score) tuples
            
        Returns:
            CharacterAction object for the selected action, or None if no action chosen
        """
        if not action_evaluations:
            return None
        
        # Sort by evaluation score (highest first)
        action_evaluations.sort(key=lambda x: x[1], reverse=True)
        
        # Select the highest-scoring action
        best_action, best_score = action_evaluations[0]
        
        # Determine character-specific action threshold
        action_threshold = self._get_character_action_threshold()
        
        # If no actions meet threshold, provide profession-specific default action
        if best_score < action_threshold:
            return self._get_profession_default_action()
        
        # Create CharacterAction object
        action_type = best_action.get('type', 'observe')
        target = best_action.get('target')
        
        # Generate reasoning based on character perspective
        reasoning = self._generate_action_reasoning(best_action, best_score)
        
        return CharacterAction(
            action_type=action_type,
            target=target,
            parameters=best_action.get('parameters', {}),
            priority=self._determine_action_priority(best_action, best_score),
            reasoning=reasoning
        )
    
    def _generate_action_reasoning(self, action: Dict[str, Any], score: float) -> str:
        """
        Generate character-appropriate reasoning for the selected action.
        
        This method creates a narrative explanation of why the character chose
        this action, written from their perspective and reflecting their personality.
        """
        action_type = action.get('type', 'observe')
        character_name = self.character_data.get('name', 'Unknown')
        
        # Basic reasoning templates (future phases will use more sophisticated generation)
        reasoning_templates = {
            'observe': f"{character_name} chooses to observe the situation carefully before acting.",
            'attack': f"{character_name} determines that aggressive action is necessary to achieve objectives.",
            'retreat': f"{character_name} assesses that tactical withdrawal is the wisest course.",
            'communicate': f"{character_name} believes communication can resolve the current situation.",
            'investigate': f"{character_name} feels compelled to gather more information about the matter.",
            'guard': f"{character_name} takes a defensive position to protect what matters most.",
        }
        
        base_reasoning = reasoning_templates.get(action_type, f"{character_name} takes action based on current assessment.")
        
        # Add personality-based flavoring
        if score > 0.8:
            if self.personality_traits.get('confident', 0.5) > 0.7:
                base_reasoning += " This decision feels absolutely correct."
            elif self.personality_traits.get('dutiful', 0.5) > 0.7:
                base_reasoning += " Duty demands nothing less."
        
        return base_reasoning
    
    def _determine_action_priority(self, action: Dict[str, Any], score: float) -> ActionPriority:
        """Determine the priority level for the selected action."""
        action_type = action.get('type', 'observe')
        
        # High priority actions
        if action_type in ['retreat', 'call_for_help'] or score > 0.9:
            return ActionPriority.CRITICAL
        elif action_type in ['attack', 'defensive_action'] or score > 0.7:
            return ActionPriority.HIGH
        elif score > 0.5:
            return ActionPriority.NORMAL
        else:
            return ActionPriority.LOW
    
    def update_internal_memory(self, new_log: Dict[str, Any]) -> None:
        """
        Update the character's internal memory system with new experiences and information.
        
        This method simulates how characters learn and adapt from their experiences,
        updating their knowledge, relationships, and behavioral patterns over time.
        
        The memory system distinguishes between:
        - Short-term memory: Recent events and observations (limited capacity)
        - Long-term memory: Important events that shape character development
        - Relationship updates: Changes in how the character views other entities
        - Belief updates: How experiences modify the character's worldview
        
        Args:
            new_log: Dictionary containing new experience/event information to process
                    Expected format:
                    {
                        'event_type': str,  # e.g., 'combat', 'dialogue', 'discovery'
                        'description': str,  # Human-readable description
                        'participants': List[str],  # Other entities involved
                        'outcome': str,  # Result of the event
                        'location': str,  # Where it happened
                        'timestamp': float,  # When it occurred
                        'significance': float,  # 0.0-1.0 importance level
                        'emotional_impact': str,  # Character's emotional response
                    }
        """
        try:
            logger.info(f"Agent {self.agent_id} updating memory with new experience")
            
            # Validate input format
            if not isinstance(new_log, dict):
                logger.warning(f"Invalid memory log format for agent {self.agent_id}")
                return
            
            # Extract key information from the log
            event_type = new_log.get('event_type', 'unknown')
            description = new_log.get('description', '')
            participants = new_log.get('participants', [])
            outcome = new_log.get('outcome', '')
            significance = new_log.get('significance', 0.5)
            emotional_impact = new_log.get('emotional_impact', 'neutral')
            
            # Create memory entry
            memory_entry = {
                'timestamp': new_log.get('timestamp', datetime.now().timestamp()),
                'event_type': event_type,
                'description': description,
                'participants': participants,
                'outcome': outcome,
                'personal_interpretation': self._generate_personal_interpretation(new_log),
                'emotional_response': emotional_impact,
                'significance': significance,
            }
            
            # Add to short-term memory
            self.short_term_memory.append(memory_entry)
            
            # Manage short-term memory capacity (keep last 20 entries)
            if len(self.short_term_memory) > 20:
                self.short_term_memory.pop(0)
            
            # Determine if this should be stored in long-term memory
            if self._should_store_in_long_term_memory(memory_entry):
                self.long_term_memory.append(memory_entry)
                logger.info(f"Storing significant event in long-term memory for {self.agent_id}")
            
            # Update relationships based on the experience
            self._update_relationships_from_experience(new_log)
            
            # Update beliefs and worldview
            self._update_worldview_from_experience(new_log)
            
            # Update personality traits if this was a significant experience
            if significance > 0.7:
                self._update_personality_from_experience(new_log)
            
            # Log the memory update
            logger.info(f"Memory updated for {self.agent_id}: {event_type} - {description[:50]}...")
            
        except Exception as e:
            logger.error(f"Error updating memory for agent {self.agent_id}: {str(e)}")
    
    def update_memory(self, event_string: str) -> None:
        """
        Append a new event string to the memory.log file within the agent's directory.
        
        This method provides persistent memory logging by writing events to a memory.log
        file in the character's directory. This allows for long-term memory persistence
        across simulation sessions.
        
        Args:
            event_string: A string describing the event to be logged
        """
        try:
            # Construct path to memory.log file in character directory
            memory_log_path = os.path.join(self.character_directory_path, 'memory.log')
            
            # Create timestamp for the log entry
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Format the log entry with timestamp
            log_entry = f"[{timestamp}] {event_string}\n"
            
            # Append to memory.log file (create if doesn't exist)
            with open(memory_log_path, 'a', encoding='utf-8') as memory_file:
                memory_file.write(log_entry)
            
            logger.debug(f"Agent {self.agent_id} appended to memory log: {event_string[:50]}...")
            
        except Exception as e:
            logger.error(f"Failed to update memory log for agent {self.agent_id}: {str(e)}")
            # Don't raise exception to avoid breaking character functionality
    
    def _generate_personal_interpretation(self, log_entry: Dict[str, Any]) -> str:
        """
        Generate the character's personal interpretation of an event.
        
        This method creates a subjective understanding of what happened,
        filtered through the character's personality, biases, and existing beliefs.
        """
        event_type = log_entry.get('event_type', 'unknown')
        description = log_entry.get('description', '')
        outcome = log_entry.get('outcome', '')
        
        # Apply character bias to interpretation
        character_name = self.character_data.get('name', 'Unknown')
        
        # Simple interpretation generation (placeholder for future AI integration)
        if event_type == 'combat':
            if 'victory' in outcome.lower():
                return f"{character_name} proved their worth in battle, as expected."
            else:
                return f"{character_name} encountered fierce resistance, but learned valuable lessons."
        
        elif event_type == 'dialogue':
            if 'successful' in outcome.lower():
                return f"{character_name} successfully communicated their position."
            else:
                return f"{character_name} encountered stubborn opposition to reason."
        
        elif event_type == 'discovery':
            return f"{character_name} uncovered important information that confirms their understanding."
        
        else:
            return f"{character_name} experienced {description} with typical results."
    
    def _should_store_in_long_term_memory(self, memory_entry: Dict[str, Any]) -> bool:
        """
        Determine if a memory should be stored in long-term memory.
        
        Factors include:
        - Significance level of the event
        - Emotional impact on the character
        - Relevance to character's goals and beliefs
        - Uniqueness of the experience
        """
        significance = memory_entry.get('significance', 0.5)
        event_type = memory_entry.get('event_type', '')
        emotional_response = memory_entry.get('emotional_response', 'neutral')
        
        # High significance events always go to long-term memory
        if significance > 0.8:
            return True
        
        # Strong emotional responses create lasting memories
        if emotional_response in ['triumph', 'rage', 'despair', 'love', 'hatred']:
            return True
        
        # First experiences of certain types are memorable
        if event_type in ['first_combat', 'betrayal', 'promotion', 'major_discovery']:
            return True
        
        # Random chance for moderate significance events
        if significance > 0.6:
            import random
            return random.random() < significance
        
        return False
    
    def _update_relationships_from_experience(self, log_entry: Dict[str, Any]) -> None:
        """Update relationship values based on shared experiences."""
        participants = log_entry.get('participants', [])
        outcome = log_entry.get('outcome', '')
        event_type = log_entry.get('event_type', '')
        
        for participant in participants:
            if participant == self.agent_id:
                continue  # Skip self
            
            current_relationship = self.relationships.get(participant, 0.0)
            
            # Calculate relationship change based on experience
            change = 0.0
            
            if event_type == 'combat':
                if 'allied' in outcome.lower() or 'cooperation' in outcome.lower():
                    change = 0.1  # Positive experience fighting together
                elif 'betrayal' in outcome.lower():
                    change = -0.3  # Strong negative impact
                elif 'enemy' in outcome.lower():
                    change = -0.1  # Combat against this entity
            
            elif event_type == 'dialogue':
                if 'agreement' in outcome.lower():
                    change = 0.05  # Small positive from successful dialogue
                elif 'conflict' in outcome.lower():
                    change = -0.05  # Small negative from disagreement
            
            elif event_type == 'assistance':
                change = 0.15  # Helping each other builds relationships
            
            # Apply the change
            new_relationship = max(-1.0, min(1.0, current_relationship + change))
            self.relationships[participant] = new_relationship
            
            if abs(change) > 0.05:  # Log significant relationship changes
                logger.info(f"{self.agent_id} relationship with {participant}: {current_relationship:.2f} -> {new_relationship:.2f}")
    
    def _update_worldview_from_experience(self, log_entry: Dict[str, Any]) -> None:
        """Update character's worldview and beliefs based on experience."""
        event_type = log_entry.get('event_type', '')
        outcome = log_entry.get('outcome', '')
        
        # Update faction relationships based on experience
        if event_type == 'faction_encounter':
            faction = log_entry.get('faction', '')
            if faction and faction in self.subjective_worldview['faction_relationships']:
                current_view = self.subjective_worldview['faction_relationships'][faction]
                
                if 'hostile' in outcome.lower():
                    new_view = max(-1.0, current_view - 0.1)
                elif 'cooperative' in outcome.lower():
                    new_view = min(1.0, current_view + 0.1)
                else:
                    new_view = current_view
                
                self.subjective_worldview['faction_relationships'][faction] = new_view
        
        # Update threat assessments
        if 'threat' in log_entry.get('description', '').lower():
            location = log_entry.get('location', '')
            if location:
                current_threats = self.subjective_worldview.get('active_threats', {})
                threat_level = self._assess_threat_from_description(log_entry.get('description', ''))
                current_threats[location] = threat_level
                self.subjective_worldview['active_threats'] = current_threats
    
    def _update_personality_from_experience(self, log_entry: Dict[str, Any]) -> None:
        """
        Update personality traits based on significant experiences.
        
        This represents character growth and development over time.
        Only major events (significance > 0.7) can change personality.
        """
        event_type = log_entry.get('event_type', '')
        outcome = log_entry.get('outcome', '')
        emotional_impact = log_entry.get('emotional_impact', 'neutral')
        
        # Small personality adjustments based on experience type
        trait_adjustments = {}
        
        if event_type == 'combat':
            if 'victory' in outcome.lower():
                trait_adjustments['confident'] = 0.02
                trait_adjustments['aggressive'] = 0.01
            elif 'defeat' in outcome.lower():
                trait_adjustments['cautious'] = 0.02
                trait_adjustments['confident'] = -0.01
        
        elif event_type == 'betrayal':
            trait_adjustments['trusting'] = -0.05
            trait_adjustments['suspicious'] = 0.03
        
        elif event_type == 'leadership_success':
            trait_adjustments['confident'] = 0.03
            trait_adjustments['leadership'] = 0.02
        
        # Apply personality adjustments
        for trait, adjustment in trait_adjustments.items():
            current_value = self.personality_traits.get(trait, 0.5)
            new_value = max(0.0, min(1.0, current_value + adjustment))
            self.personality_traits[trait] = new_value
            
            if abs(adjustment) > 0.02:  # Log significant personality changes
                logger.info(f"{self.agent_id} personality change - {trait}: {current_value:.2f} -> {new_value:.2f}")
    
    # Helper methods for decision-making system
    
    def _update_location_knowledge(self, location_info: Dict[str, Any]) -> None:
        """Update character's knowledge about locations."""
        for location_id, info in location_info.items():
            if location_id not in self.subjective_worldview['location_knowledge']:
                self.subjective_worldview['location_knowledge'][location_id] = {}
            
            # Update with new information (character's subjective interpretation)
            location_knowledge = self.subjective_worldview['location_knowledge'][location_id]
            location_knowledge.update(info)
    
    def _update_entity_knowledge(self, entity_info: Dict[str, Any]) -> None:
        """Update character's knowledge about other entities."""
        for entity_id, info in entity_info.items():
            if entity_id not in self.subjective_worldview['known_entities']:
                self.subjective_worldview['known_entities'][entity_id] = {}
            
            # Update with new information
            entity_knowledge = self.subjective_worldview['known_entities'][entity_id]
            entity_knowledge.update(info)
    
    def _update_faction_knowledge(self, faction_info: Dict[str, Any]) -> None:
        """Update character's understanding of faction relationships."""
        for faction_id, info in faction_info.items():
            if faction_id in self.subjective_worldview['faction_relationships']:
                # Modify existing relationship based on new information
                current_relationship = self.subjective_worldview['faction_relationships'][faction_id]
                # Simple adjustment logic (placeholder for more sophisticated analysis)
                if info.get('hostility_increased', False):
                    new_relationship = max(-1.0, current_relationship - 0.1)
                elif info.get('cooperation_increased', False):
                    new_relationship = min(1.0, current_relationship + 0.1)
                else:
                    new_relationship = current_relationship
                
                self.subjective_worldview['faction_relationships'][faction_id] = new_relationship
    
    def _would_character_know_about_event(self, event: Dict[str, Any]) -> bool:
        """Determine if the character would realistically know about an event."""
        event_location = event.get('location', '')
        event_scope = event.get('scope', 'local')  # local, regional, sector-wide, galaxy-wide
        
        # Characters always know about events at their current location
        if event_location == self.current_location:
            return True
        
        # Characters know about major events based on their information networks
        if event_scope in ['sector-wide', 'galaxy-wide']:
            return True
        
        # Characters might know about regional events based on their connections
        if event_scope == 'regional':
            # Simple logic: characters with high social connections know more
            social_connectivity = len(self.relationships) / 10.0  # Rough measure
            import random
            return random.random() < social_connectivity
        
        return False
    
    def _process_subjective_event(self, event: Dict[str, Any]) -> None:
        """Process an event through the character's subjective interpretation."""
        # Create subjective interpretation of the event
        interpretation = SubjectiveInterpretation(
            original_event_id=event.get('id', ''),
            character_understanding=self._interpret_event_description(event),
            emotional_response=self._determine_emotional_response(event),
            threat_assessment=self._assess_event_threat_level(event),
        )
        
        # Add to recent events in subjective worldview
        self.subjective_worldview['recent_events'].append({
            'original_event': event,
            'interpretation': interpretation,
            'processed_at': datetime.now().timestamp(),
        })
        
        # Keep only recent events (last 10)
        if len(self.subjective_worldview['recent_events']) > 10:
            self.subjective_worldview['recent_events'].pop(0)
    
    def _interpret_event_description(self, event: Dict[str, Any]) -> str:
        """Generate character's subjective interpretation of an event."""
        description = event.get('description', '')
        event_type = event.get('type', '')
        
        character_name = self.character_data.get('name', 'Unknown')
        
        # Apply character bias to event interpretation
        if event_type == 'battle':
            primary_faction = self.subjective_worldview.get('primary_faction', '')
            if primary_faction.lower() in description.lower():
                return f"{character_name} sees this as {primary_faction} forces acting with honor and purpose."
            else:
                return f"{character_name} observes military action with strategic interest."
        
        elif event_type == 'political':
            return f"{character_name} interprets this political development in light of faction interests."
        
        else:
            return f"{character_name} understands this event as: {description}"
    
    def _determine_emotional_response(self, event: Dict[str, Any]) -> str:
        """Determine character's emotional response to an event."""
        event_type = event.get('type', '')
        participants = event.get('participants', [])
        outcome = event.get('outcome', '')
        
        # Check if event involves entities the character cares about
        involves_allies = any(p in self.relationships and self.relationships[p] > 0.5 for p in participants)
        involves_enemies = any(p in self.relationships and self.relationships[p] < -0.5 for p in participants)
        
        if event_type == 'battle':
            if involves_allies and 'victory' in outcome.lower():
                return 'triumph'
            elif involves_allies and 'defeat' in outcome.lower():
                return 'concern'
            elif involves_enemies and 'defeat' in outcome.lower():
                return 'satisfaction'
            else:
                return 'interest'
        
        elif event_type == 'death':
            if involves_allies:
                return 'grief'
            elif involves_enemies:
                return 'grim_satisfaction'
            else:
                return 'solemn_reflection'
        
        else:
            return 'neutral'
    
    def _assess_event_threat_level(self, event: Dict[str, Any]) -> ThreatLevel:
        """Assess how threatening an event is to the character."""
        event_type = event.get('type', '')
        location = event.get('location', '')
        scope = event.get('scope', 'local')
        
        # Events at character's location are more threatening
        if location == self.current_location:
            if event_type in ['battle', 'invasion', 'disaster']:
                return ThreatLevel.HIGH
            elif event_type in ['unrest', 'investigation']:
                return ThreatLevel.MODERATE
        
        # Large-scale events are inherently threatening
        if scope == 'galaxy-wide' and event_type in ['war', 'invasion']:
            return ThreatLevel.MODERATE
        
        return ThreatLevel.LOW
    
    def _assess_overall_threat_level(self) -> ThreatLevel:
        """Assess the overall threat level in the character's environment."""
        active_threats = self.subjective_worldview.get('active_threats', {})
        recent_events = self.subjective_worldview.get('recent_events', [])
        
        # Check for immediate threats
        if any(threat == ThreatLevel.CRITICAL for threat in active_threats.values()):
            return ThreatLevel.CRITICAL
        
        # Check recent events for threat indicators
        recent_threat_levels = [
            event.get('interpretation', {}).get('threat_assessment', ThreatLevel.NEGLIGIBLE)
            for event in recent_events[-5:]  # Last 5 events
        ]
        
        high_threats = sum(1 for t in recent_threat_levels if t in [ThreatLevel.HIGH, ThreatLevel.CRITICAL])
        if high_threats >= 2:
            return ThreatLevel.HIGH
        
        moderate_threats = sum(1 for t in recent_threat_levels if t == ThreatLevel.MODERATE)
        if moderate_threats >= 3:
            return ThreatLevel.MODERATE
        
        return ThreatLevel.LOW
    
    def _get_current_goals(self) -> List[Dict[str, Any]]:
        """Get the character's current goals and objectives."""
        # Placeholder implementation - future phases will have more sophisticated goal tracking
        current_goals = self.subjective_worldview.get('current_goals', [])
        
        # Add default goals based on character type and situation
        if not current_goals:
            primary_faction = self.subjective_worldview.get('primary_faction', '')
            
            if 'imperial guard' in primary_faction.lower():
                current_goals = [
                    {'type': 'protect', 'target': 'imperium', 'priority': 0.8},
                    {'type': 'follow_orders', 'target': 'superior_officer', 'priority': 0.9},
                    {'type': 'survive', 'target': 'self', 'priority': 0.6},
                ]
            elif 'space marine' in primary_faction.lower():
                current_goals = [
                    {'type': 'serve_emperor', 'target': 'emperor', 'priority': 1.0},
                    {'type': 'protect', 'target': 'humanity', 'priority': 0.9},
                    {'type': 'destroy_enemies', 'target': 'heretics', 'priority': 0.8},
                ]
            else:
                current_goals = [
                    {'type': 'survive', 'target': 'self', 'priority': 0.7},
                    {'type': 'advance_faction', 'target': primary_faction, 'priority': 0.6},
                ]
        
        return current_goals
    
    def _assess_available_resources(self) -> Dict[str, Any]:
        """Assess what resources the character has available."""
        # Placeholder implementation
        return {
            'combat_readiness': 0.8,  # Based on equipment and health
            'information_network': len(self.relationships) / 10.0,  # Social connections
            'mobility': 0.7,  # Ability to move/act freely
            'authority': self.personality_traits.get('leadership', 0.5),  # Influence over others
        }
    
    def _assess_social_obligations(self) -> List[Dict[str, Any]]:
        """Assess social obligations and duties."""
        obligations = []
        
        # Obligations to highly-regarded relationships
        for entity, relationship_strength in self.relationships.items():
            if relationship_strength > 0.7:
                obligations.append({
                    'type': 'protect',
                    'target': entity,
                    'strength': relationship_strength,
                })
        
        # Faction obligations
        faction_loyalty = self.decision_weights.get('faction_loyalty', 0.5)
        if faction_loyalty > 0.6:
            primary_faction = self.subjective_worldview.get('primary_faction', '')
            obligations.append({
                'type': 'serve_faction',
                'target': primary_faction,
                'strength': faction_loyalty,
            })
        
        return obligations
    
    def _assess_mission_status(self) -> Dict[str, Any]:
        """Assess the status of current missions/objectives."""
        current_goals = self._get_current_goals()
        
        return {
            'active_missions': len(current_goals),
            'highest_priority': max((goal.get('priority', 0.5) for goal in current_goals), default=0.0),
            'mission_types': [goal.get('type', 'unknown') for goal in current_goals],
        }
    
    def _assess_environmental_factors(self) -> Dict[str, Any]:
        """Assess environmental factors affecting decision-making."""
        location_knowledge = self.subjective_worldview.get('location_knowledge', {})
        current_location_info = location_knowledge.get(self.current_location, {})
        
        return {
            'location_safety': current_location_info.get('safety_level', 0.5),
            'resource_availability': current_location_info.get('resources', 0.5),
            'strategic_importance': current_location_info.get('strategic_value', 0.5),
            'friendly_presence': current_location_info.get('friendly_forces', 0.3),
        }
    
    def _character_has_combat_capability(self) -> bool:
        """Determine if character has meaningful combat capabilities."""
        capabilities = self.character_data.get('capabilities', {})
        combat_skills = capabilities.get('skills', {})
        
        # Check for combat-related skills
        combat_keywords = ['combat', 'weapon', 'tactical', 'military', 'warfare']
        
        for skill_name, skill_description in combat_skills.items():
            if any(keyword in skill_name.lower() or keyword in skill_description.lower() 
                   for keyword in combat_keywords):
                return True
        
        # Default based on faction
        primary_faction = self.subjective_worldview.get('primary_faction', '')
        combat_factions = ['imperial guard', 'space marine', 'chaos', 'ork']
        
        return any(faction in primary_faction.lower() for faction in combat_factions)
    
    def _apply_personality_modifiers(self, base_score: float, action_type: str) -> float:
        """Apply personality-based modifiers to action scoring."""
        modified_score = base_score
        
        # Aggressive personalities prefer direct action
        if action_type in ['attack', 'confront'] and self.personality_traits.get('aggressive', 0.5) > 0.7:
            modified_score += 0.2
        
        # Cautious personalities prefer observation and defensive actions
        if action_type in ['observe', 'retreat', 'defensive_action'] and self.personality_traits.get('cautious', 0.5) > 0.7:
            modified_score += 0.15
        
        # Diplomatic personalities prefer communication
        if action_type == 'communicate' and self.personality_traits.get('diplomatic', 0.5) > 0.7:
            modified_score += 0.2
        
        # Loyal personalities prioritize faction-serving actions
        if action_type in ['guard', 'serve_faction'] and self.personality_traits.get('loyal', 0.5) > 0.7:
            modified_score += 0.15
        
        return modified_score
    
    def _apply_situational_modifiers(self, base_score: float, action: Dict[str, Any], situation: Dict[str, Any]) -> float:
        """Apply situation-specific modifiers to action scoring."""
        modified_score = base_score
        action_type = action.get('type', '')
        
        # High threat situations modify action preferences
        threat_level = situation.get('threat_level', ThreatLevel.NEGLIGIBLE)
        
        if threat_level == ThreatLevel.CRITICAL:
            if action_type in ['retreat', 'call_for_help']:
                modified_score += 0.3  # Survival actions become much more attractive
            elif action_type in ['attack', 'investigate']:
                modified_score -= 0.2  # Risky actions become less attractive
        
        # Resource limitations affect action viability
        resources = situation.get('available_resources', {})
        if action_type == 'attack' and resources.get('combat_readiness', 1.0) < 0.3:
            modified_score -= 0.4  # Can't fight effectively
        
        if action_type == 'communicate' and resources.get('information_network', 1.0) < 0.2:
            modified_score -= 0.2  # Limited communication options
        
        # Mission priorities affect action scoring
        mission_status = situation.get('mission_status', {})
        if action_type in ['investigate', 'guard'] and mission_status.get('highest_priority', 0) > 0.8:
            modified_score += 0.2  # Mission-relevant actions get priority
        
        return modified_score
    
    def _assess_threat_from_description(self, description: str) -> ThreatLevel:
        """Assess threat level based on textual description."""
        description_lower = description.lower()
        
        critical_keywords = ['annihilation', 'extermination', 'tyranid_hive', 'chaos_incursion']
        high_keywords = ['battle', 'invasion', 'attack', 'war', 'hostile']
        moderate_keywords = ['conflict', 'tension', 'unrest', 'suspicious']
        
        if any(keyword in description_lower for keyword in critical_keywords):
            return ThreatLevel.CRITICAL
        elif any(keyword in description_lower for keyword in high_keywords):
            return ThreatLevel.HIGH
        elif any(keyword in description_lower for keyword in moderate_keywords):
            return ThreatLevel.MODERATE
        else:
            return ThreatLevel.LOW
    
    # Phase 2 LLM Integration Methods
    
    def _llm_enhanced_decision_making(self, world_state_update: Dict[str, Any], 
                                    situation_assessment: Dict[str, Any], 
                                    available_actions: List[Dict[str, Any]]) -> Optional[CharacterAction]:
        """
        Enhanced decision-making using LLM integration for Phase 2 development.
        
        This method constructs a character-specific prompt, calls the LLM for decision guidance,
        and parses the response into a structured CharacterAction format.
        
        Args:
            world_state_update: Current world state information
            situation_assessment: Character's assessment of current situation
            available_actions: List of possible actions the character can take
            
        Returns:
            CharacterAction object based on LLM guidance, or None if LLM suggests waiting
            
        Raises:
            Exception: If LLM integration fails (caught by calling method for fallback)
        """
        try:
            logger.debug(f"Agent {self.agent_id} beginning LLM-enhanced decision making")
            
            # Step 1: Construct dynamic, character-specific prompt
            prompt = self._construct_character_prompt(world_state_update, situation_assessment, available_actions)
            
            # Step 2: Call LLM with constructed prompt
            llm_response = self._call_llm(prompt)
            
            # Step 3: Parse LLM response into structured action
            parsed_action = self._parse_llm_response(llm_response, available_actions)
            
            # Step 4: Validate and return the action
            if parsed_action:
                logger.debug(f"Agent {self.agent_id} successfully processed LLM response into action: {parsed_action.action_type}")
                return parsed_action
            else:
                logger.debug(f"Agent {self.agent_id} LLM response parsed as 'wait/observe' action")
                return None
                
        except Exception as e:
            logger.error(f"LLM-enhanced decision making failed for agent {self.agent_id}: {str(e)}")
            raise  # Re-raise for fallback handling
    
    def _construct_character_prompt(self, world_state_update: Dict[str, Any], 
                                  situation_assessment: Dict[str, Any], 
                                  available_actions: List[Dict[str, Any]]) -> str:
        """
        Construct a dynamic, character-specific prompt for LLM decision-making.
        
        This method builds a contextual prompt that includes:
        - Character identity, faction, and personality traits from character sheet
        - Current world state and recent events
        - Character's subjective interpretation and relationships
        - Available actions and decision context
        - Character-specific decision criteria and motivations
        
        Args:
            world_state_update: Current world state information
            situation_assessment: Character's assessment of current situation
            available_actions: List of possible actions
            
        Returns:
            Formatted prompt string for LLM processing
        """
        character_name = self.character_data.get('name', 'Unknown Character')
        primary_faction = self.subjective_worldview.get('primary_faction', 'Unknown Faction')
        
        # Build character background section
        character_background = f"""CHARACTER IDENTITY:
Name: {character_name}
Faction: {primary_faction}
Rank/Role: {self.character_data.get('rank_role', 'Unknown')}
Current Status: {self.current_status}
Morale Level: {self.morale_level:.2f} (-1.0 to 1.0 scale)"""
        
        # Build personality traits section
        personality_section = "PERSONALITY TRAITS:\n"
        for trait, value in self.personality_traits.items():
            personality_section += f"- {trait.replace('_', ' ').title()}: {value:.2f} (strength on 0.0-1.0 scale)\n"
        
        # Build decision weights section
        decision_weights_section = "DECISION-MAKING PRIORITIES:\n"
        for weight, value in self.decision_weights.items():
            decision_weights_section += f"- {weight.replace('_', ' ').title()}: {value:.2f} (importance on 0.0-1.0 scale)\n"
        
        # Build current situation section
        threat_level = situation_assessment.get('threat_level', ThreatLevel.NEGLIGIBLE)
        current_goals = situation_assessment.get('current_goals', [])
        
        # Add turn-specific context to prevent identical prompts
        current_turn = world_state_update.get('current_turn', 'Unknown')
        simulation_time = world_state_update.get('simulation_time', 'Unknown')
        
        situation_section = f"""CURRENT SITUATION:
Turn Number: {current_turn}
Simulation Time: {simulation_time}
Threat Level: {threat_level.value}
Location: {self.current_location or 'Unknown'}
Active Goals: {len(current_goals)} mission objectives
Known Entities: {len(self.subjective_worldview.get('known_entities', {}))}
Recent Events: {len(self.subjective_worldview.get('recent_events', []))}"""
        
        # Build world state update section
        world_state_section = "WORLD STATE UPDATE:\n"
        recent_events = world_state_update.get('recent_events', [])
        if recent_events:
            world_state_section += "Recent Events:\n"
            for event in recent_events[-3:]:  # Last 3 events
                world_state_section += f"- {event.get('type', 'unknown')}: {event.get('description', 'No description')}\n"
        else:
            world_state_section += "No significant recent events reported.\n"
        
        location_updates = world_state_update.get('location_updates', {})
        if location_updates:
            world_state_section += "Location Updates:\n"
            for location, info in location_updates.items():
                world_state_section += f"- {location}: {info}\n"
        
        # Build narrative context section
        narrative_section = ""
        if hasattr(self, 'narrative_state') and self.narrative_state:
            narrative_section = "NARRATIVE CONTEXT:\n"
            campaign_title = self.narrative_state.get('current_campaign', '')
            if campaign_title:
                narrative_section += f"Campaign: {campaign_title}\n"
            
            story_setting = self.narrative_state.get('story_setting', '')
            if story_setting:
                narrative_section += f"Setting: {story_setting}\n"
            
            current_atmosphere = self.narrative_state.get('current_atmosphere', '')
            if current_atmosphere:
                narrative_section += f"Atmosphere: {current_atmosphere}\n"
            
            current_prompt = self.narrative_state.get('current_narrative_prompt', '')
            if current_prompt:
                narrative_section += f"Character Situation: {current_prompt}\n"
            
            faction_prompt = self.narrative_state.get('faction_narrative_prompt', '')
            if faction_prompt:
                narrative_section += f"Faction Context: {faction_prompt}\n"
            
            story_markers = self.narrative_state.get('story_markers', [])
            if story_markers:
                narrative_section += f"Story Progress: {', '.join(story_markers[-3:])}\n"  # Last 3 markers
            
            narrative_section += "\n"
        
        # Build available actions section
        actions_section = "AVAILABLE ACTIONS:\n"
        for i, action in enumerate(available_actions, 1):
            action_desc = action.get('description', 'No description')
            if 'narrative_type' in action:
                action_desc += f" (Story Action: {action['narrative_type']})"
            actions_section += f"{i}. {action.get('type', 'unknown')}: {action_desc}\n"
        
        # Build action history context to prevent repetitive responses
        action_history_section = "ACTION HISTORY:\n"
        # Add timestamp-based differentiation for each prompt 
        import datetime
        current_timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]  # Include milliseconds
        action_history_section += f"Current Time: {current_timestamp}\n"
        action_history_section += f"Turn Context: This is turn {current_turn} of the simulation.\n"
        if hasattr(self, 'last_action_taken'):
            action_history_section += f"Previous Action: {getattr(self, 'last_action_taken', 'None')}\n"
        else:
            action_history_section += "Previous Action: This is my first decision in the simulation.\n"
        action_history_section += f"Agent State: Active and operational with current morale {self.morale_level:.2f}\n"
        
        # Build relationships context
        relationships_section = "KEY RELATIONSHIPS:\n"
        important_relationships = {k: v for k, v in self.relationships.items() if abs(v) > 0.3}
        if important_relationships:
            for entity, strength in important_relationships.items():
                relationship_type = 'Strong Ally' if strength > 0.7 else 'Ally' if strength > 0.3 else 'Enemy' if strength < -0.3 else 'Strong Enemy'
                relationships_section += f"- {entity}: {relationship_type} ({strength:.2f})\n"
        else:
            relationships_section += "No significant relationships recorded.\n"
        
        # Construct final prompt
        prompt = f"""{character_background}

{personality_section}
{decision_weights_section}
{situation_section}

{world_state_section}
{narrative_section}
{action_history_section}
{relationships_section}
{actions_section}
DECISION REQUEST:
As {character_name}, a {primary_faction} character with the personality and priorities described above, what action would you take in this situation? Consider your character's traits, faction loyalty, current goals, and the recent events.

Please respond in the following format:
ACTION: [choose one of the numbered available actions or 'wait_observe']
TARGET: [specify target if applicable, or 'none']
REASONING: [explain your decision from the character's perspective in 1-2 sentences]

Example response:
ACTION: 3
TARGET: hostile_entity_alpha
REASONING: As a loyal servant of the Imperium, my duty requires me to engage threats to protect innocent civilians. My aggressive nature and high mission success priority compel me to take direct action."""
        
        logger.debug(f"Agent {self.agent_id} constructed prompt of {len(prompt)} characters")
        return prompt
    
    def _call_llm(self, prompt: str) -> str:
        """
        Call Gemini API for LLM response with fallback to deterministic responses.
        
        This function integrates with Google's Gemini API to generate character-appropriate
        responses. If the API is unavailable or fails, it falls back to the original
        deterministic response system to maintain functionality.
        
        Args:
            prompt: Formatted prompt string for the LLM
            
        Returns:
            String response from Gemini API or fallback response system
            
        Raises:
            Exception: If both API and fallback systems fail
        """
        logger.debug(f"Agent {self.agent_id} calling LLM with prompt length: {len(prompt)} characters")
        
        # Step 1: Try Gemini API integration
        api_key = _validate_gemini_api_key()
        
        if api_key:
            try:
                # Attempt Gemini API call
                api_response = _make_gemini_api_request(prompt, api_key, timeout=30)
                
                if api_response:
                    logger.info(f"Agent {self.agent_id} successfully received Gemini API response")
                    
                    # Validate that the response follows expected format
                    if self._is_valid_llm_response_format(api_response):
                        return api_response
                    else:
                        logger.warning(f"Agent {self.agent_id} Gemini API response doesn't follow expected format, using fallback")
                        # Continue to fallback
                else:
                    logger.warning(f"Agent {self.agent_id} Gemini API returned empty response, using fallback")
                    # Continue to fallback
                    
            except Exception as e:
                logger.error(f"Agent {self.agent_id} Gemini API call failed: {e}")
                # Continue to fallback
        
        # Step 2: Use fallback response system
        try:
            logger.info(f"Agent {self.agent_id} using fallback response system")
            fallback_response = _generate_fallback_response(
                self.agent_id, 
                prompt, 
                self.character_data,
                self.personality_traits,
                self.decision_weights,
                self.subjective_worldview
            )
            return fallback_response
            
        except Exception as e:
            # Last resort - return a basic observe action
            logger.error(f"Agent {self.agent_id} fallback response generation failed: {e}")
            return "ACTION: observe\nTARGET: none\nREASONING: System error - defaulting to observation mode for safety."
    
    def _is_valid_llm_response_format(self, response: str) -> bool:
        """
        Validate that LLM response follows the expected ACTION/TARGET/REASONING format.
        
        Args:
            response: Response string from LLM
            
        Returns:
            bool: True if response is properly formatted, False otherwise
        """
        try:
            # Check for required fields
            has_action = bool(re.search(r'ACTION:\s*(.+)', response, re.IGNORECASE))
            has_target = bool(re.search(r'TARGET:\s*(.+)', response, re.IGNORECASE))
            has_reasoning = bool(re.search(r'REASONING:\s*(.+)', response, re.IGNORECASE))
            
            if has_action and has_target and has_reasoning:
                logger.debug(f"Agent {self.agent_id} LLM response format validation passed")
                return True
            else:
                logger.debug(f"Agent {self.agent_id} LLM response missing required fields - ACTION: {has_action}, TARGET: {has_target}, REASONING: {has_reasoning}")
                return False
                
        except Exception as e:
            logger.error(f"Agent {self.agent_id} error validating LLM response format: {e}")
            return False
    
    def _parse_llm_response(self, llm_response: str, available_actions: List[Dict[str, Any]]) -> Optional[CharacterAction]:
        """
        Parse LLM response string into structured CharacterAction format.
        
        This method handles various response formats and provides graceful fallback
        parsing for different LLM output styles.
        
        Expected format:
        ACTION: [action_identifier]
        TARGET: [target_value or 'none']
        REASONING: [explanation]
        
        Args:
            llm_response: Raw string response from LLM
            available_actions: List of available actions for validation
            
        Returns:
            CharacterAction object or None if parsing fails or action is 'wait'
            
        Raises:
            Exception: If response parsing fails completely
        """
        try:
            logger.debug(f"Agent {self.agent_id} parsing LLM response: {llm_response[:100]}...")
            
            # Initialize parsing variables
            action_type = None
            target = None
            reasoning = "LLM-guided decision"
            
            # Parse ACTION field
            action_match = re.search(r'ACTION:\s*(.+)', llm_response, re.IGNORECASE)
            if action_match:
                action_value = action_match.group(1).strip()
                
                # Handle numeric action references (1, 2, 3, etc.)
                if action_value.isdigit():
                    action_index = int(action_value) - 1  # Convert to 0-based index
                    if 0 <= action_index < len(available_actions):
                        action_type = available_actions[action_index].get('type', 'observe')
                    else:
                        logger.warning(f"Agent {self.agent_id} LLM referenced invalid action index: {action_value}")
                        action_type = 'observe'  # Fallback
                else:
                    # Handle direct action type references
                    action_type = action_value.lower().replace(' ', '_')
                    
                    # Validate against available actions
                    available_action_types = [action.get('type', '') for action in available_actions]
                    if action_type not in available_action_types:
                        # Try to find closest match
                        for available_type in available_action_types:
                            if available_type in action_type or action_type in available_type:
                                action_type = available_type
                                break
                        else:
                            logger.warning(f"Agent {self.agent_id} LLM specified unavailable action: {action_value}")
                            action_type = 'observe'  # Fallback
            else:
                logger.warning(f"Agent {self.agent_id} could not parse ACTION from LLM response")
                action_type = 'observe'  # Fallback
            
            # Parse TARGET field
            target_match = re.search(r'TARGET:\s*(.+)', llm_response, re.IGNORECASE)
            if target_match:
                target_value = target_match.group(1).strip()
                if target_value.lower() not in ['none', 'null', 'n/a', 'na']:
                    target = target_value
            
            # Parse REASONING field
            reasoning_match = re.search(r'REASONING:\s*(.+?)(?=\n\n|\Z)', llm_response, re.IGNORECASE | re.DOTALL)
            if reasoning_match:
                reasoning = reasoning_match.group(1).strip()
                # Clean up reasoning text
                reasoning = re.sub(r'\s+', ' ', reasoning)  # Normalize whitespace
                reasoning = reasoning[:200]  # Limit length
            
            # Handle wait/observe actions
            if action_type in ['wait', 'wait_observe', 'observe'] and not target:
                logger.debug(f"Agent {self.agent_id} LLM recommended waiting/observing")
                return None
            
            # Create and validate CharacterAction
            if action_type:
                # Determine action priority based on action type and reasoning
                priority = self._determine_llm_action_priority(action_type, reasoning)
                
                character_action = CharacterAction(
                    action_type=action_type,
                    target=target,
                    parameters={},  # Could be enhanced in future to parse parameters
                    priority=priority,
                    reasoning=f"[LLM-Guided] {reasoning}"
                )
                
                logger.debug(f"Agent {self.agent_id} successfully parsed LLM response into action: {action_type}")
                return character_action
            else:
                logger.warning(f"Agent {self.agent_id} failed to determine action type from LLM response")
                return None
                
        except Exception as e:
            logger.error(f"Error parsing LLM response for agent {self.agent_id}: {str(e)}")
            # Return None for malformed responses to trigger algorithmic fallback
            return None
    
    def _determine_llm_action_priority(self, action_type: str, reasoning: str) -> ActionPriority:
        """
        Determine action priority for LLM-guided actions.
        
        Args:
            action_type: Type of action chosen by LLM
            reasoning: LLM's reasoning for the action
            
        Returns:
            ActionPriority enum value
        """
        reasoning_lower = reasoning.lower()
        
        # Critical priority actions
        if action_type in ['retreat', 'call_for_help', 'emergency_action']:
            return ActionPriority.CRITICAL
        
        # High priority indicators in reasoning
        high_priority_keywords = ['urgent', 'immediate', 'critical', 'essential', 'vital', 'emergency']
        if any(keyword in reasoning_lower for keyword in high_priority_keywords):
            return ActionPriority.HIGH
        
        # Combat and mission actions typically high priority
        if action_type in ['attack', 'defend', 'guard', 'suppress']:
            return ActionPriority.HIGH
        
        # 任务相关的行动评级，为神圣使命分配适当优先级...
        if action_type in ['investigate', 'secure', 'advance_mission']:
            return ActionPriority.NORMAL
        
        # Low priority for routine actions
        if action_type in ['observe', 'communicate', 'move'] and 'routine' in reasoning_lower:
            return ActionPriority.LOW
        
        # Default to normal priority
        return ActionPriority.NORMAL
    
    # Public interface methods for future DirectorAgent integration
    
    def get_character_state(self) -> Dict[str, Any]:
        """
        Get current character state for DirectorAgent queries.
        
        Returns:
            Dictionary containing current character state information
        """
        return {
            'agent_id': self.agent_id,
            'name': self.character_data.get('name', 'Unknown'),
            'faction': self.subjective_worldview.get('primary_faction', 'Unknown'),
            'location': self.current_location,
            'status': self.current_status,
            'morale': self.morale_level,
            'current_goals': self._get_current_goals(),
            'recent_actions': self.short_term_memory[-5:] if self.short_term_memory else [],
            'relationships': dict(list(self.relationships.items())[:10]),  # Top 10 relationships
            'threat_assessment': self._assess_overall_threat_level().value,
        }
    
    def get_known_information(self, topic: str) -> List[Dict[str, Any]]:
        """
        Query character's knowledge about a specific topic.
        
        Args:
            topic: Topic to query about (entity name, location, faction, etc.)
            
        Returns:
            List of knowledge entries related to the topic
        """
        knowledge_entries = []
        
        # Search in known entities
        if topic in self.subjective_worldview.get('known_entities', {}):
            knowledge_entries.append({
                'type': 'entity',
                'topic': topic,
                'information': self.subjective_worldview['known_entities'][topic],
                'confidence': 0.8,  # Character's confidence in this information
            })
        
        # Search in location knowledge
        if topic in self.subjective_worldview.get('location_knowledge', {}):
            knowledge_entries.append({
                'type': 'location',
                'topic': topic,
                'information': self.subjective_worldview['location_knowledge'][topic],
                'confidence': 0.7,
            })
        
        # Search in faction relationships
        if topic in self.subjective_worldview.get('faction_relationships', {}):
            knowledge_entries.append({
                'type': 'faction',
                'topic': topic,
                'information': {
                    'relationship': self.subjective_worldview['faction_relationships'][topic],
                    'assessment': 'ally' if self.subjective_worldview['faction_relationships'][topic] > 0.3 else
                                 'enemy' if self.subjective_worldview['faction_relationships'][topic] < -0.3 else
                                 'neutral'
                },
                'confidence': 0.6,
            })
        
        # Search in memories
        topic_lower = topic.lower()
        relevant_memories = [
            memory for memory in self.short_term_memory + self.long_term_memory
            if topic_lower in memory.get('description', '').lower() or 
               topic in memory.get('participants', [])
        ]
        
        for memory in relevant_memories[-3:]:  # Last 3 relevant memories
            knowledge_entries.append({
                'type': 'memory',
                'topic': topic,
                'information': {
                    'event': memory.get('description', ''),
                    'outcome': memory.get('outcome', ''),
                    'personal_view': memory.get('personal_interpretation', ''),
                },
                'confidence': 0.9,  # High confidence in personal memories
                'timestamp': memory.get('timestamp', 0),
            })
        
        return knowledge_entries
    
    def process_communication(self, sender_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming communication from another agent.
        
        Args:
            sender_id: ID of the sending agent
            message: Message data structure
            
        Returns:
            Response message or acknowledgment
        """
        logger.info(f"Agent {self.agent_id} received communication from {sender_id}")
        
        message_type = message.get('type', 'general')
        content = message.get('content', '')
        
        # Determine relationship with sender
        relationship = self.relationships.get(sender_id, 0.0)
        
        # Generate response based on character personality and relationship
        response_tone = self._determine_communication_tone(sender_id, relationship, message_type)
        response_content = self._generate_communication_response(content, relationship, message_type)
        
        # Update memory with this communication
        comm_log = {
            'event_type': 'dialogue',
            'description': f"Communication with {sender_id}: {content}",
            'participants': [sender_id],
            'outcome': 'information_exchange',
            'significance': 0.3,
            'emotional_impact': 'neutral',
        }
        self.update_internal_memory(comm_log)
        
        return {
            'from': self.agent_id,
            'to': sender_id,
            'type': 'response',
            'content': response_content,
            'tone': response_tone,
            'timestamp': datetime.now().timestamp(),
        }
    
    def _determine_communication_tone(self, sender_id: str, relationship: float, message_type: str) -> str:
        """Determine appropriate tone for communication response."""
        if relationship > 0.7:
            return 'friendly'
        elif relationship > 0.3:
            return 'professional'
        elif relationship > -0.3:
            return 'neutral'
        elif relationship > -0.7:
            return 'cold'
        else:
            return 'hostile'
    
    def _generate_communication_response(self, content: str, relationship: float, message_type: str) -> str:
        """Generate appropriate response content."""
        character_name = self.character_data.get('name', 'Unknown')
        
        # Simple response generation (placeholder for future AI integration)
        if message_type == 'greeting':
            if relationship > 0.5:
                return f"{character_name} acknowledges the friendly greeting."
            else:
                return f"{character_name} responds with a curt nod."
        
        elif message_type == 'request':
            if relationship > 0.3:
                return f"{character_name} considers the request carefully."
            else:
                return f"{character_name} is skeptical of the request."
        
        elif message_type == 'information':
            return f"{character_name} processes the information according to their understanding."
        
        else:
            return f"{character_name} responds appropriately to the communication."
    
    def _identify_narrative_actions(self, situation_assessment: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Identify narrative actions available based on current story context.
        
        Returns story-driven actions like investigate, dialogue, diplomacy, and betrayal
        that are appropriate for the current narrative situation.
        
        Args:
            situation_assessment: Character's assessment of the current situation
            
        Returns:
            List of narrative action dictionaries
        """
        narrative_actions = []
        
        # Check if character has narrative context
        if not hasattr(self, 'narrative_state') or not self.narrative_state:
            return narrative_actions
        
        available_story_actions = self.narrative_state.get('available_narrative_actions', [])
        current_atmosphere = self.narrative_state.get('current_atmosphere', '')
        
        # Investigation actions (always available in narrative mode)
        narrative_actions.extend([
            {
                'type': 'investigate',
                'narrative_type': NarrativeActionType.INVESTIGATE.value,
                'description': 'Investigate mysterious elements in the environment',
                'target': 'environmental_clues'
            },
            {
                'type': 'observe_environment',
                'narrative_type': NarrativeActionType.OBSERVE_ENVIRONMENT.value,
                'description': 'Carefully observe the surrounding area for story details',
                'target': 'story_environment'
            }
        ])
        
        # Dialogue actions (available when there are potential conversation targets)
        if 'dialogue' in available_story_actions or 'communication' in current_atmosphere.lower():
            narrative_actions.extend([
                {
                    'type': 'dialogue',
                    'narrative_type': NarrativeActionType.DIALOGUE.value,
                    'description': 'Engage in conversation to gather information',
                    'target': 'other_characters'
                },
                {
                    'type': 'communicate_faction',
                    'narrative_type': NarrativeActionType.COMMUNICATE_FACTION.value,
                    'description': 'Communicate with faction representatives',
                    'target': 'faction_contacts'
                }
            ])
        
        # Diplomacy actions (available to characters with high faction loyalty)
        character_faction_loyalty = self.character_data.get('decision_weights', {}).get('faction_loyalty', 0.5)
        if character_faction_loyalty > 0.7:
            narrative_actions.append({
                'type': 'diplomacy',
                'narrative_type': NarrativeActionType.DIPLOMACY.value,
                'description': 'Attempt diplomatic negotiation or alliance building',
                'target': 'potential_allies'
            })
        
        # Betrayal actions (dramatic story option, rarely chosen)
        if 'betrayal' in available_story_actions or random.random() < 0.1:  # 10% chance for dramatic tension
            narrative_actions.append({
                'type': 'betrayal',
                'narrative_type': NarrativeActionType.BETRAYAL.value,
                'description': 'Betray an established relationship for personal gain',
                'target': 'trusted_ally'
            })
        
        return narrative_actions
    
    def _evaluate_narrative_action(self, action: Dict[str, Any], situation: Dict[str, Any]) -> float:
        """
        Evaluate narrative actions based on character personality and story context.
        
        Args:
            action: Narrative action to evaluate
            situation: Current situation assessment
            
        Returns:
            Float score representing action desirability for narrative purposes
        """
        score = 0.0
        action_type = action.get('type', '')
        narrative_type = action.get('narrative_type', '')
        
        # Base character personality influence
        personality_traits = self.character_data.get('personality_traits', {})
        
        if narrative_type == NarrativeActionType.INVESTIGATE.value:
            # Cautious characters prefer investigation
            if personality_traits.get('cautious', 0) > 0.6:
                score += 0.3
            # Tech-focused characters like investigation
            if 'tech' in self.character_data.get('name', '').lower():
                score += 0.2
        
        elif narrative_type == NarrativeActionType.DIALOGUE.value:
            # Charismatic characters prefer dialogue
            if personality_traits.get('charismatic', 0) > 0.6:
                score += 0.3
            # Social characters like communication
            if personality_traits.get('social', 0) > 0.5:
                score += 0.2
        
        elif narrative_type == NarrativeActionType.DIPLOMACY.value:
            # High faction loyalty characters prefer diplomacy
            faction_loyalty = self.character_data.get('decision_weights', {}).get('faction_loyalty', 0.5)
            score += faction_loyalty * 0.4
            # Personal relationships matter for diplomacy
            personal_relationships = self.character_data.get('decision_weights', {}).get('personal_relationships', 0.5)
            score += personal_relationships * 0.2
        
        elif narrative_type == NarrativeActionType.BETRAYAL.value:
            # Generally low score unless character has specific traits
            score -= 0.5  # Base negative score
            # Selfish or ruthless characters might consider betrayal
            if personality_traits.get('ruthless', 0) > 0.7:
                score += 0.4
            if personality_traits.get('selfish', 0) > 0.7:
                score += 0.3
        
        # Story context influence
        if hasattr(self, 'narrative_state') and self.narrative_state:
            current_narrative_prompt = self.narrative_state.get('current_narrative_prompt', '')
            
            # Boost actions that align with narrative prompts
            if action_type.lower() in current_narrative_prompt.lower():
                score += 0.4
            
            # Consider faction-specific prompts
            faction_prompt = self.narrative_state.get('faction_narrative_prompt', '')
            if faction_prompt and action_type.lower() in faction_prompt.lower():
                score += 0.3
        
        return max(score, 0.0)  # Ensure non-negative score
    
    def _apply_profession_modifiers(self, base_score: float, action_type: str) -> float:
        """
        Apply profession-specific scoring modifiers based on character role.
        
        Args:
            base_score: Base action score
            action_type: Type of action being evaluated
            
        Returns:
            Modified score with profession-specific bonuses/penalties
        """
        score = base_score
        character_role = self.character_data.get('role', '').lower()
        character_name = self.character_data.get('name', '').lower()
        character_specialization = self.character_data.get('specialization', '').lower()
        
        # Engineer profession bonuses
        if 'engineer' in character_role or 'engineer' in character_name:
            if action_type in ['investigate', 'analyze', 'repair', 'construct']:
                score += 0.3  # Engineers excel at technical tasks
            elif action_type in ['observe', 'assess']:
                score += 0.2  # Engineers are analytical
            elif action_type in ['attack', 'retreat']:
                score -= 0.1  # Engineers prefer non-combat solutions
                
        # Pilot profession bonuses
        elif 'pilot' in character_role or 'pilot' in character_name:
            if action_type in ['scout', 'patrol', 'escort', 'maneuver']:
                score += 0.3  # Pilots excel at mobility and reconnaissance
            elif action_type in ['attack', 'defend']:
                score += 0.2  # Pilots are combat-capable
            elif action_type in ['investigate', 'research']:
                score -= 0.1  # Pilots prefer action over analysis
                
        # Scientist profession bonuses
        elif 'scientist' in character_role or 'scientist' in character_name or 'research' in character_specialization:
            if action_type in ['observe_environment', 'investigate', 'analyze', 'research']:
                score += 0.3  # Scientists excel at observation and analysis
            elif action_type in ['experiment', 'study', 'document']:
                score += 0.2  # Scientists are methodical
            elif action_type in ['attack', 'intimidate']:
                score -= 0.2  # Scientists prefer peaceful approaches
        
        # Specialization-specific bonuses
        if 'xenobiology' in character_specialization and action_type in ['observe_environment', 'investigate']:
            score += 0.15  # Xenobiologists love studying environments
        elif 'systems' in character_specialization and action_type in ['investigate', 'repair']:
            score += 0.15  # Systems specialists focus on technical analysis
        elif 'starfighter' in character_specialization and action_type in ['scout', 'attack']:
            score += 0.15  # Starfighter specialists are combat-oriented
            
        return score
    
    def _get_profession_actions(self) -> List[Dict[str, Any]]:
        """
        Get profession-specific actions that are always available to this character.
        
        Returns:
            List of action dictionaries specific to the character's profession
        """
        profession_actions = []
        character_role = self.character_data.get('role', '').lower()
        character_name = self.character_data.get('name', '').lower()
        character_specialization = self.character_data.get('specialization', '').lower()
        
        # Engineer profession actions
        if 'engineer' in character_role or 'engineer' in character_name:
            profession_actions.extend([
                {
                    'type': 'investigate',
                    'target': 'technical_systems',
                    'description': 'Analyze technical systems and infrastructure'
                },
                {
                    'type': 'repair',
                    'target': 'damaged_equipment',
                    'description': 'Repair or optimize mechanical systems'
                },
                {
                    'type': 'assess',
                    'target': 'system_integrity',
                    'description': 'Assess structural and system integrity'
                }
            ])
            
        # Pilot profession actions
        elif 'pilot' in character_role or 'pilot' in character_name:
            profession_actions.extend([
                {
                    'type': 'scout',
                    'target': 'surrounding_area',
                    'description': 'Scout area for tactical information'
                },
                {
                    'type': 'patrol',
                    'target': 'perimeter',
                    'description': 'Patrol to maintain situational awareness'
                },
                {
                    'type': 'maneuver',
                    'target': 'tactical_position',
                    'description': 'Take strategic position for advantage'
                }
            ])
            
        # Scientist profession actions
        elif 'scientist' in character_role or 'scientist' in character_name or 'research' in character_specialization:
            profession_actions.extend([
                {
                    'type': 'observe_environment',
                    'target': 'environmental_data',
                    'description': 'Systematically observe and record environmental phenomena'
                },
                {
                    'type': 'analyze',
                    'target': 'collected_data',
                    'description': 'Analyze gathered data for patterns and insights'
                },
                {
                    'type': 'experiment',
                    'target': 'hypothesis',
                    'description': 'Conduct scientific tests to verify theories'
                }
            ])
            
        # Specialization-specific actions
        if 'xenobiology' in character_specialization:
            profession_actions.append({
                'type': 'study_lifeforms',
                'target': 'alien_specimens',
                'description': 'Study alien biological specimens'
            })
        elif 'systems' in character_specialization:
            profession_actions.append({
                'type': 'system_diagnostics',
                'target': 'complex_systems',
                'description': 'Run comprehensive system diagnostics'
            })
        elif 'starfighter' in character_specialization:
            profession_actions.append({
                'type': 'tactical_assessment',
                'target': 'combat_situation',
                'description': 'Assess tactical combat possibilities'
            })
            
        return profession_actions
    
    def _get_character_action_threshold(self) -> float:
        """
        Get character-specific action threshold based on personality and profession.
        
        Returns:
            Float threshold value (lower = more likely to take action)
        """
        base_threshold = 0.3
        
        # Adjust based on character role/profession
        character_role = self.character_data.get('role', '').lower()
        character_name = self.character_data.get('name', '').lower()
        
        # Engineers are analytical and cautious
        if 'engineer' in character_role or 'engineer' in character_name:
            return base_threshold + 0.1  # More cautious
        
        # Pilots are decisive and action-oriented
        elif 'pilot' in character_role or 'pilot' in character_name:
            return base_threshold - 0.2  # More decisive
        
        # Scientists are methodical but curious
        elif 'scientist' in character_role or 'scientist' in character_name:
            return base_threshold - 0.1  # Slightly more decisive
        
        # Adjust based on personality traits
        personality_traits = self.character_data.get('personality_traits', {})
        if isinstance(personality_traits, dict):
            # Cautious characters have higher threshold
            if personality_traits.get('cautious', 0) > 0.7:
                base_threshold += 0.15
            # Decisive/brave characters have lower threshold
            if personality_traits.get('decisive', 0) > 0.7 or personality_traits.get('brave', 0) > 0.7:
                base_threshold -= 0.15
        
        return max(0.1, min(0.5, base_threshold))  # Clamp between 0.1 and 0.5
    
    def _get_profession_default_action(self) -> Optional[CharacterAction]:
        """
        Get profession-specific default action when no other actions score high enough.
        
        Returns:
            CharacterAction object for profession-appropriate default behavior
        """
        character_role = self.character_data.get('role', '').lower()
        character_name = self.character_data.get('name', '').lower()
        character_specialization = self.character_data.get('specialization', '').lower()
        
        # Engineer default: Analyze systems or investigate technical aspects
        if 'engineer' in character_role or 'engineer' in character_name:
            return CharacterAction(
                action_type='investigate',
                target='technical_systems',
                parameters={'focus': 'system_analysis'},
                priority='medium',
                reasoning=f"As an engineer, {self.character_data.get('name', 'I')} should analyze the technical aspects of the current situation to identify potential issues or improvements."
            )
        
        # Pilot default: Scout or maintain readiness
        elif 'pilot' in character_role or 'pilot' in character_name:
            return CharacterAction(
                action_type='scout',
                target='surrounding_area',
                parameters={'focus': 'tactical_assessment'},
                priority='medium',
                reasoning=f"{self.character_data.get('name', 'I')} maintains tactical awareness and scouts the area for potential threats or opportunities, as befits a pilot's training."
            )
        
        # Scientist default: Observe and analyze
        elif 'scientist' in character_role or 'scientist' in character_name or 'research' in character_specialization:
            return CharacterAction(
                action_type='observe_environment',
                target='environmental_data',
                parameters={'focus': 'scientific_analysis'},
                priority='medium',
                reasoning=f"Dr. {self.character_data.get('name', 'Unknown')} carefully observes the environment to gather scientific data and identify phenomena worthy of further investigation."
            )
        
        # Generic professional default: Assess situation
        else:
            return CharacterAction(
                action_type='assess',
                target='current_situation',
                parameters={'focus': 'strategic_analysis'},
                priority='low',
                reasoning=f"{self.character_data.get('name', 'I')} takes time to assess the current situation and plan the next course of action."
            )


# Module-level utility functions

def create_character_from_template(template_path: str, character_name: str, **overrides) -> PersonaAgent:
    """
    Create a PersonaAgent from a character sheet template.
    
    This utility function can be used to quickly instantiate characters
    for testing and development purposes.
    
    Args:
        template_path: Path to the character sheet template file
        character_name: Name for the new character
        **overrides: Dictionary of values to override in the template
        
    Returns:
        Configured PersonaAgent instance
    """
    # This is a placeholder implementation
    # Future phases will implement sophisticated template instantiation
    agent = PersonaAgent(template_path)
    
    # Apply overrides
    if 'faction' in overrides:
        agent.subjective_worldview['primary_faction'] = overrides['faction']
    
    if 'location' in overrides:
        agent.current_location = overrides['location']
    
    return agent


def analyze_agent_compatibility(agent1: PersonaAgent, agent2: PersonaAgent) -> Dict[str, float]:
    """
    Analyze compatibility between two PersonaAgents.
    
    This utility function assesses how well two characters would work together
    based on their personality traits, faction alignments, and mutual relationships.
    
    Args:
        agent1: First PersonaAgent
        agent2: Second PersonaAgent
        
    Returns:
        Dictionary with compatibility scores for different aspects
    """
    compatibility = {}
    
    # Faction compatibility
    faction1 = agent1.subjective_worldview.get('primary_faction', '')
    faction2 = agent2.subjective_worldview.get('primary_faction', '')
    
    if faction1 == faction2:
        compatibility['faction_alignment'] = 0.8
    elif faction1 and faction2:
        # Check faction relationships from agent1's perspective
        faction_relationship = agent1.subjective_worldview.get('faction_relationships', {}).get(faction2, 0.0)
        compatibility['faction_alignment'] = max(0.0, (faction_relationship + 1.0) / 2.0)
    else:
        compatibility['faction_alignment'] = 0.5  # Unknown
    
    # Personality compatibility
    personality_compatibility = 0.5
    
    # Complementary traits (aggressive + cautious can work well)
    agent1_aggressive = agent1.personality_traits.get('aggressive', 0.5)
    agent2_cautious = agent2.personality_traits.get('cautious', 0.5)
    
    if agent1_aggressive > 0.7 and agent2_cautious > 0.7:
        personality_compatibility += 0.2
    
    # Similar loyalty levels work well together
    agent1_loyalty = agent1.decision_weights.get('faction_loyalty', 0.5)
    agent2_loyalty = agent2.decision_weights.get('faction_loyalty', 0.5)
    
    loyalty_similarity = 1.0 - abs(agent1_loyalty - agent2_loyalty)
    personality_compatibility += loyalty_similarity * 0.3
    
    compatibility['personality_match'] = max(0.0, min(1.0, personality_compatibility))
    
    # Mutual relationship compatibility
    agent1_to_agent2 = agent1.relationships.get(agent2.agent_id, 0.0)
    agent2_to_agent1 = agent2.relationships.get(agent1.agent_id, 0.0)
    
    compatibility['mutual_relationship'] = (agent1_to_agent2 + agent2_to_agent1) / 2.0
    
    # Overall compatibility
    compatibility['overall'] = (
        compatibility['faction_alignment'] * 0.4 +
        compatibility['personality_match'] * 0.4 +
        compatibility['mutual_relationship'] * 0.2
    )
    
    return compatibility

    def _process_narrative_situation_update(self, narrative_context: Dict[str, Any]) -> None:
        """
        Process narrative situation updates that drive story-focused character decisions.
        
        This method handles story elements that go beyond basic threat assessment,
        including campaign atmosphere, character-specific narrative prompts,
        environmental story elements, and story progression markers.
        
        Args:
            narrative_context: Dictionary containing narrative situation data
        """
        logger.info(f"Agent {self.agent_id} processing narrative situation update")
        
        # Extract narrative elements
        campaign_title = narrative_context.get('campaign_title', '')
        setting = narrative_context.get('setting', '')
        atmosphere = narrative_context.get('atmosphere', '')
        character_context = narrative_context.get('character_specific_context', {})
        available_story_actions = narrative_context.get('available_story_actions', [])
        story_progression = narrative_context.get('story_progression_markers', [])
        
        # Update character's narrative awareness
        if not hasattr(self, 'narrative_state'):
            self.narrative_state = {}
        
        self.narrative_state.update({
            'current_campaign': campaign_title,
            'story_setting': setting,
            'current_atmosphere': atmosphere,
            'character_story_context': character_context,
            'available_narrative_actions': available_story_actions,
            'story_markers': story_progression,
            'last_narrative_update': datetime.now().isoformat()
        })
        
        # Process character-specific narrative prompts
        character_impact = character_context.get(self.agent_id, '')
        if character_impact:
            logger.info(f"Agent {self.agent_id} received character-specific narrative prompt: {character_impact}")
            self.narrative_state['current_narrative_prompt'] = character_impact
        
        # Check for faction-specific prompts
        character_faction = self.character_data.get('faction', '').lower()
        for faction_key in character_context.keys():
            if faction_key.lower() in character_faction:
                faction_prompt = character_context[faction_key]
                logger.info(f"Agent {self.agent_id} received faction-specific narrative prompt: {faction_prompt}")
                self.narrative_state['faction_narrative_prompt'] = faction_prompt
                break
    


# Example usage and testing functions (for development purposes)

def example_usage():
    """
    Example usage of the PersonaAgent class.
    
    This function demonstrates how to create and use PersonaAgents
    for testing and development purposes.
    """
    # This would typically be called with an actual character sheet file
    # For now, we'll show the interface
    
    print("PersonaAgent Example Usage:")
    print("==========================")
    
    # Example character creation (would need actual character sheet file)
    try:
        # agent = PersonaAgent("character_sheets/brother_marcus.md")
        # print(f"Created agent: {agent.character_data.get('name', 'Unknown')}")
        
        # Example decision making
        # world_update = {
        #     'location_updates': {'hive_city_alpha': {'threat_level': 'moderate'}},
        #     'recent_events': [
        #         {
        #             'id': 'event_001',
        #             'type': 'battle',
        #             'description': 'Ork raiders spotted in sector 7',
        #             'scope': 'local'
        #         }
        #     ]
        # }
        # 
        # action = agent.decision_loop(world_update)
        # if action:
        #     print(f"Agent decided to: {action.action_type} - {action.reasoning}")
        
        print("PersonaAgent class is ready for integration with actual character sheets.")
        
    except Exception as e:
        print(f"Example requires actual character sheet file: {e}")


if __name__ == "__main__":
    # Run example usage when script is executed directly
    example_usage()