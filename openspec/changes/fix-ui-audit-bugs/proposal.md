# Proposal: fix-ui-audit-bugs

## Summary
修复 2025-11-28 UI 审查中发现的 6 个前端问题，包括 Decision Dialog 计时器 NaN 显示、Activity Stream 时间戳异常、CharacterStudio 无法访问、Landing Page 标题重复、Preview 模式 404 空白页面、以及 Demo Mode 横幅缺少关闭功能。

## Motivation
UI 审查报告发现多个影响用户体验的问题：
- 2 个严重级别 (Critical)
- 4 个警告级别 (Warning)
- 1 个建议级别 (Info)

这些问题导致用户界面显示异常、功能不可访问，需要及时修复。

## Problem Statement

### 问题 1: Decision Dialog 计时器显示 NaN:NaN
- **严重级别**: Warning
- **位置**: `frontend/src/store/slices/decisionSlice.ts`, `DecisionPointDialog.tsx`
- **原因**: `expiresAt` 无效日期导致计算出 NaN

### 问题 2: Activity Stream 时间戳异常
- **严重级别**: Warning
- **位置**: `frontend/src/components/dashboard/RealTimeActivity.tsx`
- **原因**: 时间戳单位混乱（秒 vs 毫秒），显示 "490091h ago" 或 "NaNh ago"

### 问题 3: CharacterStudio 无法访问
- **严重级别**: Critical
- **位置**: `frontend/src/App.tsx`
- **原因**: 组件存在但未集成到应用路由中

### 问题 4: Landing Page 标题重复
- **严重级别**: Warning
- **位置**: `frontend/src/pages/LandingPage.tsx`
- **原因**: 标题显示 "NARRATIVE ENGINE NARRATIVE"

### 问题 5: Preview 模式 404 空白
- **严重级别**: Warning
- **位置**: `frontend/vite.config.ts`
- **原因**: Preview 模式缺少 SPA fallback 配置

### 问题 6: Demo Mode 横幅无关闭选项
- **严重级别**: Info
- **位置**: Dashboard 组件
- **原因**: 横幅始终显示，无法关闭或记住用户选择

## Proposed Solution

### 解决方案 1: Decision Dialog NaN 修复
在 `decisionSlice.ts` 中添加时间戳验证：
```typescript
const expiresAt = new Date(action.payload.expiresAt);
if (isNaN(expiresAt.getTime())) {
  state.remainingSeconds = action.payload.timeoutSeconds || 30;
} else {
  state.remainingSeconds = Math.max(0, Math.floor((expiresAt.getTime() - Date.now()) / 1000));
}
```

### 解决方案 2: Activity Stream 时间戳规范化
在 `RealTimeActivity.tsx` 中规范化时间戳处理：
```typescript
const formatTimestamp = (timestampMs: number | null | undefined) => {
  if (!timestampMs || typeof timestampMs !== 'number' || isNaN(timestampMs)) {
    return 'Recently';
  }
  // 检测时间戳是否以秒为单位
  const normalizedTs = timestampMs < 1e11 ? timestampMs * 1000 : timestampMs;
  // ... 计算并格式化
};
```

### 解决方案 3: CharacterStudio 模态框集成
在 Dashboard 中添加按钮触发 CharacterCreationDialog 模态框：
- 添加 "Create Character" 按钮到 Dashboard
- 使用已有的 CharacterCreationDialog 组件
- 在 Insights Panel 或快捷操作区域添加入口

### 解决方案 4: Landing Page 标题修复
检查并修正标题文本，移除重复的 "NARRATIVE"。

### 解决方案 5: Preview SPA Fallback
在 vite.config.ts 的 preview 配置中添加 history API fallback 支持。

### 解决方案 6: Demo Mode 横幅改进
- 添加关闭按钮
- 使用 localStorage 记住用户选择
- 提供 "不再显示" 选项

## Impact Analysis

### 影响的文件
| 文件 | 变更类型 |
|------|---------|
| frontend/src/store/slices/decisionSlice.ts | MODIFIED |
| frontend/src/components/dashboard/RealTimeActivity.tsx | MODIFIED |
| frontend/src/components/dashboard/Dashboard.tsx | MODIFIED |
| frontend/src/pages/LandingPage.tsx | MODIFIED |
| frontend/vite.config.ts | MODIFIED |
| frontend/src/components/dashboard/DemoModeBanner.tsx | MODIFIED |

### 向后兼容性
所有修改都是 bug 修复，不会破坏现有 API 或行为。

### 测试要求
- 单元测试：验证时间戳格式化函数
- 集成测试：验证 Decision Dialog 计时器
- E2E 测试：验证完整工作流

## Alternatives Considered

### CharacterStudio 集成选项
1. **独立路由** - 添加 `/characters` 路由
2. **模态框触发** (选定) - 在 Dashboard 中通过按钮打开
3. **Tab 集成** - 作为 Dashboard 的一个标签页

选择模态框方式是因为：
- 用户无需离开 Dashboard
- 符合现有的交互模式（Decision Dialog 也是模态框）
- 实现简单，代码改动小

## Related
- UI 审查报告: `docs/audit-reports/audit-report-2025-11-28.md`
- CharacterStudio 组件: `frontend/src/components/CharacterStudio/`
