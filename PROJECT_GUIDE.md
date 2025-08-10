# 动态上下文工程框架 (Dynamic Context Engineering Framework)

*智能体互动框架 借助context engineering 技术 动态加载变化的上下文*

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://python.org)
[![Architecture](https://img.shields.io/badge/Architecture-Multi--Agent-green.svg)](https://github.com)
[![Framework](https://img.shields.io/badge/Framework-Context%20Engineering-orange.svg)](https://github.com)

---

## 🌟 项目概述 (Project Overview)

本项目是一个完整的**动态上下文工程框架**，专为智能体互动而设计。通过先进的context engineering技术，实现了：

- **动态上下文加载** - 实时上下文变化和适应
- **多层记忆系统** - 工作记忆、情景记忆、语义记忆、情感记忆
- **角色互动管理** - 复杂的社交动态和关系追踪
- **装备状态跟踪** - 实时装备状态和维护系统
- **跨文档引用** - 智能文档关联和内容同步
- **AI集成优化** - 为AI提示词动态变化效果而专门优化

### ✨ 核心特性 (Core Features)

🧠 **智能记忆管理**
- 认知科学基础的多层记忆架构
- 自动记忆重要性评估和清理
- 跨记忆层的智能查询和关联

💬 **动态角色交互**
- 9种交互类型支持（对话、战斗、协作、仪式等）
- 实时关系动态追踪和演化
- 社交环境感知和适应

🔧 **装备系统集成**
- 实时装备磨损和状态追踪
- 机械之魂情绪系统（战锤40K主题）
- 预测性维护和故障分析

📝 **动态模板引擎**
- Jinja2驱动的内容生成
- 跨文档引用解析
- 上下文感知的模板渲染

🏗️ **统一系统编排**
- 全系统健康监控和指标
- 自动故障恢复和资源管理
- 开发和生产模式支持

---

## 🚀 快速开始 (Quick Start)

### 环境要求

```bash
Python 3.8+
aiosqlite >= 0.17.0
jinja2 >= 3.0.0
```

### 安装和运行

1. **克隆项目**
```bash
git clone <your-repo-url>
cd Novel-Engine
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **运行演示**
```bash
python example_usage.py
```

4. **查看结果**
演示将展示完整的框架功能，包括：
- 系统初始化和配置
- 智能体创建和上下文管理
- 多角色交互场景
- 系统性能监控
- 优雅关闭和状态保存

---

## 🏗️ 架构设计 (Architecture)

### 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    SystemOrchestrator                       │
│                   (统一系统编排器)                             │
└─────────────────┬───────────────────────────────────────────┘
                  │
    ┌─────────────┼─────────────┐
    │             │             │
    ▼             ▼             ▼
┌─────────┐ ┌─────────────┐ ┌───────────────┐
│ Memory  │ │ Templates   │ │ Interactions  │
│ System  │ │ System      │ │ System        │
│         │ │             │ │               │
│ 🧠      │ │ 📝          │ │ 💬            │
└─────────┘ └─────────────┘ └───────────────┘
    │             │             │
    └─────────────┼─────────────┘
                  │
                  ▼
            ┌─────────────┐
            │  Database   │
            │   System    │ 
            │             │
            │ 💾          │
            └─────────────┘
```

### 核心组件 (Core Components)

#### 1. 多层记忆系统 (Layered Memory System)
- **WorkingMemory** - 工作记忆 (7±2项目容量限制)
- **EpisodicMemory** - 情景记忆 (具体事件和经历)
- **SemanticMemory** - 语义记忆 (概念和知识)
- **EmotionalMemory** - 情感记忆 (情感关联的记忆)

#### 2. 动态模板引擎 (Dynamic Template Engine)
- Jinja2模板驱动的内容生成
- 跨文档引用自动解析
- 记忆系统集成查询
- 上下文感知渲染

#### 3. 角色交互处理器 (Character Interaction Processor)
- 11种关系类型支持
- 8种社交环境模式
- 动态关系演化追踪
- 多阶段交互处理

#### 4. 动态装备系统 (Dynamic Equipment System)
- 10种装备类别处理器
- 实时磨损累积计算
- 机械之魂情绪追踪
- 预测性维护调度

#### 5. 统一系统编排器 (System Orchestrator)
- 全系统生命周期管理
- 实时性能监控和指标
- 自动健康检查和恢复
- 跨系统数据一致性验证

---

## 📚 使用指南 (Usage Guide)

### 基础使用模式

#### 1. 系统初始化
```python
from src.core.system_orchestrator import SystemOrchestrator, OrchestratorConfig

# 创建配置
config = OrchestratorConfig(
    mode=OrchestratorMode.DEVELOPMENT,
    max_concurrent_agents=10,
    enable_metrics=True
)

# 初始化编排器
orchestrator = SystemOrchestrator("data/my_project.db", config)
await orchestrator.startup()
```

#### 2. 创建智能体
```python
from src.core.data_models import CharacterState, EmotionalState

# 定义角色状态
character_state = CharacterState(
    agent_id="my_agent",
    name="智能助手Alpha",
    background_summary="专业的AI助手，擅长数据分析和逻辑推理",
    personality_traits="逻辑性强，乐于助人，注重细节",
    emotional_state=EmotionalState(
        current_mood=8,
        dominant_emotion="focused",
        energy_level=9,
        stress_level=2
    )
)

# 创建智能体上下文
result = await orchestrator.create_agent_context("my_agent", character_state)
```

#### 3. 处理动态上下文
```python
from src.core.data_models import DynamicContext, MemoryItem, MemoryType

# 创建记忆项目
memory = MemoryItem(
    memory_id="task_assignment",
    agent_id="my_agent", 
    memory_type=MemoryType.EPISODIC,
    content="接收了新的数据分析任务：分析用户行为模式",
    emotional_intensity=0.6,
    relevance_score=0.9,
    context_tags=["任务", "数据分析", "用户行为"]
)

# 创建动态上下文
context = DynamicContext(
    agent_id="my_agent",
    memory_context=[memory]
)

# 处理上下文
result = await orchestrator.process_dynamic_context(context)
```

#### 4. 多智能体交互
```python
from src.interactions.interaction_engine import InteractionType

# 编排多智能体对话
result = await orchestrator.orchestrate_multi_agent_interaction(
    participants=["agent_1", "agent_2", "agent_3"],
    interaction_type=InteractionType.DIALOGUE,
    context={
        "topic": "项目规划讨论",
        "location": "虚拟会议室",
        "urgency": "normal"
    }
)
```

### 高级功能

#### 记忆查询和分析
```python
from src.memory.memory_query_engine import QueryContext

# 复杂记忆查询
query_context = QueryContext(
    agent_id="my_agent",
    query_text="最近的任务相关记忆",
    context_filters=["任务", "工作"],
    emotional_filter_min=0.3,
    time_range_days=7
)

query_engine = orchestrator.memory_query_engine
results = await query_engine.execute_query(query_context)
```

#### 关系状态查询
```python
# 查询两个智能体之间的关系
relationship = await orchestrator.character_processor.get_relationship_status(
    "agent_1", "agent_2"
)

if relationship.success:
    rel_data = relationship.data["relationship"]
    print(f"信任等级: {rel_data.trust_level}")
    print(f"熟悉程度: {rel_data.familiarity_level}")
    print(f"交互次数: {rel_data.interaction_count}")
```

#### 系统监控
```python
# 获取系统性能指标
metrics = await orchestrator.get_system_metrics()
if metrics.success:
    current = metrics.data["current_metrics"]
    print(f"活跃智能体: {current.active_agents}")
    print(f"系统健康: {current.system_health.value}")
    print(f"平均响应时间: {current.average_response_time}ms")
```

---

## 🔧 配置选项 (Configuration)

### OrchestratorConfig 参数

```python
@dataclass
class OrchestratorConfig:
    mode: OrchestratorMode = OrchestratorMode.AUTONOMOUS
    max_concurrent_agents: int = 10            # 最大并发智能体数
    memory_cleanup_interval: int = 3600        # 记忆清理间隔(秒)
    template_cache_size: int = 100             # 模板缓存大小
    interaction_queue_size: int = 50           # 交互队列大小
    equipment_maintenance_interval: int = 1800  # 装备维护间隔(秒)
    health_check_interval: int = 300           # 健康检查间隔(秒)
    auto_save_interval: int = 600              # 自动保存间隔(秒)
    debug_logging: bool = False                # 调试日志
    enable_metrics: bool = True                # 启用指标监控
    enable_auto_backup: bool = True            # 启用自动备份
    max_memory_items_per_agent: int = 10000    # 每个智能体最大记忆项目数
    performance_monitoring: bool = True         # 性能监控
```

### 运行模式

- **AUTONOMOUS** - 完全自主运行模式
- **INTERACTIVE** - 人机交互模式  
- **SIMULATION** - 仿真测试模式
- **DEVELOPMENT** - 开发调试模式
- **PRODUCTION** - 生产部署模式

---

## 📊 性能特性 (Performance Features)

### 内存管理
- **智能缓存策略** - 自动LRU缓存管理
- **记忆重要性评估** - 基于访问频率和情感强度
- **自动清理机制** - 定期清理过期和低相关性记忆

### 并发处理
- **异步架构** - 全面的asyncio支持
- **并发智能体管理** - 支持多智能体并行处理
- **资源池管理** - 数据库连接池和资源优化

### 监控和诊断
- **实时健康检查** - 多层次系统健康监控
- **性能指标追踪** - 响应时间、错误率、资源使用
- **自动故障恢复** - 智能故障检测和恢复机制

---

## 🎯 应用场景 (Use Cases)

### 1. 智能对话系统
- 多角色对话管理
- 上下文连续性保持
- 情感状态跟踪

### 2. 游戏AI系统
- NPC行为管理
- 动态剧情生成
- 装备和物品系统

### 3. 教育培训平台
- 个性化学习助手
- 知识点关联管理
- 学习进度跟踪

### 4. 虚拟助手平台
- 多任务上下文管理
- 长期记忆保持
- 个性化服务提供

---

## 🔬 技术细节 (Technical Details)

### 数据库架构
- **SQLite** - 轻量级嵌入式数据库
- **异步操作** - aiosqlite异步数据库访问
- **ACID合规** - 事务完整性保证
- **多表关联** - 复杂数据关系支持

### 算法实现
- **认知科学原理** - 基于7±2工作记忆容量
- **情感计算** - 情感强度和关联性计算
- **社交动态建模** - 关系演化算法
- **预测分析** - 装备故障预测和维护调度

### 安全性
- **数据验证** - 全面的输入验证和清理
- **错误处理** - 综合错误处理和恢复
- **资源限制** - 内存和计算资源保护
- **审计日志** - 详细的操作审计追踪

---

## 🐛 故障排除 (Troubleshooting)

### 常见问题

#### 1. 数据库连接错误
```
解决方案: 检查数据库文件权限和路径
确保 data/ 目录存在且可写
```

#### 2. 内存使用过高
```
解决方案: 调整 max_memory_items_per_agent 参数
启用更频繁的记忆清理：memory_cleanup_interval = 1800
```

#### 3. 交互处理缓慢
```
解决方案: 增加 max_concurrent_agents 值
启用性能监控查看瓶颈：performance_monitoring = True
```

#### 4. 模板渲染失败
```
解决方案: 检查模板文件语法
确保 src/templates/ 目录包含必要的模板文件
```

### 调试模式
```python
config = OrchestratorConfig(
    mode=OrchestratorMode.DEVELOPMENT,
    debug_logging=True,
    performance_monitoring=True
)
```

---

## 🚧 开发计划 (Development Roadmap)

### Phase 1: 核心功能 ✅
- [x] 多层记忆系统
- [x] 动态模板引擎
- [x] 角色交互处理
- [x] 装备状态系统
- [x] 统一编排器

### Phase 2: 扩展功能 🔄
- [ ] Web API接口
- [ ] 图形化管理界面
- [ ] 云端部署支持
- [ ] 多语言模板支持

### Phase 3: 高级特性 📋
- [ ] 机器学习集成
- [ ] 分布式部署
- [ ] 实时协作功能
- [ ] 高级分析工具

---

## 🤝 贡献指南 (Contributing)

欢迎为项目做出贡献！请遵循以下步骤：

1. Fork 项目仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 代码规范
- 遵循 PEP 8 Python 代码规范
- 添加适当的文档字符串和注释
- 包含单元测试覆盖新功能
- 保持战锤40K主题的注释风格

---

## 📄 许可证 (License)

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

---

## 🙏 致谢 (Acknowledgments)

- **战锤40K宇宙** - 为项目提供了丰富的主题灵感
- **认知科学研究** - 为记忆系统设计提供了科学基础
- **开源社区** - 为所使用的优秀开源库致敬

---

*万机之神保佑此框架 (May the Omnissiah bless this framework)*

**++ 通过代码，我们寻求完美 ++**