# Novel-Engine UI 审查报告

## 基本信息
- **审查日期**: 2025-11-28 22:30 - 22:45
- **审查人**: Claude Code UI Auditor
- **前端版本**: storyforge-ai-frontend@0.0.0
- **测试环境**:
  - 桌面端: 默认视口 (约 1280x720)
  - 运行模式: Vite Preview (生产构建)
  - 后端: localhost:8000

## 审查进度
- [x] Landing Page (桌面端) - 完成
- [ ] Landing Page (移动端) - 未测试
- [x] Dashboard (桌面端) - 完成
- [ ] Dashboard (移动端) - 未测试
- [x] Character Creation - 发现路由问题
- [x] Decision Dialog - 完成
- [x] Error Handling - 完成

## 测试统计
| 区域 | 测试次数 | 通过 | 失败 | 问题数 |
|------|---------|------|------|--------|
| Landing Page | 3 | 3 | 0 | 1 |
| Dashboard | 5 | 5 | 0 | 2 |
| Character Creation | 1 | 0 | 1 | 1 |
| Decision Dialog | 3 | 3 | 0 | 1 |
| Error Handling | 1 | 0 | 1 | 1 |
| **总计** | **13** | **11** | **2** | **6** |

---

## 发现的问题

### 严重 (Critical) - 必须修复

| # | 页面 | 问题描述 | 复现步骤 | Console 错误 |
|---|------|---------|---------|--------------|
| 1 | 全局 | **Vite Dev Server 在 WSL2 环境下存在严重的 HMR 连接问题** | 1. 在 WSL2 中运行 `npm run dev` 2. 浏览器访问 localhost:3000 3. 页面显示白屏/黑屏，模块加载卡在 pending | `Failed to load module script: Expected a JavaScript-or-Wasm module script but the server responded with a MIME type of ""` |
| 2 | Character Creation | **CharacterStudio 组件未集成到应用路由中** | 1. 在 App.tsx 中查看路由配置 2. 发现只有 `/`, `/dashboard`, `/login` 路由 3. CharacterStudio (`/characters`) 不存在于路由表 | 无 (设计问题) |

**解决方案建议**:
1. **HMR 问题**: 使用 `npm run build && npm run preview` 替代 `npm run dev` 进行测试
2. **Character Creation**: 在 App.tsx 中添加 `/characters` 路由，或将 CharacterCreationDialog 集成到 Dashboard 中

---

### 警告 (Warning) - 建议修复

| # | 页面 | 问题描述 | 复现步骤 | 建议 |
|---|------|---------|---------|------|
| 1 | Landing Page | 页面标题中 "NARRATIVE" 重复显示 | 查看 h1 标题 | 检查 LandingPage 组件的标题文本，当前显示 "NARRATIVE ENGINE NARRATIVE" |
| 2 | Decision Dialog | **计时器显示 "NAN:NAN"** | 1. 点击 Start orchestration 2. Decision Dialog 弹出 3. 查看倒计时显示 | 检查 `remainingSeconds` 的初始化值，确保是有效数字 |
| 3 | Dashboard | **Activity Stream 时间显示异常** | 启动 orchestration 后查看活动流 | 显示 "490091h ago" 和 "NaNh ago"，需要检查时间戳处理逻辑 |
| 4 | 全局 | **Preview 模式下 404 路由显示空白页** | 直接访问 `/nonexistent-page` | SPA 路由需要服务端配置 fallback 到 index.html |

---

### 建议 (Info) - 可选改进

| # | 页面 | 问题描述 | 建议改进 |
|---|------|---------|---------|
| 1 | Landing Page | 按钮文本根据状态变化 (View Demo / Resume Simulation) | 这是预期行为，但建议在 UI 中添加说明，让用户理解状态变化 |
| 2 | Dashboard | Demo Mode 横幅始终显示 | 考虑添加 "不再显示" 选项 |

---

## Console 日志汇总

### 错误 (Errors)
仅在 Vite Dev 模式下出现:
```
Failed to load module script: Expected a JavaScript-or-Wasm module script
but the server responded with a MIME type of "".
Strict MIME type checking is enforced for module scripts per HTML spec.
```

### 警告 (Warnings)
无

### 正常日志 (Preview 模式)
- `i18next: languageChanged en-US`
- `i18next: initialized`
- `[INFO] Initializing authentication state`
- `[DEBUG] No token found in storage`
- `[INFO] Web Vital metric` (FCP, TTFB)

---

## 网络请求问题

