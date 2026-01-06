#!/usr/bin/env python3
"""
Shared types for emergent narrative system.

Contains enums and dataclasses used across narrative modules.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx

logger = logging.getLogger(__name__)


class CausalRelationType(Enum):
    """因果关系类型"""

    DIRECT_CAUSE = "direct_cause"  # 直接因果
    INDIRECT_CAUSE = "indirect_cause"  # 间接因果
    ENABLER = "enabler"  # 使能条件
    CATALYST = "catalyst"  # 催化剂
    INHIBITOR = "inhibitor"  # 抑制因素
    AMPLIFIER = "amplifier"  # 放大器
    CONTRADICTION = "contradiction"  # 矛盾冲突


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

    CRITICAL = 1  # 关键剧情事件
    HIGH = 2  # 重要情节点
    MEDIUM = 3  # 一般事件
    LOW = 4  # 背景事件
    TRIVIAL = 5  # 微小细节


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

    def __eq__(self, other):
        if not isinstance(other, CausalNode):
            return NotImplemented
        return self.node_id == other.node_id

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "node_id": self.node_id,
            "event_type": self.event_type,
            "agent_id": self.agent_id,
            "action_data": self.action_data,
            "timestamp": self.timestamp.isoformat(),
            "location": self.location,
            "participants": self.participants,
            "confidence": self.confidence,
            "narrative_weight": self.narrative_weight,
            "metadata": self.metadata,
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
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "strength": self.strength,
            "confidence": self.confidence,
            "delay_seconds": self.delay.total_seconds(),
            "conditions": self.conditions,
            "metadata": self.metadata,
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
        if (
            causal_edge.source_id not in self.nodes
            or causal_edge.target_id not in self.nodes
        ):
            logger.warning("Cannot add causal relation: nodes not found")
            return False

        edge_key = (causal_edge.source_id, causal_edge.target_id)
        self.edges[edge_key] = causal_edge

        self.graph.add_edge(
            causal_edge.source_id, causal_edge.target_id, **causal_edge.to_dict()
        )

        logger.debug(
            f"Added causal relation: {causal_edge.source_id} -> {causal_edge.target_id}"
        )
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

    def get_influential_events(
        self, time_window: timedelta = timedelta(hours=1)
    ) -> List[CausalNode]:
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
        influential_events.sort(
            key=lambda x: x.narrative_weight * x.confidence, reverse=True
        )
        return influential_events

    def detect_narrative_patterns(self) -> Dict[str, Any]:
        """检测叙事模式"""
        patterns = {
            "conflict_nodes": [],
            "resolution_nodes": [],
            "catalyst_events": [],
            "parallel_storylines": [],
            "convergence_points": [],
        }

        # 检测冲突节点（多个输入边且包含矛盾关系）
        for node_id in self.graph.nodes():
            in_edges = list(self.graph.in_edges(node_id, data=True))
            if len(in_edges) > 1:
                has_conflict = any(
                    edge_data.get("relation_type")
                    == CausalRelationType.CONTRADICTION.value
                    for _, _, edge_data in in_edges
                )
                if has_conflict:
                    patterns["conflict_nodes"].append(node_id)

        # 检测催化剂事件
        for edge_key, edge in self.edges.items():
            if edge.relation_type == CausalRelationType.CATALYST:
                patterns["catalyst_events"].append(edge_key[0])

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
                    patterns["convergence_points"].append(node_id)

        return patterns

    def predict_next_events(
        self, current_state: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
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
                            probability = (
                                edge.strength * edge.confidence * event.confidence
                            )

                            predictions.append(
                                {
                                    "event_type": next_event.event_type,
                                    "probability": probability,
                                    "trigger_event": event.node_id,
                                    "expected_delay": edge.delay.total_seconds(),
                                    "conditions": edge.conditions,
                                }
                            )

        # 按概率排序
        predictions.sort(key=lambda x: x["probability"], reverse=True)
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
