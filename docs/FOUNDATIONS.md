# 理论基础

本项目的理论基础源于 Roland Barthes 在 1967 年提出的《作者之死》。核心观点：文本的意义并非由作者单一意图决定，而是由语言系统与读者共同生成。语言先于作者存在，它是社会共享的符号结构。因此，作者不再是意义的中心，语言与文化系统才是。所有文本皆可视为“人类书写系统（Human Writing System）”中的检索与重组。

工程转译：系统的目标不是“模仿作者写作”，而是构建可在语义空间内进行打捞、重组与验证的机制。系统中的“作者”角色退位为“编排者（Orchestrator）”。Novel Engine 不直接生成意义，而是在语义网络中生成路径；系统价值在于组合逻辑、语义约束与可复现性。

核心假设与约束：
- 封闭世界、开放组合（closed world, open composition）：仅在既有语义分布内进行组合，不越出人类语言的统计边界。
- 创作即约束（composition as constraint）：生成需满足逻辑一致性、语义连贯性与来源溯源。
- 原创性是稀有重组（originality as rare recombination）：所谓“原创”是语义图谱中的低概率新路径。

工程实现要点：
- 路径多样化搜索（path diversification）
- 熵平衡生成（entropy‑balanced generation）
- 验证驱动编排（validation‑driven orchestration）
- 检索机制与权重可解释性（retrieval & traceable weighting）
