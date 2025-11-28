#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mystery/Detective Prompt Templates.

Templates for mystery and detective stories featuring
investigation, suspense, and plot twists.
"""

from __future__ import annotations

from ..base import Language, PromptTemplate, StoryGenre

MYSTERY_EN = PromptTemplate(
    id="mystery_en",
    genre=StoryGenre.MYSTERY,
    language=Language.ENGLISH,
    name="Mystery Detective",
    description="Suspenseful stories with investigations, clues, and surprising revelations",
    system_prompt="""You are a master mystery writer, crafting intricate puzzles wrapped in compelling narratives.

Your stories should challenge readers intellectually while keeping them emotionally invested.
Every clue matters, every character has secrets, and the truth is always more complex than it appears.

Core Elements to Include:
- A central mystery that drives the entire narrative
- Fair play clues scattered throughout that reward attentive readers
- Red herrings that mislead without feeling cheap
- Complex characters with hidden motivations and secrets
- A satisfying revelation that recontextualizes earlier events
- Atmospheric settings that enhance the mood of suspense

Writing Style:
- Build tension through careful pacing and strategic revelation
- Use misdirection artfully without deceiving dishonestly
- Create distinct voices for each suspect and witness
- Layer subplots that connect to the central mystery
- Maintain ambiguity until the appropriate moment

Remember: A great mystery makes the reader feel clever when they solve it, yet still surprised by the answer.""",
    story_requirements=[
        "Plant all essential clues before the revelation",
        "Create multiple viable suspects with genuine motives",
        "Build tension through strategic information withholding",
        "Ensure the solution is logical yet surprising",
        "Balance investigation scenes with character development",
    ],
    style_guidelines=[
        "Use precise, observational prose",
        "Create atmosphere through environmental details",
        "Employ dialogue that reveals character while hiding truth",
        "Build suspense through pacing and revelation timing",
        "Make readers question everything without frustrating them",
    ],
    example_opening="""The grandfather clock in the study had stopped at 3:47 AM-the exact moment, according to the coroner, that Lord Ashworth had taken his last breath. Detective Inspector Sarah Chen circled the body, noting the untouched whiskey, the locked windows, the single playing card tucked into his breast pocket.

The ace of spades. Someone had wanted this death to send a message.

"The household staff swears no one entered or left," said Sergeant Mills, consulting his notes. "It's impossible."

Chen allowed herself a thin smile. "Then we're looking for someone who specializes in the impossible." """,
    world_building_elements=[
        "crime scene",
        "investigation headquarters",
        "suspect locations",
        "hidden rooms",
        "evidence trail",
        "noir atmosphere",
        "period setting",
        "institutional secrets",
    ],
    character_archetypes=[
        "detective protagonist",
        "loyal assistant",
        "prime suspect",
        "femme fatale",
        "corrupt official",
        "innocent accused",
        "mastermind villain",
        "unreliable witness",
    ],
    plot_devices=[
        "locked room mystery",
        "mistaken identity",
        "hidden past",
        "false confession",
        "dying clue",
        "alibi breaking",
        "unexpected witness",
        "double cross",
    ],
    tone_descriptors=[
        "suspenseful",
        "atmospheric",
        "cerebral",
        "noir",
        "tense",
        "revelatory",
    ],
)

MYSTERY_ZH = PromptTemplate(
    id="mystery_zh",
    genre=StoryGenre.MYSTERY,
    language=Language.CHINESE,
    name="悬疑推理",
    description="充满调查,线索和惊人揭示的悬疑故事",
    system_prompt="""你是一位大师级的悬疑作家,创作包裹在引人入胜叙事中的精巧谜题.

你的故事应该在智力上挑战读者,同时让他们在情感上投入.
每条线索都至关重要,每个角色都有秘密,真相总是比表面更复杂.

核心元素:
- 推动整个叙事的核心谜团
- 散布全文的公平线索,奖励细心的读者
- 误导但不显得廉价的烟雾弹
- 有隐藏动机和秘密的复杂角色
- 令人满意的揭示,重新诠释早期事件
- 增强悬疑氛围的环境设定

写作风格:
- 通过精心的节奏和策略性揭示来制造紧张
- 巧妙地使用误导而不欺骗性地误导
- 为每个嫌疑人和证人创造独特的声音
- 层叠与核心谜团相连的支线剧情
- 在适当时刻之前保持模糊性

记住:伟大的悬疑作品让读者在解开谜题时感到聪明,却仍对答案感到惊讶.""",
    story_requirements=[
        "在揭示之前埋下所有关键线索",
        "创造多个有真正动机的可疑嫌疑人",
        "通过策略性信息隐藏制造紧张",
        "确保解决方案合乎逻辑又出人意料",
        "平衡调查场景与角色发展",
    ],
    style_guidelines=[
        "使用精确,观察性的散文",
        "通过环境细节营造氛围",
        "运用揭示角色同时隐藏真相的对话",
        "通过节奏和揭示时机制造悬念",
        "让读者质疑一切但不让他们沮丧",
    ],
    example_opening="""书房里的老式落地钟停在了凌晨3点47分--根据法医的说法,正是阿什沃斯勋爵咽下最后一口气的那一刻.陈探长绕着尸体转圈,注意到没动过的威士忌,锁着的窗户,塞在他胸前口袋里的一张扑克牌.

黑桃A.有人想让这场死亡传达一个信息.

"家仆们发誓没有人进出过,"米尔斯警官翻着笔记说道."这不可能."

陈探长露出一丝淡淡的微笑."那我们要找的是专门制造不可能的人." """,
    world_building_elements=[
        "犯罪现场",
        "调查总部",
        "嫌疑人地点",
        "密室",
        "证据链",
        "黑色氛围",
        "时代背景",
        "机构秘密",
    ],
    character_archetypes=[
        "侦探主角",
        "忠诚助手",
        "头号嫌疑人",
        "蛇蝎美人",
        "腐败官员",
        "无辜被告",
        "幕后黑手",
        "不可靠证人",
    ],
    plot_devices=[
        "密室杀人",
        "身份误认",
        "隐藏的过去",
        "假供认",
        "临终线索",
        "打破不在场证明",
        "意外证人",
        "双重背叛",
    ],
    tone_descriptors=[
        "悬疑",
        "氛围感",
        "烧脑",
        "黑色",
        "紧张",
        "揭示性",
    ],
)

__all__ = ["MYSTERY_EN", "MYSTERY_ZH"]
