#!/usr/bin/env python3
"""
Context-Aware Dialogue Engine with Memory and Character Voice Differentiation
"""

import hashlib
import random
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple


@dataclass
class DialogueMemory:
    """Tracks dialogue history to prevent repetition"""

    said_phrases: Set[str] = field(default_factory=set)
    recent_topics: deque = field(default_factory=lambda: deque(maxlen=10))
    character_last_words: Dict[str, List[str]] = field(default_factory=dict)
    emotional_journey: Dict[str, List[str]] = field(default_factory=dict)
    topic_exhaustion: Dict[str, int] = field(default_factory=dict)

    def has_been_said(self, phrase: str) -> bool:
        """Check if exact phrase was already used"""
        phrase_hash = hashlib.md5(phrase.encode()).hexdigest()
        return phrase_hash in self.said_phrases

    def add_dialogue(self, character: str, phrase: str, topic: str = None):
        """Record a dialogue line"""
        phrase_hash = hashlib.md5(phrase.encode()).hexdigest()
        self.said_phrases.add(phrase_hash)

        if character not in self.character_last_words:
            self.character_last_words[character] = []
        self.character_last_words[character].append(phrase)
        if len(self.character_last_words[character]) > 5:
            self.character_last_words[character].pop(0)

        if topic:
            self.recent_topics.append(topic)
            self.topic_exhaustion[topic] = (
                self.topic_exhaustion.get(topic, 0) + 1
            )

    def get_unexplored_topic(self, available_topics: List[str]) -> str:
        """Get a topic that hasn't been overused"""
        topic_scores = {}
        for topic in available_topics:
            exhaustion = self.topic_exhaustion.get(topic, 0)
            recency = 0
            for i, recent in enumerate(self.recent_topics):
                if recent == topic:
                    recency += 10 - i  # More recent = higher penalty

            score = 100 - (exhaustion * 20) - (recency * 5)
            topic_scores[topic] = max(0, score)

        # Weighted random selection
        if not topic_scores:
            return random.choice(available_topics)

        topics = list(topic_scores.keys())
        weights = list(topic_scores.values())
        total = sum(weights)
        if total == 0:
            return random.choice(topics)

        weights = [w / total for w in weights]
        return random.choices(topics, weights=weights)[0]


