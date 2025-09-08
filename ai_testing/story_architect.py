#!/usr/bin/env python3
"""
Story Architect - Intelligent Story Structure Generator
Designs complete story blueprints with proper dramatic structure
"""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class PlotStage(Enum):
    """Story progression stages following three-act structure"""

    SETUP = "setup"
    INCITING_INCIDENT = "inciting_incident"
    RISING_ACTION = "rising_action"
    MIDPOINT = "midpoint"
    CRISIS = "crisis"
    CLIMAX = "climax"
    RESOLUTION = "resolution"
    DENOUEMENT = "denouement"


class ConflictType(Enum):
    """Types of narrative conflict"""

    CHARACTER_VS_CHARACTER = "character_vs_character"
    CHARACTER_VS_SELF = "character_vs_self"
    CHARACTER_VS_NATURE = "character_vs_nature"
    CHARACTER_VS_SOCIETY = "character_vs_society"
    CHARACTER_VS_TECHNOLOGY = "character_vs_technology"
    CHARACTER_VS_FATE = "character_vs_fate"


@dataclass
class PlotPoint:
    """Single plot point in the story"""

    stage: PlotStage
    description: str
    tension_level: float  # 0.0 to 1.0
    required_characters: List[str]
    location: Optional[str] = None
    conflict_type: Optional[ConflictType] = None


@dataclass
class CharacterArc:
    """Character development trajectory"""

    character_name: str
    initial_state: str
    transformation: str
    final_state: str
    key_moments: List[PlotStage]
    relationships: Dict[str, str] = field(default_factory=dict)


@dataclass
class StoryBlueprint:
    """Complete story structure blueprint"""

    theme: str
    central_conflict: str
    plot_points: List[PlotPoint]
    character_arcs: List[CharacterArc]
    tension_curve: List[float]
    target_length: int  # in events

    def get_current_tension(self, progress: float) -> float:
        """Get tension level based on story progress"""
        index = int(progress * len(self.tension_curve))
        if index >= len(self.tension_curve):
            index = len(self.tension_curve) - 1
        return self.tension_curve[index]


