#!/usr/bin/env python3
"""
Causal graph for tracking event relationships.

因果关系图 - 追踪行动-结果的链式关系
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

import networkx as nx

from .types import CausalEdge, CausalNode, CausalRelationType

logger = logging.getLogger(__name__)

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

