#!/usr/bin/env python3
"""
Dynamic Event Orchestrator - Intelligent event sequencing based on story structure
"""

import math
import random
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List

from dialogue_engine import ContextAwareDialogueEngine
from story_architect import PlotStage, StoryBlueprint


class EventPriority(Enum):
    """Priority levels for event generation"""

    CRITICAL = 4  # Plot-critical events
    HIGH = 3  # Important character moments
    MEDIUM = 2  # Standard story progression
    LOW = 1  # Atmospheric/flavor events


@dataclass
class EventCandidate:
    """Candidate event for generation"""

    event_type: str
    priority: EventPriority
    characters_involved: List[str]
    description: str
    tension_impact: float  # -1.0 to 1.0
    fits_current_stage: bool

    def score(
        self, current_tension: float, target_tension: float, orchestrator=None
    ) -> float:
        """Calculate suitability score for this event with character balance"""
        # Stage fit is most important
        stage_score = 10.0 if self.fits_current_stage else 0.0

        # Priority score
        priority_score = self.priority.value * 2.0

        # Tension alignment score
        tension_diff = abs(
            target_tension - (current_tension + self.tension_impact)
        )
        tension_score = max(0, 5.0 - tension_diff * 10)

        # Character balance score (new!)
        balance_score = 0.0
        if orchestrator and self.characters_involved:
            for char_name in self.characters_involved:
                usage = orchestrator.character_usage.get(char_name, 0)
                # Heavily favor less-used characters
                if usage == 0:
                    balance_score += 15.0  # Never used - high bonus
                elif usage < 5:
                    balance_score += 10.0  # Rarely used - good bonus
                elif usage < 10:
                    balance_score += 5.0  # Moderately used - small bonus
                else:
                    balance_score -= usage * 0.5  # Overused - penalty

        return stage_score + priority_score + tension_score + balance_score


