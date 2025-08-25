#!/usr/bin/env python3
"""
AI Novel Generation System V2 - Enhanced with Story Architecture and Context Awareness
Complete rewrite with proper story structure, character voices, and quality control
"""

import asyncio
import json
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

# Import our new modules
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from story_architect import StoryArchitect, StoryBlueprint, PlotStage
from dialogue_engine import ContextAwareDialogueEngine, DialogueMemory
from event_orchestrator import DynamicEventOrchestrator

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Types of actions in the story"""
    DIALOGUE = "dialogue"
    ACTION = "action"
    THOUGHT = "thought"
    DESCRIPTION = "description"
    EMOTION = "emotion"
    SCENE_CHANGE = "scene_change"
    CONFLICT = "conflict"
    DISCOVERY = "discovery"
    CRISIS = "crisis"


@dataclass
class StoryEvent:
    """Enhanced story event with context"""
    timestamp: float
    character: str
    event_type: ActionType
    content: str
    emotion: Optional[str] = None
    location: Optional[str] = None
    plot_stage: Optional[PlotStage] = None
    tension_level: float = 0.5
    tags: List[str] = None
    
    def to_dict(self):
        data = asdict(self)
        data['event_type'] = self.event_type.value
        if self.plot_stage:
            data['plot_stage'] = self.plot_stage.value
        return data


@dataclass
class Character:
    """Enhanced character profile"""
    name: str
    personality: List[str]
    background: str
    motivation: str
    speech_style: str
    arc_description: Optional[str] = None
    relationships: Dict[str, str] = None


class EnhancedNovelGenerator:
    """Main novel generation system with all enhancements"""
    
    def __init__(self):
        self.story_architect = StoryArchitect()
        self.dialogue_engine = ContextAwareDialogueEngine()
        self.event_orchestrator = None  # Will be initialized with blueprint
        self.story_blueprint = None
        self.characters = []
        self.events = []
        self.scene_settings = [
            "虚空观察站的控制室",
            "量子花园的中心",
            "时间裂缝的边缘",
            "记忆图书馆",
            "星际议会大厅",
            "维度交汇点",
            "古老的神殿遗址"
        ]
    
    def create_characters(self) -> List[Character]:
        """Create enhanced characters with unique voices"""
        characters = [
            Character(
                name="量子诗人·墨羽",
                personality=["philosophical", "mysterious", "wise"],
                background="来自第七维度的意识体，能够感知所有可能性的分支",
                motivation="寻找能够统一所有现实的终极真理",
                speech_style="诗意而深邃，常用比喻和象征"
            ),
            Character(
                name="时空织者·凌风",
                personality=["analytical", "determined", "protective"],
                background="掌握时间编织技术的古老守护者",
                motivation="修复被撕裂的时空连续体",
                speech_style="理性而准确，偶尔流露情感"
            ),
            Character(
                name="虚空行者·星尘",
                personality=["curious", "brave", "emotional"],
                background="能在维度间自由穿梭的探索者",
                motivation="理解不同维度生命的本质联系",
                speech_style="充满好奇和热情，富有感染力"
            )
        ]
        
        # Register characters with dialogue engine
        for char in characters:
            self.dialogue_engine.register_character(
                char.name,
                char.personality,
                char.speech_style
            )
        
        self.characters = characters
        return characters
    
    def generate_story_blueprint(self, target_length: int = 60) -> StoryBlueprint:
        """Generate the story structure blueprint"""
        blueprint = self.story_architect.design_story_structure(
            self.characters,
            target_length
        )
        
        # Apply character arcs to characters
        for arc in blueprint.character_arcs:
            for char in self.characters:
                if char.name == arc.character_name:
                    char.arc_description = f"{arc.initial_state} → {arc.transformation} → {arc.final_state}"
                    char.relationships = arc.relationships
        
        self.story_blueprint = blueprint
        
        # Initialize event orchestrator
        self.event_orchestrator = DynamicEventOrchestrator(
            blueprint,
            self.dialogue_engine
        )
        
        return blueprint
    
    def generate_story_events(self) -> List[StoryEvent]:
        """Generate story events following the blueprint"""
        events = []
        current_location = random.choice(self.scene_settings)
        
        # Opening scene
        events.append(self._create_opening_scene(current_location))
        
        # Generate events following story structure
        for i in range(self.story_blueprint.target_length):
            # Get next event from orchestrator
            orchestrated_event = self.event_orchestrator.generate_next_event(
                self.characters,
                current_location
            )
            
            # Convert to StoryEvent
            story_event = self._convert_orchestrated_event(orchestrated_event, i)
            events.append(story_event)
            
            # Scene changes at major plot points
            if i > 0 and i % (self.story_blueprint.target_length // 4) == 0:
                new_location = self._select_appropriate_location(story_event.plot_stage)
                if new_location != current_location:
                    events.append(self._create_scene_transition(current_location, new_location))
                    current_location = new_location
            
            # Add reactions and thoughts for depth
            if story_event.event_type == ActionType.DIALOGUE and random.random() < 0.4:
                reaction_event = self._generate_reaction(story_event)
                if reaction_event:
                    events.append(reaction_event)
            
            if story_event.tension_level > 0.6 and random.random() < 0.3:
                thought_event = self._generate_thought(story_event)
                if thought_event:
                    events.append(thought_event)
        
        # Ending scene
        events.append(self._create_ending_scene())
        
        self.events = events
        return events
    
    def _create_opening_scene(self, location: str) -> StoryEvent:
        """Create opening scene event"""
        return StoryEvent(
            timestamp=time.time(),
            character="Narrator",
            event_type=ActionType.SCENE_CHANGE,
            content=location,
            location=location,
            plot_stage=PlotStage.SETUP,
            tension_level=0.2,
            tags=["opening"]
        )
    
    def _create_ending_scene(self) -> StoryEvent:
        """Create ending scene event"""
        return StoryEvent(
            timestamp=time.time(),
            character="Narrator",
            event_type=ActionType.DESCRIPTION,
            content="虚空观察站的灯光渐渐暗淡，但三位英雄的联系已经永远改变了多元宇宙的命运。",
            plot_stage=PlotStage.DENOUEMENT,
            tension_level=0.1,
            tags=["ending"]
        )
    
    def _convert_orchestrated_event(self, orchestrated: Dict, index: int) -> StoryEvent:
        """Convert orchestrated event to StoryEvent"""
        progress = index / self.story_blueprint.target_length
        plot_stage = self._get_current_plot_stage(progress)
        tension = self.story_blueprint.get_current_tension(progress)
        
        event_type_map = {
            "dialogue": ActionType.DIALOGUE,
            "conflict": ActionType.CONFLICT,
            "discovery": ActionType.DISCOVERY,
            "action": ActionType.ACTION,
            "environment": ActionType.DESCRIPTION,
            "crisis": ActionType.CRISIS
        }
        
        event_type = event_type_map.get(orchestrated["type"], ActionType.DIALOGUE)
        
        # Extract content based on type
        content = ""
        character = "Narrator"
        emotion = None
        
        if event_type == ActionType.DIALOGUE:
            content = orchestrated["content"].get("dialogue", "...")
            character = orchestrated["content"].get("speaker", "Unknown")
            emotion = orchestrated["content"].get("emotion")
        elif event_type == ActionType.CONFLICT:
            content = orchestrated["content"].get("description", "冲突发生")
            character = orchestrated["characters"][0] if orchestrated["characters"] else "Narrator"
        elif event_type == ActionType.DISCOVERY:
            content = orchestrated["content"].get("description", "发现了重要线索")
            character = orchestrated["characters"][0] if orchestrated["characters"] else "Narrator"
        elif event_type == ActionType.ACTION:
            content = orchestrated["content"].get("description", "采取行动")
            character = "Narrator"
        elif event_type == ActionType.CRISIS:
            content = orchestrated["content"].get("description", "危机时刻")
            character = "Narrator"
        else:
            content = orchestrated["content"].get("description", "...")
        
        return StoryEvent(
            timestamp=time.time(),
            character=character,
            event_type=event_type,
            content=content,
            emotion=emotion,
            location=orchestrated.get("location"),
            plot_stage=plot_stage,
            tension_level=tension,
            tags=[orchestrated["type"]]
        )
    
    def _get_current_plot_stage(self, progress: float) -> PlotStage:
        """Get current plot stage based on progress"""
        stage_index = min(
            int(progress * len(self.story_blueprint.plot_points)),
            len(self.story_blueprint.plot_points) - 1
        )
        return self.story_blueprint.plot_points[stage_index].stage
    
    def _select_appropriate_location(self, plot_stage: PlotStage) -> str:
        """Select location appropriate for plot stage"""
        location_map = {
            PlotStage.SETUP: ["虚空观察站的控制室", "量子花园的中心"],
            PlotStage.RISING_ACTION: ["记忆图书馆", "星际议会大厅"],
            PlotStage.CRISIS: ["时间裂缝的边缘", "维度交汇点"],
            PlotStage.CLIMAX: ["维度交汇点", "古老的神殿遗址"],
            PlotStage.RESOLUTION: ["虚空观察站的控制室", "量子花园的中心"]
        }
        
        options = location_map.get(plot_stage, self.scene_settings)
        return random.choice(options)
    
    def _create_scene_transition(self, old_location: str, new_location: str) -> StoryEvent:
        """Create scene transition event"""
        transitions = [
            f"空间扭曲，将众人从{old_location}传送到{new_location}",
            f"量子通道开启，连接{old_location}与{new_location}",
            f"时空裂缝闪现，{new_location}的景象浮现"
        ]
        
        return StoryEvent(
            timestamp=time.time(),
            character="Narrator",
            event_type=ActionType.SCENE_CHANGE,
            content=random.choice(transitions),
            location=new_location,
            tension_level=0.5,
            tags=["transition"]
        )
    
    def _generate_reaction(self, dialogue_event: StoryEvent) -> Optional[StoryEvent]:
        """Generate reaction to dialogue"""
        if not self.characters or dialogue_event.character == "Narrator":
            return None
        
        # Select reactor (not the speaker)
        possible_reactors = [c for c in self.characters if c.name != dialogue_event.character]
        if not possible_reactors:
            return None
        
        reactor = random.choice(possible_reactors)
        
        # Generate contextual reaction
        plot_context = {
            "tension_level": dialogue_event.tension_level,
            "stage": dialogue_event.plot_stage
        }
        
        reaction = self.dialogue_engine.generate_reaction(
            reactor.name,
            dialogue_event.character,
            dialogue_event.content,
            plot_context
        )
        
        return StoryEvent(
            timestamp=time.time(),
            character=reactor.name,
            event_type=ActionType.ACTION,
            content=reaction,
            location=dialogue_event.location,
            plot_stage=dialogue_event.plot_stage,
            tension_level=dialogue_event.tension_level,
            tags=["reaction"]
        )
    
    def _generate_thought(self, context_event: StoryEvent) -> Optional[StoryEvent]:
        """Generate internal thought based on context"""
        if not self.characters:
            return None
        
        thinker = random.choice(self.characters)
        
        # High tension thoughts
        if context_event.tension_level > 0.7:
            thoughts = [
                "这比预想的更加危险...",
                "时间不多了，必须做出选择",
                "我能感受到命运的重量"
            ]
        # Medium tension thoughts
        elif context_event.tension_level > 0.4:
            thoughts = [
                "线索开始汇聚成完整的图景",
                "也许答案一直在我们面前",
                "这种感觉...似曾相识"
            ]
        # Low tension thoughts
        else:
            thoughts = [
                "在宁静中，真理更加清晰",
                "每一步都在改变未来",
                "我们的相遇绝非偶然"
            ]
        
        return StoryEvent(
            timestamp=time.time(),
            character=thinker.name,
            event_type=ActionType.THOUGHT,
            content=random.choice(thoughts),
            emotion="contemplative",
            location=context_event.location,
            plot_stage=context_event.plot_stage,
            tension_level=context_event.tension_level,
            tags=["internal"]
        )


class ImprovedLiteraryWriter:
    """Enhanced literary writer with better narrative flow"""
    
    def __init__(self):
        self.chapter_count = 0
        
    def transform_to_novel(
        self, 
        events: List[StoryEvent], 
        characters: List[Character],
        blueprint: StoryBlueprint
    ) -> str:
        """Transform events into literary novel with story structure"""
        novel_parts = []
        
        # Title and theme
        novel_parts.append(self._generate_title(blueprint))
        
        # Prologue with theme introduction
        novel_parts.append(self._generate_prologue(characters, blueprint))
        
        # Group events by plot stages
        stage_events = self._group_events_by_stage(events)
        
        # Write chapters based on dramatic structure
        chapter_num = 1
        for stage, stage_event_list in stage_events.items():
            if stage_event_list:
                chapter = self._write_structured_chapter(
                    chapter_num,
                    stage,
                    stage_event_list,
                    characters,
                    blueprint
                )
                novel_parts.append(chapter)
                chapter_num += 1
        
        # Epilogue with theme resolution
        novel_parts.append(self._generate_epilogue(characters, blueprint))
        
        return "\n\n".join(novel_parts)
    
    def _generate_title(self, blueprint: StoryBlueprint) -> str:
        """Generate thematic title"""
        return f"《维度之间的回响》\n\n—— {blueprint.theme}"
    
    def _generate_prologue(self, characters: List[Character], blueprint: StoryBlueprint) -> str:
        """Generate thematic prologue"""
        prologue = "序章：命运的编织\n\n"
        prologue += f"在所有可能性的交汇点上，一个关于{blueprint.theme}的故事即将展开。\n\n"
        prologue += f"{blueprint.central_conflict}\n\n"
        
        for char in characters:
            prologue += f"{char.name}，{char.background}。"
            prologue += f"命运赋予了{char.arc_description}的使命。\n\n"
        
        prologue += "当量子涟漪将他们聚集在一起时，多元宇宙的命运悬于一线..."
        
        return prologue
    
    def _generate_epilogue(self, characters: List[Character], blueprint: StoryBlueprint) -> str:
        """Generate thematic epilogue"""
        epilogue = "尾声：永恒的共鸣\n\n"
        epilogue += f"关于{blueprint.theme}的真相终于显现。\n\n"
        
        for char in characters:
            epilogue += f"{char.name}完成了自己的蜕变，"
            if char.arc_description:
                epilogue += f"从{char.arc_description.split('→')[0]}成为了{char.arc_description.split('→')[-1]}。\n"
        
        epilogue += f"\n{blueprint.central_conflict}得到了解决，但这不是结束，而是新的开始。\n\n"
        epilogue += "在无限的可能性中，他们的故事将永远回响..."
        
        return epilogue
    
    def _group_events_by_stage(self, events: List[StoryEvent]) -> Dict[PlotStage, List[StoryEvent]]:
        """Group events by plot stage"""
        grouped = {}
        for event in events:
            if event.plot_stage:
                if event.plot_stage not in grouped:
                    grouped[event.plot_stage] = []
                grouped[event.plot_stage].append(event)
        return grouped
    
    def _write_structured_chapter(
        self,
        chapter_num: int,
        stage: PlotStage,
        events: List[StoryEvent],
        characters: List[Character],
        blueprint: StoryBlueprint
    ) -> str:
        """Write chapter with proper dramatic structure"""
        
        chapter_titles = {
            PlotStage.SETUP: "觉醒的预兆",
            PlotStage.INCITING_INCIDENT: "命运的召唤",
            PlotStage.RISING_ACTION: "交织的道路",
            PlotStage.MIDPOINT: "真相的一角",
            PlotStage.CRISIS: "抉择的时刻",
            PlotStage.CLIMAX: "最终的考验",
            PlotStage.RESOLUTION: "新的平衡",
            PlotStage.DENOUEMENT: "回响的开始"
        }
        
        title = chapter_titles.get(stage, f"第{chapter_num}章")
        chapter = f"第{chapter_num}章：{title}\n\n"
        
        # Add thematic introduction for chapter
        plot_point = next((p for p in blueprint.plot_points if p.stage == stage), None)
        if plot_point:
            chapter += f"【{plot_point.description}】\n\n"
        
        # Process events into narrative
        paragraph = []
        for event in events:
            narrative_text = self._convert_event_to_narrative(event, characters)
            if narrative_text:
                paragraph.append(narrative_text)
                
                # Create paragraphs at natural breaks
                if len(paragraph) >= 3 or event.event_type == ActionType.SCENE_CHANGE:
                    chapter += " ".join(paragraph) + "\n\n"
                    paragraph = []
        
        # Add remaining paragraph
        if paragraph:
            chapter += " ".join(paragraph) + "\n\n"
        
        return chapter
    
    def _convert_event_to_narrative(self, event: StoryEvent, characters: List[Character]) -> str:
        """Convert event to narrative text"""
        
        if event.event_type == ActionType.DIALOGUE:
            # Format dialogue with character voice
            emotion_desc = self._get_emotion_description(event.emotion)
            return f"「{event.content}」{event.character}{emotion_desc}。"
        
        elif event.event_type == ActionType.ACTION:
            return f"{event.character}{event.content}"
        
        elif event.event_type == ActionType.THOUGHT:
            return f"（{event.content}）{event.character}在内心深处明白。"
        
        elif event.event_type == ActionType.DESCRIPTION:
            return event.content
        
        elif event.event_type == ActionType.SCENE_CHANGE:
            return f"\n【{event.content}】\n"
        
        elif event.event_type == ActionType.CONFLICT:
            return f"紧张的氛围笼罩着众人。{event.content}"
        
        elif event.event_type == ActionType.DISCOVERY:
            return f"突然，{event.content}这个发现改变了一切。"
        
        elif event.event_type == ActionType.CRISIS:
            return f"危机时刻到来了。{event.content}每个人都感受到了选择的重量。"
        
        return event.content
    
    def _get_emotion_description(self, emotion: Optional[str]) -> str:
        """Get emotion description for dialogue"""
        if not emotion:
            return "说道"
        
        emotion_map = {
            "contemplative": "沉思着说",
            "determined": "坚定地说",
            "curious": "好奇地问",
            "worried": "担忧地说",
            "excited": "激动地说",
            "tense": "紧张地说",
            "hopeful": "充满希望地说"
        }
        
        return emotion_map.get(emotion, "说道")


async def generate_enhanced_novel():
    """Generate novel with all enhancements"""
    print("=" * 80)
    print("📚 ENHANCED AI NOVEL GENERATION SYSTEM V2")
    print("=" * 80)
    print()
    
    # Initialize generator
    generator = EnhancedNovelGenerator()
    
    # Create characters
    print("🎭 Creating characters with unique voices...")
    characters = generator.create_characters()
    
    # Generate story blueprint
    print("📐 Designing story structure...")
    blueprint = generator.generate_story_blueprint(target_length=60)
    print(f"  Theme: {blueprint.theme}")
    print(f"  Central Conflict: {blueprint.central_conflict}")
    
    # Generate events
    print("🎬 Generating story events...")
    events = generator.generate_story_events()
    print(f"  Generated {len(events)} events")
    
    # Transform to novel
    print("✍️ Writing literary novel...")
    writer = ImprovedLiteraryWriter()
    novel = writer.transform_to_novel(events, characters, blueprint)
    
    # Save outputs
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save novel
    novel_path = Path(f"ai_testing/reports/enhanced_novel_{timestamp}.txt")
    novel_path.parent.mkdir(parents=True, exist_ok=True)
    novel_path.write_text(novel, encoding='utf-8')
    
    # Save data
    data = {
        "timestamp": datetime.now().isoformat(),
        "blueprint": {
            "theme": blueprint.theme,
            "central_conflict": blueprint.central_conflict,
            "plot_points": [
                {
                    "stage": p.stage.value,
                    "description": p.description,
                    "tension": p.tension_level
                }
                for p in blueprint.plot_points
            ]
        },
        "characters": [asdict(c) for c in characters],
        "events": [e.to_dict() for e in events],
        "statistics": {
            "total_events": len(events),
            "unique_dialogues": len(generator.dialogue_engine.memory.said_phrases),
            "plot_stages_covered": len(set(e.plot_stage for e in events if e.plot_stage)),
            "average_tension": sum(e.tension_level for e in events) / len(events)
        }
    }
    
    json_path = Path(f"ai_testing/reports/enhanced_data_{timestamp}.json")
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    
    # Display results
    print()
    print("=" * 80)
    print("📊 GENERATION COMPLETE")
    print("=" * 80)
    print(f"📖 Novel Length: {len(novel)} characters")
    print(f"📝 Unique Dialogues: {len(generator.dialogue_engine.memory.said_phrases)}")
    print(f"🎭 Character Arcs Completed: {len([c for c in characters if c.arc_description])}")
    print(f"📈 Average Tension: {data['statistics']['average_tension']:.2f}")
    print()
    print(f"✅ Novel saved to: {novel_path}")
    print(f"📊 Data saved to: {json_path}")
    
    return novel, data


if __name__ == "__main__":
    print("🚀 Starting Enhanced Novel Generation System V2...")
    novel, data = asyncio.run(generate_enhanced_novel())
    print("✅ Generation complete!")