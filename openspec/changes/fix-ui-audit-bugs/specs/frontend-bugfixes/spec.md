# Spec: frontend-bugfixes

## Overview
修复前端 UI 审查中发现的 6 个问题。

---

## MODIFIED Requirements

### Requirement: Decision Point Timer Display
**Component**: DecisionPointDialog, decisionSlice

The system MUST correctly display countdown time in the Decision Dialog, even when the backend returns an invalid `expiresAt` value.

#### Scenario: Timer displays valid countdown
**Given** 用户触发 Decision Point
**When** Dialog 弹出显示计时器
**Then** 计时器显示格式正确的分:秒 (如 "01:30")
**And** 不显示 "NaN:NaN"

#### Scenario: Timer handles invalid expiresAt
**Given** 后端返回无效的 `expiresAt` 值 (null, undefined, 或无效日期字符串)
**When** 系统计算 remainingSeconds
**Then** 使用 `timeoutSeconds` 作为默认倒计时值
**And** 计时器正常显示

---

### Requirement: Activity Stream Timestamp Display
**Component**: RealTimeActivity

The Activity Stream MUST display relative timestamps correctly, handling invalid or missing values gracefully.

#### Scenario: Recent event timestamp
**Given** 事件发生在 30 秒前
**When** 显示事件时间戳
**Then** 显示 "Just now"

#### Scenario: Minutes ago timestamp
**Given** 事件发生在 5 分钟前
**When** 显示事件时间戳
**Then** 显示 "5m ago"

#### Scenario: Hours ago timestamp
**Given** 事件发生在 2 小时前
**When** 显示事件时间戳
**Then** 显示 "2h ago"

#### Scenario: Invalid timestamp handling
**Given** 事件时间戳为 null, undefined, 或 NaN
**When** 格式化时间戳
**Then** 显示 "Recently" 而不是 "NaNh ago"

#### Scenario: Timestamp unit normalization
**Given** 后端可能发送秒或毫秒为单位的时间戳
**When** 格式化时间戳
**Then** 系统自动检测并规范化单位
**And** 不显示异常值如 "490091h ago"

---

### Requirement: Character Creation Access
**Component**: Dashboard

The Dashboard MUST provide access to the Character Creation feature via a modal dialog.

#### Scenario: Open character creation dialog
**Given** 用户在 Dashboard 页面
**When** 点击 "Create Character" 按钮
**Then** CharacterCreationDialog 模态框打开

#### Scenario: Close character creation dialog
**Given** CharacterCreationDialog 已打开
**When** 用户点击关闭或完成创建
**Then** 对话框关闭
**And** 用户返回 Dashboard

---

### Requirement: Landing Page Title
**Component**: LandingPage

The Landing Page title MUST display correctly without text duplication.

#### Scenario: Correct title display
**Given** 用户访问 Landing Page
**When** 页面加载完成
**Then** 标题显示 "NARRATIVE ENGINE" 或类似（不重复）
**And** 不显示 "NARRATIVE ENGINE NARRATIVE"

---

### Requirement: SPA Route Fallback
**Component**: vite.config.ts

The application MUST correctly load when users directly access frontend routes in preview mode.

#### Scenario: Direct route access in preview mode
**Given** 应用运行在 preview 模式
**When** 用户直接访问 `/dashboard` 或其他前端路由
**Then** 应用正确加载
**And** 不显示空白页面

---

### Requirement: Demo Mode Banner Dismissible
**Component**: DemoModeBanner

The Demo Mode banner MUST be dismissible and SHALL remember the user's preference.

#### Scenario: Dismiss demo banner
**Given** Demo Mode 横幅显示
**When** 用户点击关闭按钮
**Then** 横幅消失

#### Scenario: Remember dismiss preference
**Given** 用户之前关闭了 Demo Mode 横幅
**When** 用户刷新页面或重新访问
**Then** 横幅不再显示
