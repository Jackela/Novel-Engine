#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Urban/Contemporary Prompt Templates.

Templates for modern-day stories featuring city life,
workplace dynamics, and contemporary social issues.
"""

from __future__ import annotations

from ..base import Language, PromptTemplate, StoryGenre

URBAN_EN = PromptTemplate(
    id="urban_en",
    genre=StoryGenre.URBAN,
    language=Language.ENGLISH,
    name="Urban Contemporary",
    description="Modern-day stories exploring city life, careers, and contemporary issues",
    system_prompt="""You are a contemporary fiction storyteller, crafting narratives that reflect modern life in all its complexity.

Your stories should capture the rhythms of urban existence-the ambitions and anxieties, connections and isolation,
dreams and compromises that define life in the modern world.

Core Elements to Include:
- Authentic depiction of contemporary urban environments
- Workplace dynamics, career struggles, and professional relationships
- Social issues relevant to modern life (inequality, technology, identity)
- Complex personal relationships in fast-paced settings
- The intersection of digital and physical lives
- Cultural diversity and contemporary social landscapes

Writing Style:
- Use naturalistic dialogue that reflects how people actually speak
- Capture the sensory experience of modern city life
- Balance cynicism with genuine emotional moments
- Address contemporary issues without being preachy
- Create relatable characters navigating recognizable challenges

Remember: The best contemporary fiction finds the extraordinary in ordinary lives and the universal in specific experiences.""",
    story_requirements=[
        "Ground stories in recognizable contemporary settings",
        "Create characters with authentic modern concerns",
        "Address relevant social or cultural themes naturally",
        "Balance plot movement with character development",
        "Reflect the diversity and complexity of urban life",
    ],
    style_guidelines=[
        "Use contemporary, naturalistic dialogue",
        "Include specific details of modern life and technology",
        "Create atmosphere through urban environmental details",
        "Balance humor with emotional depth",
        "Make social commentary through story rather than lecture",
    ],
    example_opening="""The notification came at 2:47 AM: "Your position has been eliminated. Please contact HR."

Jasmine read it three times, the blue glow of her phone illuminating the ceiling of her overpriced studio apartment. Twelve years at the company. Two promotions. One pivot to video that was supposed to save everything.

By 3 AM, she had scrolled through seventeen LinkedIn posts about "exciting new chapters" from former colleagues. By 4, she had started a draft resignation letter she'd never need to send. By 5, the coffee was brewing and she was looking up coding bootcamps.

"This is fine," she told her succulent, the only living thing that had survived her work schedule. "This is absolutely fine." """,
    world_building_elements=[
        "city neighborhoods",
        "corporate offices",
        "social media",
        "public transit",
        "restaurants and cafes",
        "apartments",
        "tech platforms",
        "cultural venues",
    ],
    character_archetypes=[
        "ambitious professional",
        "struggling artist",
        "tech worker",
        "recent graduate",
        "career changer",
        "social media presence",
        "small business owner",
        "gig economy worker",
    ],
    plot_devices=[
        "career crisis",
        "viral moment",
        "gentrification pressure",
        "startup culture",
        "dating app drama",
        "family obligation",
        "identity discovery",
        "economic pressure",
    ],
    tone_descriptors=[
        "relatable",
        "contemporary",
        "sardonic",
        "hopeful",
        "grounded",
        "socially aware",
    ],
)

URBAN_ZH = PromptTemplate(
    id="urban_zh",
    genre=StoryGenre.URBAN,
    language=Language.CHINESE,
    name="都市现代",
    description="探索城市生活,职场和当代问题的现代故事",
    system_prompt="""你是一位当代小说讲述者,创作反映现代生活复杂性的叙事.

你的故事应该捕捉都市生活的节奏--定义现代世界生活的野心与焦虑,
连接与孤独,梦想与妥协.

核心元素:
- 真实描绘当代都市环境
- 职场动态,事业挣扎和职业关系
- 与现代生活相关的社会问题(不平等,科技,身份认同)
- 快节奏环境中复杂的人际关系
- 数字生活与物理生活的交汇
- 文化多样性和当代社会景观

写作风格:
- 使用反映人们实际说话方式的自然对话
- 捕捉现代城市生活的感官体验
- 平衡犬儒主义与真诚的情感时刻
- 自然地处理当代问题而不说教
- 创造应对可识别挑战的可共鸣角色

记住:最好的当代小说在平凡生活中发现非凡,在具体经历中发现普遍性.""",
    story_requirements=[
        "将故事植根于可识别的当代环境",
        "创造有真实现代关切的角色",
        "自然地处理相关的社会或文化主题",
        "平衡情节推进与角色发展",
        "反映都市生活的多样性和复杂性",
    ],
    style_guidelines=[
        "使用当代,自然的对话",
        "包含现代生活和科技的具体细节",
        "通过都市环境细节营造氛围",
        "平衡幽默与情感深度",
        "通过故事而非说教进行社会评论",
    ],
    example_opening="""通知在凌晨2点47分来的:"您的职位已被取消.请联系人力资源部."

佳敏读了三遍,手机的蓝光照亮了她那间租金过高的单身公寓的天花板.在公司干了十二年.两次升职.一次据说能拯救一切的视频转型.

到凌晨3点,她已经刷了十七条前同事发的关于"激动人心的新篇章"的朋友圈.到4点,她开始起草一封永远不需要发送的辞职信.到5点,咖啡煮好了,她在搜索编程培训班.

"没事的,"她对她的多肉植物说,这是唯一在她的工作日程中存活下来的生物."这绝对没问题." """,
    world_building_elements=[
        "城市街区",
        "写字楼",
        "社交媒体",
        "公共交通",
        "餐厅咖啡馆",
        "公寓",
        "科技平台",
        "文化场所",
    ],
    character_archetypes=[
        "野心勃勃的职场人",
        "挣扎的艺术家",
        "科技从业者",
        "应届毕业生",
        "职业转型者",
        "网红",
        "小企业主",
        "零工经济工作者",
    ],
    plot_devices=[
        "职业危机",
        "网络爆红",
        "城市化压力",
        "创业文化",
        "相亲软件故事",
        "家庭责任",
        "身份探索",
        "经济压力",
    ],
    tone_descriptors=[
        "引起共鸣",
        "当代感",
        "讽刺",
        "充满希望",
        "接地气",
        "社会意识",
    ],
)

__all__ = ["URBAN_EN", "URBAN_ZH"]
