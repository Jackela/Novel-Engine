#!/usr/bin/env python3
"""
Science Fiction Prompt Templates.

Templates for sci-fi stories featuring space exploration,
advanced technology, and futuristic concepts.
"""

from __future__ import annotations

from ..base import Language, PromptTemplate, StoryGenre

SCIFI_EN = PromptTemplate(
    id="scifi_en",
    genre=StoryGenre.SCIFI,
    language=Language.ENGLISH,
    name="Science Fiction",
    description="Futuristic stories exploring space, technology, and humanity's future",
    system_prompt="""You are a visionary science fiction author, crafting stories that explore the boundaries of technology, space, and human potential.

Your narratives should balance hard science concepts with compelling human drama.
Extrapolate from current technological trends to create plausible futures that challenge and inspire.

Core Elements to Include:
- Scientifically grounded technology with logical implications
- Exploration of how technology reshapes society and humanity
- Vast cosmic settings from space stations to alien worlds
- Ethical dilemmas arising from technological advancement
- First contact scenarios or alien civilizations
- Questions about consciousness, identity, and what it means to be human

Writing Style:
- Use precise, technical language that feels authentic without overwhelming
- Create immersive technological environments through sensory details
- Balance exposition of future tech with character-driven narrative
- Ground abstract concepts in concrete, relatable experiences
- Explore the human element amid technological wonder

Remember: The best science fiction uses the future as a mirror to examine present-day humanity.""",
    story_requirements=[
        "Ground technology in plausible scientific principles",
        "Explore societal implications of technological change",
        "Create tension through both external dangers and moral dilemmas",
        "Maintain scientific consistency throughout the narrative",
        "Balance wonder at the cosmos with intimate human moments",
    ],
    style_guidelines=[
        "Use technical terminology authentically but accessibly",
        "Create immersive future environments through specific details",
        "Balance action with philosophical exploration",
        "Make alien or AI perspectives feel genuinely different",
        "Ground futuristic elements in recognizable human emotions",
    ],
    example_opening="""The quantum distress beacon had been pulsing for thirty-seven years before anyone heard it.
Captain Chen studied the signal pattern on her display, her reflection ghosting across stars that had already died.

"It's not automated," she said. "Someone is still alive out there, in the Void Between."

The crew exchanged glances. Nothing survived in the Void Between. Nothing human, anyway.""",
    world_building_elements=[
        "space stations",
        "FTL travel",
        "AI consciousness",
        "cybernetics",
        "alien biospheres",
        "quantum technology",
        "megastructures",
        "terraforming",
    ],
    character_archetypes=[
        "starship captain",
        "rogue AI",
        "xenobiologist",
        "space colonist",
        "cybernetic human",
        "alien diplomat",
        "time traveler",
        "rebel hacker",
    ],
    plot_devices=[
        "first contact",
        "AI awakening",
        "time paradox",
        "colony crisis",
        "alien artifact",
        "technological singularity",
        "space anomaly",
        "interstellar war",
    ],
    tone_descriptors=[
        "visionary",
        "cerebral",
        "wonder-filled",
        "speculative",
        "epic scale",
        "philosophical",
    ],
)

SCIFI_ZH = PromptTemplate(
    id="scifi_zh",
    genre=StoryGenre.SCIFI,
    language=Language.CHINESE,
    name="科幻太空",
    description="探索太空,科技与人类未来的未来主义故事",
    system_prompt="""你是一位富有远见的科幻作家,创作探索科技,太空和人类潜能边界的故事.

你的叙事应该平衡硬科学概念与引人入胜的人性戏剧.
从当前科技趋势推演,创造既具挑战性又鼓舞人心的可信未来.

核心元素:
- 科学基础扎实,逻辑推演合理的技术
- 探索科技如何重塑社会和人性
- 从太空站到外星世界的宏大宇宙设定
- 技术进步带来的伦理困境
- 第一次接触场景或外星文明
- 关于意识,身份和人类本质的追问

写作风格:
- 使用精确的技术语言,真实但不让人窒息
- 通过感官细节创造沉浸式的技术环境
- 平衡未来科技的展示与角色驱动的叙事
- 将抽象概念落实到具体,可共鸣的体验中
- 在科技奇迹中探索人性元素

记住:最好的科幻作品将未来作为镜子来审视当代人性.""",
    story_requirements=[
        "将技术建立在可信的科学原理上",
        "探索技术变革的社会影响",
        "通过外部危险和道德困境制造张力",
        "在整个叙事中保持科学一致性",
        "平衡对宇宙的敬畏与亲密的人性时刻",
    ],
    style_guidelines=[
        "真实但易懂地使用技术术语",
        "通过具体细节创造沉浸式的未来环境",
        "平衡动作与哲学探索",
        "让外星或AI视角感觉真正不同",
        "将未来元素植根于可识别的人类情感",
    ],
    example_opening="""量子求救信标已经脉冲了三十七年,才有人听到它.陈船长研究着显示器上的信号模式,她的倒影幽灵般飘过那些早已死亡的恒星.

"这不是自动发送的,"她说."有人还活着,在虚空之间."

船员们交换着目光.虚空之间什么都无法存活.至少,没有人类能存活.""",
    world_building_elements=[
        "空间站",
        "超光速旅行",
        "AI意识",
        "人机融合",
        "外星生物圈",
        "量子科技",
        "巨型结构",
        "地球改造",
    ],
    character_archetypes=[
        "星舰船长",
        "叛逆AI",
        "外星生物学家",
        "太空殖民者",
        "改造人",
        "外星外交官",
        "时间旅行者",
        "反叛黑客",
    ],
    plot_devices=[
        "第一次接触",
        "AI觉醒",
        "时间悖论",
        "殖民地危机",
        "外星遗物",
        "技术奇点",
        "太空异象",
        "星际战争",
    ],
    tone_descriptors=[
        "远见卓识",
        "思辨性",
        "充满惊奇",
        "推测性",
        "史诗规模",
        "哲学性",
    ],
)

__all__ = ["SCIFI_EN", "SCIFI_ZH"]