class CharacterVoice:
    """Unique voice generator for each character"""

    def __init__(self, name: str, personality: List[str], speech_style: str):
        self.name = name
        self.personality = personality
        self.speech_style = speech_style
        self.vocabulary = self._build_vocabulary()
        self.speech_patterns = self._build_patterns()
        self.emotional_modifiers = self._build_emotional_modifiers()

    def _build_vocabulary(self) -> Dict[str, List[str]]:
        """Build character-specific vocabulary"""
        base_vocab = {
            "philosophical": {
                "understanding": ["明悟", "领悟", "洞察", "觉察"],
                "reality": ["现实", "实相", "真相", "本质"],
                "connection": ["联结", "纠缠", "共鸣", "呼应"],
                "time": ["时间", "时空", "永恒", "瞬间"],
            },
            "analytical": {
                "understanding": ["分析", "推断", "计算", "评估"],
                "reality": ["数据", "参数", "模型", "系统"],
                "connection": ["关联", "接口", "链接", "网络"],
                "time": ["时间线", "时序", "周期", "节点"],
            },
            "emotional": {
                "understanding": ["感受", "体会", "感知", "直觉"],
                "reality": ["世界", "存在", "生命", "意义"],
                "connection": ["缘分", "羁绊", "心灵", "灵魂"],
                "time": ["此刻", "当下", "记忆", "未来"],
            },
            "curious": {
                "understanding": ["发现", "探索", "寻找", "揭示"],
                "reality": ["奥秘", "谜题", "未知", "可能"],
                "connection": ["相遇", "交汇", "融合", "碰撞"],
                "time": ["旅程", "冒险", "历程", "轨迹"],
            },
        }

        # Select vocabulary based on personality
        vocab = {}
        for trait in self.personality:
            if trait in base_vocab:
                vocab.update(base_vocab[trait])

        if not vocab:  # Default if no match
            vocab = base_vocab["philosophical"]

        return vocab

    def _build_patterns(self) -> List[str]:
        """Build character-specific speech patterns"""
        patterns_map = {
            "philosophical": [
                "在{concept}的深处，我看到了{understanding}",
                "如果{reality}只是{illusion}，那么{truth}在哪里？",
                "{time}与{space}的交织点上，{revelation}正在显现",
            ],
            "analytical": [
                "根据我的计算，{probability}的概率是{percentage}%",
                "数据显示，{pattern}正在{action}",
                "逻辑推断表明，{cause}导致了{effect}",
            ],
            "emotional": [
                "我能感受到{feeling}在{location}回荡",
                "这种{emotion}...它超越了{boundary}",
                "在{moment}，我的{heart}告诉我{truth}",
            ],
            "protective": [
                "我不会让{danger}伤害{target}",
                "守护{value}是我的{mission}",
                "无论{cost}，我都会{action}",
            ],
        }

        patterns = []
        for trait in self.personality:
            if trait in patterns_map:
                patterns.extend(patterns_map[trait])

        if not patterns:
            patterns = ["我认为{subject}是{description}"]

        return patterns

    def _build_emotional_modifiers(self) -> Dict[str, Dict[str, str]]:
        """Build emotional expression modifiers"""
        return {
            "contemplative": {
                "prefix": "沉思片刻后，",
                "suffix": "...这值得深思。",
                "tone": "缓慢而深沉",
            },
            "excited": {"prefix": "突然，", "suffix": "！", "tone": "急促而激动"},
            "worried": {
                "prefix": "有些不安地，",
                "suffix": "...我担心可能...",
                "tone": "犹豫而紧张",
            },
            "determined": {
                "prefix": "坚定地，",
                "suffix": "。没有退路了。",
                "tone": "果断而有力",
            },
            "curious": {
                "prefix": "好奇地，",
                "suffix": "...这是什么意思？",
                "tone": "探询而期待",
            },
        }

    def generate_dialogue(
        self, topic: str, emotion: str, context: Dict
    ) -> str:
        """Generate character-specific dialogue"""
        # Select appropriate vocabulary
        vocab_choice = random.choice(list(self.vocabulary.keys()))
        words = self.vocabulary.get(vocab_choice, ["默认"])

        # Build base content
        if random.random() < 0.4 and self.speech_patterns:
            # Use a speech pattern
            pattern = random.choice(self.speech_patterns)
            # Simple template filling (in real implementation, would be more sophisticated)
            dialogue = pattern
            for key in ["{concept}", "{understanding}", "{reality}", "{time}"]:
                if key in dialogue:
                    dialogue = dialogue.replace(key, random.choice(words))
        else:
            # Construct from vocabulary
            dialogue = self._construct_from_topic(topic, words, context)

        # Apply emotional modifiers
        if emotion in self.emotional_modifiers:
            mod = self.emotional_modifiers[emotion]
            if random.random() < 0.5:
                dialogue = mod["prefix"] + dialogue
            if random.random() < 0.3:
                dialogue = dialogue.rstrip("。.!！?？") + mod["suffix"]

        # Apply character-specific style
        dialogue = self._apply_style(dialogue)

        return dialogue

    def _construct_from_topic(
        self, topic: str, words: List[str], context: Dict
    ) -> str:
        """Construct dialogue from topic and vocabulary"""
        templates = {
            "discovery": [
                f"这个{random.choice(words)}揭示了新的可能性",
                f"我发现了关于{random.choice(words)}的真相",
                f"看，{random.choice(words)}正在改变",
            ],
            "conflict": [
                f"我们必须面对{random.choice(words)}的挑战",
                f"这个{random.choice(words)}威胁着一切",
                f"{random.choice(words)}正在崩塌",
            ],
            "resolution": [
                f"通过{random.choice(words)}，我们找到了答案",
                f"{random.choice(words)}指引着前进的道路",
                f"最终，{random.choice(words)}带来了平衡",
            ],
            "reflection": [
                f"在{random.choice(words)}中，我看到了自己",
                f"{random.choice(words)}让我明白了什么是重要的",
                f"也许{random.choice(words)}一直在我们心中",
            ],
        }

        if topic in templates:
            return random.choice(templates[topic])

        return f"关于{random.choice(words)}，我有了新的理解"

    def _apply_style(self, dialogue: str) -> str:
        """Apply character-specific speaking style"""
        if "诗意" in self.speech_style:
            # Add poetic elements
            if random.random() < 0.3:
                dialogue = "..." + dialogue + "..."
        elif "理性" in self.speech_style:
            # Add analytical elements
            if random.random() < 0.3:
                dialogue = f"准确地说，{dialogue}"
        elif "热情" in self.speech_style:
            # Add enthusiastic elements
            if random.random() < 0.3:
                dialogue = dialogue.replace("。", "！")

        return dialogue


