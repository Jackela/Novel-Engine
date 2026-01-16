#!/usr/bin/env python3
"""
Narrative coherence engine for story consistency.

叙事连贯性引擎 - 智能故事整合与一致性保证
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from src.core.llm_service import LLMRequest, ResponseFormat, get_llm_service

from .causal_graph import CausalGraph
from .types import CausalNode

logger = logging.getLogger(__name__)


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

    async def integrate_event_into_narrative(
        self, event: CausalNode, context_events: List[CausalNode] = None
    ) -> Dict[str, Any]:
        """将事件整合到叙事中"""

        # 获取相关的上下文事件
        if context_events is None:
            context_events = self._get_relevant_context_events(event)

        # 检查事件一致性
        consistency_check = await self._check_event_consistency(event, context_events)

        if not consistency_check["consistent"]:
            logger.warning(
                f"Event consistency issues detected: {consistency_check['issues']}"
            )
            # 尝试修正事件
            corrected_event = await self._correct_event_inconsistencies(
                event, consistency_check
            )
            if corrected_event:
                event = corrected_event
            else:
                logger.error(
                    f"Failed to correct event inconsistencies for {event.node_id}"
                )
                return {"success": False, "issues": consistency_check["issues"]}

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
            "event_id": event.node_id,
            "timestamp": event.timestamp,
            "agent_id": event.agent_id,
            "narrative_text": narrative_text,
            "plot_thread": plot_thread,
            "character_development": self._extract_character_development(event),
            "causal_links": [
                edge.source_id
                for edge in self.causal_graph.edges.values()
                if edge.target_id == event.node_id
            ],
        }

        self.story_timeline.append(narrative_entry)
        self.story_timeline.sort(key=lambda x: x["timestamp"])

        return {
            "success": True,
            "narrative_entry": narrative_entry,
            "plot_thread": plot_thread,
            "character_development": narrative_entry["character_development"],
        }

    def _get_relevant_context_events(
        self, event: CausalNode, time_window: timedelta = timedelta(hours=2)
    ) -> List[CausalNode]:
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

    async def _check_event_consistency(
        self, event: CausalNode, context_events: List[CausalNode]
    ) -> Dict[str, Any]:
        """检查事件一致性"""
        issues = []

        # 应用注册的一致性规则
        for rule in self.consistency_rules:
            try:
                if not rule({"event": event, "context": context_events}):
                    issues.append(f"Failed consistency rule: {rule.__name__}")
            except Exception as e:
                logger.error(f"Consistency rule error: {e}")

        # 基本一致性检查
        # 1. 时间一致性
        if context_events:
            latest_context = max(context_events, key=lambda x: x.timestamp)
            if event.timestamp < latest_context.timestamp:
                issues.append(
                    "Temporal inconsistency: event occurs before required context"
                )

        # 2. 位置一致性
        if event.location and event.agent_id:
            # 检查Agent是否能在该位置执行该动作
            recent_agent_events = [
                e for e in context_events if e.agent_id == event.agent_id and e.location
            ]
            if recent_agent_events:
                last_location = recent_agent_events[-1].location
                if (
                    event.location != last_location
                    and event.action_data.get("type") != "move"
                ):
                    issues.append(
                        f"Location inconsistency: Agent at {last_location} but event at {event.location}"
                    )

        # 3. 因果一致性
        required_preconditions = event.metadata.get("requires", [])
        for condition in required_preconditions:
            if not any(
                self._event_satisfies_condition(ctx_event, condition)
                for ctx_event in context_events
            ):
                issues.append(f"Missing precondition: {condition}")

        return {
            "consistent": len(issues) == 0,
            "issues": issues,
            "confidence": max(0.0, 1.0 - len(issues) * 0.2),
        }

    def _event_satisfies_condition(self, event: CausalNode, condition: str) -> bool:
        """检查事件是否满足条件"""
        # 简化的条件匹配逻辑
        return (
            condition.lower() in event.event_type.lower()
            or condition.lower() in str(event.action_data).lower()
            or condition in event.metadata.get("provides", [])
        )

    async def _correct_event_inconsistencies(
        self, event: CausalNode, consistency_check: Dict[str, Any]
    ) -> Optional[CausalNode]:
        """尝试修正事件的不一致性"""
        if not self.llm_service or not consistency_check["issues"]:
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
                max_tokens=500,
            )

            llm_response = await self.llm_service.process_request(llm_request)

            if llm_response and llm_response.success:
                correction_data = json.loads(llm_response.content)

                # 创建修正后的事件
                corrected_event = CausalNode(
                    node_id=event.node_id,
                    event_type=correction_data.get("event_type", event.event_type),
                    agent_id=event.agent_id,
                    action_data=correction_data.get("action_data", event.action_data),
                    timestamp=event.timestamp,
                    location=correction_data.get("location", event.location),
                    participants=event.participants,
                    confidence=event.confidence * 0.9,  # 略微降低置信度
                    narrative_weight=event.narrative_weight,
                    metadata={
                        **event.metadata,
                        "corrected": True,
                        "correction_reason": correction_data.get("explanation", ""),
                    },
                )

                logger.info(
                    f"Event {event.node_id} corrected: {correction_data.get('explanation', '')}"
                )
                return corrected_event

        except Exception as e:
            logger.error(f"Event correction failed: {e}")

        return None

    def _update_character_arc(self, agent_id: str, event: CausalNode):
        """更新角色弧线"""
        if agent_id not in self.character_arcs:
            self.character_arcs[agent_id] = {
                "events": [],
                "development_stages": [],
                "personality_changes": [],
                "relationships": {},
                "goals_evolution": [],
            }

        arc = self.character_arcs[agent_id]
        arc["events"].append(
            {
                "event_id": event.node_id,
                "timestamp": event.timestamp,
                "event_type": event.event_type,
                "significance": event.narrative_weight,
            }
        )

        # 分析角色发展阶段
        if len(arc["events"]) % 5 == 0:  # 每5个事件评估一次发展阶段
            stage = self._analyze_character_development_stage(
                agent_id, arc["events"][-5:]
            )
            if stage:
                arc["development_stages"].append(stage)

    def _analyze_character_development_stage(
        self, agent_id: str, recent_events: List[Dict]
    ) -> Optional[Dict]:
        """分析角色发展阶段"""
        if not recent_events:
            return None

        # 简化的发展阶段分析
        event_types = [evt["event_type"] for evt in recent_events]

        stage_type = "exploration"
        if any(
            "combat" in et.lower() or "conflict" in et.lower() for et in event_types
        ):
            stage_type = "conflict"
        elif any(
            "social" in et.lower() or "negotiate" in et.lower() for et in event_types
        ):
            stage_type = "social_development"
        elif any(
            "discover" in et.lower() or "learn" in et.lower() for et in event_types
        ):
            stage_type = "learning"

        return {
            "stage_type": stage_type,
            "start_time": recent_events[0]["timestamp"],
            "end_time": recent_events[-1]["timestamp"],
            "key_events": [evt["event_id"] for evt in recent_events],
        }

    def _identify_plot_thread(
        self, event: CausalNode, context_events: List[CausalNode]
    ) -> Optional[str]:
        """识别情节线索"""
        # 基于事件类型和参与者识别情节线索

        # 检查是否与现有情节线索相关
        for thread_id, thread_data in self.plot_threads.items():
            if (
                event.location == thread_data.get("primary_location")
                or event.agent_id in thread_data.get("involved_agents", [])
                or event.event_type in thread_data.get("related_event_types", [])
            ):
                return thread_id

        # 创建新的情节线索
        if event.narrative_weight > 0.5:  # 只为重要事件创建新线索
            thread_id = f"thread_{len(self.plot_threads) + 1}"
            self.plot_threads[thread_id] = {
                "thread_id": thread_id,
                "primary_location": event.location,
                "involved_agents": [event.agent_id] if event.agent_id else [],
                "related_event_types": [event.event_type],
                "start_time": event.timestamp,
                "events": [],
                "status": "active",
            }
            return thread_id

        return None

    def _update_plot_thread(self, thread_id: str, event: CausalNode):
        """更新情节线索"""
        if thread_id not in self.plot_threads:
            return

        thread = self.plot_threads[thread_id]
        thread["events"].append(event.node_id)

        # 更新涉及的Agent
        if event.agent_id and event.agent_id not in thread["involved_agents"]:
            thread["involved_agents"].append(event.agent_id)

        # 更新相关事件类型
        if event.event_type not in thread["related_event_types"]:
            thread["related_event_types"].append(event.event_type)

        thread["last_update"] = event.timestamp

    async def _generate_coherent_narrative(
        self, event: CausalNode, context_events: List[CausalNode]
    ) -> str:
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
                max_tokens=400,
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
            f"{agent_name}的{action}在{location}引起了一些反应，故事由此展开新的篇章。",
        ]

        # 根据事件ID选择模板，保证一致性
        template_index = hash(event.node_id) % len(narrative_templates)
        return narrative_templates[template_index]

    def _extract_character_development(self, event: CausalNode) -> Dict[str, Any]:
        """提取角色发展信息"""
        if not event.agent_id:
            return {}

        development = {
            "agent_id": event.agent_id,
            "development_type": "action_based",
            "growth_indicators": [],
            "relationship_changes": [],
            "skill_demonstrations": [],
        }

        # 基于事件类型推断发展
        event_type = event.event_type.lower()

        if "social" in event_type or "negotiate" in event_type:
            development["growth_indicators"].append("social_skills")
        elif "combat" in event_type or "attack" in event_type:
            development["growth_indicators"].append("combat_experience")
        elif "explore" in event_type or "investigate" in event_type:
            development["growth_indicators"].append("knowledge_seeking")
        elif "help" in event_type or "assist" in event_type:
            development["growth_indicators"].append("altruism")

        # 分析参与者关系
        if event.participants:
            for participant in event.participants:
                if participant != event.agent_id:
                    development["relationship_changes"].append(
                        {
                            "other_agent": participant,
                            "interaction_type": event.event_type,
                            "context": event.location,
                        }
                    )

        return development

    def get_narrative_timeline(
        self,
        start_time: datetime = None,
        end_time: datetime = None,
        agent_filter: List[str] = None,
    ) -> List[Dict[str, Any]]:
        """获取叙事时间线"""
        filtered_timeline = self.story_timeline

        # 时间过滤
        if start_time:
            filtered_timeline = [
                entry for entry in filtered_timeline if entry["timestamp"] >= start_time
            ]

        if end_time:
            filtered_timeline = [
                entry for entry in filtered_timeline if entry["timestamp"] <= end_time
            ]

        # Agent过滤
        if agent_filter:
            filtered_timeline = [
                entry
                for entry in filtered_timeline
                if entry["agent_id"] in agent_filter
            ]

        return filtered_timeline

    def get_coherence_report(self) -> Dict[str, Any]:
        """获取叙事连贯性报告"""
        return {
            "total_events": len(self.story_timeline),
            "character_arcs": len(self.character_arcs),
            "plot_threads": len(self.plot_threads),
            "active_plot_threads": len(
                [t for t in self.plot_threads.values() if t["status"] == "active"]
            ),
            "consistency_rule_count": len(self.consistency_rules),
            "timeline_span": {
                "start": (
                    self.story_timeline[0]["timestamp"].isoformat()
                    if self.story_timeline
                    else None
                ),
                "end": (
                    self.story_timeline[-1]["timestamp"].isoformat()
                    if self.story_timeline
                    else None
                ),
            },
            "character_summary": {
                aid: len(arc["events"]) for aid, arc in self.character_arcs.items()
            },
            "plot_thread_summary": {
                tid: len(thread["events"]) for tid, thread in self.plot_threads.items()
            },
        }

