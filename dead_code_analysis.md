# 死代码分析报告

**生成日期**: 2026-03-04  
**扫描范围**: `src/` 目录  
**扫描工具**: vulture  
**总死代码项**: 2,683 行

---

## 一、按模块统计

| 模块 | 死代码数量 | 占比 | 状态 |
|------|-----------|------|------|
| contexts | 915 | 34.1% | 存在 |
| core | 446 | 16.6% | 存在 |
| api | 238 | 8.9% | 存在 |
| interactions | 161 | 6.0% | 存在 |
| ai_intelligence | 146 | 5.4% | **已删除** |
| security | 141 | 5.3% | 存在 |
| performance | 80 | 3.0% | 存在 |
| infrastructure | 78 | 2.9% | 存在 |
| agents | 75 | 2.8% | 存在 |
| performance_optimizations | 62 | 2.3% | 存在 |
| events | 59 | 2.2% | 存在 |
| director_components | 53 | 2.0% | 存在 |
| memory | 32 | 1.2% | 存在 |
| orchestrators | 26 | 1.0% | 存在 |
| templates | 25 | 0.9% | 存在 |
| caching | 21 | 0.8% | 存在 |
| bridge/bridges | 34 | 1.3% | 存在 |
| database | 14 | 0.5% | 存在 |
| metrics | 14 | 0.5% | 存在 |
| prompts | 14 | 0.5% | 存在 |
| quality | 12 | 0.4% | 存在 |
| director | 11 | 0.4% | 存在 |
| config | 10 | 0.4% | 存在 |
| decision | 9 | 0.3% | 存在 |
| architecture | 3 | 0.1% | 存在 |
| services | 2 | 0.1% | 存在 |
| workspaces | 2 | 0.1% | 存在 |

---

## 二、按置信度分类

| 置信度 | 数量 | 建议操作 |
|--------|------|----------|
| 100% | 17 | 🔴 **立即删除** - 确定未使用 |
| 90% | 25 | 🟡 **安全删除** - 可能是import未使用 |
| 60-89% | 2,641 | 🟠 **需要审查** - 可能是误报或接口方法 |

---

## 三、关键发现

### 3.1 已删除模块 (ai_intelligence/)
- **状态**: 目录不存在但报告中有146项死代码
- **说明**: 此模块可能已被删除或重命名
- **操作**: 从报告中忽略

### 3.2 高优先级清理目标 (90%+置信度)

#### agents/ 模块 (3项)
1. `context_manager.py:18` - 未使用的 import `PersonaCore`
2. `decision_engine.py:22` - 未使用的 import `CharacterContextManager`
3. `decision_engine.py:23` - 未使用的 import `PersonaCore`

#### api/ 模块 (9项)
主要是未使用的 import 和异常处理变量

#### contexts/ 模块 (4项)
主要是异常处理中的未使用变量

---

## 四、死代码类型分布

### 4.1 变量未使用 (约60%)
- 函数内局部变量
- 类属性
- 异常处理变量 (`exc_type`, `exc_val`, `tb`)

### 4.2 方法未使用 (约25%)
- 类内部私有方法
- 公共API方法但未被调用
- 接口/抽象方法实现

### 4.3 类未使用 (约10%)
- 完整的未使用类
- 可能是实验代码或占位符

### 4.4 Import未使用 (约5%)
- 高置信度，安全删除

---

## 五、风险评估

### 🔴 高风险区域
- `contexts/` - 915项，核心模块需谨慎
- `core/` - 446项，基础模块影响大
- `api/` - 238项，可能影响公开接口

### 🟡 中风险区域
- `agents/` - 75项，agent系统代码
- `interactions/` - 161项，交互系统

### 🟢 低风险区域
- `ai_intelligence/` - 已删除，报告过时
- `templates/character/` - 多个未使用类，可能是实验代码

---

## 六、清理建议

### 阶段一: 安全清理 (高置信度)
- 清理所有90%+置信度的死代码
- 主要是未使用的 import 和明显的未使用变量
- 预计删除: ~50项

### 阶段二: 实验代码审查
- 审查 `templates/character/` 下的未使用类
- 审查 `performance_optimizations/` 模块
- 决定是删除还是移动到 experiments/

### 阶段三: 核心模块谨慎清理
- 对 contexts/ 和 core/ 进行逐文件审查
- 保留接口方法和可能用于未来的功能
- 添加 `# noqa` 注释给误报

### 阶段四: Vulture配置
- 创建 `pyproject.toml` 或 `setup.cfg` 配置
- 添加 whitelist 文件
- 配置忽略模式（如 `__init__.py` 中的导出）

---

## 七、注意事项

1. **不要删除**:
   - 带有 `@pytest.mark.skip` 的测试代码
   - `if __name__ == "__main__"` 中的代码
   - 接口/抽象基类中的必需方法
   - `__init__.py` 中用于导出的 import

2. **谨慎处理**:
   - 60%置信度的方法可能是接口实现
   - 属性可能是供外部使用的
   - 异常变量可能用于调试

3. **测试验证**:
   - 每次删除后运行 `pytest`
   - 检查 import 是否正常
   - 验证无运行时错误

---

## 八、文件清单

需要审查的关键文件（按死代码数量排序）:

1. `src/contexts/` - 915项（需分阶段处理）
2. `src/core/` - 446项（需分阶段处理）
3. `src/api/` - 238项
4. `src/interactions/` - 161项
5. `src/security/` - 141项
6. `src/performance/` - 80项
7. `src/agents/` - 75项
8. `src/performance_optimizations/` - 62项