class ContextAwareDialogueEngine:
    """Main dialogue generation engine with context awareness"""

    def __init__(self):
        self.memory = DialogueMemory()
        self.character_voices: Dict[str, CharacterVoice] = {}
        self.plot_progress = 0.0
        self.current_tension = 0.0

    def register_character(
        self, name: str, personality: List[str], speech_style: str
    ):
        """Register a character with unique voice"""
        self.character_voices[name] = CharacterVoice(
            name, personality, speech_style
        )

    def generate_contextual_dialogue(
        self, character_name: str, plot_context: Dict, emotion: str = None
    ) -> Tuple[str, str]:
        """Generate dialogue that fits the current context"""

        if character_name not in self.character_voices:
            return "...", "neutral"

        voice = self.character_voices[character_name]

        # Determine topic from plot context
        suggested_events = plot_context.get("suggested_events", ["dialogue"])
        topic = self.memory.get_unexplored_topic(suggested_events)

        # Determine emotion based on tension if not specified
        if not emotion:
            tension = plot_context.get("tension_level", 0.5)
            if tension > 0.7:
                emotion = random.choice(["tense", "determined", "worried"])
            elif tension > 0.4:
                emotion = random.choice(
                    ["curious", "contemplative", "focused"]
                )
            else:
                emotion = random.choice(
                    ["contemplative", "hopeful", "peaceful"]
                )

        # Generate dialogue
        max_attempts = 5
        for _ in range(max_attempts):
            dialogue = voice.generate_dialogue(topic, emotion, plot_context)

            # Check for repetition
            if not self.memory.has_been_said(dialogue):
                self.memory.add_dialogue(character_name, dialogue, topic)
                return dialogue, emotion

        # Fallback if all attempts resulted in repetition
        fallback = f"这个{topic}的意义超出了言语..."
        self.memory.add_dialogue(character_name, fallback, topic)
        return fallback, emotion

    def generate_reaction(
        self,
        reactor_name: str,
        speaker_name: str,
        previous_dialogue: str,
        plot_context: Dict,
    ) -> str:
        """Generate contextual reaction to previous dialogue"""

        if reactor_name not in self.character_voices:
            return f"{reactor_name}若有所思地点了点头。"

        voice = self.character_voices[reactor_name]
        tension = plot_context.get("tension_level", 0.5)

        # Determine reaction type based on character relationship and tension
        if tension > 0.7:
            reactions = [
                f"紧张地握紧拳头，{reactor_name}感受到了压力",
                f"{reactor_name}的眼中闪过一丝担忧",
                f"深吸一口气，{reactor_name}准备面对即将到来的挑战",
            ]
        elif tension > 0.4:
            reactions = [
                f"{reactor_name}若有所思地看着{speaker_name}",
                f"微微点头，{reactor_name}似乎理解了什么",
                f"{reactor_name}的表情变得专注",
            ]
        else:
            reactions = [
                f"{reactor_name}露出了理解的微笑",
                f"平静地，{reactor_name}陷入沉思",
                f"{reactor_name}的眼中闪现出希望的光芒",
            ]

        # Add personality-specific reactions
        if "analytical" in voice.personality:
            reactions.append(f"{reactor_name}快速分析着听到的信息")
        elif "emotional" in voice.personality:
            reactions.append(f"{reactor_name}能感受到话语中的深层含义")
        elif "curious" in voice.personality:
            reactions.append(f"{reactor_name}露出了好奇的表情")

        return random.choice(reactions)