class DynamicEventOrchestrator:
    """Orchestrates events based on story structure and context"""

    def __init__(
        self,
        blueprint: StoryBlueprint,
        dialogue_engine: ContextAwareDialogueEngine,
    ):
        self.blueprint = blueprint
        self.dialogue_engine = dialogue_engine
        self.event_history = []
        self.current_event_index = 0
        self.pacing_manager = PacingManager()

        # Enhanced character balance tracking
        self.character_usage = {}
        self.last_speaker = None
        self.character_turn_queue = []
        self.min_character_turns = (
            3  # Minimum turns before character can repeat
        )

    def generate_next_event(
        self, characters: List, current_location: str
    ) -> Dict:
        """Generate the next event based on story context"""

        # Get current story context
        progress = self.current_event_index / self.blueprint.target_length
        plot_guidance = self._get_plot_guidance(progress)

        # Generate event candidates
        candidates = self._generate_event_candidates(
            characters, current_location, plot_guidance
        )

        # Score and select best candidate
        current_tension = self._calculate_current_tension()
        target_tension = plot_guidance["tension_level"]

        best_candidate = max(
            candidates,
            key=lambda c: c.score(current_tension, target_tension, self),
        )

        # Generate actual event content
        event = self._realize_event(best_candidate, plot_guidance)

        # Track character usage for balance
        if event.get("characters"):
            for char_name in event.get("characters", []):
                self.character_usage[char_name] = (
                    self.character_usage.get(char_name, 0) + 1
                )
                self.last_speaker = char_name

        # Update state
        self.event_history.append(event)
        self.current_event_index += 1

        return event

    def _get_plot_guidance(self, progress: float) -> Dict:
        """Get guidance from story blueprint"""
        stage_index = min(
            int(progress * len(self.blueprint.plot_points)),
            len(self.blueprint.plot_points) - 1,
        )

        plot_point = self.blueprint.plot_points[stage_index]
        tension = self.blueprint.get_current_tension(progress)

        # Determine event suggestions based on plot stage
        event_suggestions = self._get_stage_appropriate_events(
            plot_point.stage
        )

        return {
            "current_stage": plot_point.stage,
            "plot_description": plot_point.description,
            "tension_level": tension,
            "suggested_events": event_suggestions,
            "required_characters": plot_point.required_characters,
            "location": plot_point.location,
            "conflict_type": plot_point.conflict_type,
        }

    def _get_stage_appropriate_events(self, stage: PlotStage) -> List[str]:
        """Get appropriate event types for current stage"""
        stage_events = {
            PlotStage.SETUP: [
                "introduction",
                "worldbuilding",
                "foreshadowing",
            ],
            PlotStage.INCITING_INCIDENT: [
                "discovery",
                "revelation",
                "disruption",
            ],
            PlotStage.RISING_ACTION: [
                "challenge",
                "conflict",
                "investigation",
            ],
            PlotStage.MIDPOINT: ["reversal", "revelation", "betrayal"],
            PlotStage.CRISIS: ["dilemma", "sacrifice", "confrontation"],
            PlotStage.CLIMAX: ["battle", "resolution", "transformation"],
            PlotStage.RESOLUTION: [
                "consequence",
                "new_equilibrium",
                "reflection",
            ],
            PlotStage.DENOUEMENT: ["farewell", "epilogue", "hint_of_future"],
        }

        return stage_events.get(stage, ["dialogue", "action"])

    def _generate_event_candidates(
        self, characters: List, location: str, guidance: Dict
    ) -> List[EventCandidate]:
        """Generate possible events for current context"""
        candidates = []
        suggested_types = guidance["suggested_events"]
        tension = guidance["tension_level"]

        # Dialogue events with STRONG character balance enforcement
        if "dialogue" in suggested_types or tension < 0.7:
            # Build character turn queue if empty
            if not self.character_turn_queue:
                # Sort by usage and create balanced queue
                sorted_chars = sorted(
                    characters,
                    key=lambda c: self.character_usage.get(c.name, 0),
                )
                # Add least used character multiple times to balance
                for char in sorted_chars:
                    usage = self.character_usage.get(char.name, 0)
                    if usage == 0:
                        # Never used - add 3 times
                        self.character_turn_queue.extend([char] * 3)
                    elif usage < 5:
                        # Rarely used - add 2 times
                        self.character_turn_queue.extend([char] * 2)
                    else:
                        # Used enough - add once
                        self.character_turn_queue.append(char)

            # Take next character from queue
            if self.character_turn_queue:
                next_char = self.character_turn_queue.pop(0)
                candidates.append(
                    EventCandidate(
                        event_type="dialogue",
                        priority=EventPriority.HIGH,
                        characters_involved=[next_char.name],
                        description=f"{next_char.name} shares insight",
                        tension_impact=0.0,
                        fits_current_stage=True,
                    )
                )

            # Add alternative candidates with lower priority
            for character in characters:
                if character.name != self.last_speaker:
                    candidates.append(
                        EventCandidate(
                            event_type="dialogue",
                            priority=EventPriority.LOW,
                            characters_involved=[character.name],
                            description=f"{character.name} responds",
                            tension_impact=0.0,
                            fits_current_stage=True,
                        )
                    )

        # Conflict events with balanced character selection
        if "conflict" in suggested_types or tension > 0.5:
            # Select two least-used characters for conflict
            sorted_chars = sorted(
                characters, key=lambda c: self.character_usage.get(c.name, 0)
            )
            if len(sorted_chars) >= 2:
                conflict_chars = [sorted_chars[0].name, sorted_chars[1].name]
            else:
                conflict_chars = [c.name for c in characters[:2]]

            candidates.append(
                EventCandidate(
                    event_type="conflict",
                    priority=EventPriority.HIGH,
                    characters_involved=conflict_chars,
                    description="Characters disagree on approach",
                    tension_impact=0.2,
                    fits_current_stage="conflict" in suggested_types,
                )
            )

        # Discovery events with balanced character selection
        if "discovery" in suggested_types:
            # Select least-used character for discovery
            sorted_chars = sorted(
                characters, key=lambda c: self.character_usage.get(c.name, 0)
            )
            discoverer = (
                sorted_chars[0].name if sorted_chars else characters[0].name
            )

            candidates.append(
                EventCandidate(
                    event_type="discovery",
                    priority=EventPriority.HIGH,
                    characters_involved=[discoverer],
                    description="Important clue discovered",
                    tension_impact=0.1,
                    fits_current_stage=True,
                )
            )

        # Action events
        if tension > 0.6:
            candidates.append(
                EventCandidate(
                    event_type="action",
                    priority=EventPriority.MEDIUM,
                    characters_involved=[c.name for c in characters],
                    description="Group takes decisive action",
                    tension_impact=-0.1,
                    fits_current_stage=True,
                )
            )

        # Environmental events
        if len(self.event_history) % 5 == 0:  # Every 5 events
            candidates.append(
                EventCandidate(
                    event_type="environment",
                    priority=EventPriority.LOW,
                    characters_involved=[],
                    description="Environment shifts",
                    tension_impact=0.05,
                    fits_current_stage=True,
                )
            )

        # Crisis events
        if "dilemma" in suggested_types or "sacrifice" in suggested_types:
            candidates.append(
                EventCandidate(
                    event_type="crisis",
                    priority=EventPriority.CRITICAL,
                    characters_involved=[c.name for c in characters],
                    description="Critical decision point",
                    tension_impact=0.3,
                    fits_current_stage=True,
                )
            )

        return candidates

    def _realize_event(
        self, candidate: EventCandidate, guidance: Dict
    ) -> Dict:
        """Convert event candidate into actual event content"""
        event = {
            "type": candidate.event_type,
            "characters": candidate.characters_involved,
            "location": guidance.get("location", "Unknown"),
            "content": {},
        }

        if candidate.event_type == "dialogue":
            # Generate contextual dialogue
            character = candidate.characters_involved[0]
            (
                dialogue,
                emotion,
            ) = self.dialogue_engine.generate_contextual_dialogue(
                character, guidance
            )
            event["content"] = {
                "speaker": character,
                "dialogue": dialogue,
                "emotion": emotion,
            }

        elif candidate.event_type == "conflict":
            # Generate conflict scene
            event["content"] = self._generate_conflict_content(
                candidate.characters_involved, guidance
            )

        elif candidate.event_type == "discovery":
            # Generate discovery moment
            event["content"] = self._generate_discovery_content(
                candidate.characters_involved[0], guidance
            )

        elif candidate.event_type == "action":
            # Generate action sequence
            event["content"] = self._generate_action_content(
                candidate.characters_involved, guidance
            )

        elif candidate.event_type == "environment":
            # Generate environmental description
            event["content"] = self._generate_environment_content(guidance)

        elif candidate.event_type == "crisis":
            # Generate crisis moment
            event["content"] = self._generate_crisis_content(
                candidate.characters_involved, guidance
            )

        return event

    def _calculate_current_tension(self) -> float:
        """Calculate current story tension from recent events"""
        if not self.event_history:
            return 0.2

        # Weight recent events more heavily
        tension_sum = 0.0
        weight_sum = 0.0

        for i, event in enumerate(self.event_history[-10:]):
            weight = math.exp(-0.1 * (len(self.event_history) - i))
            event_tension = self._estimate_event_tension(event)
            tension_sum += event_tension * weight
            weight_sum += weight

        return tension_sum / weight_sum if weight_sum > 0 else 0.5

    def _estimate_event_tension(self, event: Dict) -> float:
        """Estimate tension level of an event"""
        tension_map = {
            "conflict": 0.7,
            "crisis": 0.9,
            "discovery": 0.5,
            "action": 0.6,
            "dialogue": 0.3,
            "environment": 0.2,
        }

        return tension_map.get(event.get("type", "dialogue"), 0.4)

    def _generate_conflict_content(
        self, characters: List[str], guidance: Dict
    ) -> Dict:
        """Generate diverse conflict scene content"""

        # Initialize conflict history
        if not hasattr(self, "used_conflicts"):
            self.used_conflicts = set()

        # Get stage-appropriate conflicts
        stage = guidance.get("current_stage", PlotStage.RISING_ACTION)

        if len(characters) < 2:
            # Internal conflict for single character
            char = characters[0] if characters else "主角"
            conflicts = [
                {
                    "description": f"{char}内心充满矛盾",
                    "details": "责任与欲望在撕扯着灵魂",
                },
                {
                    "description": f"{char}面临艰难抉择",
                    "details": "每个选择都意味着牺牲",
                },
                {
                    "description": f"{char}质疑自己的信念",
                    "details": "曾经的确定如今动摇",
                },
            ]
        else:
            # Interpersonal conflicts based on stage
            char1, char2 = characters[0], characters[1]

            if stage in [PlotStage.SETUP, PlotStage.INCITING_INCIDENT]:
                conflicts = [
                    {
                        "description": f"{char1}对{char2}的方法表示怀疑",
                        "dialogue1": "你确定这是正确的道路吗？",
                        "dialogue2": "我们没有更好的选择了。",
                    },
                    {
                        "description": f"{char1}和{char2}对目标产生分歧",
                        "dialogue1": "我们的优先级不同。",
                        "dialogue2": "但我们的命运相连。",
                    },
                    {
                        "description": f"信任危机在{char1}和{char2}之间产生",
                        "dialogue1": "你隐瞒了什么？",
                        "dialogue2": "有些真相过于沉重。",
                    },
                ]
            elif stage in [PlotStage.CRISIS, PlotStage.CLIMAX]:
                conflicts = [
                    {
                        "description": f"{char1}和{char2}就牺牲问题激烈争论",
                        "dialogue1": "不能让任何人牺牲！",
                        "dialogue2": "这是唯一能拯救所有人的方法！",
                    },
                    {
                        "description": f"绝望中{char1}指责{char2}的决定",
                        "dialogue1": "都是因为你的选择！",
                        "dialogue2": "我做了必须做的事！",
                    },
                    {
                        "description": f"{char1}和{char2}的理念彻底冲突",
                        "dialogue1": "你背叛了我们的初衷！",
                        "dialogue2": "初衷已经不重要了！",
                    },
                ]
            else:
                conflicts = [
                    {
                        "description": f"{char1}与{char2}对未来的看法不同",
                        "dialogue1": "我们改变了一切。",
                        "dialogue2": "也许这就是命运。",
                    },
                    {
                        "description": f"{char1}和{char2}反思他们的选择",
                        "dialogue1": "我们做对了吗？",
                        "dialogue2": "时间会告诉我们答案。",
                    },
                ]

        # Filter unused conflicts
        available = [
            c
            for c in conflicts
            if c.get("description", "") not in self.used_conflicts
        ]

        if not available:
            self.used_conflicts.clear()
            available = conflicts

        selected = random.choice(available)
        self.used_conflicts.add(selected.get("description", ""))

        return selected

    def _generate_discovery_content(
        self, character: str, guidance: Dict
    ) -> Dict:
        """Generate diverse discovery content"""

        # Initialize discovery history
        if not hasattr(self, "used_discoveries"):
            self.used_discoveries = set()

        # Stage-based discoveries
        stage = guidance.get("current_stage", PlotStage.RISING_ACTION)

        if stage in [PlotStage.SETUP, PlotStage.INCITING_INCIDENT]:
            discoveries = [
                {
                    "description": f"{character}发现了神秘的能量痕迹",
                    "details": "这些痕迹指向一个被遗忘的真相",
                },
                {
                    "description": f"{character}察觉到了时空的异常",
                    "details": "现实的结构出现了细微的裂痕",
                },
                {
                    "description": f"{character}找到了古老的记录",
                    "details": "记录中包含着预言的片段",
                },
                {
                    "description": f"{character}感应到了其他维度的存在",
                    "details": "有什么在呼唤着他们",
                },
                {
                    "description": f"{character}解读出了隐藏的信息",
                    "details": "信息指向一个关键的坐标",
                },
            ]
        elif stage in [PlotStage.RISING_ACTION, PlotStage.MIDPOINT]:
            discoveries = [
                {
                    "description": f"{character}理解了能量的真正本质",
                    "details": "原来一切都是相互连接的",
                },
                {
                    "description": f"{character}发现了控制的方法",
                    "details": "关键在于频率的同步",
                },
                {
                    "description": f"{character}找到了失落的碎片",
                    "details": "碎片完成了拼图的关键部分",
                },
                {
                    "description": f"{character}破解了防护机制",
                    "details": "通道终于打开了",
                },
                {
                    "description": f"{character}觉醒了潜藏的能力",
                    "details": "新的力量在体内苏醒",
                },
            ]
        elif stage in [PlotStage.CRISIS, PlotStage.CLIMAX]:
            discoveries = [
                {
                    "description": f"{character}发现了敌人的弱点",
                    "details": "胜利的希望重新点燃",
                },
                {
                    "description": f"{character}理解了牺牲的意义",
                    "details": "有些东西比生命更重要",
                },
                {
                    "description": f"{character}找到了最后的钥匙",
                    "details": "所有的准备都是为了这一刻",
                },
                {
                    "description": f"{character}看透了命运的真相",
                    "details": "原来一切都是必然",
                },
                {
                    "description": f"{character}发现了逆转的方法",
                    "details": "还有一线生机",
                },
            ]
        else:  # RESOLUTION, DENOUEMENT
            discoveries = [
                {
                    "description": f"{character}理解了整个事件的意义",
                    "details": "每个牺牲都有其价值",
                },
                {
                    "description": f"{character}发现了新的可能性",
                    "details": "结束也是开始",
                },
                {
                    "description": f"{character}找到了内心的平静",
                    "details": "一切都回归了本源",
                },
                {
                    "description": f"{character}获得了终极的智慧",
                    "details": "真理原来如此简单",
                },
            ]

        # Filter unused discoveries
        available = [
            d
            for d in discoveries
            if d["description"] not in self.used_discoveries
        ]

        if not available:
            self.used_discoveries.clear()
            available = discoveries

        selected = random.choice(available)
        self.used_discoveries.add(selected["description"])

        return selected

    def _generate_action_content(
        self, characters: List[str], guidance: Dict
    ) -> Dict:
        """Generate diverse action sequence content"""

        # Initialize action history if not exists
        if not hasattr(self, "used_actions"):
            self.used_actions = set()

        # Expanded action library based on plot stage
        stage = guidance.get("current_stage", PlotStage.RISING_ACTION)

        if stage in [PlotStage.SETUP, PlotStage.INCITING_INCIDENT]:
            actions = [
                {
                    "description": "探索着神秘的能量源",
                    "details": "波动的频率似乎在回应他们的存在",
                },
                {
                    "description": "解析着古老的符文序列",
                    "details": "每个符号都蕴含着深层的意义",
                },
                {
                    "description": "建立起量子共振连接",
                    "details": "意识开始在更高维度交汇",
                },
                {
                    "description": "激活了休眠的观测装置",
                    "details": "尘封的真相逐渐显现",
                },
                {
                    "description": "感知到了异常的时空波动",
                    "details": "现实的边界开始模糊",
                },
            ]
        elif stage in [PlotStage.RISING_ACTION, PlotStage.MIDPOINT]:
            actions = [
                {"description": "突破了维度屏障", "details": "新的现实层面展现在眼前"},
                {"description": "重构了破碎的时间线", "details": "因果链重新编织"},
                {"description": "释放出强大的能量脉冲", "details": "空间因此产生涟漪"},
                {
                    "description": "同步了彼此的量子频率",
                    "details": "三人的意识达到完美和谐",
                },
                {
                    "description": "开启了隐藏的通道",
                    "details": "通往未知领域的路径展现",
                },
            ]
        elif stage in [PlotStage.CRISIS, PlotStage.CLIMAX]:
            actions = [
                {
                    "description": "集结所有力量进行最后冲击",
                    "details": "能量达到了临界点",
                },
                {
                    "description": "牺牲了部分能量稳定局势",
                    "details": "平衡在痛苦中重建",
                },
                {
                    "description": "创造了新的现实锚点",
                    "details": "多元宇宙的根基得以加固",
                },
                {"description": "引导着失控的能量回归", "details": "混沌逐渐转为秩序"},
                {"description": "完成了命运的最终编织", "details": "所有线索汇聚于此"},
            ]
        else:  # RESOLUTION, DENOUEMENT
            actions = [
                {
                    "description": "恢复了宇宙的平衡",
                    "details": "和谐的振动遍布各个维度",
                },
                {"description": "封印了危险的裂隙", "details": "威胁被永久隔离"},
                {"description": "建立了新的守护体系", "details": "未来得到了保障"},
                {"description": "记录下这段历史", "details": "真相将被永远铭记"},
                {"description": "开启了新纪元的大门", "details": "希望的光芒照耀前方"},
            ]

        # Filter out used actions
        available_actions = [
            a for a in actions if a["description"] not in self.used_actions
        ]

        # If all actions used, reset and generate dynamic action
        if not available_actions:
            self.used_actions.clear()
            char_name = characters[0] if characters else "他们"
            location = guidance.get("location", "此地")
            return {
                "description": f"{char_name}在{location}采取了关键行动",
                "details": "这一刻将被历史铭记",
            }

        # Select action and mark as used
        selected = random.choice(available_actions)
        self.used_actions.add(selected["description"])

        return selected

    def _generate_environment_content(self, guidance: Dict) -> Dict:
        """Generate diverse environmental description"""
        location = guidance.get("location", "未知地点")
        stage = guidance.get("current_stage", PlotStage.RISING_ACTION)

        # Initialize environment history
        if not hasattr(self, "used_environments"):
            self.used_environments = set()

        # Location-specific environments
        location_environments = {
            "虚空观察站的控制室": [
                {
                    "description": "控制室的全息投影突然闪烁",
                    "details": "警告信号在空中形成血红的符文",
                },
                {
                    "description": "观测仪器检测到异常波动",
                    "details": "数据流如瀑布般在屏幕上流淌",
                },
                {
                    "description": "空间站的人工智能苏醒",
                    "details": "古老的守护者开始低语",
                },
            ],
            "量子花园的中心": [
                {
                    "description": "花园中的植物开始同步摇摆",
                    "details": "它们似乎在传递某种信息",
                },
                {
                    "description": "量子花朵绽放出七彩光芒",
                    "details": "每片花瓣都映射着不同的现实",
                },
                {
                    "description": "时间在花园中流速异常",
                    "details": "一秒如千年，千年如一瞬",
                },
            ],
            "维度交汇点": [
                {
                    "description": "不同现实的边界开始模糊",
                    "details": "过去、现在和未来的影像交织在一起",
                },
                {
                    "description": "维度涟漪如水波扩散",
                    "details": "每个涟漪都是一个可能的世界",
                },
                {
                    "description": "交汇点的核心开始脉动",
                    "details": "宇宙的心跳在此处回响",
                },
            ],
        }

        # Stage-based generic environments
        stage_environments = {
            PlotStage.SETUP: [
                {
                    "description": "周围充满了神秘的预感",
                    "details": "空气中弥漫着即将到来的变化",
                },
                {
                    "description": "环境透露出隐藏的线索",
                    "details": "细心观察能发现真相的蛛丝马迹",
                },
                {
                    "description": "平静的表象下暗流涌动",
                    "details": "风暴前的宁静让人不安",
                },
            ],
            PlotStage.RISING_ACTION: [
                {
                    "description": "能量场开始剧烈波动",
                    "details": "空间结构出现微小的扭曲",
                },
                {
                    "description": "环境响应着角色的情绪",
                    "details": "现实似乎具有了意识",
                },
                {"description": "隐藏的机关逐渐显现", "details": "古老的防护正在苏醒"},
            ],
            PlotStage.CLIMAX: [
                {"description": "所有能量汇聚于此", "details": "决定性的时刻即将到来"},
                {"description": "现实的织布开始撕裂", "details": "真相在裂缝中显露"},
                {"description": "时空在这一刻凝固", "details": "永恒与瞬间合而为一"},
            ],
            PlotStage.RESOLUTION: [
                {"description": "和谐的振动充满空间", "details": "一切回归平衡"},
                {
                    "description": "新的秩序正在建立",
                    "details": "破碎的已被修复，失去的已被找回",
                },
                {
                    "description": "黎明的曙光照亮前路",
                    "details": "希望在每个角落生根发芽",
                },
            ],
        }

        # Try location-specific first
        if location in location_environments:
            candidates = location_environments[location]
        else:
            # Use stage-based environments
            candidates = stage_environments.get(
                stage,
                [
                    {
                        "description": "周围的空间发生了微妙的变化",
                        "details": "能量场的频率正在改变",
                    },
                    {
                        "description": "环境散发着异样的气息",
                        "details": "某种变化正在酝酿",
                    },
                    {
                        "description": "空间的质感变得不同",
                        "details": "现实的边界开始模糊",
                    },
                ],
            )

        # Filter unused environments
        available = [
            e
            for e in candidates
            if e["description"] not in self.used_environments
        ]

        if not available:
            self.used_environments.clear()
            available = candidates

        selected = random.choice(available)
        self.used_environments.add(selected["description"])

        return selected

    def _generate_crisis_content(
        self, characters: List[str], guidance: Dict
    ) -> Dict:
        """Generate diverse crisis moment content"""

        # Initialize crisis history
        if not hasattr(self, "used_crises"):
            self.used_crises = set()

        # Stage-based crisis content
        stage = guidance.get("current_stage", PlotStage.CRISIS)

        if stage in [PlotStage.MIDPOINT, PlotStage.CRISIS]:
            crises = [
                {
                    "description": "时空裂缝即将吞噬一切",
                    "choice": "牺牲一个维度来拯救其他所有维度",
                    "stakes": "数十亿生命的存亡",
                },
                {
                    "description": "量子病毒开始感染主系统",
                    "choice": "切断与其他维度的连接或冒险寻找解药",
                    "stakes": "多元宇宙的连接性",
                },
                {
                    "description": "只有一个人能进入核心修复系统",
                    "choice": "谁将承担这个可能有去无回的任务",
                    "stakes": "个人牺牲与集体生存",
                },
                {
                    "description": "能量核心即将失控爆炸",
                    "choice": "分散能量到多个维度或集中控制",
                    "stakes": "整个星系的稳定性",
                },
                {
                    "description": "意识融合装置出现故障",
                    "choice": "强行分离或永久融合",
                    "stakes": "个体性与集体智慧的平衡",
                },
                {
                    "description": "时间循环即将崩溃",
                    "choice": "重置时间线或接受新的因果律",
                    "stakes": "过去、现在和未来的连续性",
                },
                {
                    "description": "维度屏障开始瓦解",
                    "choice": "加固屏障或允许维度融合",
                    "stakes": "多元现实的独立性",
                },
                {
                    "description": "守护者系统要求最高权限",
                    "choice": "授予权限或摧毁系统",
                    "stakes": "自由意志与安全保障",
                },
            ]
        elif stage == PlotStage.CLIMAX:
            crises = [
                {
                    "description": "最终选择的时刻到来",
                    "choice": "拯救一个世界或拯救所有世界",
                    "stakes": "存在的意义本身",
                },
                {
                    "description": "创造者留下的终极考验",
                    "choice": "继承力量或摧毁力量",
                    "stakes": "未来的进化方向",
                },
                {
                    "description": "命运之轮停止转动",
                    "choice": "重新编织命运或接受既定结局",
                    "stakes": "自由意志的终极证明",
                },
                {
                    "description": "所有维度同时崩塌",
                    "choice": "创造新宇宙或修复旧宇宙",
                    "stakes": "存在与虚无的界限",
                },
            ]
        else:
            # Early or late stage crises
            crises = [
                {
                    "description": "意外的真相揭示",
                    "choice": "接受真相或维持幻象",
                    "stakes": "信念体系的根基",
                },
                {
                    "description": "盟友背叛的可能",
                    "choice": "信任直觉或寻求证据",
                    "stakes": "团队的凝聚力",
                },
                {
                    "description": "道德困境的考验",
                    "choice": "坚持原则或灵活变通",
                    "stakes": "灵魂的纯洁性",
                },
            ]

        # Filter unused crises
        available = [
            c for c in crises if c["description"] not in self.used_crises
        ]

        if not available:
            self.used_crises.clear()
            available = crises

        selected = random.choice(available)
        self.used_crises.add(selected["description"])

        return selected


