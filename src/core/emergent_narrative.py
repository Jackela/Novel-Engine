#!/usr/bin/env python3
"""
涌现式叙事系统 (Emergent Narrative System)
=======================================

Milestone 2 Implementation: CausalGraph + Multi-Agent Negotiation + Narrative Coherence

核心理念：通过Agent间的真实交互和因果关系图，自然涌现出连贯的叙事，
而非预设剧本。每个决策都会在因果图中留下轨迹，影响后续的故事发展。

Features:
- CausalGraph 因果关系图：追踪行动-结果的链式关系
- AgentNegotiation 多Agent协商：冲突解决与合作机制  
- NarrativeCoherence 叙事连贯性：智能故事整合与一致性保证
- EmergentEventGenerator 涌现事件生成：基于因果图的新事件生成
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Tuple, Union, Callable
from enum import Enum
from datetime import datetime, timedelta
import json
import uuid
from collections import defaultdict, deque
import networkx as nx
import numpy as np
from abc import ABC, abstractmethod

# Import LLM service for intelligent narrative generation
from src.llm_service import get_llm_service, LLMRequest, ResponseFormat

logger = logging.getLogger(__name__)


class CausalRelationType(Enum):
    """因果关系类型"""
    DIRECT_CAUSE = "direct_cause"           # 直接因果
    INDIRECT_CAUSE = "indirect_cause"       # 间接因果
    ENABLER = "enabler"                     # 使能条件
    CATALYST = "catalyst"                   # 催化剂
    INHIBITOR = "inhibitor"                # 抑制因素
    AMPLIFIER = "amplifier"                # 放大器
    CONTRADICTION = "contradiction"         # 矛盾冲突


class NegotiationStatus(Enum):
    """协商状态"""
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    DEADLOCK = "deadlock"
    RESOLVED = "resolved"
    FAILED = "failed"
    TIMEOUT = "timeout"


class EventPriority(Enum):
    """事件优先级"""
    CRITICAL = 1    # 关键剧情事件
    HIGH = 2        # 重要情节点
    MEDIUM = 3      # 一般事件
    LOW = 4         # 背景事件
    TRIVIAL = 5     # 微小细节


@dataclass
class CausalNode:
    """因果图节点"""
    node_id: str
    event_type: str
    agent_id: Optional[str]
    action_data: Dict[str, Any]
    timestamp: datetime
    location: Optional[str] = None
    participants: List[str] = field(default_factory=list)
    confidence: float = 1.0  # 事件确信度
    narrative_weight: float = 1.0  # 叙事权重
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self):
        return hash(self.node_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'node_id': self.node_id,
            'event_type': self.event_type,
            'agent_id': self.agent_id,
            'action_data': self.action_data,
            'timestamp': self.timestamp.isoformat(),
            'location': self.location,
            'participants': self.participants,
            'confidence': self.confidence,
            'narrative_weight': self.narrative_weight,
            'metadata': self.metadata
        }


@dataclass
class CausalEdge:
    """因果关系边"""
    source_id: str
    target_id: str
    relation_type: CausalRelationType
    strength: float  # 关系强度 0-1
    confidence: float  # 置信度 0-1
    delay: timedelta = timedelta(0)  # 时间延迟
    conditions: List[str] = field(default_factory=list)  # 触发条件
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'source_id': self.source_id,
            'target_id': self.target_id,
            'relation_type': self.relation_type.value,
            'strength': self.strength,
            'confidence': self.confidence,
            'delay_seconds': self.delay.total_seconds(),
            'conditions': self.conditions,
            'metadata': self.metadata
        }


class CausalGraph:
    """因果关系图 - 追踪事件间的因果链"""
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.nodes: Dict[str, CausalNode] = {}
        self.edges: Dict[Tuple[str, str], CausalEdge] = {}
        self.temporal_index: Dict[datetime, List[str]] = defaultdict(list)
        self.agent_index: Dict[str, List[str]] = defaultdict(list)
        self.location_index: Dict[str, List[str]] = defaultdict(list)
        
    def add_event(self, event_node: CausalNode) -> str:
        """添加事件节点到因果图"""
        self.nodes[event_node.node_id] = event_node
        self.graph.add_node(event_node.node_id, **event_node.to_dict())
        
        # 更新索引
        self.temporal_index[event_node.timestamp].append(event_node.node_id)
        if event_node.agent_id:
            self.agent_index[event_node.agent_id].append(event_node.node_id)
        if event_node.location:
            self.location_index[event_node.location].append(event_node.node_id)
        
        logger.debug(f"Added event node: {event_node.node_id}")
        return event_node.node_id
    
    def add_causal_relation(self, causal_edge: CausalEdge) -> bool:
        """添加因果关系"""
        if (causal_edge.source_id not in self.nodes or 
            causal_edge.target_id not in self.nodes):
            logger.warning(f"Cannot add causal relation: nodes not found")
            return False
        
        edge_key = (causal_edge.source_id, causal_edge.target_id)
        self.edges[edge_key] = causal_edge
        
        self.graph.add_edge(
            causal_edge.source_id, 
            causal_edge.target_id, 
            **causal_edge.to_dict()
        )
        
        logger.debug(f"Added causal relation: {causal_edge.source_id} -> {causal_edge.target_id}")
        return True
    
    def find_causal_chain(self, start_node: str, max_depth: int = 5) -> List[List[str]]:
        """查找因果链"""
        chains = []
        
        def dfs(current: str, path: List[str], depth: int):
            if depth >= max_depth:
                return
            
            for successor in self.graph.successors(current):
                new_path = path + [successor]
                chains.append(new_path.copy())
                dfs(successor, new_path, depth + 1)
        
        dfs(start_node, [start_node], 0)
        return chains
    
    def get_influential_events(self, time_window: timedelta = timedelta(hours=1)) -> List[CausalNode]:
        """获取有影响力的事件"""
        now = datetime.now()
        cutoff_time = now - time_window
        
        influential_events = []
        for node_id, node in self.nodes.items():
            if node.timestamp >= cutoff_time:
                # 计算影响力：出度 * 叙事权重 * 置信度
                out_degree = self.graph.out_degree(node_id)
                influence_score = out_degree * node.narrative_weight * node.confidence
                
                if influence_score > 1.0:  # 阈值
                    influential_events.append(node)
        
        # 按影响力排序
        influential_events.sort(key=lambda x: x.narrative_weight * x.confidence, reverse=True)
        return influential_events
    
    def detect_narrative_patterns(self) -> Dict[str, Any]:
        """检测叙事模式"""
        patterns = {
            'conflict_nodes': [],
            'resolution_nodes': [],
            'catalyst_events': [],
            'parallel_storylines': [],
            'convergence_points': []
        }
        
        # 检测冲突节点（多个输入边且包含矛盾关系）
        for node_id in self.graph.nodes():
            in_edges = list(self.graph.in_edges(node_id, data=True))
            if len(in_edges) > 1:
                has_conflict = any(edge_data.get('relation_type') == CausalRelationType.CONTRADICTION.value 
                                 for _, _, edge_data in in_edges)
                if has_conflict:
                    patterns['conflict_nodes'].append(node_id)
        
        # 检测催化剂事件
        for edge_key, edge in self.edges.items():
            if edge.relation_type == CausalRelationType.CATALYST:
                patterns['catalyst_events'].append(edge_key[0])
        
        # 检测收敛点（多个故事线汇聚）
        for node_id in self.graph.nodes():
            in_degree = self.graph.in_degree(node_id)
            if in_degree >= 3:  # 3个或更多输入
                # 检查输入来自不同的故事线
                source_agents = set()
                for pred in self.graph.predecessors(node_id):
                    if pred in self.nodes:
                        agent_id = self.nodes[pred].agent_id
                        if agent_id:
                            source_agents.add(agent_id)
                
                if len(source_agents) >= 2:
                    patterns['convergence_points'].append(node_id)
        
        return patterns
    
    def predict_next_events(self, current_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """预测可能的下一个事件"""
        predictions = []
        
        # 基于最近事件的因果链预测
        recent_events = self.get_influential_events()
        
        for event in recent_events[:5]:  # 只考虑前5个最有影响力的事件
            # 查找此事件可能导致的后续事件
            chains = self.find_causal_chain(event.node_id, max_depth=2)
            
            for chain in chains:
                if len(chain) > 1:  # 至少有一个后续事件
                    next_node_id = chain[1]
                    if next_node_id in self.nodes:
                        next_event = self.nodes[next_node_id]
                        
                        # 计算发生概率
                        edge_key = (event.node_id, next_node_id)
                        if edge_key in self.edges:
                            edge = self.edges[edge_key]
                            probability = edge.strength * edge.confidence * event.confidence
                            
                            predictions.append({
                                'event_type': next_event.event_type,
                                'probability': probability,
                                'trigger_event': event.node_id,
                                'expected_delay': edge.delay.total_seconds(),
                                'conditions': edge.conditions
                            })
        
        # 按概率排序
        predictions.sort(key=lambda x: x['probability'], reverse=True)
        return predictions[:10]  # 返回前10个预测


@dataclass
class NegotiationProposal:
    """协商提议"""
    proposal_id: str
    proposer_id: str
    proposal_type: str  # "action", "resource_allocation", "territory", "cooperation"
    content: Dict[str, Any]
    target_agents: List[str]
    requirements: List[str] = field(default_factory=list)
    benefits_offered: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None


@dataclass
class NegotiationResponse:
    """协商回应"""
    response_id: str
    proposal_id: str
    responder_id: str
    response_type: str  # "accept", "reject", "counter", "conditional"
    content: Dict[str, Any]
    counter_proposal: Optional[Dict[str, Any]] = None
    conditions: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class NegotiationSession:
    """协商会话"""
    session_id: str
    participants: List[str]
    topic: str
    status: NegotiationStatus
    proposals: List[NegotiationProposal] = field(default_factory=list)
    responses: List[NegotiationResponse] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    resolution: Optional[Dict[str, Any]] = None
    timeout_minutes: int = 30


class AgentNegotiationEngine:
    """多Agent协商引擎"""
    
    def __init__(self, llm_service=None):
        self.llm_service = llm_service or get_llm_service()
        self.active_sessions: Dict[str, NegotiationSession] = {}
        self.negotiation_history: List[NegotiationSession] = []
        self.agent_negotiation_profiles: Dict[str, Dict[str, Any]] = {}
    
    def initialize_agent_profile(self, agent_id: str, 
                                negotiation_style: Dict[str, float] = None,
                                priorities: List[str] = None):
        """初始化Agent协商档案"""
        if negotiation_style is None:
            negotiation_style = {
                'cooperativeness': 0.5,
                'competitiveness': 0.5,
                'compromise_willingness': 0.6,
                'patience': 0.7,
                'trust_level': 0.5
            }
        
        self.agent_negotiation_profiles[agent_id] = {
            'style': negotiation_style,
            'priorities': priorities or ['survival', 'mission_success'],
            'successful_negotiations': 0,
            'failed_negotiations': 0,
            'reputation': 0.5
        }
    
    async def initiate_negotiation(self, 
                                 initiator_id: str,
                                 target_agents: List[str],
                                 topic: str,
                                 initial_proposal: Dict[str, Any]) -> str:
        """发起协商"""
        session_id = str(uuid.uuid4())
        
        # 创建协商会话
        session = NegotiationSession(
            session_id=session_id,
            participants=[initiator_id] + target_agents,
            topic=topic,
            status=NegotiationStatus.INITIATED
        )
        
        # 创建初始提议
        proposal = NegotiationProposal(
            proposal_id=str(uuid.uuid4()),
            proposer_id=initiator_id,
            proposal_type=initial_proposal.get('type', 'general'),
            content=initial_proposal,
            target_agents=target_agents,
            expires_at=datetime.now() + timedelta(minutes=session.timeout_minutes)
        )
        
        session.proposals.append(proposal)
        self.active_sessions[session_id] = session
        
        logger.info(f"Negotiation initiated: {session_id} by {initiator_id}")
        
        # 通知目标Agent
        await self._notify_agents_of_proposal(proposal, target_agents)
        
        return session_id
    
    async def _notify_agents_of_proposal(self, proposal: NegotiationProposal, target_agents: List[str]):
        """通知Agent收到新的协商提议"""
        # 这里应该集成到消息系统中
        for agent_id in target_agents:
            logger.debug(f"Notified {agent_id} of proposal {proposal.proposal_id}")
    
    async def respond_to_proposal(self, 
                                proposal_id: str,
                                responder_id: str,
                                response_type: str,
                                response_content: Dict[str, Any] = None) -> bool:
        """回应协商提议"""
        
        # 查找包含此提议的会话
        session = None
        for s in self.active_sessions.values():
            if any(p.proposal_id == proposal_id for p in s.proposals):
                session = s
                break
        
        if not session:
            logger.warning(f"No active session found for proposal {proposal_id}")
            return False
        
        # 验证回应者是否为参与者
        if responder_id not in session.participants:
            logger.warning(f"Agent {responder_id} not participant in session {session.session_id}")
            return False
        
        # 创建回应
        response = NegotiationResponse(
            response_id=str(uuid.uuid4()),
            proposal_id=proposal_id,
            responder_id=responder_id,
            response_type=response_type,
            content=response_content or {}
        )
        
        session.responses.append(response)
        session.updated_at = datetime.now()
        session.status = NegotiationStatus.IN_PROGRESS
        
        # 检查是否需要生成智能回应
        if response_type in ['counter', 'conditional']:
            await self._generate_intelligent_counter_proposal(session, response)
        
        # 检查协商状态
        await self._evaluate_negotiation_status(session)
        
        logger.debug(f"Response added to negotiation {session.session_id}: {response_type}")
        return True
    
    async def _generate_intelligent_counter_proposal(self, 
                                                   session: NegotiationSession,
                                                   response: NegotiationResponse):
        """生成智能反提议"""
        if not self.llm_service:
            return
        
        # 获取协商历史和Agent档案
        responder_profile = self.agent_negotiation_profiles.get(response.responder_id, {})
        
        # 构建LLM请求
        prompt = f"""
        基于以下协商情境，为Agent {response.responder_id}生成一个合理的反提议：

        协商主题：{session.topic}
        原始提议：{session.proposals[-1].content}
        Agent性格特征：{responder_profile.get('style', {})}
        Agent优先级：{responder_profile.get('priorities', [])}
        
        请生成一个JSON格式的反提议，包含：
        - type: 提议类型
        - content: 具体内容
        - requirements: 要求条件
        - benefits_offered: 提供的好处
        """
        
        try:
            llm_request = LLMRequest(
                prompt=prompt,
                response_format=ResponseFormat.JSON,
                max_tokens=500
            )
            
            llm_response = await self.llm_service.process_request(llm_request)
            
            if llm_response and llm_response.success:
                counter_proposal = json.loads(llm_response.content)
                response.counter_proposal = counter_proposal
                logger.debug(f"Generated intelligent counter-proposal for {response.responder_id}")
        
        except Exception as e:
            logger.error(f"Failed to generate counter-proposal: {e}")
    
    async def _evaluate_negotiation_status(self, session: NegotiationSession):
        """评估协商状态"""
        # 检查超时
        if datetime.now() > session.created_at + timedelta(minutes=session.timeout_minutes):
            session.status = NegotiationStatus.TIMEOUT
            self._finalize_session(session)
            return
        
        # 检查是否所有参与者都已回应
        latest_proposal = session.proposals[-1] if session.proposals else None
        if not latest_proposal:
            return
        
        target_responses = [r for r in session.responses if r.proposal_id == latest_proposal.proposal_id]
        
        if len(target_responses) >= len(latest_proposal.target_agents):
            # 所有目标Agent都已回应
            await self._attempt_resolution(session)
    
    async def _attempt_resolution(self, session: NegotiationSession):
        """尝试解决协商"""
        latest_proposal = session.proposals[-1]
        responses = [r for r in session.responses if r.proposal_id == latest_proposal.proposal_id]
        
        # 统计回应类型
        accepts = [r for r in responses if r.response_type == 'accept']
        rejects = [r for r in responses if r.response_type == 'reject']
        counters = [r for r in responses if r.response_type in ['counter', 'conditional']]
        
        # 决议逻辑
        if len(accepts) == len(responses):
            # 全部接受
            session.status = NegotiationStatus.RESOLVED
            session.resolution = {
                'type': 'unanimous_acceptance',
                'proposal': latest_proposal.content,
                'participants': session.participants
            }
            self._update_agent_reputations(session, success=True)
        
        elif len(rejects) > len(accepts):
            # 拒绝过多
            if len(counters) > 0:
                # 有反提议，继续协商
                await self._handle_counter_proposals(session, counters)
            else:
                # 无反提议，协商失败
                session.status = NegotiationStatus.FAILED
                self._update_agent_reputations(session, success=False)
        
        else:
            # 混合回应，尝试智能调解
            await self._intelligent_mediation(session, responses)
        
        if session.status in [NegotiationStatus.RESOLVED, NegotiationStatus.FAILED, NegotiationStatus.TIMEOUT]:
            self._finalize_session(session)
    
    async def _handle_counter_proposals(self, session: NegotiationSession, counters: List[NegotiationResponse]):
        """处理反提议"""
        if not counters:
            return
        
        # 选择最有希望的反提议
        best_counter = max(counters, key=lambda x: self._evaluate_proposal_viability(x.counter_proposal))
        
        # 创建新的提议基于最佳反提议
        new_proposal = NegotiationProposal(
            proposal_id=str(uuid.uuid4()),
            proposer_id=best_counter.responder_id,
            proposal_type=best_counter.counter_proposal.get('type', 'counter'),
            content=best_counter.counter_proposal,
            target_agents=[aid for aid in session.participants if aid != best_counter.responder_id],
            expires_at=datetime.now() + timedelta(minutes=session.timeout_minutes//2)
        )
        
        session.proposals.append(new_proposal)
        await self._notify_agents_of_proposal(new_proposal, new_proposal.target_agents)
        
        logger.info(f"New counter-proposal created in session {session.session_id}")
    
    def _evaluate_proposal_viability(self, proposal: Dict[str, Any]) -> float:
        """评估提议的可行性"""
        if not proposal:
            return 0.0
        
        # 简化的可行性评分
        score = 0.5  # 基础分
        
        # 根据提议内容调整分数
        if 'benefits_offered' in proposal and proposal['benefits_offered']:
            score += 0.2
        
        if 'requirements' in proposal:
            req_count = len(proposal['requirements'])
            score -= min(0.3, req_count * 0.1)  # 要求越多，分数越低
        
        return max(0.0, min(1.0, score))
    
    async def _intelligent_mediation(self, session: NegotiationSession, responses: List[NegotiationResponse]):
        """智能调解"""
        if not self.llm_service:
            session.status = NegotiationStatus.DEADLOCK
            return
        
        # 构建调解请求
        mediation_context = {
            'topic': session.topic,
            'original_proposal': session.proposals[-1].content,
            'responses': [{'agent': r.responder_id, 'type': r.response_type, 'content': r.content} 
                         for r in responses],
            'participant_profiles': {aid: self.agent_negotiation_profiles.get(aid, {}) 
                                   for aid in session.participants}
        }
        
        prompt = f"""
        作为智能调解员，请为以下协商冲突提供解决方案：

        协商情况：{json.dumps(mediation_context, indent=2)}

        请生成一个妥协方案，包含：
        - 调解后的提议内容
        - 对每个参与者的好处说明
        - 实施建议

        返回JSON格式结果。
        """
        
        try:
            llm_request = LLMRequest(
                prompt=prompt,
                response_format=ResponseFormat.JSON,
                max_tokens=800
            )
            
            llm_response = await self.llm_service.process_request(llm_request)
            
            if llm_response and llm_response.success:
                mediation_result = json.loads(llm_response.content)
                
                # 创建调解提议
                mediated_proposal = NegotiationProposal(
                    proposal_id=str(uuid.uuid4()),
                    proposer_id="mediator",
                    proposal_type="mediated_compromise",
                    content=mediation_result,
                    target_agents=session.participants,
                    expires_at=datetime.now() + timedelta(minutes=15)
                )
                
                session.proposals.append(mediated_proposal)
                await self._notify_agents_of_proposal(mediated_proposal, session.participants)
                
                logger.info(f"Mediated proposal created for session {session.session_id}")
            else:
                session.status = NegotiationStatus.DEADLOCK
        
        except Exception as e:
            logger.error(f"Mediation failed: {e}")
            session.status = NegotiationStatus.DEADLOCK
    
    def _update_agent_reputations(self, session: NegotiationSession, success: bool):
        """更新Agent声誉"""
        for agent_id in session.participants:
            if agent_id in self.agent_negotiation_profiles:
                profile = self.agent_negotiation_profiles[agent_id]
                if success:
                    profile['successful_negotiations'] += 1
                    profile['reputation'] = min(1.0, profile['reputation'] + 0.1)
                else:
                    profile['failed_negotiations'] += 1
                    profile['reputation'] = max(0.0, profile['reputation'] - 0.05)
    
    def _finalize_session(self, session: NegotiationSession):
        """结束协商会话"""
        if session.session_id in self.active_sessions:
            del self.active_sessions[session.session_id]
        
        self.negotiation_history.append(session)
        logger.info(f"Negotiation session {session.session_id} finalized with status: {session.status}")
    
    def get_negotiation_summary(self, session_id: str) -> Dict[str, Any]:
        """获取协商摘要"""
        # 在活跃会话中查找
        session = self.active_sessions.get(session_id)
        
        # 在历史记录中查找
        if not session:
            for hist_session in self.negotiation_history:
                if hist_session.session_id == session_id:
                    session = hist_session
                    break
        
        if not session:
            return {}
        
        return {
            'session_id': session.session_id,
            'participants': session.participants,
            'topic': session.topic,
            'status': session.status.value,
            'proposal_count': len(session.proposals),
            'response_count': len(session.responses),
            'duration_minutes': (session.updated_at - session.created_at).total_seconds() / 60,
            'resolution': session.resolution,
            'created_at': session.created_at.isoformat(),
            'updated_at': session.updated_at.isoformat()
        }


class NarrativeCoherenceEngine:
    """叙事连贯性引擎 - 保证故事的一致性和连贯性"""
    
    def __init__(self, causal_graph: CausalGraph, llm_service=None):
        self.causal_graph = causal_graph
        self.llm_service = llm_service or get_llm_service()
        self.story_timeline: List[Dict[str, Any]] = []
        self.character_arcs: Dict[str, Dict[str, Any]] = {}
        self.plot_threads: Dict[str, Dict[str, Any]] = {}
        self.consistency_rules: List[Callable[[Dict], bool]] = []
        
    def register_consistency_rule(self, rule_func: Callable[[Dict], bool]):
        """注册一致性检查规则"""
        self.consistency_rules.append(rule_func)
    
    async def integrate_event_into_narrative(self, 
                                           event: CausalNode,
                                           context_events: List[CausalNode] = None) -> Dict[str, Any]:
        """将事件整合到叙事中"""
        
        # 获取相关的上下文事件
        if context_events is None:
            context_events = self._get_relevant_context_events(event)
        
        # 检查事件一致性
        consistency_check = await self._check_event_consistency(event, context_events)
        
        if not consistency_check['consistent']:
            logger.warning(f"Event consistency issues detected: {consistency_check['issues']}")
            # 尝试修正事件
            corrected_event = await self._correct_event_inconsistencies(event, consistency_check)
            if corrected_event:
                event = corrected_event
            else:
                logger.error(f"Failed to correct event inconsistencies for {event.node_id}")
                return {'success': False, 'issues': consistency_check['issues']}
        
        # 更新角色弧线
        if event.agent_id:
            self._update_character_arc(event.agent_id, event)
        
        # 更新情节线索
        plot_thread = self._identify_plot_thread(event, context_events)
        if plot_thread:
            self._update_plot_thread(plot_thread, event)
        
        # 生成叙事文本
        narrative_text = await self._generate_coherent_narrative(event, context_events)
        
        # 添加到时间线
        narrative_entry = {
            'event_id': event.node_id,
            'timestamp': event.timestamp,
            'agent_id': event.agent_id,
            'narrative_text': narrative_text,
            'plot_thread': plot_thread,
            'character_development': self._extract_character_development(event),
            'causal_links': [edge.source_id for edge in self.causal_graph.edges.values() 
                           if edge.target_id == event.node_id]
        }
        
        self.story_timeline.append(narrative_entry)
        self.story_timeline.sort(key=lambda x: x['timestamp'])
        
        return {
            'success': True,
            'narrative_entry': narrative_entry,
            'plot_thread': plot_thread,
            'character_development': narrative_entry['character_development']
        }
    
    def _get_relevant_context_events(self, event: CausalNode, 
                                    time_window: timedelta = timedelta(hours=2)) -> List[CausalNode]:
        """获取相关的上下文事件"""
        relevant_events = []
        
        # 时间窗口内的事件
        cutoff_time = event.timestamp - time_window
        for node in self.causal_graph.nodes.values():
            if node.timestamp >= cutoff_time and node.node_id != event.node_id:
                relevant_events.append(node)
        
        # 因果相关的事件
        for pred in self.causal_graph.graph.predecessors(event.node_id):
            if pred in self.causal_graph.nodes:
                relevant_events.append(self.causal_graph.nodes[pred])
        
        # 去重并按时间排序
        seen = set()
        unique_events = []
        for evt in relevant_events:
            if evt.node_id not in seen:
                seen.add(evt.node_id)
                unique_events.append(evt)
        
        unique_events.sort(key=lambda x: x.timestamp)
        return unique_events
    
    async def _check_event_consistency(self, 
                                     event: CausalNode,
                                     context_events: List[CausalNode]) -> Dict[str, Any]:
        """检查事件一致性"""
        issues = []
        
        # 应用注册的一致性规则
        for rule in self.consistency_rules:
            try:
                if not rule({'event': event, 'context': context_events}):
                    issues.append(f"Failed consistency rule: {rule.__name__}")
            except Exception as e:
                logger.error(f"Consistency rule error: {e}")
        
        # 基本一致性检查
        # 1. 时间一致性
        if context_events:
            latest_context = max(context_events, key=lambda x: x.timestamp)
            if event.timestamp < latest_context.timestamp:
                issues.append("Temporal inconsistency: event occurs before required context")
        
        # 2. 位置一致性
        if event.location and event.agent_id:
            # 检查Agent是否能在该位置执行该动作
            recent_agent_events = [e for e in context_events 
                                 if e.agent_id == event.agent_id and e.location]
            if recent_agent_events:
                last_location = recent_agent_events[-1].location
                if event.location != last_location and event.action_data.get('type') != 'move':
                    issues.append(f"Location inconsistency: Agent at {last_location} but event at {event.location}")
        
        # 3. 因果一致性
        required_preconditions = event.metadata.get('requires', [])
        for condition in required_preconditions:
            if not any(self._event_satisfies_condition(ctx_event, condition) for ctx_event in context_events):
                issues.append(f"Missing precondition: {condition}")
        
        return {
            'consistent': len(issues) == 0,
            'issues': issues,
            'confidence': max(0.0, 1.0 - len(issues) * 0.2)
        }
    
    def _event_satisfies_condition(self, event: CausalNode, condition: str) -> bool:
        """检查事件是否满足条件"""
        # 简化的条件匹配逻辑
        return (condition.lower() in event.event_type.lower() or
                condition.lower() in str(event.action_data).lower() or
                condition in event.metadata.get('provides', []))
    
    async def _correct_event_inconsistencies(self, 
                                           event: CausalNode,
                                           consistency_check: Dict[str, Any]) -> Optional[CausalNode]:
        """尝试修正事件的不一致性"""
        if not self.llm_service or not consistency_check['issues']:
            return None
        
        correction_prompt = f"""
        请修正以下事件的不一致性问题：

        原始事件：
        - ID: {event.node_id}
        - 类型: {event.event_type}
        - Agent: {event.agent_id}
        - 动作: {event.action_data}
        - 位置: {event.location}
        - 时间: {event.timestamp}

        发现的问题：
        {', '.join(consistency_check['issues'])}

        请提供修正后的事件数据，保持JSON格式：
        {{
            "event_type": "修正后的事件类型",
            "action_data": {{"修正后的动作数据"}},
            "location": "修正后的位置",
            "explanation": "修正说明"
        }}
        """
        
        try:
            llm_request = LLMRequest(
                prompt=correction_prompt,
                response_format=ResponseFormat.JSON,
                max_tokens=500
            )
            
            llm_response = await self.llm_service.process_request(llm_request)
            
            if llm_response and llm_response.success:
                correction_data = json.loads(llm_response.content)
                
                # 创建修正后的事件
                corrected_event = CausalNode(
                    node_id=event.node_id,
                    event_type=correction_data.get('event_type', event.event_type),
                    agent_id=event.agent_id,
                    action_data=correction_data.get('action_data', event.action_data),
                    timestamp=event.timestamp,
                    location=correction_data.get('location', event.location),
                    participants=event.participants,
                    confidence=event.confidence * 0.9,  # 略微降低置信度
                    narrative_weight=event.narrative_weight,
                    metadata={**event.metadata, 'corrected': True, 
                             'correction_reason': correction_data.get('explanation', '')}
                )
                
                logger.info(f"Event {event.node_id} corrected: {correction_data.get('explanation', '')}")
                return corrected_event
        
        except Exception as e:
            logger.error(f"Event correction failed: {e}")
        
        return None
    
    def _update_character_arc(self, agent_id: str, event: CausalNode):
        """更新角色弧线"""
        if agent_id not in self.character_arcs:
            self.character_arcs[agent_id] = {
                'events': [],
                'development_stages': [],
                'personality_changes': [],
                'relationships': {},
                'goals_evolution': []
            }
        
        arc = self.character_arcs[agent_id]
        arc['events'].append({
            'event_id': event.node_id,
            'timestamp': event.timestamp,
            'event_type': event.event_type,
            'significance': event.narrative_weight
        })
        
        # 分析角色发展阶段
        if len(arc['events']) % 5 == 0:  # 每5个事件评估一次发展阶段
            stage = self._analyze_character_development_stage(agent_id, arc['events'][-5:])
            if stage:
                arc['development_stages'].append(stage)
    
    def _analyze_character_development_stage(self, agent_id: str, recent_events: List[Dict]) -> Optional[Dict]:
        """分析角色发展阶段"""
        if not recent_events:
            return None
        
        # 简化的发展阶段分析
        event_types = [evt['event_type'] for evt in recent_events]
        
        stage_type = "exploration"
        if any("combat" in et.lower() or "conflict" in et.lower() for et in event_types):
            stage_type = "conflict"
        elif any("social" in et.lower() or "negotiate" in et.lower() for et in event_types):
            stage_type = "social_development"
        elif any("discover" in et.lower() or "learn" in et.lower() for et in event_types):
            stage_type = "learning"
        
        return {
            'stage_type': stage_type,
            'start_time': recent_events[0]['timestamp'],
            'end_time': recent_events[-1]['timestamp'],
            'key_events': [evt['event_id'] for evt in recent_events]
        }
    
    def _identify_plot_thread(self, event: CausalNode, context_events: List[CausalNode]) -> Optional[str]:
        """识别情节线索"""
        # 基于事件类型和参与者识别情节线索
        thread_key = f"{event.event_type}_{event.location or 'global'}"
        
        # 检查是否与现有情节线索相关
        for thread_id, thread_data in self.plot_threads.items():
            if (event.location == thread_data.get('primary_location') or
                event.agent_id in thread_data.get('involved_agents', []) or
                event.event_type in thread_data.get('related_event_types', [])):
                return thread_id
        
        # 创建新的情节线索
        if event.narrative_weight > 0.5:  # 只为重要事件创建新线索
            thread_id = f"thread_{len(self.plot_threads) + 1}"
            self.plot_threads[thread_id] = {
                'thread_id': thread_id,
                'primary_location': event.location,
                'involved_agents': [event.agent_id] if event.agent_id else [],
                'related_event_types': [event.event_type],
                'start_time': event.timestamp,
                'events': [],
                'status': 'active'
            }
            return thread_id
        
        return None
    
    def _update_plot_thread(self, thread_id: str, event: CausalNode):
        """更新情节线索"""
        if thread_id not in self.plot_threads:
            return
        
        thread = self.plot_threads[thread_id]
        thread['events'].append(event.node_id)
        
        # 更新涉及的Agent
        if event.agent_id and event.agent_id not in thread['involved_agents']:
            thread['involved_agents'].append(event.agent_id)
        
        # 更新相关事件类型
        if event.event_type not in thread['related_event_types']:
            thread['related_event_types'].append(event.event_type)
        
        thread['last_update'] = event.timestamp
    
    async def _generate_coherent_narrative(self, 
                                         event: CausalNode,
                                         context_events: List[CausalNode]) -> str:
        """生成连贯的叙事文本"""
        if not self.llm_service:
            # 返回基础的事件描述
            return f"{event.agent_id or 'Someone'} 进行了 {event.event_type} 在 {event.location or 'unknown location'}"
        
        # 构建叙事上下文
        context_summary = self._create_context_summary(context_events)
        
        narrative_prompt = f"""
        基于以下情境，为当前事件生成一段连贯且生动的叙事文本（150-300字）：

        当前事件：
        - Agent: {event.agent_id}
        - 动作类型: {event.event_type}
        - 具体动作: {event.action_data}
        - 地点: {event.location}
        - 时间: {event.timestamp}

        故事背景：
        {context_summary}

        请生成第三人称叙事，要求：
        1. 保持与之前事件的连贯性
        2. 体现角色的个性和动机
        3. 描述环境和氛围
        4. 为后续发展留有悬念
        """
        
        try:
            llm_request = LLMRequest(
                prompt=narrative_prompt,
                response_format=ResponseFormat.TEXT,
                max_tokens=400
            )
            
            llm_response = await self.llm_service.process_request(llm_request)
            
            if llm_response and llm_response.success:
                return llm_response.content.strip()
        
        except Exception as e:
            logger.error(f"Narrative generation failed: {e}")
        
        # 备用基础叙事
        return self._generate_basic_narrative(event)
    
    def _create_context_summary(self, context_events: List[CausalNode]) -> str:
        """创建上下文摘要"""
        if not context_events:
            return "故事刚刚开始。"
        
        # 按时间排序并选取最相关的事件
        recent_events = sorted(context_events, key=lambda x: x.timestamp)[-5:]
        
        summary_parts = []
        for event in recent_events:
            agent_name = event.agent_id or "某人"
            action_desc = event.event_type
            location = event.location or "未知地点"
            summary_parts.append(f"{agent_name}在{location}{action_desc}")
        
        return "；".join(summary_parts) + "。"
    
    def _generate_basic_narrative(self, event: CausalNode) -> str:
        """生成基础叙事文本"""
        agent_name = event.agent_id or "某个神秘人物"
        action = event.event_type
        location = event.location or "未知的地方"
        
        narrative_templates = [
            f"{agent_name}在{location}进行了{action}，这一举动可能改变接下来的发展。",
            f"在{location}，{agent_name}选择了{action}，周围的环境似乎因此而发生了微妙的变化。",
            f"{agent_name}的{action}在{location}引起了一些反应，故事由此展开新的篇章。"
        ]
        
        # 根据事件ID选择模板，保证一致性
        template_index = hash(event.node_id) % len(narrative_templates)
        return narrative_templates[template_index]
    
    def _extract_character_development(self, event: CausalNode) -> Dict[str, Any]:
        """提取角色发展信息"""
        if not event.agent_id:
            return {}
        
        development = {
            'agent_id': event.agent_id,
            'development_type': 'action_based',
            'growth_indicators': [],
            'relationship_changes': [],
            'skill_demonstrations': []
        }
        
        # 基于事件类型推断发展
        event_type = event.event_type.lower()
        
        if 'social' in event_type or 'negotiate' in event_type:
            development['growth_indicators'].append('social_skills')
        elif 'combat' in event_type or 'attack' in event_type:
            development['growth_indicators'].append('combat_experience')
        elif 'explore' in event_type or 'investigate' in event_type:
            development['growth_indicators'].append('knowledge_seeking')
        elif 'help' in event_type or 'assist' in event_type:
            development['growth_indicators'].append('altruism')
        
        # 分析参与者关系
        if event.participants:
            for participant in event.participants:
                if participant != event.agent_id:
                    development['relationship_changes'].append({
                        'other_agent': participant,
                        'interaction_type': event.event_type,
                        'context': event.location
                    })
        
        return development
    
    def get_narrative_timeline(self, 
                             start_time: datetime = None,
                             end_time: datetime = None,
                             agent_filter: List[str] = None) -> List[Dict[str, Any]]:
        """获取叙事时间线"""
        filtered_timeline = self.story_timeline
        
        # 时间过滤
        if start_time:
            filtered_timeline = [entry for entry in filtered_timeline 
                               if entry['timestamp'] >= start_time]
        
        if end_time:
            filtered_timeline = [entry for entry in filtered_timeline 
                               if entry['timestamp'] <= end_time]
        
        # Agent过滤
        if agent_filter:
            filtered_timeline = [entry for entry in filtered_timeline 
                               if entry['agent_id'] in agent_filter]
        
        return filtered_timeline
    
    def get_coherence_report(self) -> Dict[str, Any]:
        """获取叙事连贯性报告"""
        return {
            'total_events': len(self.story_timeline),
            'character_arcs': len(self.character_arcs),
            'plot_threads': len(self.plot_threads),
            'active_plot_threads': len([t for t in self.plot_threads.values() 
                                      if t['status'] == 'active']),
            'consistency_rule_count': len(self.consistency_rules),
            'timeline_span': {
                'start': self.story_timeline[0]['timestamp'].isoformat() if self.story_timeline else None,
                'end': self.story_timeline[-1]['timestamp'].isoformat() if self.story_timeline else None
            },
            'character_summary': {aid: len(arc['events']) for aid, arc in self.character_arcs.items()},
            'plot_thread_summary': {tid: len(thread['events']) for tid, thread in self.plot_threads.items()}
        }


class EmergentNarrativeEngine:
    """涌现式叙事引擎 - 主引擎类"""
    
    def __init__(self, llm_service=None):
        self.causal_graph = CausalGraph()
        self.negotiation_engine = AgentNegotiationEngine(llm_service)
        self.coherence_engine = NarrativeCoherenceEngine(self.causal_graph, llm_service)
        self.llm_service = llm_service or get_llm_service()
        
        self.active_agents: Set[str] = set()
        self.global_narrative_state: Dict[str, Any] = {}
        
        # 注册默认的一致性规则
        self._register_default_consistency_rules()
        
        logger.info("涌现式叙事引擎初始化完成")
    
    def _register_default_consistency_rules(self):
        """注册默认的一致性规则"""
        
        def basic_causality_rule(data: Dict) -> bool:
            """基础因果逻辑规则"""
            event = data['event']
            context = data['context']
            
            # 检查Agent不能同时在多个地方
            if event.agent_id and event.location:
                same_time_events = [e for e in context 
                                  if e.agent_id == event.agent_id and 
                                  abs((e.timestamp - event.timestamp).total_seconds()) < 60]
                
                for same_time_event in same_time_events:
                    if (same_time_event.location and 
                        same_time_event.location != event.location):
                        return False
            
            return True
        
        def temporal_logic_rule(data: Dict) -> bool:
            """时间逻辑规则"""
            event = data['event']
            
            # 事件不能在未来发生
            return event.timestamp <= datetime.now()
        
        self.coherence_engine.register_consistency_rule(basic_causality_rule)
        self.coherence_engine.register_consistency_rule(temporal_logic_rule)
    
    async def initialize_agent(self, 
                             agent_id: str,
                             negotiation_style: Dict[str, float] = None,
                             priorities: List[str] = None) -> bool:
        """初始化Agent"""
        
        # 初始化协商引擎中的Agent
        self.negotiation_engine.initialize_agent_profile(
            agent_id=agent_id,
            negotiation_style=negotiation_style,
            priorities=priorities
        )
        
        self.active_agents.add(agent_id)
        
        logger.info(f"Agent {agent_id} initialized in emergent narrative engine")
        return True
    
    async def process_agent_action(self, 
                                 agent_id: str,
                                 action_type: str,
                                 action_data: Dict[str, Any],
                                 location: str = None,
                                 participants: List[str] = None) -> Dict[str, Any]:
        """处理Agent行动并生成叙事"""
        
        # 创建事件节点
        event_node = CausalNode(
            node_id=str(uuid.uuid4()),
            event_type=action_type,
            agent_id=agent_id,
            action_data=action_data,
            timestamp=datetime.now(),
            location=location,
            participants=participants or []
        )
        
        # 添加到因果图
        self.causal_graph.add_event(event_node)
        
        # 分析可能的因果关系
        await self._analyze_and_add_causal_relations(event_node)
        
        # 检查是否需要协商
        negotiation_result = await self._check_and_handle_conflicts(event_node)
        
        # 整合到叙事中
        integration_result = await self.coherence_engine.integrate_event_into_narrative(
            event_node
        )
        
        # 预测后续事件
        predictions = self.causal_graph.predict_next_events(self.global_narrative_state)
        
        return {
            'event_id': event_node.node_id,
            'narrative_integration': integration_result,
            'negotiation_result': negotiation_result,
            'causal_effects': self._get_causal_effects(event_node),
            'story_predictions': predictions[:3],  # 前3个预测
            'emergent_opportunities': await self._identify_emergent_opportunities(event_node)
        }
    
    async def _analyze_and_add_causal_relations(self, event_node: CausalNode):
        """分析并添加因果关系"""
        
        # 查找可能的因果前因
        potential_causes = []
        
        # 时间窗口内的相关事件
        time_window = timedelta(hours=1)
        cutoff_time = event_node.timestamp - time_window
        
        for existing_node in self.causal_graph.nodes.values():
            if existing_node.timestamp >= cutoff_time and existing_node.node_id != event_node.node_id:
                
                # 基于位置的关联
                if (existing_node.location == event_node.location or 
                    (existing_node.agent_id == event_node.agent_id)):
                    
                    causal_strength = self._calculate_causal_strength(existing_node, event_node)
                    if causal_strength > 0.3:
                        
                        # 确定关系类型
                        relation_type = self._determine_relation_type(existing_node, event_node)
                        
                        causal_edge = CausalEdge(
                            source_id=existing_node.node_id,
                            target_id=event_node.node_id,
                            relation_type=relation_type,
                            strength=causal_strength,
                            confidence=min(existing_node.confidence, event_node.confidence),
                            delay=event_node.timestamp - existing_node.timestamp
                        )
                        
                        self.causal_graph.add_causal_relation(causal_edge)
                        potential_causes.append((existing_node, causal_edge))
        
        logger.debug(f"Added {len(potential_causes)} causal relations for event {event_node.node_id}")
    
    def _calculate_causal_strength(self, cause_event: CausalNode, effect_event: CausalNode) -> float:
        """计算因果关系强度"""
        strength = 0.0
        
        # 基础关联
        # 1. 同一Agent的连续动作
        if cause_event.agent_id == effect_event.agent_id:
            strength += 0.4
        
        # 2. 同一位置的事件
        if cause_event.location == effect_event.location:
            strength += 0.3
        
        # 3. 参与者重叠
        cause_participants = set([cause_event.agent_id] + cause_event.participants)
        effect_participants = set([effect_event.agent_id] + effect_event.participants)
        overlap = len(cause_participants.intersection(effect_participants))
        if overlap > 0:
            strength += overlap * 0.1
        
        # 4. 事件类型的逻辑关联
        if self._are_logically_related(cause_event.event_type, effect_event.event_type):
            strength += 0.2
        
        # 5. 时间接近性
        time_diff = (effect_event.timestamp - cause_event.timestamp).total_seconds()
        if 0 < time_diff <= 3600:  # 1小时内
            time_factor = max(0, 1.0 - time_diff / 3600)
            strength += 0.1 * time_factor
        
        return min(1.0, strength)
    
    def _are_logically_related(self, cause_type: str, effect_type: str) -> bool:
        """判断事件类型是否逻辑相关"""
        logic_pairs = [
            ('attack', 'defend'),
            ('question', 'answer'),
            ('offer', 'accept'),
            ('offer', 'reject'),
            ('move', 'arrive'),
            ('search', 'discover'),
            ('negotiate', 'agree'),
            ('negotiate', 'disagree')
        ]
        
        for cause, effect in logic_pairs:
            if cause in cause_type.lower() and effect in effect_type.lower():
                return True
        
        return False
    
    def _determine_relation_type(self, cause_event: CausalNode, effect_event: CausalNode) -> CausalRelationType:
        """确定因果关系类型"""
        
        # 基于事件类型判断
        if cause_event.agent_id == effect_event.agent_id:
            return CausalRelationType.DIRECT_CAUSE
        
        elif any(participant in effect_event.participants for participant in [cause_event.agent_id] + cause_event.participants):
            return CausalRelationType.CATALYST
        
        elif self._are_contradictory_events(cause_event, effect_event):
            return CausalRelationType.CONTRADICTION
        
        elif self._is_enabling_event(cause_event, effect_event):
            return CausalRelationType.ENABLER
        
        else:
            return CausalRelationType.INDIRECT_CAUSE
    
    def _are_contradictory_events(self, event1: CausalNode, event2: CausalNode) -> bool:
        """判断两个事件是否矛盾"""
        contradictory_pairs = [
            ('attack', 'help'),
            ('accept', 'reject'),
            ('agree', 'disagree'),
            ('approach', 'retreat'),
            ('create', 'destroy')
        ]
        
        type1 = event1.event_type.lower()
        type2 = event2.event_type.lower()
        
        for pair in contradictory_pairs:
            if ((pair[0] in type1 and pair[1] in type2) or 
                (pair[1] in type1 and pair[0] in type2)):
                return True
        
        return False
    
    def _is_enabling_event(self, cause_event: CausalNode, effect_event: CausalNode) -> bool:
        """判断是否为使能事件"""
        enabling_pairs = [
            ('discover', 'use'),
            ('unlock', 'enter'),
            ('learn', 'apply'),
            ('prepare', 'execute'),
            ('plan', 'implement')
        ]
        
        cause_type = cause_event.event_type.lower()
        effect_type = effect_event.event_type.lower()
        
        for cause, effect in enabling_pairs:
            if cause in cause_type and effect in effect_type:
                return True
        
        return False
    
    async def _check_and_handle_conflicts(self, event_node: CausalNode) -> Dict[str, Any]:
        """检查并处理冲突"""
        conflicts = []
        
        # 检查是否与其他Agent的行动冲突
        for existing_event in self.causal_graph.nodes.values():
            if (existing_event.node_id != event_node.node_id and
                existing_event.agent_id != event_node.agent_id and
                abs((existing_event.timestamp - event_node.timestamp).total_seconds()) < 300):  # 5分钟内
                
                conflict_score = self._calculate_conflict_score(existing_event, event_node)
                if conflict_score > 0.5:
                    conflicts.append({
                        'conflicting_event': existing_event.node_id,
                        'conflict_type': self._classify_conflict_type(existing_event, event_node),
                        'severity': conflict_score
                    })
        
        negotiation_results = []
        
        # 如果存在冲突，启动协商
        if conflicts:
            high_severity_conflicts = [c for c in conflicts if c['severity'] > 0.7]
            
            for conflict in high_severity_conflicts:
                conflicting_event = self.causal_graph.nodes[conflict['conflicting_event']]
                
                # 启动协商
                negotiation_id = await self.negotiation_engine.initiate_negotiation(
                    initiator_id=event_node.agent_id,
                    target_agents=[conflicting_event.agent_id],
                    topic=f"conflict_resolution_{conflict['conflict_type']}",
                    initial_proposal={
                        'type': 'conflict_resolution',
                        'conflict_description': conflict,
                        'proposed_solution': self._suggest_conflict_resolution(conflict)
                    }
                )
                
                negotiation_results.append({
                    'negotiation_id': negotiation_id,
                    'conflict': conflict,
                    'status': 'initiated'
                })
        
        return {
            'conflicts_detected': len(conflicts),
            'conflicts': conflicts,
            'negotiations_started': len(negotiation_results),
            'negotiation_results': negotiation_results
        }
    
    def _calculate_conflict_score(self, event1: CausalNode, event2: CausalNode) -> float:
        """计算冲突分数"""
        score = 0.0
        
        # 位置冲突
        if event1.location == event2.location:
            score += 0.3
        
        # 资源冲突
        if self._check_resource_conflict(event1, event2):
            score += 0.4
        
        # 目标冲突
        if self._check_goal_conflict(event1, event2):
            score += 0.5
        
        # 直接对抗
        if self._are_contradictory_events(event1, event2):
            score += 0.6
        
        return min(1.0, score)
    
    def _check_resource_conflict(self, event1: CausalNode, event2: CausalNode) -> bool:
        """检查资源冲突"""
        # 简化的资源冲突检测
        resources1 = set(event1.action_data.get('resources', []))
        resources2 = set(event2.action_data.get('resources', []))
        
        return len(resources1.intersection(resources2)) > 0
    
    def _check_goal_conflict(self, event1: CausalNode, event2: CausalNode) -> bool:
        """检查目标冲突"""
        # 简化的目标冲突检测
        goals1 = set(event1.action_data.get('goals', []))
        goals2 = set(event2.action_data.get('goals', []))
        
        # 如果目标相同但Agent不同，可能存在竞争
        return len(goals1.intersection(goals2)) > 0 and event1.agent_id != event2.agent_id
    
    def _classify_conflict_type(self, event1: CausalNode, event2: CausalNode) -> str:
        """分类冲突类型"""
        if self._check_resource_conflict(event1, event2):
            return 'resource_competition'
        elif self._check_goal_conflict(event1, event2):
            return 'goal_competition'
        elif event1.location == event2.location:
            return 'territorial_dispute'
        elif self._are_contradictory_events(event1, event2):
            return 'direct_opposition'
        else:
            return 'general_conflict'
    
    def _suggest_conflict_resolution(self, conflict: Dict[str, Any]) -> Dict[str, Any]:
        """建议冲突解决方案"""
        conflict_type = conflict['conflict_type']
        
        resolution_strategies = {
            'resource_competition': {
                'type': 'resource_sharing',
                'description': 'Propose resource sharing or time-based allocation',
                'benefits': 'Both parties achieve goals without direct competition'
            },
            'goal_competition': {
                'type': 'goal_differentiation',
                'description': 'Suggest different approaches to similar goals',
                'benefits': 'Reduce direct competition while allowing both to progress'
            },
            'territorial_dispute': {
                'type': 'space_coordination',
                'description': 'Coordinate timing or designate specific areas',
                'benefits': 'Avoid physical conflicts and optimize space usage'
            },
            'direct_opposition': {
                'type': 'compromise_negotiation',
                'description': 'Seek middle ground or alternative approaches',
                'benefits': 'Maintain relationships while addressing core needs'
            },
            'general_conflict': {
                'type': 'mediated_discussion',
                'description': 'Open dialogue to understand underlying issues',
                'benefits': 'Clarify misunderstandings and find mutual benefits'
            }
        }
        
        return resolution_strategies.get(conflict_type, resolution_strategies['general_conflict'])
    
    def _get_causal_effects(self, event_node: CausalNode) -> Dict[str, Any]:
        """获取因果效应分析"""
        
        # 查找此事件的直接后果
        successors = list(self.causal_graph.graph.successors(event_node.node_id))
        
        # 分析影响范围
        influence_scope = {
            'direct_effects': len(successors),
            'affected_agents': set(),
            'affected_locations': set(),
            'causal_chains': []
        }
        
        for successor_id in successors:
            if successor_id in self.causal_graph.nodes:
                successor = self.causal_graph.nodes[successor_id]
                if successor.agent_id:
                    influence_scope['affected_agents'].add(successor.agent_id)
                if successor.location:
                    influence_scope['affected_locations'].add(successor.location)
        
        # 查找因果链
        chains = self.causal_graph.find_causal_chain(event_node.node_id, max_depth=3)
        influence_scope['causal_chains'] = chains[:5]  # 最多返回5个链条
        
        # 转换集合为列表以便序列化
        influence_scope['affected_agents'] = list(influence_scope['affected_agents'])
        influence_scope['affected_locations'] = list(influence_scope['affected_locations'])
        
        return influence_scope
    
    async def _identify_emergent_opportunities(self, event_node: CausalNode) -> List[Dict[str, Any]]:
        """识别涌现机会"""
        opportunities = []
        
        # 基于叙事模式识别机会
        narrative_patterns = self.causal_graph.detect_narrative_patterns()
        
        # 检查是否接近收敛点
        if event_node.node_id in narrative_patterns.get('convergence_points', []):
            opportunities.append({
                'type': 'story_convergence',
                'description': 'Multiple storylines are converging, creating dramatic potential',
                'potential_impact': 'high',
                'suggested_actions': ['coordinate_with_other_agents', 'prepare_for_major_event']
            })
        
        # 检查催化剂机会
        if event_node.event_type in ['discover', 'reveal', 'unlock']:
            opportunities.append({
                'type': 'catalyst_moment',
                'description': 'This event could catalyze significant story developments',
                'potential_impact': 'medium',
                'suggested_actions': ['share_information', 'take_decisive_action']
            })
        
        # 检查角色发展机会
        if event_node.agent_id and event_node.narrative_weight > 0.7:
            opportunities.append({
                'type': 'character_development',
                'description': 'Significant character growth opportunity detected',
                'potential_impact': 'medium',
                'suggested_actions': ['reflect_on_experience', 'form_new_relationships']
            })
        
        # 使用LLM识别更深层的机会
        if self.llm_service:
            llm_opportunities = await self._llm_identify_opportunities(event_node)
            opportunities.extend(llm_opportunities)
        
        return opportunities[:5]  # 限制返回数量
    
    async def _llm_identify_opportunities(self, event_node: CausalNode) -> List[Dict[str, Any]]:
        """使用LLM识别涌现机会"""
        
        # 获取相关上下文
        context_events = []
        for node in self.causal_graph.nodes.values():
            if (abs((node.timestamp - event_node.timestamp).total_seconds()) < 3600 and
                node.node_id != event_node.node_id):
                context_events.append(node)
        
        context_events.sort(key=lambda x: x.timestamp)
        context_summary = [f"{e.agent_id}: {e.event_type}" for e in context_events[-5:]]
        
        opportunity_prompt = f"""
        分析以下故事情境，识别可能的涌现机会：

        当前事件：
        - Agent: {event_node.agent_id}
        - 动作: {event_node.event_type}
        - 详情: {event_node.action_data}
        - 地点: {event_node.location}

        最近上下文：
        {'; '.join(context_summary)}

        请识别3个潜在的故事发展机会，每个包含：
        - type: 机会类型
        - description: 描述
        - potential_impact: high/medium/low
        - suggested_actions: 建议的后续行动列表

        返回JSON数组格式。
        """
        
        try:
            llm_request = LLMRequest(
                prompt=opportunity_prompt,
                response_format=ResponseFormat.JSON,
                max_tokens=600
            )
            
            llm_response = await self.llm_service.process_request(llm_request)
            
            if llm_response and llm_response.success:
                opportunities = json.loads(llm_response.content)
                if isinstance(opportunities, list):
                    return opportunities[:3]  # 限制为3个
        
        except Exception as e:
            logger.error(f"LLM opportunity identification failed: {e}")
        
        return []
    
    async def generate_story_summary(self, 
                                   time_range: Tuple[datetime, datetime] = None,
                                   agent_focus: List[str] = None) -> Dict[str, Any]:
        """生成故事摘要"""
        
        # 获取叙事时间线
        timeline = self.coherence_engine.get_narrative_timeline(
            start_time=time_range[0] if time_range else None,
            end_time=time_range[1] if time_range else None,
            agent_filter=agent_focus
        )
        
        if not timeline:
            return {'summary': '暂无故事内容', 'timeline': []}
        
        # 使用LLM生成综合摘要
        story_summary = await self._generate_comprehensive_summary(timeline)
        
        # 分析叙事模式
        patterns = self.causal_graph.detect_narrative_patterns()
        
        # 获取连贯性报告
        coherence_report = self.coherence_engine.get_coherence_report()
        
        return {
            'summary': story_summary,
            'timeline_count': len(timeline),
            'narrative_patterns': patterns,
            'coherence_report': coherence_report,
            'key_events': timeline[:5] if len(timeline) > 5 else timeline,
            'character_arcs': len(self.coherence_engine.character_arcs),
            'plot_threads': len(self.coherence_engine.plot_threads)
        }
    
    async def _generate_comprehensive_summary(self, timeline: List[Dict[str, Any]]) -> str:
        """生成综合故事摘要"""
        if not self.llm_service or not timeline:
            return "故事正在发展中..."
        
        # 提取关键信息
        key_events = timeline[:10]  # 最多10个关键事件
        characters = list(set([event['agent_id'] for event in timeline if event['agent_id']]))
        
        summary_prompt = f"""
        基于以下叙事时间线，生成一份200-400字的故事摘要：

        主要角色：{', '.join(characters)}

        关键事件时间线：
        """
        
        for i, event in enumerate(key_events, 1):
            summary_prompt += f"\n{i}. {event['agent_id']}: {event['narrative_text'][:100]}..."
        
        summary_prompt += """

        请生成一份连贯的故事摘要，要求：
        1. 突出主要情节发展
        2. 体现角色关系和成长
        3. 保持叙事的戏剧张力
        4. 为后续发展留下悬念
        """
        
        try:
            llm_request = LLMRequest(
                prompt=summary_prompt,
                response_format=ResponseFormat.TEXT,
                max_tokens=500
            )
            
            llm_response = await self.llm_service.process_request(llm_request)
            
            if llm_response and llm_response.success:
                return llm_response.content.strip()
        
        except Exception as e:
            logger.error(f"Story summary generation failed: {e}")
        
        return f"故事围绕{len(characters)}名角色展开，经历了{len(timeline)}个重要事件，正在不断发展中..."
    
    def get_engine_status(self) -> Dict[str, Any]:
        """获取引擎状态"""
        return {
            'active_agents': len(self.active_agents),
            'total_events': len(self.causal_graph.nodes),
            'causal_relations': len(self.causal_graph.edges),
            'active_negotiations': len(self.negotiation_engine.active_sessions),
            'plot_threads': len(self.coherence_engine.plot_threads),
            'character_arcs': len(self.coherence_engine.character_arcs),
            'story_timeline_length': len(self.coherence_engine.story_timeline),
            'narrative_patterns': len(self.causal_graph.detect_narrative_patterns()),
        }


# Factory function
def create_emergent_narrative_engine(llm_service=None) -> EmergentNarrativeEngine:
    """创建涌现式叙事引擎实例"""
    return EmergentNarrativeEngine(llm_service)


if __name__ == "__main__":
    # 示例用法
    async def example_usage():
        engine = create_emergent_narrative_engine()
        
        # 初始化两个Agent
        await engine.initialize_agent("alice", {'cooperativeness': 0.8}, ['exploration', 'help_others'])
        await engine.initialize_agent("bob", {'competitiveness': 0.7}, ['survival', 'resource_gathering'])
        
        # 处理一系列行动
        result1 = await engine.process_agent_action(
            agent_id="alice",
            action_type="explore",
            action_data={"target": "ancient_ruins"},
            location="mysterious_valley"
        )
        
        print(f"Alice的探索结果：{result1['narrative_integration']['success']}")
        
        result2 = await engine.process_agent_action(
            agent_id="bob",
            action_type="claim_territory",
            action_data={"area": "mysterious_valley"},
            location="mysterious_valley"
        )
        
        print(f"Bob的领域声明：{result2['negotiation_result']['conflicts_detected']} 个冲突")
        
        # 生成故事摘要
        story_summary = await engine.generate_story_summary()
        print(f"\n故事摘要：\n{story_summary['summary']}")
    
    # 运行示例
    # asyncio.run(example_usage())