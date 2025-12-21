## 1. Environment Setup
- [x] 1.1 启动 Backend API (port 8000)
- [x] 1.2 启动 Frontend Dev Server (port 3000)
- [x] 1.3 验证服务健康状态

## 2. Chrome DevTools MCP Testing
- [x] 2.1 打开浏览器页面
- [x] 2.2 Landing Page 截图
- [x] 2.3 Dashboard 截图
- [x] 2.4 MFD 各模式截图 (NET, TIME, SIG)
- [x] 2.5 Decision Dialog 截图 (跳过 - 需要 live SSE 事件，已在 spec 中记录为 future work)
- [x] 2.6 Mobile 响应式截图

## 3. Bug Detection
- [x] 3.1 检查 Console 错误 (无错误，仅 SSE heartbeat warning)
- [x] 3.2 检查 Network 请求 (正常)
- [x] 3.3 修复发现的问题 (无需修复)

## 4. Documentation
- [x] 4.1 更新 README.md 截图引用
- [x] 4.2 更新 README.en.md 截图引用
- [x] 4.3 创建 CONTRIBUTING.md
- [x] 4.4 创建 SECURITY.md
- [x] 4.5 创建 CHANGELOG.md

## 5. Validation
- [x] 5.1 运行 lint 检查 (预存在 7 个 lint 错误，非本次引入)
- [x] 5.2 运行 type-check (通过)
- [x] 5.3 验证截图文件完整 (6 个截图)
- [x] 5.4 运行 openspec validate

## Screenshots Captured
| File | Size | Description |
|------|------|-------------|
| landing-hero.png | 224KB | Landing page hero section |
| dashboard-overview.png | 137KB | Full dashboard view |
| mfd-net.png | 153KB | Character Networks view |
| mfd-time.png | 159KB | Narrative Timeline view |
| mfd-sig.png | 158KB | Event Cascade Flow view |
| dashboard-mobile.png | 91KB | Mobile responsive view |

## Files Created/Modified
- `README.md` - Added Feature Preview section with screenshots
- `README.en.md` - Added Feature Preview section with screenshots
- `CONTRIBUTING.md` - New contribution guidelines
- `SECURITY.md` - New security policy
- `CHANGELOG.md` - New changelog
- `docs/assets/screenshots/` - 6 new screenshot files
