# 项目需求文档

## 项目信息
- **项目编号**: NE-2024-002
- **项目名称**: Python类型系统全面修复
- **预算**: 3个开发团队周
- **交付期限**: 2周
- **优先级**: P0

---

## 1. 项目背景

Novel-Engine平台当前存在大量mypy类型错误，影响代码可维护性和IDE支持。当前统计：
- 总错误数: ~4,458个
- 主要类型: no-untyped-def (1,291个), arg-type, return-type等

类型系统缺陷导致：
- 静态分析无法有效发现问题
- IDE自动补全和导航受限
- 重构风险高
- 新成员上手困难

---

## 2. 功能需求

### 2.1 必须实现 (P0)

#### 2.1.1 错误修复优先级
| 错误类型 | 当前数量 | 目标数量 | 优先级 |
|----------|----------|----------|--------|
| no-untyped-def | ~1,291 | <200 | P0 |
| arg-type | ~800 | <100 | P0 |
| return-type | ~650 | <100 | P0 |
| var-annotated | ~520 | <50 | P0 |
| assignment | ~380 | <50 | P0 |
| 其他 | ~817 | <100 | P1 |

#### 2.1.2 模块修复顺序
1. **src/contexts/** - 核心业务逻辑，优先级最高
2. **src/core/** - 领域模型和实体
3. **src/api/** - API层类型定义
4. **src/repositories/** - 数据访问层
5. **src/services/** - 业务服务层
6. **src/agents/** - Agent逻辑

#### 2.1.3 类型注解要求
- [ ] 所有函数参数添加类型注解
- [ ] 所有函数返回值添加类型注解
- [ ] 类属性添加类型注解
- [ ] 模块级变量添加类型注解
- [ ] 复杂数据结构使用TypedDict或dataclass

### 2.2 应该实现 (P1)
- [ ] 类型存根文件(stubs)补充
- [ ] 泛型使用规范化
- [ ] Protocol接口定义

---

## 3. 非功能需求

### 3.1 质量要求
- 类型注解必须准确反映运行时行为
- 禁止使用 `Any` 除非经过CTO审批
- 使用 `Optional[X]` 而非 `Union[X, None]`
- 使用 `X | Y` 语法 (Python 3.10+) 替代 `Union[X, Y]`

### 3.2 兼容性要求
- 保持Python 3.11+兼容
- 不得引入运行时行为变更
- 保持向后兼容的API签名

### 3.3 工具链
- mypy >= 1.7.0
- 严格模式启用: `strict = True`
- 忽略规则需经审批并记录原因

---

## 4. 验收标准

### 4.1 错误数量验收
- [ ] `mypy src/` 总错误数 < 500
- [ ] no-untyped-def 错误 < 200
- [ ] arg-type/return-type 错误各 < 100

### 4.2 质量验收
- [ ] 无新增 `Any` 类型（审批通过的除外）
- [ ] 类型覆盖率报告 > 90%
- [ ] 所有模块可通过 `mypy --strict` 检查

### 4.3 回归验收
- [ ] 所有单元测试通过
- [ ] 所有集成测试通过
- [ ] 运行时行为无变更（通过回归测试验证）

---

## 5. 交付物清单

| 序号 | 交付物 | 路径 | 说明 |
|------|--------|------|------|
| 1 | 修复计划 | `deliverables/type_fix_plan.md` | 分模块修复策略 |
| 2 | 修复后代码 | `deliverables/fixed_files/` | 变更的文件清单 |
| 3 | MyPy报告 | `deliverables/mypy_report.md` | 修复前后对比 |
| 4 | 迁移指南 | `deliverables/migration_guide.md` | 类型规范与最佳实践 |

---

## 6. 技术约束

### 6.1 禁止事项
- 禁止使用 `# type: ignore` 掩盖问题（临时除外，需标记TODO）
- 禁止修改业务逻辑来"修复"类型错误
- 禁止添加运行时开销的类型检查

### 6.2 推荐模式
```python
# ✅ 推荐
from typing import Optional, Sequence

def process_items(items: Sequence[str]) -> Optional[dict[str, int]]:
    if not items:
        return None
    return {item: len(item) for item in items}

# ❌ 避免
def process_items(items):  # 无类型注解
    ...
```

---

## 7. 风险与应对

| 风险 | 可能性 | 影响 | 应对措施 |
|------|--------|------|----------|
| 循环导入问题 | 中 | 高 | 使用 TYPE_CHECKING 标志 |
| 第三方库无类型 | 高 | 中 | 添加存根或忽略配置 |
| 过度注解导致复杂 | 中 | 低 | 代码审查把关 |

---

**文档版本**: v1.0  
**创建日期**: 2024-03-04  
**审批人**: CTO Office
