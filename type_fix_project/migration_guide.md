# Python类型注解迁移指南

**项目**: NE-2024-002 MyPy类型修复  
**版本**: 1.0  
**日期**: 2026-03-04

---

## 1. 概述

本指南记录了从非类型化Python代码迁移到完全类型注解的最佳实践和模式。

---

## 2. 常见错误修复模式

### 2.1 no-untyped-def (函数缺少返回类型)

**问题**:
```python
def process_data(data):
    ...
```

**修复**:
```python
def process_data(data: dict[str, Any]) -> None:
    ...
```

**批量修复命令**:
```bash
# 为所有__init__方法添加返回类型
sed -i 's/def __init__(self):/def __init__(self) -> None:/g' src/**/*.py

# 为私有方法添加返回类型
sed -i 's/def _\([a-z_]*\)(self):/def _\1(self) -> None:/g' src/**/*.py
```

### 2.2 var-annotated (变量需要类型注解)

**问题**:
```python
items = []  # Need type annotation
```

**修复**:
```python
items: list[str] = []
```

### 2.3 union-attr (Union类型属性访问)

**问题**:
```python
def process(obj: MyClass | None) -> None:
    obj.method()  # Error: Item "None" has no attribute "method"
```

**修复**:
```python
def process(obj: MyClass | None) -> None:
    if obj is not None:
        obj.method()
```

### 2.4 assignment (类型不匹配)

**问题**:
```python
count: int = get_float_value()  # float cannot be assigned to int
```

**修复**:
```python
count: int = int(get_float_value())
```

### 2.5 arg-type (参数类型不匹配)

**问题**:
```python
def func(data: dict[str, int]) -> None:
    ...

func({"key": "value"})  # str cannot be assigned to int
```

**修复**:
```python
def func(data: dict[str, int]) -> None:
    ...

func({"key": 123})  # Correct type
```

---

## 3. 类型注解最佳实践

### 3.1 函数返回类型

| 场景 | 返回类型 | 示例 |
|------|----------|------|
| 不返回任何值 | `-> None` | `def process() -> None:` |
| 返回字符串 | `-> str` | `def get_name() -> str:` |
| 返回可选值 | `-> T \| None` | `def find() -> User \| None:` |
| 返回列表 | `-> list[T]` | `def get_items() -> list[str]:` |
| 返回字典 | `-> dict[K, V]` | `def get_config() -> dict[str, Any]:` |
| 异步函数 | `-> Coroutine[Any, Any, T]` | `async def fetch() -> Data:` |

### 3.2 参数类型

```python
from typing import Any, Optional, Union

# 基本类型
def basic(name: str, age: int, active: bool) -> None:
    ...

# 可选参数
def optional(name: str, nickname: Optional[str] = None) -> None:
    ...

# Union类型
def union(value: Union[str, int]) -> None:
    ...

# 使用 | 语法 (Python 3.10+)
def modern(value: str | int) -> None:
    ...

# **kwargs
def with_kwargs(**kwargs: Any) -> None:
    ...

# *args
def with_args(*args: str) -> None:
    ...
```

### 3.3 泛型类型

```python
from typing import TypeVar, Generic

T = TypeVar('T')

class Container(Generic[T]):
    def __init__(self, value: T) -> None:
        self.value = value
    
    def get(self) -> T:
        return self.value
```

---

## 4. 工具配置

### 4.1 MyPy配置 (pyproject.toml)

```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
ignore_missing_imports = true
```

### 4.2 预提交钩子 (.pre-commit-config.yaml)

```yaml
repos:
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
        args: [--ignore-missing-imports]
```

---

## 5. 验证命令

### 5.1 运行MyPy检查

```bash
# 检查整个src目录
python -m mypy src/ --ignore-missing-imports

# 检查特定文件
python -m mypy src/api/app.py --ignore-missing-imports

# 生成详细报告
python -m mypy src/ --ignore-missing-imports --show-error-codes

# 检查统计
python -m mypy src/ --ignore-missing-imports --no-error-summary 2>&1 | grep -oE "\[([a-z-]+)\]$" | sort | uniq -c
```

### 5.2 运行测试

```bash
# 单元测试
pytest tests/unit/ -x

# 集成测试
pytest tests/integration/ -x

# 全量测试
pytest tests/ -x --timeout=120
```

---

## 6. 持续维护

### 6.1 代码审查检查清单

- [ ] 所有函数都有返回类型注解
- [ ] 所有参数都有类型注解
- [ ] 没有使用 `Any` 除非必要
- [ ] 复杂类型使用 TypeAlias
- [ ] MyPy检查通过

### 6.2 CI集成

```yaml
# .github/workflows/type-check.yml
name: Type Check
on: [push, pull_request]
jobs:
  mypy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install mypy
      - run: python -m mypy src/ --ignore-missing-imports --no-error-summary
```

---

## 7. 参考资源

- [MyPy文档](https://mypy.readthedocs.io/)
- [Python类型提示指南](https://docs.python.org/3/library/typing.html)
- [PEP 484 - 类型提示](https://peps.python.org/pep-0484/)
- [PEP 585 - 标准集合中的类型提示](https://peps.python.org/pep-0585/)

---

**完**
