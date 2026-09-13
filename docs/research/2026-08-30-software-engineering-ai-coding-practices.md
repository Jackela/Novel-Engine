# 软件工程与 AI Coding 最佳实践、规则与理论研究

- 调查日期：2026-08-30；最终复核：2026-08-31
- 状态：**research candidate**
- 目录规模：50 项质量/交付控制 + 50 项架构/理论 + 58 项 AI Coding 规则，共 158 项逐条证据目录；另附 20 条跨域综合导航和 10 个争议命题的三线交叉结论。综合导航不冒充新增的独立证据项。
- 范围：软件工程通用知识，以及质量、测试、可靠性、可观测性、安全、隐私、供应链、配置、交付、发布和事件响应的可执行实践。
- 明确边界：**本文不是 Novel Engine 项目政策、架构决策、发布批准、合规证明或标准符合性声明。**任何规则进入项目基线前，仍需经过对应 issue、OpenSpec、ADR、代码审查和项目验收流程。
- 方法：仅以标准发布组织、政府机构、项目官方文档和原始论文为证据；将规范、风险控制、经验实践、方法和指标分开；反例用于防止把条件性建议绝对化。

## 1. 研究边界与证据等级

“列出所有最佳实践”不存在可证明完备的终点：软件工程规则受系统风险、法规、生命周期、团队规模、部署环境和证据成本影响。本文用 SWEBOK 作为完整性导航，用风险控制表收敛高价值、可执行且尽量不重复的条目。

### 1.1 证据类型

| 标记 | 含义 | 权威边界 |
|---|---|---|
| 强制 | 适用法律、监管、合同或已批准组织政策的要求 | 只有确认适用范围后才可写成“必须” |
| 规范 | ISO、IEC、IEEE 等标准中的规范性要求 | 只有标准被合同引用或声明符合时才强制；公开摘要不足以证明符合 |
| 控制 | NIST、CISA、OWASP、SLSA 等风险控制或框架 | 应按威胁模型、业务风险和成本裁剪 |
| 实践 | Google SRE、Google Engineering Practices 等一手工程经验 | 是条件性经验，不是普适定律 |
| 方法 | 原始论文或正式方法提出的验证技术 | 需证明适用前提、oracle 和采样策略 |
| 指标 | SLI/SLO、覆盖率、DORA 等测量信号 | 指标不是控制、质量证明或个人绩效目标 |

### 1.2 证据状态词

- source-backed：有一手来源直接支持。
- observed：在当前本地仓库中实际观察到，但本轮未重新执行全套验证。
- verified：已通过对应权威验证面复现或执行；只对该验证面明确声明的契约成立，不自动扩展为业务真值、风险接受、人工验收或发布批准。
- candidate：待项目决策采纳。
- owner-required：需要项目负责人、法务、安全或发布责任人判断。
- unknown：现有证据不能下结论。

### 1.3 多代理调查与交叉验证方法

- 架构/理论线：从标准、原始论文和作者原文整理需求、设计、分布式、形式方法、过程和演化规律。
- 质量/交付线：独立整理测试、SRE、安全、隐私、供应链、发布、事件响应和度量控制。
- AI Coding 线：独立整理 agent 编排、上下文、权限、工具、评测、生产力与治理证据。
- 三线分别复核 DRY、SOLID、微服务、测试金字塔、TDD、trunk-based、人工逐行审查、多 agent、AI 提效和指标目标化，再由主线合并分歧。
- 独立性边界：这些代理共享同一协作环境和相近模型能力，因此属于多路径二次审阅，不构成正式 IV&V；其一致意见仍只是 candidate evidence。

## 2. 当前本地基线

以下是 2026-08-31 最终复核时读取仓库得到的 observed 快照，不代表本研究稿重新验证了全部 CI：

