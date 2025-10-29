#!/usr/bin/env python3
"""
Main emergent narrative engine orchestrating all subsystems.

涌现式叙事引擎主引擎 - 通过Agent间的真实交互和因果关系图，
自然涌现出连贯的叙事，而非预设剧本。
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from src.llm_service import LLMRequest, ResponseFormat, UnifiedLLMService, get_llm_service

# Type alias for compatibility
LLMService = UnifiedLLMService

from .causal_graph import CausalGraph
from .narrative_coherence import NarrativeCoherenceEngine
from .negotiation import AgentNegotiationEngine
from .types import CausalEdge, CausalNode, CausalRelationType, EventPriority

logger = logging.getLogger(__name__)

class EmergentNarrativeEngine:
    """涌现式叙事引擎 - 主引擎类"""

    def __init__(self, llm_service: Optional[LLMService] = None) -> None:
        self.causal_graph = CausalGraph()
        self.negotiation_engine = AgentNegotiationEngine(llm_service)
        self.coherence_engine = NarrativeCoherenceEngine(self.causal_graph, llm_service)
        self.llm_service = llm_service or get_llm_service()

        self.active_agents: Set[str] = set()
        self.global_narrative_state: Dict[str, Any] = {}

        # 注册默认的一致性规则
        self._register_default_consistency_rules()

        logger.info("涌现式叙事引擎初始化完成")

    def _register_default_consistency_rules(self) -> None:
        """注册默认的一致性规则"""

        def basic_causality_rule(data: Dict[str, Any]) -> bool:
            """基础因果逻辑规则"""
            event = data["event"]
            context = data["context"]

            # 检查Agent不能同时在多个地方
            if event.agent_id and event.location:
                same_time_events = [
                    e
                    for e in context
                    if e.agent_id == event.agent_id
                    and abs((e.timestamp - event.timestamp).total_seconds()) < 60
                ]

                for same_time_event in same_time_events:
                    if (
                        same_time_event.location
                        and same_time_event.location != event.location
                    ):
                        return False

            return True

        def temporal_logic_rule(data: Dict[str, Any]) -> bool:
            """时间逻辑规则"""
            event = data["event"]

            # 事件不能在未来发生
            return event.timestamp <= datetime.now()

        self.coherence_engine.register_consistency_rule(basic_causality_rule)
        self.coherence_engine.register_consistency_rule(temporal_logic_rule)

    async def initialize_agent(
        self,
        agent_id: str,
        negotiation_style: Optional[Dict[str, float]] = None,
        priorities: Optional[List[str]] = None,
    ) -> bool:
        """初始化Agent"""

        # 初始化协商引擎中的Agent
        self.negotiation_engine.initialize_agent_profile(
            agent_id=agent_id,
            negotiation_style=negotiation_style,
            priorities=priorities,
        )

        self.active_agents.add(agent_id)

        logger.info(f"Agent {agent_id} initialized in emergent narrative engine")
        return True

    async def process_agent_action(
        self,
        agent_id: str,
        action_type: str,
        action_data: Dict[str, Any],
        location: Optional[str] = None,
        participants: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """处理Agent行动并生成叙事"""

        # 创建事件节点
        event_node = CausalNode(
            node_id=str(uuid.uuid4()),
            event_type=action_type,
            agent_id=agent_id,
            action_data=action_data,
            timestamp=datetime.now(),
            location=location,
            participants=participants or [],
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
            "event_id": event_node.node_id,
            "narrative_integration": integration_result,
            "negotiation_result": negotiation_result,
            "causal_effects": self._get_causal_effects(event_node),
            "story_predictions": predictions[:3],  # 前3个预测
            "emergent_opportunities": await self._identify_emergent_opportunities(
                event_node
            ),
        }

    async def _analyze_and_add_causal_relations(self, event_node: CausalNode) -> None:
        """分析并添加因果关系"""

        # 查找可能的因果前因
        potential_causes = []

        # 时间窗口内的相关事件
        time_window = timedelta(hours=1)
        cutoff_time = event_node.timestamp - time_window

        for existing_node in self.causal_graph.nodes.values():
            if (
                existing_node.timestamp >= cutoff_time
                and existing_node.node_id != event_node.node_id
            ):

                # 基于位置的关联
                if existing_node.location == event_node.location or (
                    existing_node.agent_id == event_node.agent_id
                ):

                    causal_strength = self._calculate_causal_strength(
                        existing_node, event_node
                    )
                    if causal_strength > 0.3:

                        # 确定关系类型
                        relation_type = self._determine_relation_type(
                            existing_node, event_node
                        )

                        causal_edge = CausalEdge(
                            source_id=existing_node.node_id,
                            target_id=event_node.node_id,
                            relation_type=relation_type,
                            strength=causal_strength,
                            confidence=min(
                                existing_node.confidence, event_node.confidence
                            ),
                            delay=event_node.timestamp - existing_node.timestamp,
                        )

                        self.causal_graph.add_causal_relation(causal_edge)
                        potential_causes.append((existing_node, causal_edge))

        logger.debug(
            f"Added {len(potential_causes)} causal relations for event {event_node.node_id}"
        )

    def _calculate_causal_strength(
        self, cause_event: CausalNode, effect_event: CausalNode
    ) -> float:
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
            ("attack", "defend"),
            ("question", "answer"),
            ("offer", "accept"),
            ("offer", "reject"),
            ("move", "arrive"),
            ("search", "discover"),
            ("negotiate", "agree"),
            ("negotiate", "disagree"),
        ]

        for cause, effect in logic_pairs:
            if cause in cause_type.lower() and effect in effect_type.lower():
                return True

        return False

    def _determine_relation_type(
        self, cause_event: CausalNode, effect_event: CausalNode
    ) -> CausalRelationType:
        """确定因果关系类型"""

        # 基于事件类型判断
        if cause_event.agent_id == effect_event.agent_id:
            return CausalRelationType.DIRECT_CAUSE

        elif any(
            participant in effect_event.participants
            for participant in [cause_event.agent_id] + cause_event.participants
        ):
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
            ("attack", "help"),
            ("accept", "reject"),
            ("agree", "disagree"),
            ("approach", "retreat"),
            ("create", "destroy"),
        ]

        type1 = event1.event_type.lower()
        type2 = event2.event_type.lower()

        for pair in contradictory_pairs:
            if (pair[0] in type1 and pair[1] in type2) or (
                pair[1] in type1 and pair[0] in type2
            ):
                return True

        return False

    def _is_enabling_event(
        self, cause_event: CausalNode, effect_event: CausalNode
    ) -> bool:
        """判断是否为使能事件"""
        enabling_pairs = [
            ("discover", "use"),
            ("unlock", "enter"),
            ("learn", "apply"),
            ("prepare", "execute"),
            ("plan", "implement"),
        ]

        cause_type = cause_event.event_type.lower()
        effect_type = effect_event.event_type.lower()

        for cause, effect in enabling_pairs:
            if cause in cause_type and effect in effect_type:
                return True

        return False

    async def _check_and_handle_conflicts(
        self, event_node: CausalNode
    ) -> Dict[str, Any]:
        """检查并处理冲突"""
        conflicts = []

        # 检查是否与其他Agent的行动冲突
        for existing_event in self.causal_graph.nodes.values():
            if (
                existing_event.node_id != event_node.node_id
                and existing_event.agent_id != event_node.agent_id
                and abs(
                    (existing_event.timestamp - event_node.timestamp).total_seconds()
                )
                < 300
            ):  # 5分钟内

                conflict_score = self._calculate_conflict_score(
                    existing_event, event_node
                )
                if conflict_score > 0.5:
                    conflicts.append(
                        {
                            "conflicting_event": existing_event.node_id,
                            "conflict_type": self._classify_conflict_type(
                                existing_event, event_node
                            ),
                            "severity": conflict_score,
                        }
                    )

        negotiation_results = []

        # 如果存在冲突，启动协商
        if conflicts:
            high_severity_conflicts = [c for c in conflicts if c["severity"] > 0.7]

            for conflict in high_severity_conflicts:
                conflicting_event = self.causal_graph.nodes[
                    conflict["conflicting_event"]
                ]

                # 启动协商
                negotiation_id = await self.negotiation_engine.initiate_negotiation(
                    initiator_id=event_node.agent_id,
                    target_agents=[conflicting_event.agent_id],
                    topic=f"conflict_resolution_{conflict['conflict_type']}",
                    initial_proposal={
                        "type": "conflict_resolution",
                        "conflict_description": conflict,
                        "proposed_solution": self._suggest_conflict_resolution(
                            conflict
                        ),
                    },
                )

                negotiation_results.append(
                    {
                        "negotiation_id": negotiation_id,
                        "conflict": conflict,
                        "status": "initiated",
                    }
                )

        return {
            "conflicts_detected": len(conflicts),
            "conflicts": conflicts,
            "negotiations_started": len(negotiation_results),
            "negotiation_results": negotiation_results,
        }

    def _calculate_conflict_score(
        self, event1: CausalNode, event2: CausalNode
    ) -> float:
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
        resources1 = set(event1.action_data.get("resources", []))
        resources2 = set(event2.action_data.get("resources", []))

        return len(resources1.intersection(resources2)) > 0

    def _check_goal_conflict(self, event1: CausalNode, event2: CausalNode) -> bool:
        """检查目标冲突"""
        # 简化的目标冲突检测
        goals1 = set(event1.action_data.get("goals", []))
        goals2 = set(event2.action_data.get("goals", []))

        # 如果目标相同但Agent不同，可能存在竞争
        return (
            len(goals1.intersection(goals2)) > 0 and event1.agent_id != event2.agent_id
        )

    def _classify_conflict_type(self, event1: CausalNode, event2: CausalNode) -> str:
        """分类冲突类型"""
        if self._check_resource_conflict(event1, event2):
            return "resource_competition"
        elif self._check_goal_conflict(event1, event2):
            return "goal_competition"
        elif event1.location == event2.location:
            return "territorial_dispute"
        elif self._are_contradictory_events(event1, event2):
            return "direct_opposition"
        else:
            return "general_conflict"

    def _suggest_conflict_resolution(self, conflict: Dict[str, Any]) -> Dict[str, Any]:
        """建议冲突解决方案"""
        conflict_type = conflict["conflict_type"]

        resolution_strategies = {
            "resource_competition": {
                "type": "resource_sharing",
                "description": "Propose resource sharing or time-based allocation",
                "benefits": "Both parties achieve goals without direct competition",
            },
            "goal_competition": {
                "type": "goal_differentiation",
                "description": "Suggest different approaches to similar goals",
                "benefits": "Reduce direct competition while allowing both to progress",
            },
            "territorial_dispute": {
                "type": "space_coordination",
                "description": "Coordinate timing or designate specific areas",
                "benefits": "Avoid physical conflicts and optimize space usage",
            },
            "direct_opposition": {
                "type": "compromise_negotiation",
                "description": "Seek middle ground or alternative approaches",
                "benefits": "Maintain relationships while addressing core needs",
            },
            "general_conflict": {
                "type": "mediated_discussion",
                "description": "Open dialogue to understand underlying issues",
                "benefits": "Clarify misunderstandings and find mutual benefits",
            },
        }

        return resolution_strategies.get(
            conflict_type, resolution_strategies["general_conflict"]
        )

    def _get_causal_effects(self, event_node: CausalNode) -> Dict[str, Any]:
        """获取因果效应分析"""

        # 查找此事件的直接后果
        successors = list(self.causal_graph.graph.successors(event_node.node_id))

        # 分析影响范围
        influence_scope = {
            "direct_effects": len(successors),
            "affected_agents": set(),
            "affected_locations": set(),
            "causal_chains": [],
        }

        for successor_id in successors:
            if successor_id in self.causal_graph.nodes:
                successor = self.causal_graph.nodes[successor_id]
                if successor.agent_id:
                    influence_scope["affected_agents"].add(successor.agent_id)
                if successor.location:
                    influence_scope["affected_locations"].add(successor.location)

        # 查找因果链
        chains = self.causal_graph.find_causal_chain(event_node.node_id, max_depth=3)
        influence_scope["causal_chains"] = chains[:5]  # 最多返回5个链条

        # 转换集合为列表以便序列化
        influence_scope["affected_agents"] = list(influence_scope["affected_agents"])
        influence_scope["affected_locations"] = list(
            influence_scope["affected_locations"]
        )

        return influence_scope

    async def _identify_emergent_opportunities(
        self, event_node: CausalNode
    ) -> List[Dict[str, Any]]:
        """识别涌现机会"""
        opportunities = []

        # 基于叙事模式识别机会
        narrative_patterns = self.causal_graph.detect_narrative_patterns()

        # 检查是否接近收敛点
        if event_node.node_id in narrative_patterns.get("convergence_points", []):
            opportunities.append(
                {
                    "type": "story_convergence",
                    "description": "Multiple storylines are converging, creating dramatic potential",
                    "potential_impact": "high",
                    "suggested_actions": [
                        "coordinate_with_other_agents",
                        "prepare_for_major_event",
                    ],
                }
            )

        # 检查催化剂机会
        if event_node.event_type in ["discover", "reveal", "unlock"]:
            opportunities.append(
                {
                    "type": "catalyst_moment",
                    "description": "This event could catalyze significant story developments",
                    "potential_impact": "medium",
                    "suggested_actions": ["share_information", "take_decisive_action"],
                }
            )

        # 检查角色发展机会
        if event_node.agent_id and event_node.narrative_weight > 0.7:
            opportunities.append(
                {
                    "type": "character_development",
                    "description": "Significant character growth opportunity detected",
                    "potential_impact": "medium",
                    "suggested_actions": [
                        "reflect_on_experience",
                        "form_new_relationships",
                    ],
                }
            )

        # 使用LLM识别更深层的机会
        if self.llm_service:
            llm_opportunities = await self._llm_identify_opportunities(event_node)
            opportunities.extend(llm_opportunities)

        return opportunities[:5]  # 限制返回数量

    async def _llm_identify_opportunities(
        self, event_node: CausalNode
    ) -> List[Dict[str, Any]]:
        """使用LLM识别涌现机会"""

        # 获取相关上下文
        context_events = []
        for node in self.causal_graph.nodes.values():
            if (
                abs((node.timestamp - event_node.timestamp).total_seconds()) < 3600
                and node.node_id != event_node.node_id
            ):
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
                max_tokens=600,
            )

            llm_response = await self.llm_service.process_request(llm_request)

            if llm_response and llm_response.success:
                opportunities = json.loads(llm_response.content)
                if isinstance(opportunities, list):
                    return opportunities[:3]  # 限制为3个

        except Exception as e:
            logger.error(f"LLM opportunity identification failed: {e}")

        return []

    async def generate_story_summary(
        self,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        agent_focus: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """生成故事摘要"""

        # 获取叙事时间线
        timeline = self.coherence_engine.get_narrative_timeline(
            start_time=time_range[0] if time_range else None,
            end_time=time_range[1] if time_range else None,
            agent_filter=agent_focus,
        )

        if not timeline:
            return {"summary": "暂无故事内容", "timeline": []}

        # 使用LLM生成综合摘要
        story_summary = await self._generate_comprehensive_summary(timeline)

        # 分析叙事模式
        patterns = self.causal_graph.detect_narrative_patterns()

        # 获取连贯性报告
        coherence_report = self.coherence_engine.get_coherence_report()

        return {
            "summary": story_summary,
            "timeline_count": len(timeline),
            "narrative_patterns": patterns,
            "coherence_report": coherence_report,
            "key_events": timeline[:5] if len(timeline) > 5 else timeline,
            "character_arcs": len(self.coherence_engine.character_arcs),
            "plot_threads": len(self.coherence_engine.plot_threads),
        }

    async def _generate_comprehensive_summary(
        self, timeline: List[Dict[str, Any]]
    ) -> str:
        """生成综合故事摘要"""
        if not self.llm_service or not timeline:
            return "故事正在发展中..."

        # 提取关键信息
        key_events = timeline[:10]  # 最多10个关键事件
        characters = list(
            set([event["agent_id"] for event in timeline if event["agent_id"]])
        )

        summary_prompt = f"""
        基于以下叙事时间线，生成一份200-400字的故事摘要：

        主要角色：{', '.join(characters)}

        关键事件时间线：
        """

        for i, event in enumerate(key_events, 1):
            summary_prompt += (
                f"\n{i}. {event['agent_id']}: {event['narrative_text'][:100]}..."
            )

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
                max_tokens=500,
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
            "active_agents": len(self.active_agents),
            "total_events": len(self.causal_graph.nodes),
            "causal_relations": len(self.causal_graph.edges),
            "active_negotiations": len(self.negotiation_engine.active_sessions),
            "plot_threads": len(self.coherence_engine.plot_threads),
            "character_arcs": len(self.coherence_engine.character_arcs),
            "story_timeline_length": len(self.coherence_engine.story_timeline),
            "narrative_patterns": len(self.causal_graph.detect_narrative_patterns()),
        }


# Factory function
def create_emergent_narrative_engine(llm_service: Optional[LLMService] = None) -> EmergentNarrativeEngine:
    """创建涌现式叙事引擎实例"""
    return EmergentNarrativeEngine(llm_service)


if __name__ == "__main__":
    # 示例用法
    async def example_usage():
        engine = create_emergent_narrative_engine()

        # 初始化两个Agent
        await engine.initialize_agent(
            "alice", {"cooperativeness": 0.8}, ["exploration", "help_others"]
        )
        await engine.initialize_agent(
            "bob", {"competitiveness": 0.7}, ["survival", "resource_gathering"]
        )

        # 处理一系列行动
        result1 = await engine.process_agent_action(
            agent_id="alice",
            action_type="explore",
            action_data={"target": "ancient_ruins"},
            location="mysterious_valley",
        )

        logger.info(f"Alice的探索结果：{result1['narrative_integration']['success']}")

        result2 = await engine.process_agent_action(
            agent_id="bob",
            action_type="claim_territory",
            action_data={"area": "mysterious_valley"},
            location="mysterious_valley",
        )

        logger.info(
            f"Bob的领域声明：{result2['negotiation_result']['conflicts_detected']} 个冲突"
        )

        # 生成故事摘要
        story_summary = await engine.generate_story_summary()
        logger.info(f"\n故事摘要：\n{story_summary['summary']}")

    # 运行示例
    # asyncio.run(example_usage())