### 失败的请求 (Dev 模式)
| # | URL | 状态 | 问题 |
|---|-----|------|------|
| 1 | /meta/system-status | net::ERR_ABORTED | Vite proxy 问题 |
| 2 | /health | net::ERR_ABORTED | Vite proxy 问题 |
| 3 | /api/orchestration/status | net::ERR_ABORTED | Vite proxy 问题 |
| 4 | /api/analytics/metrics | net::ERR_ABORTED | Vite proxy 问题 |

**注**: 这些问题在 Preview 模式下不存在，因为 Preview 不使用 Vite proxy。

### Preview 模式
所有 API 请求成功 (200)

---

## 功能验证

### Landing Page
- [x] 页面正确加载和渲染
- [x] "View Demo" 按钮正常工作 -> 导航到 /dashboard
- [x] "Enter Dashboard" 按钮可见
- [x] "Request Access" 链接正确 (mailto:)
- [x] 三个功能卡片正确显示
- [x] 版本标识 "Novel Engine v1.0" 显示正确

### Dashboard
- [x] 页面正确加载和渲染
- [x] Demo Mode 横幅显示
- [x] Engine Panel 显示 Turn Pipeline
- [x] World State Map 显示 5 个角色
- [x] Insights Panel 显示
- [x] MFD 模式选择器 (DATA/NET/TIME/SIG) 显示
- [x] Analytics 数据显示 (Story Quality, Engagement, Coherence)
- [x] Real-time Activity Stream 显示 "● Live" 状态
- [x] SSE 连接正常 ("Real-time event stream connected")
- [x] Start orchestration 按钮正常工作
- [x] 状态变化 IDLE -> RUNNING 正常

### Decision Dialog
- [x] 对话框正确弹出
- [x] 显示 4 个选项 (INVESTIGATE, RETREAT, CONFRONT, SEEK HELP)
- [x] 选项选择功能正常
- [x] Confirm 按钮关闭对话框
- [x] Skip 按钮可见
- [ ] 计时器显示异常 (NAN:NAN)

### Character Creation
- [ ] **组件存在但未集成到路由** - CharacterStudio 在 `/frontend/src/components/CharacterStudio/` 但 App.tsx 中没有对应路由

### Error Handling
- [ ] **404 页面显示空白** - Preview 模式下需要服务端配置 SPA fallback

---

## 截图索引
| 文件名 | 描述 |
|--------|------|
| landing-desktop-initial.png | Landing Page 初始状态 |
| dashboard-desktop-initial.png | Dashboard 初始状态 |
| dashboard-from-viewdemo.png | 从 View Demo 导航后的 Dashboard |
| decision-dialog-initial.png | Decision Dialog 弹出状态 (显示 NAN:NAN bug) |
| decision-dialog-option-selected.png | Decision Dialog 选项选中状态 |
| dashboard-running-state.png | Dashboard 运行状态 (显示时间 bug) |

---

## 总结

### 整体评估
**良好** - 应用核心功能正常工作，UI 渲染正确，后端 API 连接正常。

发现 **6 个问题**，其中 **2 个严重**，**4 个警告**。

### 优先修复建议
1. **高优先级**: 修复 Decision Dialog 计时器 NaN 显示问题
2. **高优先级**: 修复 Activity Stream 时间戳异常显示
3. **高优先级**: 将 CharacterStudio 集成到应用路由
4. **中优先级**: 检查 Landing Page 标题文本重复问题
5. **中优先级**: 配置 Preview 模式的 SPA fallback
6. **低优先级**: 考虑添加 Demo Mode 横幅的关闭/记住选项

### 后续建议
- 完成移动端响应式测试
- 进行完整的 10 次重复点击测试
- 测试键盘导航 (Tab, Enter, Escape)
- 测试后端断开时的错误恢复

### 环境建议
对于 WSL2 开发环境，已在 `vite.config.ts` 中应用以下优化:
```typescript
server: {
  host: '0.0.0.0',          // 绑定所有接口
  port: 3000,
  strictPort: true,         // 端口占用时失败
  hmr: {
    protocol: 'ws',
    host: 'localhost',
    clientPort: 3000,       // 防止端口映射混乱
  },
  watch: {
    usePolling: true,
    interval: 100,          // 更快的轮询响应
  },
}
```

**已应用修复**: 2025-11-28 22:35 - 更新了 vite.config.ts

---

**报告生成时间**: 2025-11-28 22:32
**最后更新**: 2025-11-28 22:45
