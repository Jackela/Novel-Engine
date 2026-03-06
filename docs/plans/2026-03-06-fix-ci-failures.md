# CI失败修复计划

## 问题概述

GitHub Actions中有以下失败检查：

1. **Validate Test Markers** - 1675个测试缺少金字塔标记
2. **CodeQL** - 48个新警告，包括4个高危安全漏洞
3. **CI Success** - 因上述问题失败

---

## 修复任务

### FIX-1: 修复测试金字塔标记 (1675个测试)

**优先级:** P0 (阻塞CI)  
**工作量:** 高  
**模式:** 外包公司模式

#### 分析
- 65个文件包含无标记测试
- 需要添加 `@pytest.mark.unit`, `@pytest.mark.integration`, 或 `@pytest.mark.e2e`
- 大部分应该是单元测试

#### 任务分配
将65个文件分成4组，分配给4个Worker：

| Worker | 文件范围 | 预计数量 |
|--------|----------|----------|
| FIX-1A | tests/agents/, tests/api/ | ~400 |
| FIX-1B | tests/contexts/ | ~500 |
| FIX-1C | tests/unit/, tests/integration/ | ~400 |
| FIX-1D | tests/e2e/, tests/根目录 | ~375 |

#### 验收标准
- [ ] 所有1675个测试都有金字塔标记
- [ ] `validate-test-markers.py --all` 通过
- [ ] 测试仍能正常运行

---

### FIX-2: 修复CodeQL安全问题

**优先级:** P0 (安全风险)  
**工作量:** 中  
**模式:** 外包公司模式

#### 分析
- 48个新警告
- 4个高危安全漏洞
- 需要先查看具体问题

#### 任务分配

| Worker | 任务 | 范围 |
|--------|------|------|
| FIX-2A | 调查高危漏洞 | 4个high severity |
| FIX-2B | 修复高危漏洞 | 根据FIX-2A结果 |
| FIX-2C | 修复中低危警告 | 剩余44个 |

---

## 执行计划

### Phase 1: 修复测试标记
1. 派遣FIX-1A, FIX-1B, FIX-1C, FIX-1D并行工作
2. 每个Worker处理分配的文件
3. QC审查每个Worker的产出
4. 合并所有修复

### Phase 2: 修复CodeQL问题
1. 派遣FIX-2A调查高危漏洞
2. 派遣FIX-2B修复高危漏洞
3. 派遣FIX-2C修复中低危警告

### Phase 3: 验证
1. 本地运行validate-test-markers
2. 本地运行安全扫描
3. 推送并监控GitHub Actions

---

## 时间线

| 阶段 | 预计时间 | 依赖 |
|------|----------|------|
| FIX-1 (测试标记) | 2-3天 | 无 |
| FIX-2 (CodeQL) | 1-2天 | 无 |
| 验证 | 2-4小时 | FIX-1, FIX-2 |

**总计: 3-5天**

---

## 成功指标

- ✅ Validate Test Markers 检查通过
- ✅ CodeQL 无高危漏洞
- ✅ CI Success 检查通过
- ✅ 所有测试正常运行