| 项目 | 当前观察 |
|---|---|
| Git | main，HEAD 2a1d959f，最近提交为 release: v0.6.0 (#438)；本轮未 fetch/pull，不对远端当前领先/落后关系作结论 |
| 产品与工具链 | server 0.6.0；Node.js >=24；pnpm 11.6.0；TypeScript 6.0.x |
| 后端 | Fastify 5、TypeBox、Drizzle、better-sqlite3；分层边界由 dependency-cruiser 执行 |
| 前端 | React 19、Vite 8、Vitest、Playwright；API 类型由 OpenAPI 快照生成 |
| 本地质量门禁 | SSOT、仓库卫生、文件大小、迁移通道、llms.txt、OpenAPI 快照、OpenSpec、类型检查、lint、单元测试和构建 |
| CI 额外门禁 | 生产依赖审计、API 类型漂移、React 静态诊断、Playwright 用户流程、容器新装/持久化/重启/深链、SQLite quick_check |
| 项目权威边界 | 根 CONTEXT.md 管领域词汇；docs/adr 管架构决策；GitHub Issues 管任务；OpenSpec 管产品规格 |
| 本轮验证状态 | 仅做文档与配置读取；未执行 just check、just validate 或完整 CI，故不得写成 verified |

本文的通用控制与上述基线可能存在三种关系：已经实现、部分实现、尚未采用。除非另有项目证据，本文不替项目做该判定。

## 3. SWEBOK 完整性框架

[IEEE Computer Society SWEBOK Guide v4.0a](https://www.computer.org/education/bodies-of-knowledge/software-engineering) 用于检查知识面，而不是作为逐项强制清单。本文当前覆盖情况如下：

| SWEBOK V4 知识领域 | 本稿状态 | 主要落点 |
|---|---|---|
| Software Requirements | 重点覆盖 | 第 5.1 节：需求质量、V&V、追踪、示例和假设 |
| Software Architecture | 重点覆盖 | 第 5.3、5.4 节：架构描述、边界、风格、分布式与形式模型 |
| Software Design | 重点覆盖 | 第 5.2、5.3 节：模块化、契约、领域边界和设计启发式 |
| Software Construction | 重点覆盖 | 第 4.1、4.3、4.5 及第 6 章：审查、安全编码、CI 与 AI 辅助实现 |
| Software Testing | 重点覆盖 | 第 4.1 节 |
| Software Engineering Operations | 重点覆盖 | 第 4.2、4.5、4.6 节 |
| Software Maintenance | 部分 | 版本、迁移、恢复、漏洞响应 |
| Software Configuration Management | 重点覆盖 | 第 4.4、4.5 节 |
| Software Engineering Management | 部分 | 责任、门禁、SLO、事件指挥和指标 |
| Software Engineering Process | 部分 | 生命周期、SQA、测试过程、CI |
| Software Engineering Models and Methods | 重点覆盖 | 第 4.1、5.4、6.5 节：性质、蜕变、fuzz、mutation、形式模型和 eval |
| Software Quality | 重点覆盖 | 第 4.1 节 |
| Software Security | 重点覆盖 | 第 4.3、4.4 节 |
| Software Engineering Professional Practice | 重点覆盖 | 第 3.1、5.5、6.7 节：专业责任、协作、人类问责和证据边界 |
| Software Engineering Economics | 部分 | 第 3.1、4.6、5.5、5.6、6.5 节：批量、流动、风险、债务和全成本 |
| Computing Foundations | 部分 | 第 5.2—5.4 节：抽象、类型/契约、状态和分布式语义 |
| Mathematical Foundations | 部分 | 第 5.3—5.5 节：逻辑、状态机、CAP、时序和排队理论 |
| Engineering Foundations | 重点覆盖 | 第 3.1、4—6 章：测量、实验、风险、验证、运行和持续改进 |

AI Coding 不是 SWEBOK V4 的独立知识领域。本稿把它作为横切扩展：它不得替代需求、架构、测试、安全、配置管理或专业责任。

### 3.1 二十条跨域综合导航

这些是从第 4—6 章证据目录综合出的导航，不作为 158 项逐条证据目录之外的新增规范，也不代表每项都要用同一实现形式。需要采纳时，应回到对应章节的一手来源、适用条件和反例。

| # | 元规则 | 最小检查 |
|---:|---|---|
| 1 | 公众利益、避免伤害、诚实和专业胜任优先于交付压力 | 是否披露重大风险、能力边界、利益冲突和已知缺陷；见 [ACM Code of Ethics](https://www.acm.org/code-of-ethics) |
| 2 | 先确认问题、用户、结果和成功标准，再选技术 | 是否有真实用户任务、反例和退出条件，而不只是功能清单 |
| 3 | 每个事实、需求、决定、状态、证据和发布指针有唯一 owner | `candidate/observed` 不得自动升级成 `verified/approved/released` |
| 4 | 在同一边界内保持领域语言一致 | 代码、API、测试和文档是否使用同一概念；跨上下文歧义是否显式翻译 |
| 5 | 选择满足已确认需求的最简单可验证方案 | 简单不等于删除安全、恢复、兼容或可观测性要求；用 KISS/YAGNI 控制无证据复杂度 |
| 6 | 对变化优化：隐藏易变决定，保持稳定接口 | 一项变化传播到多少模块、团队、数据和部署单元 |
| 7 | 契约、前后条件、不变量、错误语义和版本必须显式 | happy path 以外，失败、取消、超时、权限和未知输入如何表现 |
| 8 | 严格解析自己接受的输入，保守承诺自己输出的行为 | 盲目“宽容接收”会固化错误和安全缺陷；见 [RFC 9413](https://www.rfc-editor.org/rfc/rfc9413.html) |
| 9 | API 错误应机器可识别、稳定且不泄密 | HTTP API 可采用 [RFC 9457 Problem Details](https://www.rfc-editor.org/rfc/rfc9457.html)，并保留领域错误与追踪 ID |
| 10 | 数据库约束、事务边界、迁移与恢复共同保护数据完整性 | 应用校验不能替代唯一性/外键等持久化约束；迁移需真实升级、回退或前向修复证据 |
| 11 | 并发与分布式行为必须声明原子性、顺序、幂等和一致性 | 不用本地时间或“恰好一次”口号替代真实协议语义 |
| 12 | 错误不能被无差别吞掉；只捕获能处理的已知失败 | 未知编程错误保持可见；降级、重试和补偿需有界且可观测 |
| 13 | 性能先测量后优化，并设置容量与尾延迟预算 | 优化是否由 profile/负载证据驱动，是否损害正确性、成本或可维护性 |
| 14 | 默认安全、最小权限、数据最小化和最短保留 | 新实例未配置时是否安全；秘密、PII、日志和遥测是否有拒收/脱敏/删除规则 |
| 15 | 可访问性属于完成定义，不是发布后的修饰 | 关键用户旅程按 [WCAG 2.2](https://www.w3.org/TR/WCAG22/) 检查键盘、焦点、语义、对比度、缩放和辅助技术 |
| 16 | 文档靠近权威源，解释“为什么、边界和如何验证” | README、ADR、API、runbook 和代码是否漂移；生成文档是否可再生 |
| 17 | 自动化重复且客观的检查，人负责目的、风险和例外 | 自动门禁能拒绝候选，但不能代替业务验收、风险接受或发布授权 |
| 18 | 小批量、短反馈、可回滚优于大批量猜测 | 变更是否独立理解、验证、部署和回退；长期分支与大 PR 是否增加集成风险 |
| 19 | 指标用于系统学习，不作为单一个人目标 | 同一系统边界内联合看质量、速度、稳定性、成本和用户结果，并监测博弈 |
| 20 | 每次事故、缺陷和失败实验都应进入可验证的改进闭环 | 是否有 owner、期限、回归测试/控制变更和效果复核，而非只写复盘 |

## 4. 质量、测试、可靠性、安全、供应链与交付：50 项精炼控制

### 4.1 软件质量与测试

| # | 类型与名称 | 核心命题与适用条件 | 反例或误用 | 可执行检查 | 一手来源 |
|---:|---|---|---|---|---|
| 1 | 规范：生命周期过程治理 | 为需求、架构、实现、验证、运行、维护和退役定义责任、输入、输出及追踪关系；适合需审计交付的项目 | 把标准机械映射成瀑布阶段；12207 不规定唯一生命周期模型 | 抽样需求能否追至设计、代码、测试、发布和变更记录 | [ISO/IEC/IEEE 12207:2026，2026-04-29](https://www.iso.org/standard/90219.html) |
| 2 | 规范：产品质量模型 | 按功能适合性、性能效率、兼容性、交互能力、可靠性、安全性、可维护性、灵活性和安全防护定义可验收要求 | 用测试通过率或覆盖率代替整体质量 | 每个重要质量特性是否有阈值、测法、责任人和接受风险 | [ISO/IEC 25010:2023，2023-11](https://www.iso.org/standard/78176.html) |
| 3 | 规范：使用质量与上下文 | 在明确用户、任务、环境和风险下评价结果质量 | 实验室延迟低便宣称用户体验良好；忽略可访问性和误用风险 | 是否记录目标用户、关键任务、环境约束和任务成功指标 | [ISO/IEC 25019:2023，2023-11](https://www.iso.org/standard/78177.html) |
| 4 | 规范：SQA 过程 | 质量保证贯穿计划、控制、执行和不符合项闭环；高风险系统需适当独立性 | 把 QA 等同于发布前点测；开发者自行关闭全部重大例外 | 是否有 SQA 计划、审查点、豁免批准和关闭证据 | [IEEE 730-2026，2026-08-21](https://standards.ieee.org/ieee/730/10854/) |
| 5 | 规范：风险驱动测试过程 | 测试依据、设计、环境、数据、执行、异常和报告均可追踪；允许有理由裁剪 | 复制完整模板却没有风险覆盖；以敏捷为由完全无记录 | 风险到测试条件、用例、结果、缺陷或接受风险能否闭环 | [ISO/IEC/IEEE 29119-2:2021](https://www.iso.org/standard/79428.html)、[29119-3:2021](https://www.iso.org/standard/79429.html)、[29119-4:2021](https://www.iso.org/standard/79430.html) |
| 6 | 实践：代码审查改善代码健康 | 变更应使系统整体更健康；技术事实优先于个人偏好，不以完美阻塞合理改进 | 只看格式；把审查当权威签字；大批量变更无法理解 | 非机械变更是否有独立审查、上下文、验证证据和争议结论 | [Google Engineering Practices](https://google.github.io/eng-practices/review/reviewer/standard.html) |
| 7 | 实践：小而窄的行为测试 | 大多数行为用快速、局部、可诊断测试覆盖；测试公开行为而非实现细节 | 强制所有项目采用同一 80/15/5 比例；mock 内部调用使重构即碎 | 测试能否快速定位失败；行为不变的重构是否仍通过 | [Google SWE Book, Testing Overview](https://abseil.io/resources/swe-book/html/ch11.html) |
| 8 | 实践：集成与契约验证 | 在进程、数据库、网络、序列化和第三方边界验证真实契约 | 单元测试全部 mock 后宣称迁移、鉴权或协议兼容已验证 | 每个关键边界是否至少有真实实现或高保真替身的契约测试 | [Google SWE Book, Larger Testing](https://abseil.io/resources/swe-book/html/ch14.html) |
| 9 | 实践：端到端只保关键旅程 | E2E 用于少数跨组件、用户价值高且低层测试无法证明的流程 | 以大量慢而脆的 E2E 代替单元和集成；只覆盖快乐路径 | E2E 是否映射关键旅程；失败能否定位；重复覆盖是否下沉 | [Google Testing Blog，2015-04-22](https://testing.googleblog.com/2015/04/just-say-no-to-more-end-to-end-tests.html) |
| 10 | 控制：确定性、密闭性与 flaky 治理 | 控制时间、随机、网络、数据、并发和外部状态；flaky 是缺陷 | 反复重跑直到绿；长期隔离而无人修复 | 同一提交重复运行是否一致；隔离项是否有 owner、期限和根因 | [Google SWE Book, Test Maintainability](https://abseil.io/resources/swe-book/html/ch11.html) |
| 11 | 方法：性质与蜕变测试 | 用不变量和输入变换发现示例测试遗漏；适合输入空间大或缺精确 oracle | 生成无业务约束垃圾；把性质写成实现的同义重述 | 是否有业务不变量、有效生成器、缩减策略和固定回归种子 | [QuickCheck 原始论文，2000](https://doi.org/10.1145/351240.351266)、[Metamorphic Testing 原始报告，1998](https://www.cse.ust.hk/faculty/scc/publ/CS98-01-metamorphictesting.pdf) |
| 12 | 方法与指标：fuzz、mutation、coverage 互证 | fuzz 探索非预期输入，sanitizer 暴露内存问题，mutation 检查测试能否杀死缺陷；覆盖率只表示代码被执行 | 100% 覆盖即正确；fuzzer 不看可达覆盖；为 mutation 分数制造脆弱断言 | 高风险解析器是否持续 fuzz；崩溃是否最小化并回归；幸存变异是否分类 | [Google Fuzzing](https://github.com/google/fuzzing/blob/master/docs/intro-to-fuzzing.md)、[Mutation Testing 原始论文，1978](https://doi.org/10.1109/C-M.1978.218136) |

### 4.2 可靠性与可观测性

| # | 类型与名称 | 核心命题与适用条件 | 反例或误用 | 可执行检查 | 一手来源 |
|---:|---|---|---|---|---|
| 13 | 指标与控制：SLI、SLO、SLA | SLI 测量用户结果，SLO 是目标，SLA 才含商业后果；通常不追求 100% | 只看主机 uptime；把内部目标误称 SLA；所有请求只看平均值 | 是否按用户旅程定义成功率、延迟分位数、窗口和数据源 | [Google SRE, SLO](https://sre.google/sre-book/service-level-objectives/) |
| 14 | 控制：错误预算 | 1-SLO 是允许的不可靠空间，用于平衡变更速度和稳定性 | 预算耗尽仍正常发高风险功能；把预算当团队处罚 | 是否有预算窗口、消耗速率、例外条件和冻结或降速规则 | [Google SRE Workbook, Error Budget Policy](https://sre.google/workbook/error-budget-policy/) |
| 15 | 指标：四个黄金信号 | 延迟、流量、错误、饱和度是在线服务基础观察面，同时需要黑盒用户探测 | 只采 CPU、内存；平均延迟掩盖尾部；仪表盘很多却无人负责 | 关键服务是否有用户成功、尾延迟、错误和容量余量 | [Google SRE, Monitoring](https://sre.google/sre-book/monitoring-distributed-systems/) |
| 16 | 实践：可行动告警 | 告警分 page、ticket、log；只有需及时人工行动时才 page | 每个异常都 page；无 runbook、无 owner、长期静默 | 每条 page 是否说明用户影响、owner、runbook、升级和解除条件 | [Google SRE Workbook, Monitoring](https://sre.google/workbook/monitoring/) |
| 17 | 控制：容量、负载、压力与长稳测试 | 在预期峰值、突发、超载和长时间运行下验证容量边界 | 只测平均流量；用压测环境结果直接承诺生产容量 | 是否测最大安全吞吐、饱和点、恢复时间和依赖限额 | [Google SRE, Monitoring](https://sre.google/sre-book/monitoring-distributed-systems/) |
| 18 | 控制：deadline、timeout 与取消传播 | 远程工作必须受端到端时限约束；取消后停止无价值工作 | 每层独立长 timeout 使总时长相乘；客户端取消但后端继续 | deadline 是否跨层传播；慢依赖是否有明确失败语义 | [Google SRE, Cascading Failures](https://sre.google/sre-book/addressing-cascading-failures/) |
| 19 | 控制：有界重试、退避和 jitter | 仅对暂时且幂等或可去重失败重试，并限制次数和系统级预算 | 每层都重试；对非幂等写入盲重试；无 jitter 形成同步风暴 | 是否只在一层重试；有 attempt 上限、总 deadline、jitter 和幂等键 | [Google SRE, Cascading Failures](https://sre.google/sre-book/addressing-cascading-failures/) |
| 20 | 控制：背压、队列上限与负载脱落 | 接近饱和时拒绝、降级或限流，避免无界排队和级联故障 | 以不能丢请求为由无限排队；直到 OOM 才失败 | 队列是否有界；拒绝是否尽早；过载下核心功能能否保持 | [Google SRE, Cascading Failures](https://sre.google/sre-book/addressing-cascading-failures/) |
| 21 | 控制：故障隔离与优雅降级 | 用隔舱、限额、冗余、故障域和降级路径限制爆炸半径 | 所有副本同区同配置；冗余共享单点；降级从未演练 | 单依赖或单区故障是否只影响既定范围；降级输出是否安全明确 | [Google SRE, Cascading Failures](https://sre.google/sre-book/addressing-cascading-failures/) |
| 22 | 控制：RTO、RPO、备份与恢复演练 | 备份只是恢复能力的一部分；定义恢复时间和数据损失容忍度并实际还原 | 只检查备份任务成功；备份和生产处于同权限、同故障域 | 最近一次独立环境恢复是否达到 RTO/RPO 并验证业务可用 | [NIST SP 800-34r1，2010](https://csrc.nist.gov/pubs/sp/800/34/r1/upd1/final)、[CISA StopRansomware Guide，2023-10-19](https://www.cisa.gov/stopransomware/ransomware-guide) |
| 23 | 控制：可关联且安全的遥测 | trace、metric、log 通过稳定上下文关联；跨进程使用 Trace Context；baggage 不放秘密 | 高基数字段耗尽系统；日志写 token 或 PII；误以为 baggage 有完整性保护 | 是否能从告警追至请求、部署和依赖；敏感字段是否拒收、脱敏和限存 | [OpenTelemetry 1.60.0](https://opentelemetry.io/docs/specs/otel/)、[W3C Trace Context，2021-11-23](https://www.w3.org/TR/trace-context/)、[OTel Baggage 风险](https://opentelemetry.io/docs/concepts/signals/baggage/) |

### 4.3 安全与隐私

| # | 类型与名称 | 核心命题与适用条件 | 反例或误用 | 可执行检查 | 一手来源 |
|---:|---|---|---|---|---|
| 24 | 控制：安全风险治理 | 用 Govern、Identify、Protect、Detect、Respond、Recover 建立全生命周期风险闭环 | 把 CSF 当产品认证或逐项打勾；没有业务风险和责任人 | 高风险资产是否有 owner、现状、目标、控制和剩余风险 | [NIST CSF 2.0，2024-02-26](https://www.nist.gov/cyberframework) |
| 25 | 控制：SSDF 安全开发基线 | 将组织准备、保护软件、生产安全软件、响应漏洞嵌入 SDLC | 仅发布前扫描；安全团队独自承担安全结果 | SSDF 实践是否映射 owner、流水线证据、例外和改进计划 | [NIST SP 800-218 v1.1，2022-02-03](https://doi.org/10.6028/NIST.SP.800-218) |
| 26 | 控制：Secure by Design 和 Default | 厂商承担客户安全结果；关键安全能力默认启用，不把安全成本和配置负担转嫁客户 | 支持 MFA 但默认关闭或额外收费；默认口令长期有效 | 新实例未配置时是否仍安全；关键安全功能是否默认开且可观测 | [CISA Secure by Design，2023-10](https://www.cisa.gov/sites/default/files/2023-10/Shifting-the-Balance-of-Cybersecurity-Risk-Principles-and-Approaches-for-Secure-by-Design-Software.pdf) |
| 27 | 控制：持续威胁建模 | 明确系统、可能出错之处、缓解方式和验证充分性；覆盖数据流、信任边界和滥用场景 | 上线前只画一次图；列 STRIDE 名词却无攻击路径和措施 | 架构或数据流变化是否触发更新；高风险威胁是否有验证证据 | [OWASP Threat Modeling Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html) |
| 28 | 控制：消除高危缺陷类别 | 参数化查询、严格解析、内存安全语言、输出编码和边界检查优先于事后检测 | 自制字符串转义；用 WAF 代替 SQLi 修复；无论证采用内存不安全语言 | 是否存在拼接 SQL 或命令、路径穿越、缺失授权、危险内存操作 | [CISA/FBI Product Security Bad Practices，2025-01-17](https://www.cisa.gov/news-events/alerts/2025/01/17/cisa-and-fbi-release-updated-guidance-product-security-bad-practices)、[MITRE CWE Top 25，2025](https://cwe.mitre.org/top25/index.html) |
| 29 | 控制：Zero Trust 与最小权限 | 不因网络位置或所有权隐式信任；每次访问按主体、资源、动作和上下文授权 | 内网即可信；只认证不做对象级授权；长期管理员权限 | 高价值操作是否逐请求鉴权、默认拒绝、限时授权且可撤销 | [NIST SP 800-207，2020-08-11](https://csrc.nist.gov/pubs/sp/800/207/final) |
| 30 | 控制：秘密与密钥生命周期 | 集中保管、最小权限、短期凭证、轮换、审计、吊销和紧急访问；日志不得泄漏 | 把 .env 当完整秘密管理；硬编码密钥；轮换从未演练 | 仓库、镜像和日志是否扫描；秘密能否无停机轮换并追踪访问 | [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html) |
| 31 | 控制：组合式安全验证 | SAST、SCA、DAST、fuzz、渗透和人工业务逻辑检查互补；ASVS 可作验收基线 | 单一扫描器零告警即安全；自动扫描遗漏越权和业务滥用 | 每个威胁及 ASVS 适用项是否有对应验证和例外理由 | [OWASP ASVS 5.0.0，2025-05-30](https://owasp.org/www-project-application-security-verification-standard/)、[OWASP WSTG](https://wstg.owasp.org/) |
| 32 | 指标与控制：漏洞风险排序 | 联合资产重要性、可利用性、暴露面、补偿控制、KEV 和 CVSS Threat/Environmental 判断 | 只按 CVSS Base 排序；低分 KEV 延后；把 CVSS 当风险值 | KEV 是否单独升级；决策是否记录资产、暴露、利用情报和期限 | [CVSS v4.0 Spec 1.2，2024-06-18](https://www.first.org/cvss/v4.0/specification-document)、[CISA KEV](https://www.cisa.gov/known-exploited-vulnerabilities-catalog) |
| 33 | 规范与控制：漏洞披露和 PSIRT | 提供可发现渠道，安全接收、确认、分级、修复、沟通和复盘 | security 地址无人值守；奖励计划代替修复责任；无协调披露规则 | 渠道、SLA、加密方式、状态沟通、CVE 或通告、修复证据是否明确 | [NIST SP 800-216，2023-05](https://csrc.nist.gov/pubs/sp/800/216/final)、[ISO/IEC 29147:2018](https://www.iso.org/standard/72311.html) |
| 34 | 强制与控制：数据清单、目的限定、最小化和限存 | 只处理实现合法明确目的所必要的数据，并设保留和删除规则；法规适用时强制 | 以未来可能有用无限收集；测试复制全量生产数据 | 每字段是否有目的、合法基础、owner、保留期、共享方和删除验证 | [GDPR 2016/679 第 5 条](https://eur-lex.europa.eu/eli/reg/2016/679/oj)、[NIST Privacy Framework 1.0，2020-01](https://www.nist.gov/privacy-framework/privacy-framework) |
| 35 | 强制与控制：Privacy by Design、DPIA 和可分离性 | 默认最少暴露；高风险处理上线前评估；通过隔离、聚合、假名化或差分隐私降风险 | 把加密等同匿名；上线后补 DPIA；差分隐私无预算治理 | 是否有 DPIA、隐私目标、重新识别测试、退出和删除路径 | [GDPR 第 25、32、35 条](https://eur-lex.europa.eu/eli/reg/2016/679/oj)、[NISTIR 8062，2017](https://csrc.nist.gov/pubs/ir/8062/final)、[NIST SP 800-226，2025-03-06](https://csrc.nist.gov/pubs/sp/800/226/final) |

### 4.4 软件供应链

| # | 类型与名称 | 核心命题与适用条件 | 反例或误用 | 可执行检查 | 一手来源 |
|---:|---|---|---|---|---|
| 36 | 控制：全生命周期 C-SCRM | 采购、开发、构建、交付、运行和退役均评估供应商、组件、服务及集中风险 | 只发供应商问卷；认为开源天然安全或商业软件天然可信 | 关键供应商是否有来源、更新、漏洞响应、退出方案和持续监测 | [NIST SP 800-161r1 Update 1，更新至 2024-11-01](https://csrc.nist.gov/pubs/sp/800/161/r1/upd1/final) |
| 37 | 控制：每个发布物生成可关联 SBOM | SBOM 应关联准确制品，含组件标识、版本、供应关系和必要元数据 | 只生成一次；SBOM 与镜像不一致；把 SBOM 当安全证明 | 每个制品 digest 是否能定位 SBOM；抽样与实际安装内容是否一致 | [CISA SBOM Minimum Elements，2025](https://www.cisa.gov/sites/default/files/2025-08/2025_CISA_SBOM_Minimum_Elements.pdf)、[SPDX 3.0](https://spdx.dev/use/specifications/) |
| 38 | 控制：依赖最小化、固定和更新治理 | 只引入必要依赖，锁定解析结果并验证来源或哈希；更新经自动验证和风险审查 | 永不更新即安全；无上限自动升级生产；只扫直接依赖 | 是否能重建同一依赖图；过期、废弃、传递依赖和许可风险是否有 owner | [NIST SP 800-161r1 Update 1](https://csrc.nist.gov/pubs/sp/800/161/r1/upd1/final) |
| 39 | 控制：SLSA 来源与构建可信度 | Source Track 管变更来源；Build Track 从 provenance 到托管签名、隔离和密钥保护逐级增强 | 宣称 SLSA 3 即代码无漏洞；把一个制品等级赋予全部传递依赖 | 目标级别是否明确；builder、source、parameters、digest 是否验证 | [SLSA v1.2，2025-11-24](https://slsa.dev/spec/v1.2/) |
| 40 | 控制：制品签名、证明与身份验证 | 消费端验证 digest、签名者身份、信任根和声明，而非只确认存在签名 | 下载签名但不验身份；允许任意签名者；只验 tag 不验 digest | 部署前是否策略化验证签名者、透明日志、digest 和 attestations | [Sigstore Cosign Verification](https://docs.sigstore.dev/cosign/verifying/verify/) |
| 41 | 控制：隔离、短生命周期 CI 与可复核构建 | 构建环境最小权限、短期凭证、隔离不可信代码；可重建或可重复性用于发现污染 | PR 代码取得生产秘密；自托管 runner 长期复用；本机可构建即来源证明 | 外部 PR 是否无高权凭证；runner 是否清理；输出或 provenance 能否比较 | [NIST SP 800-204D，2024-02-12](https://csrc.nist.gov/pubs/sp/800/204/d/final)、[SLSA v1.2 Build Track](https://slsa.dev/spec/v1.2/build-track-basics) |

### 4.5 配置、交付与发布

| # | 类型与名称 | 核心命题与适用条件 | 反例或误用 | 可执行检查 | 一手来源 |
|---:|---|---|---|---|---|
| 42 | 实践与控制：配置外置、IaC 和 GitOps 对账 | 配置不写死在代码；期望状态声明化、版本化、自动拉取并持续对账；秘密由专用系统管理 | 所有秘密明文环境变量化；控制台手改不回写；自动覆盖紧急修复 | 环境能否由受审版本重建；漂移是否告警；秘密是否只存引用 | [12-Factor Config](https://12factor.net/config)、[OpenGitOps Principles 1.0.0](https://opengitops.dev/) |
| 43 | 实践：Build once 与不可变提升 | 构建、release、run 分离；同一 digest 经验证后提升，不在生产重新构建 | staging 和 prod 各自构建；覆盖同一版本标签；无法追至源提交 | 发布记录是否含 commit、build、依赖、配置、制品 digest 和审批 | [12-Factor Build-Release-Run](https://12factor.net/build-release-run) |
| 44 | 规范与实践：公共 API 版本、兼容迁移和 flag 生命周期 | 声明公共 API 后按破坏性、兼容功能、修复递增版本；迁移可前后兼容；临时 flag 有退出计划 | 无公共 API 却机械 SemVer；可变 tag；长期 flag 变成第二套架构 | 版本是否不可修改；兼容矩阵、迁移回退、flag owner 和到期日是否存在 | [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html) |
| 45 | 控制：渐进发布、金丝雀与回滚 | 先向小流量暴露新二进制或配置，与控制组比较，再扩容或回滚 | 样本不可比却直接比较；只看技术指标不看业务正确性；回滚未演练 | 是否预设观察窗、成功与停止条件、自动暂停和迁移回退方案 | [Google SRE Workbook, Canarying Releases](https://sre.google/workbook/canarying-releases/) |
| 46 | 实践：小批量、持续集成和提交门禁 | 尽早合并小变更；每次提交运行可重复的分层门禁并快速反馈 | 长期红灯继续合并；全部慢测放每次提交；门禁失败无 owner | 主干是否始终可构建；红灯修复时长、变更大小和失败归属是否可见 | [Google SWE Book, Continuous Integration](https://abseil.io/resources/swe-book/html/ch23.html) |

### 4.6 事件响应与交付指标

| # | 类型与名称 | 核心命题与适用条件 | 反例或误用 | 可执行检查 | 一手来源 |
|---:|---|---|---|---|---|
| 47 | 控制：IR 融入风险管理全周期 | 准备先于事件；检测、响应、恢复与资产、身份、备份和供应链联动 | 只有联系人表；事件发生才决定权限、证据和通报流程 | 计划是否覆盖准备、检测、分析、遏制、恢复、通知和改进 | [NIST SP 800-61r3，2025-04-03](https://csrc.nist.gov/pubs/sp/800/61/r3/final) |
| 48 | 实践与控制：明确事件指挥、通信和证据 | 明确 IC、Operations、Communications、Planning；一个实时事件文档，显式交接，授权角色才改生产 | 多人同时救火；技术负责人承担全部沟通；无时间线和证据保全 | 演练能否迅速确认指挥者、频道、状态页、决策日志和升级路径 | [Google SRE, Managing Incidents](https://sre.google/sre-book/managing-incidents/)、[CISA Incident Response Playbooks，2021](https://www.cisa.gov/sites/default/files/publications/Cybersecurity_Incident_Vulnerability_Response_Playbooks_508C.pdf) |
| 49 | 实践：无责复盘、行动负责和演练 | 分析影响、时间线、触发与促成因素、检测、缓解和措施效果；行动项有单一 owner、期限和验证 | 无责变成无人负责；根因只写人为错误；复盘无行动项 | 行动项是否按风险排序并验证；相似事故是否做趋势分析和演练 | [Google SRE, Postmortem Culture](https://sre.google/sre-book/postmortem-culture/)、[Lessons Learned and DiRT](https://sre.google/sre-book/lessons-learned/) |
| 50 | 指标：DORA 五项交付性能 | 当前五项为变更前置时间、部署频率、失败部署恢复时间、变更失败率、部署返工率；联合衡量吞吐与不稳定性 | 仍称四大指标；跨异构团队排名；单项优化；直接绑定个人奖惩 | 在同一服务和窗口看趋势并联合解释；记录数据来源和偏差 | [DORA Metrics，当前五指标](https://dora.dev/guides/dora-metrics/)、[DORA Metrics History，2026-01-02 更新](https://dora.dev/insights/dora-metrics-history/) |

## 5. 架构、设计理论与方法

类型：`S` 标准，`T` 形式理论，`E` 实证规律，`P` 原则/启发式，`R` 方法/实践。标准只有被采纳后才构成项目义务；理论只在其假设内成立；原则用于权衡而不是评分。

### 5.1 基础、生命周期与需求工程

| # | 规则或理论 | 适用命题 | 误用与可执行检查 | 一手来源 |
|---:|---|---|---|---|
| 1 | SWEBOK v4.0a｜知识体系 | 用 18 个知识域检查专业覆盖面 | 不是强制流程或成熟度认证；检查各知识域是否有 owner 和验证面 | [IEEE CS SWEBOK](https://www.computer.org/education/bodies-of-knowledge/software-engineering) |
| 2 | 生命周期过程｜S | 12207 从构想到退役给出可裁剪、可迭代的过程框架 | 不等同瀑布；检查裁剪理由、输入、输出、责任和追踪 | [ISO/IEC/IEEE 12207:2026](https://www.iso.org/standard/90219.html) |
| 3 | 需求工程闭环｜S | 需求要经历获取、分析、验证、确认、沟通、记录和管理 | PRD 写完不等于需求完成；检查来源、理由、优先级、验收和 owner | [ISO/IEC/IEEE 29148:2018](https://www.iso.org/standard/72089.html) |
| 4 | 需求质量｜S | 单项需求应必要、适当、无歧义、完整、单一、可行、可验证和正确；需求集还要一致 | “更详细”不等于可验证；检查模糊量词、复合义务、冲突和边界 | [ISO/IEC/IEEE 29148:2018](https://www.iso.org/standard/72089.html) |
| 5 | Verification / Validation｜S | verification 问“是否符合规定”，validation 问“是否适合真实用途” | 测试通过不能替代用户确认；两类证据和责任人必须分开 | [ISO/IEC/IEEE 29148:2018](https://www.iso.org/standard/72089.html) |
| 6 | 双向追踪与变更管理｜S/R | 需求与来源、设计、实现、测试和发布建立可维护追踪 | 追踪链接存在不证明内容正确；抽样正向、反向和变更影响 | [ISO/IEC/IEEE 29148:2018](https://www.iso.org/standard/72089.html) |
| 7 | Zave–Jackson 需求问题｜T | 在共同语言中，领域假设 `K` 与机器规约 `S` 应蕴涵需求 `R` | 不把业务目标全写成软件功能；列出环境假设及其失效行为 | [Zave & Jackson 1997](https://doi.org/10.1145/237432.237434) |
| 8 | User Story 3Cs / INVEST｜P/R | story 是 Card、Conversation、Confirmation；INVEST 帮助迭代切分 | 一行故事不是完整规约；检查对话、确认、价值、依赖和大小 | [Bill Wake 2003](https://xp123.com/invest-in-good-stories-and-smart-tasks/) |
| 9 | Given–When–Then｜R | 用领域语言表达上下文、事件和可观察结果 | 不应退化成 UI 点击脚本或内部实现断言；覆盖正常、边界、失败示例 | [Cucumber Gherkin](https://cucumber.io/docs/gherkin/reference/) |
| 10 | BCP 14 关键词｜S/R | `MUST` 是绝对要求，`SHOULD` 允许经权衡例外，`MAY` 真正可选 | 先声明词义；每个 MUST 必须必要且可验证，SHOULD 偏离要留理由 | [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119)、[RFC 8174](https://www.rfc-editor.org/rfc/rfc8174) |

### 5.2 模块化、设计与代码结构

| # | 规则或理论 | 适用命题 | 误用与可执行检查 | 一手来源 |
|---:|---|---|---|---|
| 11 | No Silver Bullet｜论证/观察性启发式 | 软件有本质与偶然困难；单一技术不能保证数量级普遍提升 | 不等于工具无用；提效主张必须限定任务、基线、质量和维护成本 | [Brooks 1986](https://www.cs.unc.edu/techreports/86-020.pdf) |
| 12 | Information Hiding｜P | 模块隐藏最可能变化的设计决策，而非按处理步骤机械拆分 | 私有字段或包装层本身不等于信息隐藏；看变化传播范围和接口稳定性 | [Parnas 1972](https://doi.org/10.1145/361598.361623) |
| 13 | Separation of Concerns｜P | 推理时分离关注点，同时显式处理组合关系 | 不是每个 concern 都建一层/服务；检查组合点和横切后果 | [Dijkstra EWD447](https://www.cs.utexas.edu/~EWD/transcriptions/EWD04xx/EWD447.html) |
| 14 | High Cohesion / Low Coupling｜P/E | 聚合共同变化的职责，减少跨模块知识、数据和时序依赖 | “零耦合”会制造消息链和间接层；检查目的、依赖方向及修改扩散 | [Stevens et al. 1974](https://doi.org/10.1147/sj.132.0115) |
| 15 | DRY｜P | 消除同一知识和意图的多重权威表示 | 不是文本零重复；只有因同一业务原因共同变化时才抽取 | [Hunt & Thomas, DRY](https://media.pragprog.com/titles/tpp20/dry.pdf) |
| 16 | SRP/OCP/ISP/DIP｜P | 围绕真实变化轴、稳定抽象、客户端需要和策略依赖设计 | 一类一方法、凡事接口、容器等于 DIP 均属误用；检查间接层是否真降成本 | [Martin 2000](https://objectmentor.com/resources/articles/Principles_and_Patterns.pdf) |
| 17 | Liskov Substitution｜T/P | 子类型必须保持父类型的行为性质、前后条件和不变量 | 编译通过不够；对全部实现运行同一契约测试并检查异常、副作用、历史约束 | [Liskov & Wing 1994](https://doi.org/10.1145/197320.197383) |
| 18 | Design by Contract｜T/R | 前置条件定义调用者义务，后置条件定义供应者保证，不变量定义有效状态 | 断言不能代替不可信输入校验；检查契约与真实需求、失败责任和继承规则 | [Meyer 1992](https://se.inf.ethz.ch/~meyer/publications/computer/contract.pdf) |
| 19 | Law of Demeter｜P | 模块尽量只知道直接协作者，减少对远端结构的知识 | 链式调用不必一律禁止；新增委托应表达真实能力并降低耦合 | [Lieberherr et al. 1988](https://www2.ccs.neu.edu/research/demeter/biblio/LoD.html) |

补充启发式：`KISS` 倾向选择满足需求的最简单可验证方案；`YAGNI` 反对为尚无证据的未来需求建能力；二者都不能用来删掉安全、迁移、可观测性或已确认的扩展要求。

### 5.3 架构与分布式系统

| # | 规则或理论 | 适用命题 | 误用与可执行检查 | 一手来源 |
|---:|---|---|---|---|
| 20 | Architecture Description｜S | 由 stakeholder、concern、viewpoint、view、model kind 和 rationale 构成架构描述 | 一张组件图不够；每个视图要说明受众、问题、模型语义和一致性 | [ISO/IEC/IEEE 42010:2022](https://www.iso.org/standard/74393.html) |
| 21 | Ports and Adapters｜P | 应用核心用 ports 表达契约，由 adapters 连接 UI、DB、测试和外部系统 | 不要求固定层数或每函数一个 port；核心应能脱离具体基础设施运行 | [Cockburn 2005](https://alistair.cockburn.us/hexagonal-architecture) |
| 22 | DDD / Bounded Context｜P/R | 复杂领域中，一个上下文内保持统一语言和模型，上下文关系显式映射 | DDD 不等于实体/仓库模板；检查术语、所有权、语义冲突和集成关系 | [Evans DDD Reference](https://www.domainlanguage.com/ddd/reference/) |
| 23 | ADR｜R | 以不可覆写的小记录保存 context、decision、status 和 consequences | ADR 存在不等于批准或实现；保留负面后果、替代项和 superseded 链 | [Nygard 2011](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions) |
| 24 | C4 Model｜R | 按受众用 Context、Container、Component、Code 层级缩放架构视图 | 不把所有层级塞一图；标边界、职责、技术、关系方向及更新 owner | [C4 Model](https://c4model.com/diagrams) |
| 25 | REST｜T/P | REST 是协同约束形成的架构风格，不是 JSON over HTTP | 声明采用哪些约束、预期质量收益及未采用约束的代价 | [Fielding 2000](https://ics.uci.edu/~fielding/pubs/dissertation/abstract.htm) |
| 26 | CAP｜T | 在异步网络发生分区的模型下，原子一致性与所有请求终止的可用性不能同时保证 | 不是日常“任选两个”；逐操作声明分区行为、模型定义、降级与恢复 | [Gilbert & Lynch 2002](https://doi.org/10.1145/564585.564601) |
| 27 | Microservices｜P/风格 | 只在独立部署、扩缩、自治和隔离收益大于网络、数据、平台与认知成本时拆分 | 不按表或技术层拆；模块化单体通常是低复杂度基线 | [Lewis & Fowler 2014](https://martinfowler.com/articles/microservices.html)、[trade-offs](https://martinfowler.com/articles/microservice-trade-offs.html) |

分布式扩展规则：先定义一致性模型、时钟与排序语义；写操作用幂等键或去重；重试只针对可识别的暂时失败；事件的“至少一次/至多一次/效果上恰好一次”必须分开；异步化、CQRS、事件溯源和 serverless 只有在解耦、审计、弹性或团队收益超过一致性、调试和平台锁定成本时采用。Lamport 时钟说明“发生先后”可被部分排序，但不能凭本地墙钟推导全局因果（[Lamport 1978](https://www.microsoft.com/en-us/research/publication/time-clocks-ordering-events-distributed-system/)）。

### 5.4 建模与形式化方法

| # | 规则或理论 | 适用命题 | 误用与可执行检查 | 一手来源 |
|---:|---|---|---|---|
| 28 | UML 2.5.1｜S/语言 | 按结构或行为问题选择标准图语义 | UML 不是开发方法；只建有受众和维护价值的模型 | [OMG UML](https://www.omg.org/spec/UML/) |
| 29 | BPMN 2.0.2｜S/语言 | 用事件、活动、网关和消息表达业务过程及协作 | 外观像流程图不等于 BPMN；检查 token、异常、消息和终止语义 | [OMG BPMN](https://www.omg.org/spec/BPMN/) |
| 30 | SysML 2.0｜S/语言 | 适合软硬件、人员和流程构成的跨学科系统 | 纯软件小项目不必全量采用；模型仍需与接口、测试和实物证据回链 | [OMG SysML](https://www.omg.org/spec/SysML) |
| 31 | Statecharts / SCXML｜T/S | 用层次、正交并发、事件和守卫建模复杂反应式系统 | 不是普通流程图；测试非法转换、竞态、优先级和事件队列 | [Harel 1987](https://doi.org/10.1016/0167-6423%2887%2990035-9)、[SCXML](https://www.w3.org/TR/scxml/) |
| 32 | Hoare Logic｜T | 用前置条件、程序、后置条件和不变量证明程序性质 | 正确证明错误规格仍无意义；显式记录未建模环境假设 | [Hoare 1969](https://doi.org/10.1145/363235.363259) |
| 33 | TLA+｜T/R | 用状态、动作、不变量、活性和公平性分析并发协议 | 模型通过不证明实现正确；反例要回写实现测试并审查模型映射 | [TLA+](https://lamport.org/tla/tla.html) |
| 34 | Stepwise Refinement｜T/R | 逐步细化任务与数据表示，同时保持上层约束 | 不等于单向瀑布；每一步都需说明保持了什么性质 | [Wirth 1971](https://doi.org/10.1145/362575.362577) |

形式验证结论必须写成“在模型 M、假设 A 和可信计算基 T 下满足性质 P”。它不能自动证明业务意图正确、模型与实现一致或运行环境可信；AI 生成的规格、lemma 和证明脚本仍是 candidate。

### 5.5 过程、流动与团队

| # | 规则或理论 | 适用命题 | 误用与可执行检查 | 一手来源 |
|---:|---|---|---|---|
| 35 | Spiral Model｜R | 每轮按最大风险选择原型、分析、实现或验证活动 | 不是重复瀑布；检查本轮风险、降险证据和下一轮依据 | [Boehm 1988](https://doi.org/10.1109/2.59) |
| 36 | Agile Manifesto｜P | 偏好互动、可工作软件、协作与响应变化，同时承认另一侧也有价值 | 敏捷不等于无文档、无计划或无架构；检查短反馈、价值和可持续性 | [Agile Manifesto](https://agilemanifesto.org/)、[Principles](https://agilemanifesto.org/principles.html) |
| 37 | Scrum 2020｜R | 用透明、检视、适应及明确责任、工件和承诺管理复杂工作 | 删除核心要素仍称 Scrum 无意义；检查 Goal、DoD、增量和真实适应 | [Scrum Guide 2020](https://scrumguides.org/scrum-guide.html) |
| 38 | Kanban 2025｜R | 定义和可视化 workflow，控制 WIP，以 throughput、age、cycle time 管流动 | 看板列不等于 Kanban；检查拉动规则、WIP 和历史分布 | [Kanban Guide 2025](https://kanbanguides.org/the-kanban-guide/2025.5/) |
| 39 | Little's Law｜T | 稳态、有限均值、同一边界下 `L = λW` | 不是因果律；核对边界、时间窗、稳定性和尾部分布 | [Little 1961](https://doi.org/10.1287/opre.9.3.383) |
| 40 | Conway's Law｜E | 系统设计倾向受组织沟通结构约束 | 不是宿命，也不证明多 agent 更正确；检查技术依赖与沟通边界 | [Conway 1968](https://melconway.com/Home/pdf/committees.pdf) |
| 41 | Brooks's Law｜经验性论证 | 已延期且不可任意分割的工作，增员可能因培训和沟通变得更慢 | 不是永远不能增员；量化 onboarding、并行性和净贡献时间 | [Brooks 1975/1995，Addison-Wesley](https://www.informit.com/store/mythical-man-month-essays-on-software-engineering-anniversary-9780201835953) |
| 42 | Psychological Safety｜E | 能提出问题、承认错误和表达异议，有助于团队学习 | 不等于舒适、无冲突或无责任；检查坏消息能否上达及领导反应 | [Edmondson 1999](https://doi.org/10.2307/2666999) |
| 43 | Shared Mental Models｜E | 对任务、设备、角色和交互形成足够一致的心智模型可改善协调 | 文档存在不等于理解一致；用情景演练测试预期 | [Cannon-Bowers et al. 1991](https://doi.org/10.1177/154193129103501917) |
| 44 | Cognitive Load Theory｜E | 工作记忆有限，文档、接口和 onboarding 应减少非必要负担并渐进披露 | 不能据此直接证明某架构风格更优；按新手/专家实测关键任务 | [Sweller 1988](https://doi.org/10.1207/s15516709cog1202_4) |

### 5.6 维护、演化与兼容性

| # | 规则或理论 | 适用命题 | 误用与可执行检查 | 一手来源 |
|---:|---|---|---|---|
| 45 | 软件维护过程｜S | 维护覆盖分析、修改、迁移和退役，不只修 bug | 检查变更分类、影响、批准、回归、迁移和退役责任 | [ISO/IEC/IEEE 14764:2022](https://www.iso.org/standard/80710.html) |
| 46 | Lehman's Laws｜E | E-type 系统呈持续变化、复杂性增长和反馈调节等经验规律 | 不是物理定律；只对相应系统按版本数据检验，并持续简化 | [Lehman et al. 1997](https://users.ece.utexas.edu/~perry/work/papers/feast1.pdf) |
| 47 | Technical Debt｜P | 为早期交付接受的理解/结构缺口会产生持续额外成本，应有偿还条件 | 不是所有旧代码或 bug；记录 principal、interest、触发器和 owner | [Cunningham 1992](https://c2.com/doc/oopsla92.html) |
| 48 | Refactoring｜R | 以小步、不改变外部可观察行为的变换改善内部结构 | 功能修改或大重写不应冒充重构；需行为基线并保持每步绿色 | [Fowler, Refactoring](https://martinfowler.com/bliki/DefinitionOfRefactoring.html) |
| 49 | Hyrum's Law｜观察性启发式 | 用户足够多时，几乎所有可观察行为都可能有人依赖 | 不是冻结一切；界定支持契约，用 consumer tests、遥测、弃用和版本化管理未知依赖 | [Hyrum's Law](https://www.hyrumslaw.com/) |
| 50 | Leaky Abstractions｜观察性启发式 | 非平凡抽象会在某些故障、性能或资源边界泄漏 | 不应因此拒绝抽象；记录泄漏边界、诊断入口并防止扩散 | [Spolsky 2002](https://www.joelonsoftware.com/2002/11/11/the-law-of-leaky-abstractions/) |

## 6. AI Coding：实践、风险与验证

本章把 `model + prompt + context + tools + harness + environment` 视为一个工程系统。类型列沿用第 1.1 节；“实践”与“方法”均需本地验证，“控制”按风险裁剪，“指标/实证”只提供测量或样本内证据。来源代码见 6.9；`N` 为标准/框架，`O/OA/GH/OW` 为官方指南，`AN` 为官方工程指南或明确标注的厂商案例，`E` 为原始实证。产品案例和样本内百分比只说明“可能”，不能直接外推。

### 6.1 任务、分解与控制循环

| # | 类型 | 规则 | 适用边界、失败模式与检查 | 来源 |
|---:|---|---|---|---|
| 1 | 实践 | 先选最简单可验证方案 | 稳定流程用确定性代码或 workflow；只有步骤和路径需动态推理时才上 agent。检查：不用 LLM 能否更可靠完成 | AN1、OA1 |
| 2 | 实践 | Workflow 与 agent 分开 | workflow 预定义路径，agent 动态选择过程；不要只因“更智能”扩大自治面 | AN1 |
| 3 | 规范/控制 | 任务契约可版本化、可协商 | 写目标、非目标、来源、假设、权限、输入输出、验收、证据、终态和 owner；prompt 不等于已确认需求 | N1、ISO29148 |
| 4 | 实践 | 先画依赖图再分工 | 只有无前置依赖的子任务并行；先完成共享事实、接口或基线 | AN1、OA4 |
| 5 | 实践 | Router 仅用于稳定分类 | 类别边界和专门处理器可评测时才路由；模糊路由会增加误分和维护成本 | AN1 |
| 6 | 实践 | 并行 workers 仅在读写独立时使用 | 显式列文件、资源、事实和外部副作用的读写集；冲突写入改为串行或唯一 owner | OA4、AN4 |
| 7 | 实践 | Orchestrator-workers 用于动态任务 | 中央 agent 负责分解、综合、冲突裁决和最终重验；不要把综合责任分散给全部 workers | AN1、AN4 |
| 8 | 方法 | Evaluator-optimizer 仅在有 rubric 时使用 | 仅在质量标准清晰、反馈可行动且迭代有上限时使用；无 rubric 会自我循环 | AN1、OA5 |
| 9 | 实践/控制 | 形成 observe–plan–act–check–verify 闭环 | 每步重新读取环境真值；计划和模型记忆不能替代当前文件、API、UI 或测试结果 | OA2、AN3 |
| 10 | 控制 | 预算、重试和停止条件显式 | 同时限定工具、轮次、时间、token、成本、并发和递归；规定可重试错误、幂等、退避、补偿及 `success/hold/failed-safe/owner-required` | OA2、SRE |
| 11 | 控制 | 概率组件置于确定性控制面内 | 授权、状态迁移、schema、不变量、预算和发布门由代码/策略执行；prompt 禁令不是安全边界 | N1、OA2、OW1 |
| 12 | 控制 | 长任务可恢复且工具幂等 | 用检查点、持久状态、唯一请求 ID 和安全重放；进程中断不应复制副作用 | AN3、OA6 |
| 13 | 实践/指标 | 多 agent 不是默认优化 | 只有可分解、可封装、可独立验证且协调成本低时使用；与单 agent 比质量、墙钟、成本、冲突和返工 | AN4、E5 |
| 14 | 实践 | 子 agent 交付结构化摘要并保留分歧 | 报结论、证据、置信度、未知、冲突和下一步；多数同源 agent 共识不能消除系统性不确定性 | OA4、AN4 |

### 6.2 仓库、上下文与实现纪律

| # | 类型 | 规则 | 适用边界、失败模式与检查 | 来源 |
|---:|---|---|---|---|
| 15 | 实践 | 编辑前读 owning layer、基线和契约 | 先复现问题，读实际候选、状态、差异、测试和权威文档；避免凭摘要改错层 | OA7、AN3 |
| 16 | 实践 | 每次只做一个可验证变化切片 | 小 diff、单一目的、明确验收；不要顺手清理邻近代码 | GH1、OA7 |
| 17 | 实践/控制 | 持久状态放在聊天之外 | 任务、决策、版本、证据和未完成项进入仓库或受控系统；聊天摘要不是 SSOT | AN3、OA7 |
| 18 | 实践 | 交付时工作区可解释 | 报 status、diff、执行检查、跳过项和原因；不覆盖用户 WIP，不把未提交变化冒充发布 | GH1、OA7 |
| 19 | 实践/方法 | 指令短、单义、去重复并做消融测试 | 同一规则只保留一个权威位置；规则变更要用代表任务比较，避免 prompt 叠加成冲突 | OA3、AN2 |
| 20 | 实践 | 指令保持正确抽象高度 | 写长期边界、权威来源和验证方式，不把容易漂移的实现细节全塞根指令 | OA3、AN2 |
| 21 | 实践 | 使用分层、路径特定、可版本化仓库说明 | 根规则管全局，深层规则管局部；冲突优先级可预测，大小受控 | OA3 |
| 22 | 实践 | 最小高信号上下文，按需检索 | 只加载当前任务所需事实、接口和证据；长上下文会稀释重要约束并增加攻击面 | AN2 |
| 23 | 实践 | 在自然里程碑压缩上下文 | 保留目标、决定、约束、ID、验证结果、阻塞和下一步；不要把旧推测压成事实 | AN2、AN3 |
| 24 | 实践 | 示例少而多样且权威 | 用正常、边界、失败的代表例；示例漂移会比无示例更危险 | OA5、AN2 |
| 25 | 实践/控制 | 工具最少、非重叠、可自描述 | schema、权限、副作用、错误类型和重试语义明确；多个相似工具会增加误选 | AN1、OA2 |
| 26 | 控制 | 结构化输出由服务端语义验证 | JSON/schema 只证明语法；还要校验跨字段不变量、领域规则、版本、来源和 unknown/null/hold | OA2、N1 |
| 27 | 控制 | 数据面与控制面分离 | 网页、检索、代码注释、日志、工具错误及下游模型输出默认是数据；升级成指令/权限/事实需显式规则与 owner | OA2、OW2 |
| 28 | 控制 | 一切 AI 产物从 candidate 开始 | 代码、命令、SQL、URL、需求、ADR、测试和 review 都需外部真值或 owning surface 验证 | N1、GH1、OW1 |
| 29 | 控制 | 在隔离、可丢弃、可复现环境执行 | 未知仓库和依赖不直接接触宿主凭据或生产；环境应能重建和销毁 | OA8、GH1 |
| 30 | 控制 | 固定并记录运行清单 | runtime、依赖、镜像、模型快照、effort、prompt、tools、harness、dataset、seed 可追溯 | N1、OA6 |
| 31 | 方法/指标 | 资源约束也是实验变量 | CPU、RAM、timeout、并发、网络和 egress 不一致会污染 benchmark；小分差先复测并报告 CI | AN6 |

### 6.3 权限、安全、供应链与副作用

| # | 类型 | 规则 | 适用边界、失败模式与检查 | 来源 |
|---:|---|---|---|---|
| 32 | 控制 | 默认只读和最小权限 | 写权限限定 workspace/branch；凭据按任务、范围和时效发放；做 deny-by-default 测试 | N1、OA8、GH1 |
| 33 | 控制 | 按威胁模型隔离文件、网络、秘密和控制通道 | “双 sandbox”只是实现模式；共享凭据或控制通道仍是同一失效域 | OA8、AN1 |
| 34 | 控制 | 高风险动作精确到本次批准 | 删除、发布、发送、支付、生产写、权限提升、敏感数据和高成本动作展示 target/参数/影响；改参后重批 | OA8、GH1 |
| 35 | 控制/人因 | 防止 approval fatigue | 低风险用安全 allowlist，高风险保留硬门；监测批准率、绕过和撤销，禁止泛化授权 | OA8、AN8 |
| 36 | 控制 | 提示注入用纵深防御 | 隔离外部内容，限制工具/数据/egress，动作前再授权，并维护间接注入回归集 | OA2、OW2、E1、E2 |
| 37 | 控制 | Prompt 不是秘密库或权限边界 | 不放 key、访问控制真值或不可泄漏策略；即使 prompt 泄露，服务端鉴权仍应安全 | OA2 |
| 38 | 控制 | 独立核验包、Action、脚本、URL、版本和许可证 | 防幻觉包、typosquat、恶意更新；看 registry、签名、CVE、license、lockfile 和 SBOM，CI action 固定不可变 revision | N1、GH1、OW1 |
| 39 | 控制 | Agent 产出与合并/发布权分离 | 在受限 branch/worktree 工作；branch protection、required checks、owner approval 和 session attribution 可追踪 | GH1、OA8 |

[OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) 可作为 agent 威胁模型起点：ASI01 目标劫持、ASI02 工具误用、ASI03 身份与权限滥用、ASI04 agentic 供应链、ASI05 意外代码执行、ASI06 记忆与上下文投毒、ASI07 不安全的 agent 间通信、ASI08 级联故障、ASI09 人机信任利用、ASI10 失控 agent。Top 10 是风险导航，不是安全认证或完整威胁模型。

### 6.4 测试、审查与验收

| # | 类型 | 规则 | 适用边界、失败模式与检查 | 来源 |
|---:|---|---|---|---|
| 40 | 方法/实践 | TDD 按任务条件采用 | bug、纯逻辑和明确契约可先观察正确失败再实现；探索/UI 可先学习后固化契约 | GH1、AN7 |
| 41 | 控制 | 不得为过门禁弱化测试 | 禁止静默删除、skip 或降低断言；测试契约确需变化时单独说明并由 owner 审查 | GH1、OW1 |
| 42 | 方法/实践 | 按风险组合验证，不迷信固定金字塔 | unit、contract、integration、E2E、type、static、security、fuzz、smoke 映射真实风险 | N1、GH1 |
| 43 | 方法 | 从 owning surface 验证 | UI 用真实浏览器/可访问性，API 用契约/集成，迁移走真实升级，发布用目标环境；低层绿灯不证明用户旅程 | N1、AN3 |
| 44 | 控制/方法 | 实现与复核分开，但不要伪称 IV&V | fresh-context reviewer 可减少即时偏差；同模型、prompt、数据或前提只算 second pass。高风险独立验证需不同人员/规格/工具/攻击视角 | N1、OA4、GH1 |
| 45 | 控制 | 人类责任按风险分级且不可外包 | 合并、发布和部署有具名 owner；鉴权、密码学、迁移、依赖、CI/IaC、生产控制逐行/逐语义审查并独立测试；机械低风险项可强门禁加抽样 | N1、GH1、OW1 |

### 6.5 Evals、基准与生产力

| # | 类型 | 规则 | 适用边界、失败模式与检查 | 来源 |
|---:|---|---|---|---|
| 46 | 方法 | Eval-driven development | 先把真实需求、事故和失败写成任务与 grader，再改模型、prompt、tools 或 harness；每次修复加回归 | OA5、AN5 |
| 47 | 方法 | 数据集覆盖代表、边界、负例、对抗和私有 holdout | 训练/调优材料不得进入隔离 holdout；按生产分布采样并记录覆盖矩阵 | OA5、AN5、E3 |
| 48 | 方法/指标 | 随机系统多 trial 并报告分布 | 预注册次数，报告均值、方差/CI 和失败分布；agent failure 与 infra failure 分开；确定性任务无需机械重复 | AN5、AN6 |
| 49 | 方法 | 同时评 outcome、policy checkpoint 和 trace | 最终状态优先，过程用于诊断越权、浪费和首次失败；看似合理的 trace 不替代结果 | OA5、AN5 |
| 50 | 方法 | 优先确定性 grader，LLM judge 持续校准 | rubric、golden set、对抗测试和双盲人评一致率；同源模型自评有偏置 | OA5、AN5 |
| 51 | 控制/方法 | 分开 capability、regression、production acceptance | 能力探索、冻结回归、canary/SLO 和业务验收回答不同问题；eval 通过不是发布批准 | N2、AN5 |
| 52 | 控制/方法 | 评估污染按持续对抗治理 | 时间切分、滚动新题、私有 canary、检索隔离、近邻/答案扫描和异常轨迹审计；URL blocklist 不够 | E3、AN9 |
| 53 | 实证/指标 | 生产力只在目标团队和真实仓库实测 | 同时测周期、返工、缺陷、安全、审查时间和任务选择偏差；狭窄实验的加速或减速均不可普遍外推 | E4、E5 |
| 54 | 实践/指标 | 成本/延迟优化在质量和安全门之后 | 按真实任务比较质量、成功率、安全、墙钟、token/$、重试及人工时间的 Pareto 前沿 | OA1、AN1 |

### 6.6 追溯、运行与治理

| # | 类型 | 规则 | 适用边界、失败模式与检查 | 来源 |
|---:|---|---|---|---|
| 55 | 控制 | 建立风险相称的端到端 lineage | 追踪来源→转换→决策→产物→验证→批准/发布，保存版本/哈希、状态和 owner；不必永久记录每个 token，需脱敏和限存 | N1、N2、OA6 |
| 56 | 控制 | 关键失败 fail closed | 鉴权、策略、未知 target、解析或审查器故障时不执行动作；有界重试后进入人工升级或安全终态 | N1、OA8 |
| 57 | 框架/控制 | Govern–Map–Measure–Manage 循环治理 | 风险 register、owner、阈值、复审频率和残余风险批准持续更新；一次清单不是治理完成 | N2、N3 |
| 58 | 控制 | 建立 AI Coding 事故响应 | 隔离、撤销凭据、回滚、保存 trace、通知、复盘，并把事故转成测试、威胁用例和控制改进 | N1、N2、OW1 |

### 6.7 三个不可跨越的权属边界

1. **事实**由 owning surface、权威来源或外部真值确认；自动测试可以在其明确契约内形成 verified 证据，但 AI、截图、测试和多 agent 共识都不能单独证明更宽的业务真值。
2. **风险**由有权限且可问责的人接受；自动门禁可以拒绝，但不能伪造“已批准”。
3. **发布**由正式 owner 与 release pointer 决定；`observed` 或 `automated-evidence` 不等于 `verified / approved / released`。

### 6.8 SP 800-218A 的适用对象

[NIST SP 800-218A](https://csrc.nist.gov/pubs/sp/800/218/a/final) 是生成式 AI / dual-use foundation model 的 SSDF Community Profile，明确面向三类主体：AI 模型生产者、使用这些模型的 AI 系统生产者，以及这些 AI 系统的采购方。普通仅使用 coding assistant、且不生产或采购相应 AI 系统的团队，不应自动宣称 218A 直接适用；其软件开发基线通常仍从 [SP 800-218 v1.1](https://doi.org/10.6028/NIST.SP.800-218) 出发，并按实际角色和风险结合 [AI RMF 1.0](https://doi.org/10.6028/NIST.AI.100-1) / [GenAI Profile](https://doi.org/10.6028/NIST.AI.600-1)。具体适用性需由安全、采购或合规 owner 确认。

### 6.9 AI Coding 一手来源代码

| 代码 | 来源 |
|---|---|
| N1 | [NIST SP 800-218 SSDF v1.1](https://doi.org/10.6028/NIST.SP.800-218) |
| N2 | [NIST AI RMF 1.0](https://doi.org/10.6028/NIST.AI.100-1) |
| N3 | [NIST AI 600-1 GenAI Profile](https://doi.org/10.6028/NIST.AI.600-1) |
| ISO29148 | [ISO/IEC/IEEE 29148:2018](https://www.iso.org/standard/72089.html) |
| OA1 | [OpenAI, How OpenAI uses Codex](https://openai.com/business/guides-and-resources/how-openai-uses-codex/) |
| OA2 | [OpenAI, Safety in building agents](https://developers.openai.com/api/docs/guides/agent-builder-safety) |
| OA3 | [OpenAI, AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md) |
| OA4 | [OpenAI, Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents) |
| OA5 | [OpenAI, Evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices)；概念适用，页面所述旧 Evals 产品将弃用，不应形成长期产品依赖 |
| OA6 | [OpenAI API Overview](https://developers.openai.com/api/reference/overview) |
| OA7 | [OpenAI, Harness engineering](https://openai.com/index/harness-engineering/)；单组织案例 |
| OA8 | [OpenAI, Agent approvals and security](https://learn.chatgpt.com/docs/agent-approvals-security) |
| AN1 | [Anthropic, Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) |
| AN2 | [Anthropic, Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) |
| AN3 | [Anthropic, Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)；单团队案例 |
| AN4 | [Anthropic, Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)；百分点与 token 倍数不可外推 |
| AN5 | [Anthropic, Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) |
| AN6 | [Anthropic, Infrastructure noise in agentic coding evals](https://www.anthropic.com/engineering/infrastructure-noise) |
| AN7 | [Anthropic, Claude Code best practices](https://www.anthropic.com/engineering/claude-code-best-practices) |
| AN8 | [Anthropic, Claude Code auto mode](https://www.anthropic.com/engineering/claude-code-auto-mode)；单产品案例 |
| AN9 | [Anthropic, Eval awareness in BrowseComp](https://www.anthropic.com/engineering/eval-awareness-browsecomp)；机制可类推，发生率不可直接套 coding |
| GH1 | [GitHub Copilot best practices](https://docs.github.com/en/copilot/get-started/best-practices)、[review output](https://docs.github.com/en/copilot/how-tos/copilot-on-github/use-copilot-agents/review-copilot-output) |
| OW1 | [OWASP Secure Coding with AI Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secure_Coding_with_AI_Cheat_Sheet.html) |
| OW2 | [OWASP LLM/GenAI and Agentic Security](https://genai.owasp.org/) |
| E1 | [InjecAgent, ACL Findings 2024](https://aclanthology.org/2024.findings-acl.624/) |
| E2 | [AgentDojo, NeurIPS 2024](https://proceedings.nips.cc/paper_files/paper/2024/hash/97091a5177d8dc64b1da8bf3e1f6fb54-Abstract-Datasets_and_Benchmarks_Track.html) |
| E3 | [LiveCodeBench, ICLR 2025](https://proceedings.iclr.cc/paper_files/paper/2025/hash/94074dd5a072d28ff75a76dabed43767-Abstract-Conference.html) |
| E4 | [Peng et al. 2023 RCT](https://arxiv.org/abs/2302.06590)；95 人、单一 JavaScript 任务，样本内快 55.8% |
| E5 | [METR 2025 RCT](https://metr.org/Early_2025_AI_Experienced_OS_Devs_Study-paper.pdf)、[2026 update](https://metr.org/blog/2026-02-24-uplift-update)；熟悉仓库样本曾慢 19%，后续估计受选择偏差影响 |
| SRE | [Google SRE, Cascading Failures](https://sre.google/sre-book/addressing-cascading-failures/) |

## 7. 2026 版本纠偏

| 常见旧口径 | 截至 2026-08-31 的当前口径 |
|---|---|
| ISO/IEC/IEEE 12207:2017 | 当前版为 12207:2026，2017 已撤回 |
| IEEE 730-2014 | 当前版为 IEEE 730-2026，2026-08-21 发布 |
| OWASP ASVS 4.x | 当前稳定版为 5.0.0，2025-05-30 发布 |
| OWASP LLM Top 10 2025 | 当前资源为 [OWASP GenAI LLM Top 10 2026](https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/)，2026-08-03 发布 |
| 缺少 agent 专项风险表 | [OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) 于 2025-12-09 发布，适合作为威胁建模起点 |
| SLSA 1.0 | 当前版为 1.2，2025-11-24 发布 |
| NIST SP 800-61r2 | 当前版为 SP 800-61r3，2025-04-03 发布并取代 r2 |
| DORA 四项指标 | 当前官方口径为五项，新增部署返工率并重构恢复时间分组 |
| OpenTelemetry 旧版规范 | 当前规范页面显示 1.60.0；实现需锁定 SDK 和语义约定版本 |
| NIST Privacy Framework 1.1 已定稿 | 最终版仍是 1.0（2020）；不得把草案当最终标准 |
| DORA 2025 初版 | 当前勘误版为 v2025.2，见[官方勘误](https://dora.dev/research/2025/errata/) |

## 8. 争议命题与条件性判定

| 命题 | 当前判定 | 成立条件与边界 | 三线交叉验证结论 |
|---|---|---|---|
| DRY 必须贯彻 | 条件性启发式 | 消除同一知识的重复，不是消除所有相似代码；错误抽象可能比少量重复更坏 | 三线一致；判断标准是“是否因同一业务原因共同变化” |
| SOLID 是普适规则 | 条件性启发式 | 对存在变化压力、替换需求和多实现边界的模块有价值；小型稳定模块机械拆接口会增加认知负担 | 三线一致；LSP 的行为契约强于其余设计启发式 |
| 微服务优于单体 | 否 | 仅在独立部署、团队自治、扩缩容或故障隔离收益超过分布式复杂度时成立；模块化单体是合理基线 | 三线一致；可靠性控制不能单独决定架构风格 |
| 测试金字塔比例固定 | 否；原则条件性成立 | 多数快速窄测试、少数昂贵大测试是成本模型，不是固定比例；协议、数据、UI、硬件系统可不同 | 三线一致；以风险覆盖、诊断性、速度和稳定性评估，而非形状 |
| TDD 必须采用 | 条件性实践 | 适合可例示行为、复杂规则和高回归风险代码；原型、生成代码、迁移、视觉工作可用其他验证顺序 | 三线一致；不以测试书写顺序替代最终质量证据 |
| Trunk-based 必然最佳 | 条件性实践 | 小批量、高自动化、快速集成时通常有效；隔离认证、硬件周期、外部审查或多版本维护可能需受控分支 | 三线一致；目标是短反馈和低集成漂移，而非特定分支名 |
| AI 输出必须人工逐行审查 | 应改为风险分级控制 | 安全关键、鉴权、迁移、生产配置、未知依赖、不可逆操作应逐行或逐语义审查；机械生成物可用可信生成器和确定性门禁 | 三线一致；低风险可缩小人工范围，但最终责任和授权不能外包 |
| 多 agent 必然更优 | 否 | 仅在任务可分、上下文可封装、验证可独立且协调成本低时可能更优；共享前提会产生相关性错误 | 三线一致；同源多 agent 只是 second pass，不是 IV&V，必须和单 agent 实测 |
| AI 必然提高交付效率 | 否 | AI 是社会技术系统的放大器；生成时间节省可能转移为审计、返工和不稳定性 | 三线一致；现代实验结果方向不一，只能在目标团队/仓库测端到端效果 |
| 指标可直接作为绩效目标 | 否 | 覆盖率、缺陷数、提交数和 DORA 指标应看同一系统内趋势并与定性证据、反指标联合使用 | 三线一致；指标是系统信号，目标化会诱发选择偏差和博弈 |

## 9. 项目采纳前待决问题

1. AI 生成代码的审查等级如何按可逆性、数据敏感度、权限和爆炸半径划分。
2. 自动测试、静态分析、形式化验证与人工批准分别能证明什么，不能证明什么。
3. 测试覆盖率、mutation score、SLO 和 DORA 是否设置阈值；阈值由谁批准、如何防止指标博弈。
4. 架构风格、分支策略、发布策略是否与 Novel Engine 当前单机自托管形态匹配。
5. SLSA 目标级别、SBOM 格式、签名身份和消费端验证是否值得进入项目路线图。
6. trace、日志、prompt 和模型输入输出的隐私字段、保留期和访问边界。
7. 多 agent 交叉审查是否真正独立，如何避免共享模型、上下文和错误假设造成伪共识。
8. 研究结论转为项目政策时，需要哪些 issue、ADR、OpenSpec、验证和 owner 批准。

## 10. 来源索引

### 10.1 软件工程、质量与测试

- [IEEE Computer Society, SWEBOK Guide v4.0a](https://www.computer.org/education/bodies-of-knowledge/software-engineering)
- [ISO/IEC/IEEE 12207:2026](https://www.iso.org/standard/90219.html)
- [IEEE 730-2026](https://standards.ieee.org/ieee/730/10854/)
- [ISO/IEC 25010:2023](https://www.iso.org/standard/78176.html)
- [ISO/IEC 25019:2023](https://www.iso.org/standard/78177.html)
- [ISO/IEC/IEEE 29119-1:2022](https://www.iso.org/standard/81291.html)
- [ISO/IEC/IEEE 29119-2:2021](https://www.iso.org/standard/79428.html)
- [ISO/IEC/IEEE 29119-3:2021](https://www.iso.org/standard/79429.html)
- [ISO/IEC/IEEE 29119-4:2021](https://www.iso.org/standard/79430.html)
- [Google Software Engineering, Testing Overview](https://abseil.io/resources/swe-book/html/ch11.html)
- [Google Software Engineering, Larger Testing](https://abseil.io/resources/swe-book/html/ch14.html)
- [Google Software Engineering, Continuous Integration](https://abseil.io/resources/swe-book/html/ch23.html)
- [Google Engineering Practices, Code Review](https://google.github.io/eng-practices/review/)
- [QuickCheck 原始论文，2000](https://doi.org/10.1145/351240.351266)
- [Metamorphic Testing 原始报告，1998](https://www.cse.ust.hk/faculty/scc/publ/CS98-01-metamorphictesting.pdf)
- [Mutation Testing 原始论文，1978](https://doi.org/10.1109/C-M.1978.218136)
- [Google Fuzzing Documentation](https://github.com/google/fuzzing/blob/master/docs/intro-to-fuzzing.md)

### 10.2 可靠性、可观测性与事件响应

- [Google SRE, Service Level Objectives](https://sre.google/sre-book/service-level-objectives/)
- [Google SRE Workbook, Error Budget Policy](https://sre.google/workbook/error-budget-policy/)
- [Google SRE, Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)
- [Google SRE, Cascading Failures](https://sre.google/sre-book/addressing-cascading-failures/)
- [Google SRE Workbook, Canarying Releases](https://sre.google/workbook/canarying-releases/)
- [Google SRE, Managing Incidents](https://sre.google/sre-book/managing-incidents/)
- [Google SRE, Postmortem Culture](https://sre.google/sre-book/postmortem-culture/)
- [OpenTelemetry Specification 1.60.0](https://opentelemetry.io/docs/specs/otel/)
- [W3C Trace Context Recommendation](https://www.w3.org/TR/trace-context/)
- [NIST SP 800-34r1](https://csrc.nist.gov/pubs/sp/800/34/r1/upd1/final)
- [NIST SP 800-61r3](https://csrc.nist.gov/pubs/sp/800/61/r3/final)
- [CISA Incident and Vulnerability Response Playbooks](https://www.cisa.gov/sites/default/files/publications/Cybersecurity_Incident_Vulnerability_Response_Playbooks_508C.pdf)

### 10.3 安全与隐私

- [NIST Cybersecurity Framework 2.0](https://www.nist.gov/cyberframework)
- [NIST SP 800-218 SSDF v1.1](https://doi.org/10.6028/NIST.SP.800-218)
- [NIST SP 800-218A](https://csrc.nist.gov/pubs/sp/800/218/a/final)
- [NIST AI 600-1](https://doi.org/10.6028/NIST.AI.600-1)
- [CISA Secure by Design](https://www.cisa.gov/sites/default/files/2023-10/Shifting-the-Balance-of-Cybersecurity-Risk-Principles-and-Approaches-for-Secure-by-Design-Software.pdf)
- [CISA/FBI Product Security Bad Practices](https://www.cisa.gov/news-events/alerts/2025/01/17/cisa-and-fbi-release-updated-guidance-product-security-bad-practices)
- [OWASP ASVS 5.0.0](https://owasp.org/www-project-application-security-verification-standard/)
- [OWASP WSTG](https://wstg.owasp.org/)
- [OWASP Threat Modeling Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [MITRE CWE Top 25](https://cwe.mitre.org/top25/index.html)
- [FIRST CVSS v4.0 Specification](https://www.first.org/cvss/v4.0/specification-document)
- [CISA Known Exploited Vulnerabilities Catalog](https://www.cisa.gov/known-exploited-vulnerabilities-catalog)
- [NIST SP 800-207 Zero Trust Architecture](https://csrc.nist.gov/pubs/sp/800/207/final)
- [NIST SP 800-216 Vulnerability Disclosure](https://csrc.nist.gov/pubs/sp/800/216/final)
- [ISO/IEC 29147:2018](https://www.iso.org/standard/72311.html)
- [NIST Privacy Framework 1.0](https://www.nist.gov/privacy-framework/privacy-framework)
- [NISTIR 8062](https://csrc.nist.gov/pubs/ir/8062/final)
- [NIST SP 800-226 Differential Privacy](https://csrc.nist.gov/pubs/sp/800/226/final)
- [EU GDPR 2016/679](https://eur-lex.europa.eu/eli/reg/2016/679/oj)

### 10.4 供应链、配置与交付

- [NIST SP 800-161r1 Update 1](https://csrc.nist.gov/pubs/sp/800/161/r1/upd1/final)
- [NIST SP 800-204D](https://csrc.nist.gov/pubs/sp/800/204/d/final)
- [CISA SBOM Minimum Elements 2025](https://www.cisa.gov/sites/default/files/2025-08/2025_CISA_SBOM_Minimum_Elements.pdf)
- [SPDX Specifications](https://spdx.dev/use/specifications/)
- [SLSA v1.2](https://slsa.dev/spec/v1.2/)
- [Sigstore Cosign Verification](https://docs.sigstore.dev/cosign/verifying/verify/)
- [OpenGitOps Principles 1.0.0](https://opengitops.dev/)
- [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html)
- [The Twelve-Factor App, Config](https://12factor.net/config)
- [The Twelve-Factor App, Build Release Run](https://12factor.net/build-release-run)
- [DORA Software Delivery Performance Metrics](https://dora.dev/guides/dora-metrics/)
- [DORA 2025 Research](https://dora.dev/research/2025/)
- [DORA 2025 Measurement Frameworks](https://dora.dev/research/2025/measurement-frameworks/)

### 10.5 架构、理论、过程与演化

- [ISO/IEC/IEEE 29148:2018 Requirements Engineering](https://www.iso.org/standard/72089.html)
- [ISO/IEC/IEEE 42010:2022 Architecture Description](https://www.iso.org/standard/74393.html)
- [ISO/IEC/IEEE 14764:2022 Software Maintenance](https://www.iso.org/standard/80710.html)
- [Parnas, Information Hiding, 1972](https://doi.org/10.1145/361598.361623)
- [Dijkstra, Separation of Concerns, EWD447](https://www.cs.utexas.edu/~EWD/transcriptions/EWD04xx/EWD447.html)
- [Liskov and Wing, Behavioral Subtyping, 1994](https://doi.org/10.1145/197320.197383)
- [Brooks, No Silver Bullet, 1986](https://www.cs.unc.edu/techreports/86-020.pdf)
- [Gilbert and Lynch, CAP, 2002](https://doi.org/10.1145/564585.564601)
- [Lamport, Time, Clocks, and Ordering, 1978](https://www.microsoft.com/en-us/research/publication/time-clocks-ordering-events-distributed-system/)
- [Hoare, Axiomatic Basis, 1969](https://doi.org/10.1145/363235.363259)
- [Little, L = λW, 1961](https://doi.org/10.1287/opre.9.3.383)
- [Conway, How Do Committees Invent?, 1968](https://melconway.com/Home/pdf/committees.pdf)
- [Agile Manifesto and Principles](https://agilemanifesto.org/principles.html)
- [Lehman et al., Laws of Software Evolution, 1997](https://users.ece.utexas.edu/~perry/work/papers/feast1.pdf)
- [Cunningham, Technical Debt, 1992](https://c2.com/doc/oopsla92.html)
- [Fowler, Definition of Refactoring](https://martinfowler.com/bliki/DefinitionOfRefactoring.html)

### 10.6 AI Coding

AI Coding 的标准、官方指南、厂商案例和原始实证已按证据代码完整列于第 6.9 节；不在此重复，以避免形成第二份来源表。

## 11. 采用与维护说明

1. 本文条目进入项目政策前，必须转换为具体风险、owner、验证面、例外规则和退出条件。
2. 规范版本、法律适用性和当前工具版本应在采用时重新核对；本页日期不是永久有效证明。
3. 来源更新不自动改变项目政策；政策变更仍需项目正式决策。
4. 自动门禁可在其明确测试契约内形成 verified evidence，但不能替代更宽的业务真值、人工风险接受、用户任务确认或发布批准。
5. 本文已经并入三条独立调查线；后续维护仍应重新检查编号、重复项、来源等级和跨章节冲突。