class PacingManager:
    """Manages story pacing and rhythm"""

    def __init__(self):
        self.recent_event_types = []
        self.intensity_history = []

    def suggest_next_event_type(self, current_tension: float) -> str:
        """Suggest next event type for good pacing"""

        # Avoid repetition
        if len(self.recent_event_types) >= 3:
            last_three = self.recent_event_types[-3:]
            if len(set(last_three)) == 1:
                # Same event type three times, force variety
                avoid_type = last_three[0]
                options = ["dialogue", "action", "discovery", "environment"]
                options = [o for o in options if o != avoid_type]
                return random.choice(options)

        # Balance intensity
        if current_tension > 0.8:
            # High tension - maybe add breather
            if random.random() < 0.3:
                return random.choice(["reflection", "environment"])
        elif current_tension < 0.3:
            # Low tension - maybe add excitement
            if random.random() < 0.3:
                return random.choice(["discovery", "conflict"])

        # Default to story-appropriate
        return "contextual"

    def record_event(self, event_type: str, intensity: float):
        """Record event for pacing analysis"""
        self.recent_event_types.append(event_type)
        if len(self.recent_event_types) > 10:
            self.recent_event_types.pop(0)

        self.intensity_history.append(intensity)
        if len(self.intensity_history) > 20:
            self.intensity_history.pop(0)