class StoryArchitect:
    """Intelligent story structure designer"""

    def __init__(self):
        self.themes = [
            "统一与分裂的平衡",
            "个体意识与集体智慧",
            "选择的重量与命运的必然",
            "时间的循环与线性",
            "现实的多重性与唯一性",
        ]

        self.conflicts = [
            "时空连续体即将崩塌，需要三人合力修复",
            "一个能毁灭所有维度的实体正在觉醒",
            "平行宇宙开始融合，造成现实混乱",
            "时间循环困住了整个宇宙，必须打破",
            "意识病毒正在感染所有维度的生命",
        ]

    def design_story_structure(
        self, characters: List, target_length: int = 50
    ) -> StoryBlueprint:
        """Design complete story structure with proper dramatic arc"""

        theme = random.choice(self.themes)
        central_conflict = random.choice(self.conflicts)

        # Create plot points following three-act structure
        plot_points = self._create_plot_points(characters)

        # Design character arcs
        character_arcs = self._design_character_arcs(characters)

        # Generate tension curve
        tension_curve = self._generate_tension_curve(len(plot_points))

        return StoryBlueprint(
            theme=theme,
            central_conflict=central_conflict,
            plot_points=plot_points,
            character_arcs=character_arcs,
            tension_curve=tension_curve,
            target_length=target_length,
        )

    def _create_plot_points(self, characters: List) -> List[PlotPoint]:
        """Create plot points with proper story structure"""
        char_names = [c.name if hasattr(c, "name") else str(c) for c in characters]

        plot_points = [
            # Act 1 - Setup (25%)
            PlotPoint(
                stage=PlotStage.SETUP,
                description="三位主角在虚空观察站相遇，感受到异常的能量波动",
                tension_level=0.2,
                required_characters=char_names,
                location="虚空观察站的控制室",
            ),
            PlotPoint(
                stage=PlotStage.INCITING_INCIDENT,
                description="发现时空裂缝正在扩大，威胁到所有维度的稳定",
                tension_level=0.4,
                required_characters=char_names[:2],
                conflict_type=ConflictType.CHARACTER_VS_NATURE,
            ),
            # Act 2 - Confrontation (50%)
            PlotPoint(
                stage=PlotStage.RISING_ACTION,
                description="寻找古老的量子密钥，遭遇来自其他维度的阻力",
                tension_level=0.5,
                required_characters=char_names,
                location="记忆图书馆",
                conflict_type=ConflictType.CHARACTER_VS_TECHNOLOGY,
            ),
            PlotPoint(
                stage=PlotStage.MIDPOINT,
                description="发现其中一人与危机有神秘联系，信任开始动摇",
                tension_level=0.6,
                required_characters=char_names,
                conflict_type=ConflictType.CHARACTER_VS_CHARACTER,
            ),
            PlotPoint(
                stage=PlotStage.CRISIS,
                description="必须在拯救单一维度和保护所有现实之间做出选择",
                tension_level=0.8,
                required_characters=char_names,
                location="维度交汇点",
                conflict_type=ConflictType.CHARACTER_VS_FATE,
            ),
            # Act 3 - Resolution (25%)
            PlotPoint(
                stage=PlotStage.CLIMAX,
                description="三人合力，通过牺牲个体意识来修复时空裂缝",
                tension_level=0.9,
                required_characters=char_names,
                conflict_type=ConflictType.CHARACTER_VS_SELF,
            ),
            PlotPoint(
                stage=PlotStage.RESOLUTION,
                description="时空恢复稳定，但三人的联系永远改变了多元宇宙",
                tension_level=0.4,
                required_characters=char_names,
            ),
            PlotPoint(
                stage=PlotStage.DENOUEMENT,
                description="各自回到自己的维度，但保持着量子纠缠的联系",
                tension_level=0.2,
                required_characters=char_names,
            ),
        ]

        return plot_points

    def _design_character_arcs(self, characters: List) -> List[CharacterArc]:
        """Design character development arcs"""
        arcs = []

        arc_templates = [
            {
                "initial": "孤独的探索者",
                "transformation": "学会信任与合作",
                "final": "连接的守护者",
            },
            {
                "initial": "理性的分析者",
                "transformation": "接受直觉与情感",
                "final": "平衡的智者",
            },
            {
                "initial": "充满疑虑的旁观者",
                "transformation": "承担责任与使命",
                "final": "坚定的行动者",
            },
        ]

        for i, character in enumerate(characters[:3]):
            template = arc_templates[i % len(arc_templates)]
            name = character.name if hasattr(character, "name") else f"Character_{i}"

            arc = CharacterArc(
                character_name=name,
                initial_state=template["initial"],
                transformation=template["transformation"],
                final_state=template["final"],
                key_moments=[
                    PlotStage.INCITING_INCIDENT,
                    PlotStage.MIDPOINT,
                    PlotStage.CLIMAX,
                ],
            )
            arcs.append(arc)

        # Add relationships
        if len(arcs) >= 2:
            arcs[0].relationships[arcs[1].character_name] = "从怀疑到信任"
            arcs[1].relationships[arcs[0].character_name] = "从冷漠到关心"

        if len(arcs) >= 3:
            arcs[0].relationships[arcs[2].character_name] = "发现共同使命"
            arcs[2].relationships[arcs[0].character_name] = "找到精神导师"

        return arcs

    def _generate_tension_curve(self, num_points: int) -> List[float]:
        """Generate dramatic tension curve"""
        # Classic three-act tension curve
        curve = []

        # Act 1: Gradual buildup
        for i in range(num_points // 4):
            curve.append(0.2 + (0.3 * i / (num_points // 4)))

        # Act 2: Rising tension with minor peaks and valleys
        for i in range(num_points // 2):
            base = 0.5 + (0.3 * i / (num_points // 2))
            variation = random.uniform(-0.1, 0.1)
            curve.append(min(0.9, max(0.3, base + variation)))

        # Act 3: Climax and resolution
        curve.append(0.95)  # Climax peak
        curve.append(0.9)

        # Falling action
        remaining = num_points - len(curve)
        for i in range(remaining):
            curve.append(0.9 - (0.7 * (i + 1) / remaining))

        return curve

    def get_plot_guidance(self, blueprint: StoryBlueprint, current_event: int) -> Dict:
        """Get guidance for next event based on story structure"""
        progress = current_event / blueprint.target_length

        # Find current plot stage
        stage_progress = progress * len(blueprint.plot_points)
        current_stage_index = min(int(stage_progress), len(blueprint.plot_points) - 1)
        current_plot_point = blueprint.plot_points[current_stage_index]

        # Get current tension
        tension = blueprint.get_current_tension(progress)

        # Determine needed action type based on stage and tension
        if tension > 0.7:
            suggested_events = ["conflict", "revelation", "decision"]
        elif tension > 0.4:
            suggested_events = ["discovery", "challenge", "dialogue"]
        else:
            suggested_events = ["exploration", "reflection", "worldbuilding"]

        return {
            "current_stage": current_plot_point.stage.value,
            "plot_description": current_plot_point.description,
            "tension_level": tension,
            "suggested_events": suggested_events,
            "required_characters": current_plot_point.required_characters,
            "location": current_plot_point.location,
        }
