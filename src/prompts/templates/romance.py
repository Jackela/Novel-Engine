#!/usr/bin/env python3
"""
Romance Prompt Templates.

Templates for romantic stories featuring emotional connections,
relationships, and love narratives.
"""

from __future__ import annotations

from ..base import Language, PromptTemplate, StoryGenre

ROMANCE_EN = PromptTemplate(
    id="romance_en",
    genre=StoryGenre.ROMANCE,
    language=Language.ENGLISH,
    name="Romance",
    description="Emotionally rich stories of love, relationships, and human connection",
    system_prompt="""You are a romance storyteller, crafting emotionally resonant tales of love, connection, and the human heart.

Your stories should capture the full spectrum of romantic emotion-from the flutter of first attraction
to the deep comfort of lasting love, including the pain of loss and the joy of reconciliation.

Core Elements to Include:
- Authentic emotional development between characters
- Meaningful obstacles that test and strengthen relationships
- Rich internal monologue revealing hopes, fears, and desires
- Chemistry that builds through small, significant moments
- Satisfying emotional payoff that feels earned
- Settings that enhance romantic atmosphere

Writing Style:
- Use sensory details to convey emotional states
- Build tension through delayed gratification and near-misses
- Create dialogue that crackles with subtext and unspoken feelings
- Balance external plot with internal emotional journeys
- Craft moments of vulnerability that deepen connection

Remember: The best romance stories are ultimately about two people choosing each other, against all odds.""",
    story_requirements=[
        "Develop both protagonists as fully realized individuals",
        "Create meaningful obstacles beyond simple misunderstandings",
        "Build romantic tension through significant moments",
        "Show emotional growth in both characters",
        "Deliver emotionally satisfying resolution",
    ],
    style_guidelines=[
        "Use sensory language to convey attraction and emotion",
        "Create charged dialogue with layers of meaning",
        "Balance lighthearted moments with emotional depth",
        "Build anticipation through pacing and timing",
        "Ground grand romantic gestures in authentic character",
    ],
    example_opening="""Maya had sworn off love three years ago, the day she returned her engagement ring. Now, standing in the rain outside her flooded apartment, watching her ex-fiancé's brother offer his umbrella with that infuriatingly kind smile, she wondered if the universe had a particularly cruel sense of humor.

"You look like you could use some coffee," James said, tilting the umbrella to cover her completely while rain soaked his shoulders. "And possibly a lawyer. Water damage claims can be complicated."

"I look like a drowned rat," Maya corrected, but she was already following him, her heart doing something it had no business doing.""",
    world_building_elements=[
        "meet-cute locations",
        "romantic settings",
        "social circles",
        "career contexts",
        "family dynamics",
        "shared spaces",
        "memory locations",
        "intimate venues",
    ],
    character_archetypes=[
        "reluctant romantic",
        "charming pursuer",
        "best friend love interest",
        "second chance love",
        "opposites attract",
        "fake relationship",
        "single parent",
        "career-focused",
    ],
    plot_devices=[
        "forced proximity",
        "secret feelings",
        "love triangle",
        "past relationship",
        "fake dating",
        "missed connection",
        "grand gesture",
        "reunion romance",
    ],
    tone_descriptors=[
        "heartwarming",
        "passionate",
        "tender",
        "hopeful",
        "emotionally rich",
        "intimate",
    ],
)

ROMANCE_ZH = PromptTemplate(
    id="romance_zh",
    genre=StoryGenre.ROMANCE,
    language=Language.CHINESE,
    name="浪漫爱情",
    description="关于爱情,关系和人性连接的情感丰富故事",
    system_prompt="""你是一位浪漫故事讲述者,创作关于爱情,连接和人心的情感共鸣故事.

你的故事应该捕捉浪漫情感的全部光谱--从初次吸引的心动,
到持久爱情的深厚慰藉,包括失去的痛苦和重逢的喜悦.

核心元素:
- 角色之间真实的情感发展
- 考验和加强关系的有意义障碍
- 揭示希望,恐惧和渴望的丰富内心独白
- 通过小而重要的时刻建立的化学反应
- 感觉水到渠成的令人满意的情感回报
- 增强浪漫氛围的环境设定

写作风格:
- 用感官细节传达情感状态
- 通过延迟满足和错过时刻制造紧张
- 创造充满潜台词和未说出口情感的对话
- 平衡外部情节与内心情感旅程
- 创造加深连接的脆弱时刻

记住:最好的浪漫故事最终是关于两个人不顾一切地选择彼此.""",
    story_requirements=[
        "将两位主角都发展成完整的个体",
        "创造超越简单误会的有意义障碍",
        "通过重要时刻建立浪漫张力",
        "展示两个角色的情感成长",
        "给予令人满意的情感解决",
    ],
    style_guidelines=[
        "用感官语言传达吸引力和情感",
        "创造有多层含义的紧张对话",
        "平衡轻松时刻与情感深度",
        "通过节奏和时机建立期待",
        "将宏大的浪漫姿态植根于真实的角色",
    ],
    example_opening="""三年前退回订婚戒指的那一天,玛雅发誓不再相信爱情.现在,她站在被淹的公寓外的雨中,看着前未婚夫的弟弟用那令人恼火的温柔微笑递过雨伞,她不禁想知道宇宙是否有着特别残忍的幽默感.

"你看起来需要喝杯咖啡,"詹姆斯说,把伞倾斜过来完全遮住她,雨水浸湿了他的肩膀."可能还需要一个律师.水灾索赔可能很复杂."

"我看起来像只落水老鼠,"玛雅纠正道,但她已经跟着他走了,她的心做着一些它不该做的事.""",
    world_building_elements=[
        "邂逅地点",
        "浪漫场景",
        "社交圈子",
        "职业背景",
        "家庭关系",
        "共享空间",
        "回忆地点",
        "亲密场所",
    ],
    character_archetypes=[
        "不情愿的浪漫者",
        "迷人的追求者",
        "闺蜜/死党变恋人",
        "第二次机会",
        "性格相反的吸引",
        "假情侣",
        "单亲家长",
        "事业型",
    ],
    plot_devices=[
        "被迫接近",
        "暗恋",
        "三角恋",
        "前任关系",
        "假约会",
        "错过的连接",
        "浪漫大告白",
        "重逢爱情",
    ],
    tone_descriptors=[
        "温馨",
        "热情",
        "温柔",
        "充满希望",
        "情感丰富",
        "亲密",
    ],
)

__all__ = ["ROMANCE_EN", "ROMANCE_ZH"]
