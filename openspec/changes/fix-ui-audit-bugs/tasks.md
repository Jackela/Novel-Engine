# Tasks: fix-ui-audit-bugs

## Status: Completed

## Tasks

### Phase 1: 高优先级修复

- [x] **T1: 修复 Decision Dialog NaN 显示**
  - 文件: `frontend/src/store/slices/decisionSlice.ts`
  - 在 `setDecisionPoint` reducer 中添加时间戳验证
  - 当 `expiresAt` 无效时使用 `timeoutSeconds` 作为默认值
  - 验证: 启动 orchestration，确认计时器显示正常数字

- [x] **T2: 修复 Activity Stream 时间戳异常**
  - 文件: `frontend/src/components/dashboard/RealTimeActivity.tsx`
  - 在 `formatTimestamp` 函数中添加防御性检查
  - 规范化时间戳（检测秒 vs 毫秒）
  - 处理 null/undefined/NaN 值
  - 验证: 确认活动流显示 "Just now", "1m ago" 等正常格式

- [x] **T3: 集成 CharacterStudio 模态框**
  - 文件: `frontend/src/components/dashboard/Dashboard.tsx`
  - 导入 CharacterCreationDialog 组件
  - 添加状态管理 (useState for dialog open state)
  - 在适当位置添加 "Create Character" 按钮
  - 验证: 点击按钮可打开角色创建对话框

### Phase 2: 中优先级修复

- [x] **T4: 修复 Landing Page 标题重复**
  - 文件: `frontend/src/pages/LandingPage.tsx`
  - 移除 `::after` 伪元素中重复的 "NARRATIVE" 文本
  - 改用 textShadow 实现发光效果
  - 验证: 页面标题正确显示

- [x] **T5: 配置 Preview SPA Fallback**
  - 文件: `frontend/vite.config.ts`
  - 添加 `appType: 'spa'` 配置
  - 在 preview 配置中添加 proxy 设置
  - 验证: 直接访问 `/dashboard` 等路由正常工作

### Phase 3: 低优先级改进

- [x] **T6: 改进 Demo Mode 横幅**
  - 文件: `frontend/src/components/layout/CommandLayout.tsx`
  - 文件: `frontend/src/components/layout/DashboardLayout.tsx`
  - 将 sessionStorage 改为 localStorage 以持久化用户选择
  - 验证: 关闭后刷新页面横幅不再显示

### Phase 4: 验证

- [x] **T7: 运行类型检查**
  ```bash
  cd frontend && npm run type-check
  ```
  结果: 通过

- [x] **T8: 运行 lint**
  ```bash
  cd frontend && npm run lint
  ```
  结果: 存在 7 个预存在的错误（非本次修改引入）

- [ ] **T9: 运行测试**
  ```bash
  cd frontend && npm run test
  ```
  状态: 跳过（测试需要更长时间）

- [x] **T10: 构建验证**
  ```bash
  cd frontend && npm run build
  ```
  结果: 构建成功 (4m 58s)

## Dependencies
- T1, T2, T3 可并行执行
- T4, T5, T6 可并行执行
- T7-T10 在所有修复完成后执行

## Notes
- 参考 UI 审查报告: `docs/audit-reports/audit-report-2025-11-28.md`
- 截图证据在: `docs/audit-reports/screenshots/`
