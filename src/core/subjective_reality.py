#!/usr/bin/env python3
"""
主观现实引擎 (Subjective Reality Engine)
===================================

Wave 1 Implementation: TurnBriefFactory + FogOfWarService + BeliefModel

核心理念：每个Agent拥有不同的世界观和信息视图，通过主观现实引擎生成个性化的Turn Brief，
实现"同一事件，不同视角"的真实AI叙事体验。

Features:
- WorldState vs TurnBrief 区分：客观事实 vs 主观认知
- Fog-of-War 迷雾战争机制：信息获取的现实性约束
- BeliefModel 信念模型：Agent个性化世界观系统
- PersonalizedNarrative 个性化叙事：基于主观现实的故事生成
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class InformationSource(Enum):
    """信息来源类型"""

    DIRECT_OBSERVATION = "direct_observation"  # 直接观察
    HEARSAY = "hearsay"  # 道听途说
    DEDUCTION = "deduction"  # 逻辑推理
    MEMORY_RECONSTRUCTION = "memory_reconstruction"  # 记忆重构
    INTUITION = "intuition"  # 直觉判断
    RUMOR = "rumor"  # 谣言传闻


class ReliabilityLevel(Enum):
    """信息可靠性等级"""

    CONFIRMED = 1.0  # 确认事实
    HIGH = 0.8  # 高可信度
    MEDIUM = 0.6  # 中等可信度
    LOW = 0.4  # 低可信度
    SUSPECT = 0.2  # 存疑信息
    UNKNOWN = 0.0  # 未知真实性


class KnowledgeCategory(Enum):
    """知识类别"""

    SPATIAL = "spatial"  # 空间信息
    TEMPORAL = "temporal"  # 时间信息
    SOCIAL = "social"  # 社交关系
    TACTICAL = "tactical"  # 战术信息
    EMOTIONAL = "emotional"  # 情感状态
    ENVIRONMENTAL = "environmental"  # 环境状况
    RESOURCE = "resource"  # 资源状态


@dataclass
class InformationFragment:
    """信息片段 - 主观现实的基本单元"""

    fragment_id: str
    content: Dict[str, Any]
    source: InformationSource
    reliability: ReliabilityLevel
    category: KnowledgeCategory
    timestamp: datetime
    agent_id: str
    location_context: Optional[str] = None
    social_context: Optional[List[str]] = None
    decay_rate: float = 0.1  # 记忆衰减率
    confirmation_count: int = 0  # 确认次数

    def get_current_reliability(self) -> float:
        """计算考虑时间衰减的当前可靠性"""
        time_decay = max(
            0,
            1.0
            - self.decay_rate
            * (datetime.now() - self.timestamp).total_seconds()
            / 3600,
        )
        confirmation_boost = min(0.3, self.confirmation_count * 0.05)
        return min(
            1.0, self.reliability.value * time_decay + confirmation_boost
        )


@dataclass
class BeliefModel:
    """信念模型 - Agent的主观世界观"""

    agent_id: str
    personality_bias: Dict[str, float] = field(default_factory=dict)
    trust_network: Dict[str, float] = field(
        default_factory=dict
    )  # 对其他Agent的信任度
    information_fragments: List[InformationFragment] = field(
        default_factory=list
    )
    active_hypotheses: Dict[str, float] = field(
        default_factory=dict
    )  # 假设->可信度
    cognitive_filters: Dict[KnowledgeCategory, float] = field(
        default_factory=dict
    )

    def __post_init__(self):
        """初始化认知过滤器"""
        if not self.cognitive_filters:
            # 默认认知偏好权重
            self.cognitive_filters = {
                KnowledgeCategory.SPATIAL: 1.0,
                KnowledgeCategory.TEMPORAL: 1.0,
                KnowledgeCategory.SOCIAL: 0.8,
                KnowledgeCategory.TACTICAL: 0.9,
                KnowledgeCategory.EMOTIONAL: 0.6,
                KnowledgeCategory.ENVIRONMENTAL: 0.8,
                KnowledgeCategory.RESOURCE: 1.0,
            }

    def add_information(self, fragment: InformationFragment) -> None:
        """添加信息片段到信念模型"""
        # 检查是否与现有信息冲突
        conflicts = self._detect_conflicts(fragment)
        if conflicts:
            logger.debug(
                f"Information conflict detected for {self.agent_id}: {conflicts}"
            )
            # 根据可靠性和信任度处理冲突
            self._resolve_conflicts(fragment, conflicts)

        self.information_fragments.append(fragment)
        self._update_hypotheses(fragment)

    def _detect_conflicts(
        self, new_fragment: InformationFragment
    ) -> List[InformationFragment]:
        """检测信息冲突"""
        conflicts = []
        for existing in self.information_fragments:
            if (
                existing.category == new_fragment.category
                and existing.location_context == new_fragment.location_context
                and self._are_contradictory(
                    existing.content, new_fragment.content
                )
            ):
                conflicts.append(existing)
        return conflicts

    def _are_contradictory(self, content1: Dict, content2: Dict) -> bool:
        """判断两个信息内容是否矛盾"""
        # 简化的矛盾检测逻辑
        for key in content1:
            if key in content2 and content1[key] != content2[key]:
                return True
        return False

    def _resolve_conflicts(
        self,
        new_fragment: InformationFragment,
        conflicts: List[InformationFragment],
    ):
        """解决信息冲突"""
        new_reliability = new_fragment.get_current_reliability()

        for conflict in conflicts:
            conflict_reliability = conflict.get_current_reliability()

            # 信任度调整
            source_trust = self.trust_network.get(conflict.agent_id, 0.5)
            adjusted_conflict_reliability = conflict_reliability * source_trust

            # 保留可靠性更高的信息
            if new_reliability > adjusted_conflict_reliability:
                self.information_fragments.remove(conflict)
                logger.debug(
                    f"Replaced conflicting information for {self.agent_id}"
                )

    def _update_hypotheses(self, fragment: InformationFragment):
        """根据新信息更新假设"""
        # 简化的假设更新逻辑
        category_weight = self.cognitive_filters.get(fragment.category, 1.0)
        reliability = fragment.get_current_reliability()

        # 生成假设键
        hypothesis_key = f"{fragment.category.value}_{fragment.location_context or 'global'}"
        current_confidence = self.active_hypotheses.get(hypothesis_key, 0.0)

        # 更新假设可信度
        self.active_hypotheses[hypothesis_key] = min(
            1.0, current_confidence + reliability * category_weight * 0.1
        )


@dataclass
class FogOfWarState:
    """迷雾战争状态"""

    agent_id: str
    visible_locations: Set[str] = field(default_factory=set)
    known_agents: Dict[str, float] = field(
        default_factory=dict
    )  # agent_id -> 了解程度
    information_access_level: Dict[KnowledgeCategory, float] = field(
        default_factory=dict
    )
    last_update: datetime = field(default_factory=datetime.now)

    def can_access_information(
        self, category: KnowledgeCategory, location: str = None
    ) -> float:
        """判断能否访问某类信息，返回访问程度(0-1)"""
        base_access = self.information_access_level.get(category, 0.3)

        # 位置影响
        location_modifier = (
            1.0 if (location and location in self.visible_locations) else 0.5
        )

        # 时间衰减
        time_decay = max(
            0.1,
            1.0 - (datetime.now() - self.last_update).total_seconds() / 7200,
        )

        return min(1.0, base_access * location_modifier * time_decay)


class FogOfWarService:
    """迷雾战争服务 - 管理信息访问权限"""

    def __init__(self):
        self.fog_states: Dict[str, FogOfWarState] = {}
        self.global_visibility_map: Dict[str, Set[str]] = defaultdict(
            set
        )  # location -> visible_agents

    def initialize_agent_fog(
        self, agent_id: str, initial_location: str = None
    ):
        """初始化Agent的迷雾战争状态"""
        fog_state = FogOfWarState(
            agent_id=agent_id,
            information_access_level={
                KnowledgeCategory.SPATIAL: 0.8,
                KnowledgeCategory.TEMPORAL: 0.9,
                KnowledgeCategory.SOCIAL: 0.4,
                KnowledgeCategory.TACTICAL: 0.3,
                KnowledgeCategory.EMOTIONAL: 0.2,
                KnowledgeCategory.ENVIRONMENTAL: 0.7,
                KnowledgeCategory.RESOURCE: 0.5,
            },
        )

        if initial_location:
            fog_state.visible_locations.add(initial_location)
            self.global_visibility_map[initial_location].add(agent_id)

        self.fog_states[agent_id] = fog_state

    def update_visibility(
        self,
        agent_id: str,
        new_locations: List[str],
        lost_locations: List[str] = None,
    ):
        """更新Agent的可见区域"""
        if agent_id not in self.fog_states:
            self.initialize_agent_fog(agent_id)

        fog_state = self.fog_states[agent_id]

        # 添加新可见位置
        for location in new_locations:
            fog_state.visible_locations.add(location)
            self.global_visibility_map[location].add(agent_id)

        # 移除失去可见性的位置
        if lost_locations:
            for location in lost_locations:
                fog_state.visible_locations.discard(location)
                self.global_visibility_map[location].discard(agent_id)

        fog_state.last_update = datetime.now()

    def get_visible_agents(self, agent_id: str) -> List[str]:
        """获取Agent可见的其他Agent"""
        if agent_id not in self.fog_states:
            return []

        fog_state = self.fog_states[agent_id]
        visible_agents = set()

        # 在可见位置查找其他Agent
        for location in fog_state.visible_locations:
            visible_agents.update(self.global_visibility_map[location])

        visible_agents.discard(agent_id)  # 移除自己
        return list(visible_agents)

    def filter_world_state_for_agent(
        self, world_state: Dict, agent_id: str
    ) -> Dict:
        """为特定Agent过滤世界状态信息"""
        if agent_id not in self.fog_states:
            # 如果没有初始化，返回最小信息
            return {
                "visible_locations": [],
                "known_agents": [],
                "available_actions": ["observe", "move"],
                "timestamp": datetime.now().isoformat(),
            }

        fog_state = self.fog_states[agent_id]
        filtered_state = {
            "timestamp": datetime.now().isoformat(),
            "visible_locations": list(fog_state.visible_locations),
            "known_agents": [],
            "available_actions": [],
            "environmental_info": {},
            "social_context": {},
        }

        # 过滤可见Agent信息
        visible_agents = self.get_visible_agents(agent_id)
        for visible_agent in visible_agents:
            access_level = fog_state.can_access_information(
                KnowledgeCategory.SOCIAL
            )
            if access_level > 0.3:
                filtered_state["known_agents"].append(
                    {
                        "agent_id": visible_agent,
                        "visibility": access_level,
                        "last_seen": fog_state.last_update.isoformat(),
                    }
                )

        # 过滤环境信息
        env_access = fog_state.can_access_information(
            KnowledgeCategory.ENVIRONMENTAL
        )
        if env_access > 0.2:
            for location in fog_state.visible_locations:
                if location in world_state.get("locations", {}):
                    filtered_state["environmental_info"][location] = {
                        "description": world_state["locations"][location].get(
                            "description", "Unknown"
                        ),
                        "visibility": env_access,
                    }

        # 生成可用行动
        filtered_state["available_actions"] = self._generate_available_actions(
            fog_state, world_state
        )

        return filtered_state

    def _generate_available_actions(
        self, fog_state: FogOfWarState, world_state: Dict
    ) -> List[str]:
        """根据迷雾战争状态生成可用行动"""
        actions = ["observe"]  # 基础行动

        # 根据可见性添加行动
        if len(fog_state.visible_locations) > 0:
            actions.extend(["investigate", "move"])

        # 根据已知Agent添加社交行动
        if len(fog_state.known_agents) > 0:
            actions.extend(["communicate", "negotiate"])

        # 根据信息访问等级添加专业行动
        tactical_access = fog_state.can_access_information(
            KnowledgeCategory.TACTICAL
        )
        if tactical_access > 0.5:
            actions.append("plan")

        resource_access = fog_state.can_access_information(
            KnowledgeCategory.RESOURCE
        )
        if resource_access > 0.4:
            actions.extend(["gather", "craft"])

        return actions


@dataclass
class PersonalizedTurnBrief:
    """个性化回合简报"""

    agent_id: str
    turn_number: int
    subjective_world_state: Dict[str, Any]
    available_information: List[InformationFragment]
    recommended_actions: List[str]
    narrative_context: str
    confidence_levels: Dict[str, float]
    created_at: datetime = field(default_factory=datetime.now)


class TurnBriefFactory:
    """回合简报工厂 - 生成个性化的Turn Brief"""

    def __init__(self, fog_service: FogOfWarService):
        self.fog_service = fog_service
        self.belief_models: Dict[str, BeliefModel] = {}
        self.narrative_templates = self._load_narrative_templates()

    def _load_narrative_templates(self) -> Dict[str, str]:
        """加载叙事模板"""
        return {
            "exploration": "在未知的{location}中，{agent_name}仔细观察着周围的环境...",
            "social": "面对{other_agents}，{agent_name}考虑着如何应对这个微妙的局面...",
            "tactical": "基于当前掌握的情报，{agent_name}开始制定下一步的行动计划...",
            "resource": "检视手头的资源后，{agent_name}权衡着各种可能的选择...",
            "mystery": "太多的未知因素让{agent_name}感到困惑，需要更多的信息才能做出判断...",
        }

    def initialize_belief_model(
        self, agent_id: str, personality_traits: Dict[str, float] = None
    ):
        """初始化Agent的信念模型"""
        if personality_traits is None:
            personality_traits = {}

        belief_model = BeliefModel(
            agent_id=agent_id, personality_bias=personality_traits
        )

        self.belief_models[agent_id] = belief_model
        return belief_model

    async def create_personalized_brief(
        self,
        agent_id: str,
        turn_number: int,
        global_world_state: Dict,
        recent_events: List[Dict] = None,
    ) -> PersonalizedTurnBrief:
        """创建个性化回合简报"""

        # 获取或创建信念模型
        if agent_id not in self.belief_models:
            self.initialize_belief_model(agent_id)

        belief_model = self.belief_models[agent_id]

        # 通过迷雾战争过滤世界状态
        filtered_world_state = self.fog_service.filter_world_state_for_agent(
            global_world_state, agent_id
        )

        # 处理最近事件
        if recent_events:
            await self._process_recent_events(belief_model, recent_events)

        # 提取可用信息
        available_info = self._extract_available_information(
            belief_model, filtered_world_state
        )

        # 生成推荐行动
        recommended_actions = self._generate_recommended_actions(
            belief_model, filtered_world_state, available_info
        )

        # 生成叙事背景
        narrative_context = self._generate_narrative_context(
            agent_id, filtered_world_state, available_info
        )

        # 计算信息可信度
        confidence_levels = self._calculate_confidence_levels(
            belief_model, available_info
        )

        return PersonalizedTurnBrief(
            agent_id=agent_id,
            turn_number=turn_number,
            subjective_world_state=filtered_world_state,
            available_information=available_info,
            recommended_actions=recommended_actions,
            narrative_context=narrative_context,
            confidence_levels=confidence_levels,
        )

    async def _process_recent_events(
        self, belief_model: BeliefModel, events: List[Dict]
    ):
        """处理最近发生的事件"""
        for event in events:
            # 将事件转换为信息片段
            fragment = InformationFragment(
                fragment_id=f"event_{event.get('id', hash(str(event)))}",
                content=event,
                source=InformationSource.DIRECT_OBSERVATION,
                reliability=ReliabilityLevel.HIGH,
                category=self._categorize_event(event),
                timestamp=datetime.fromisoformat(
                    event.get("timestamp", datetime.now().isoformat())
                ),
                agent_id=belief_model.agent_id,
                location_context=event.get("location"),
                social_context=event.get("involved_agents", []),
            )

            belief_model.add_information(fragment)

    def _categorize_event(self, event: Dict) -> KnowledgeCategory:
        """将事件分类到知识类别"""
        event_type = event.get("type", "").lower()

        if "move" in event_type or "location" in event_type:
            return KnowledgeCategory.SPATIAL
        elif "communicate" in event_type or "social" in event_type:
            return KnowledgeCategory.SOCIAL
        elif "combat" in event_type or "attack" in event_type:
            return KnowledgeCategory.TACTICAL
        elif "gather" in event_type or "resource" in event_type:
            return KnowledgeCategory.RESOURCE
        elif "emotion" in event_type or "feel" in event_type:
            return KnowledgeCategory.EMOTIONAL
        else:
            return KnowledgeCategory.ENVIRONMENTAL

    def _extract_available_information(
        self, belief_model: BeliefModel, world_state: Dict
    ) -> List[InformationFragment]:
        """提取可用的信息片段"""
        available_info = []

        # 从信念模型中提取可靠的信息
        for fragment in belief_model.information_fragments:
            if fragment.get_current_reliability() > 0.3:
                available_info.append(fragment)

        # 从当前世界状态生成新的信息片段
        for location in world_state.get("visible_locations", []):
            fragment = InformationFragment(
                fragment_id=f"current_{location}_{datetime.now().isoformat()}",
                content={"location": location, "visible": True},
                source=InformationSource.DIRECT_OBSERVATION,
                reliability=ReliabilityLevel.CONFIRMED,
                category=KnowledgeCategory.SPATIAL,
                timestamp=datetime.now(),
                agent_id=belief_model.agent_id,
                location_context=location,
            )
            available_info.append(fragment)

        # 按可靠性排序
        available_info.sort(
            key=lambda x: x.get_current_reliability(), reverse=True
        )

        return available_info[:20]  # 限制信息数量

    def _generate_recommended_actions(
        self,
        belief_model: BeliefModel,
        world_state: Dict,
        available_info: List[InformationFragment],
    ) -> List[str]:
        """生成推荐行动"""
        actions = set(world_state.get("available_actions", ["observe"]))

        # 基于信念模型的个性化行动推荐
        personality_bias = belief_model.personality_bias

        # 探索性格偏好
        if personality_bias.get("curiosity", 0.5) > 0.6:
            actions.update(["investigate", "explore"])

        # 社交性格偏好
        if (
            personality_bias.get("sociability", 0.5) > 0.6
            and len(world_state.get("known_agents", [])) > 0
        ):
            actions.update(["communicate", "negotiate"])

        # 谨慎性格偏好
        if personality_bias.get("caution", 0.5) > 0.7:
            actions.update(["observe", "assess"])

        # 基于可用信息的行动推荐
        tactical_info = [
            f
            for f in available_info
            if f.category == KnowledgeCategory.TACTICAL
        ]
        if tactical_info and len(tactical_info) > 2:
            actions.add("plan")

        resource_info = [
            f
            for f in available_info
            if f.category == KnowledgeCategory.RESOURCE
        ]
        if resource_info:
            actions.update(["gather", "craft"])

        return list(actions)[:8]  # 限制行动数量

    def _generate_narrative_context(
        self,
        agent_id: str,
        world_state: Dict,
        available_info: List[InformationFragment],
    ) -> str:
        """生成叙事背景"""

        # 选择主要的情境类型
        situation_type = self._determine_situation_type(
            world_state, available_info
        )

        # 获取叙事模板
        template = self.narrative_templates.get(
            situation_type, self.narrative_templates["mystery"]
        )

        # 填充模板变量
        context_vars = {
            "agent_name": agent_id.replace("_", " ").title(),
            "location": ", ".join(
                world_state.get("visible_locations", ["未知区域"])
            ),
            "other_agents": ", ".join(
                [
                    a.get("agent_id", "Unknown")
                    for a in world_state.get("known_agents", [])
                ]
            ),
        }

        try:
            narrative = template.format(**context_vars)
        except KeyError:
            # 如果模板变量不完整，使用默认叙事
            narrative = f"{context_vars['agent_name']}正在评估当前的情况，思考着下一步该如何行动。"

        # 添加基于可用信息的补充描述
        info_summary = self._summarize_information(available_info)
        if info_summary:
            narrative += f"\n\n{info_summary}"

        return narrative

    def _determine_situation_type(
        self, world_state: Dict, available_info: List[InformationFragment]
    ) -> str:
        """确定当前情境类型"""

        # 统计信息类型
        info_categories = defaultdict(int)
        for info in available_info:
            info_categories[info.category] += 1

        # 判断主要情境
        if len(world_state.get("known_agents", [])) > 0:
            return "social"
        elif info_categories[KnowledgeCategory.TACTICAL] > 2:
            return "tactical"
        elif info_categories[KnowledgeCategory.RESOURCE] > 1:
            return "resource"
        elif len(world_state.get("visible_locations", [])) > 1:
            return "exploration"
        else:
            return "mystery"

    def _summarize_information(
        self, available_info: List[InformationFragment]
    ) -> str:
        """汇总可用信息"""
        if not available_info:
            return ""

        # 按类别分组信息
        categorized_info = defaultdict(list)
        for info in available_info[:5]:  # 只取前5个最重要的信息
            categorized_info[info.category].append(info)

        summary_parts = []

        # 生成每个类别的摘要
        for category, infos in categorized_info.items():
            if category == KnowledgeCategory.SPATIAL:
                locations = [
                    info.content.get("location", "Unknown") for info in infos
                ]
                summary_parts.append(f"已知区域：{', '.join(set(locations))}")
            elif category == KnowledgeCategory.SOCIAL:
                agents = [
                    info.content.get("agent_id", "Unknown") for info in infos
                ]
                summary_parts.append(f"已知人员：{', '.join(set(agents))}")
            elif category == KnowledgeCategory.RESOURCE:
                summary_parts.append("掌握了一些资源信息")
            elif category == KnowledgeCategory.TACTICAL:
                summary_parts.append("获得了战术情报")

        if summary_parts:
            return "当前掌握的情报：" + "；".join(summary_parts) + "。"

        return ""

    def _calculate_confidence_levels(
        self,
        belief_model: BeliefModel,
        available_info: List[InformationFragment],
    ) -> Dict[str, float]:
        """计算各类信息的可信度"""
        confidence = {}

        # 计算各知识类别的平均可信度
        for category in KnowledgeCategory:
            relevant_info = [
                info for info in available_info if info.category == category
            ]
            if relevant_info:
                avg_reliability = sum(
                    info.get_current_reliability() for info in relevant_info
                ) / len(relevant_info)
                confidence[category.value] = round(avg_reliability, 2)
            else:
                confidence[category.value] = 0.0

        # 计算整体信息可信度
        if available_info:
            overall_confidence = sum(
                info.get_current_reliability() for info in available_info
            ) / len(available_info)
            confidence["overall"] = round(overall_confidence, 2)
        else:
            confidence["overall"] = 0.0

        return confidence


class SubjectiveRealityEngine:
    """主观现实引擎主类"""

    def __init__(self):
        self.fog_service = FogOfWarService()
        self.turn_brief_factory = TurnBriefFactory(self.fog_service)
        self.active_agents: Set[str] = set()

        logger.info("主观现实引擎初始化完成")

    async def initialize(self) -> bool:
        """Initialize the subjective reality engine and all subsystems."""
        try:
            logger.info("Initializing SubjectiveRealityEngine subsystems")

            # Ensure fog service is ready
            if not hasattr(self.fog_service, "fog_states"):
                logger.error("FogOfWarService not properly initialized")
                return False

            # Ensure turn brief factory is ready
            if not hasattr(self.turn_brief_factory, "fog_service"):
                logger.error("TurnBriefFactory not properly initialized")
                return False

            logger.info(
                "SubjectiveRealityEngine initialization completed successfully"
            )
            return True

        except Exception as e:
            logger.error(f"SubjectiveRealityEngine initialization failed: {e}")
            return False

    async def initialize_agent(
        self,
        agent_id: str,
        personality_traits: Dict[str, float] = None,
        initial_location: str = None,
    ) -> BeliefModel:
        """初始化Agent的主观现实系统"""

        # 初始化迷雾战争状态
        self.fog_service.initialize_agent_fog(agent_id, initial_location)

        # 初始化信念模型
        belief_model = self.turn_brief_factory.initialize_belief_model(
            agent_id, personality_traits
        )

        self.active_agents.add(agent_id)

        logger.info(f"Agent {agent_id} 的主观现实系统初始化完成")
        return belief_model

    async def generate_turn_brief(
        self,
        agent_id: str,
        turn_number: int,
        global_world_state: Dict,
        recent_events: List[Dict] = None,
    ) -> PersonalizedTurnBrief:
        """生成Agent的个性化回合简报"""

        if agent_id not in self.active_agents:
            await self.initialize_agent(agent_id)

        brief = await self.turn_brief_factory.create_personalized_brief(
            agent_id=agent_id,
            turn_number=turn_number,
            global_world_state=global_world_state,
            recent_events=recent_events,
        )

        logger.debug(
            f"Generated personalized brief for {agent_id} (Turn {turn_number})"
        )
        return brief

    async def update_agent_knowledge(
        self, agent_id: str, new_information: List[Dict]
    ):
        """更新Agent的知识状态"""

        if agent_id not in self.active_agents:
            logger.warning(
                f"Attempted to update knowledge for uninitialized agent: {agent_id}"
            )
            return

        belief_model = self.turn_brief_factory.belief_models[agent_id]

        for info_dict in new_information:
            fragment = InformationFragment(
                fragment_id=info_dict.get(
                    "id", f"info_{hash(str(info_dict))}"
                ),
                content=info_dict.get("content", {}),
                source=InformationSource[
                    info_dict.get("source", "DIRECT_OBSERVATION")
                ],
                reliability=ReliabilityLevel[
                    info_dict.get("reliability", "MEDIUM")
                ],
                category=KnowledgeCategory[
                    info_dict.get("category", "ENVIRONMENTAL")
                ],
                timestamp=datetime.fromisoformat(
                    info_dict.get("timestamp", datetime.now().isoformat())
                ),
                agent_id=agent_id,
                location_context=info_dict.get("location"),
                social_context=info_dict.get("social_context", []),
            )

            belief_model.add_information(fragment)

        logger.debug(
            f"Updated knowledge for {agent_id}: {len(new_information)} new information fragments"
        )

    def get_agent_belief_summary(self, agent_id: str) -> Dict[str, Any]:
        """获取Agent信念模型摘要"""
        if agent_id not in self.active_agents:
            return {}

        belief_model = self.turn_brief_factory.belief_models[agent_id]
        fog_state = self.fog_service.fog_states.get(agent_id)

        return {
            "agent_id": agent_id,
            "total_information_fragments": len(
                belief_model.information_fragments
            ),
            "active_hypotheses": len(belief_model.active_hypotheses),
            "visible_locations": list(fog_state.visible_locations)
            if fog_state
            else [],
            "trust_network_size": len(belief_model.trust_network),
            "last_update": fog_state.last_update.isoformat()
            if fog_state
            else None,
            "personality_traits": belief_model.personality_bias,
        }


# Factory function for easy instantiation
def create_subjective_reality_engine() -> SubjectiveRealityEngine:
    """创建主观现实引擎实例"""
    return SubjectiveRealityEngine()


if __name__ == "__main__":
    # 示例用法
    async def example_usage():
        engine = create_subjective_reality_engine()

        # 初始化一个Agent
        await engine.initialize_agent(
            agent_id="test_agent",
            personality_traits={"curiosity": 0.8, "caution": 0.6},
            initial_location="command_center",
        )

        # 模拟全局世界状态
        global_world_state = {
            "locations": {
                "command_center": {"description": "指挥中心"},
                "laboratory": {"description": "实验室"},
            },
            "agents": {"test_agent": {"location": "command_center"}},
        }

        # 生成个性化简报
        brief = await engine.generate_turn_brief(
            agent_id="test_agent",
            turn_number=1,
            global_world_state=global_world_state,
        )

        print("生成的个性化简报：")
        print(f"叙事背景：{brief.narrative_context}")
        print(f"推荐行动：{brief.recommended_actions}")
        print(f"可信度：{brief.confidence_levels}")

    # 运行示例
    # asyncio.run(example_usage())
