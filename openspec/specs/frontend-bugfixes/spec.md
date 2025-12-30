# Frontend Bugfixes

## Purpose
Record critical UI fixes that must remain stable for end users.

## Requirements

### Decision Point Timer Display
The system MUST correctly display countdown time in the Decision Dialog, even when the backend returns an invalid `expiresAt` value.

#### Scenario: Timer displays valid countdown
- **Given** 用户触发 Decision Point
- **When** Dialog 弹出显示计时器
- **Then** 计时器显示格式正确的分:秒 (如 "01:30")，且不显示 "NaN:NaN"

#### Scenario: Timer handles invalid expiresAt
- **Given** 后端返回无效的 `expiresAt` 值 (null, undefined, 或无效日期字符串)
- **When** 系统计算 remainingSeconds
- **Then** 使用 `timeoutSeconds` 作为默认倒计时值，且计时器正常显示

### Activity Stream Timestamp Display
The Activity Stream MUST display relative timestamps correctly, handling invalid or missing values gracefully.

#### Scenario: Recent event timestamp
- **Given** 事件发生在 30 秒前
- **When** 显示事件时间戳
- **Then** 显示 "Just now"

#### Scenario: Invalid timestamp handling
- **Given** 事件时间戳为 null, undefined, 或 NaN
- **When** 格式化时间戳
- **Then** 显示 "Recently" 而不是 "NaNh ago"

### Character Creation Access
The Dashboard MUST provide access to the Character Creation feature via a modal dialog.

#### Scenario: Open character creation dialog
- **Given** 用户在 Dashboard 页面
- **When** 点击 "Create Character" 按钮
- **Then** CharacterCreationDialog 模态框打开

### Landing Page Title
The Landing Page title MUST display correctly without text duplication.

#### Scenario: Correct title display
- **Given** 用户访问 Landing Page
- **When** 页面加载完成
- **Then** 标题显示 "NARRATIVE ENGINE"（不重复）

### SPA Route Fallback
The application MUST correctly load when users directly access frontend routes in preview mode.

#### Scenario: Direct route access in preview mode
- **Given** 应用运行在 preview 模式
- **When** 用户直接访问 `/dashboard`
- **Then** 应用正确加载且不显示空白页面

### Demo Mode Banner Dismissible
The Demo Mode banner MUST be dismissible and SHALL remember the user's preference using localStorage.

#### Scenario: Remember dismiss preference
- **Given** 用户之前关闭了 Demo Mode 横幅
- **When** 用户刷新页面或重新访问
- **Then** 横幅不再显示
