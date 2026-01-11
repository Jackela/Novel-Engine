# Novel Engine 测试套件

本目录包含 Novel Engine 的完整测试套件，涵盖单元测试、集成测试和端到端（E2E）测试。

## 目录结构

```
tests/
├── integration/          # 集成测试
│   └── api-characters.test.ts
├── e2e/                  # 端到端测试
│   ├── character-creation.spec.ts
│   └── narrative-generation.spec.ts
└── README.md

frontend/src/services/__tests__/
└── api.test.ts          # 单元测试
```

## 运行测试

### 前提条件

确保已安装所有依赖：

```bash
# 安装前端依赖
cd frontend
npm install

# 安装 Python 依赖
cd ..
pip install -r requirements.txt

# 安装 Playwright 浏览器
cd frontend
npx playwright install
```

### 单元测试

运行所有单元测试：

```bash
cd frontend
npm run test:unit
```

监听模式（自动重新运行）：

```bash
npm run test:watch
```

带覆盖率报告：

```bash
npm run test:coverage
```

### 集成测试

集成测试需要后端服务运行。

1. 启动后端：

```bash
python -m uvicorn src.api.app:create_app --factory --host 127.0.0.1 --port 8000
```

2. 运行集成测试：

```bash
cd frontend
npm run test:integration
```

### 端到端测试

E2E 测试会自动启动前后端服务（通过 playwright.config.ts 配置）。

运行所有 E2E 测试：

```bash
npx playwright test
```

运行特定测试文件：

```bash
# 角色创建测试
npm run test:e2e:character

# 叙事生成测试
npm run test:e2e:narrative
```

带 UI 界面运行（推荐用于调试）：

```bash
npm run test:e2e:ui
```

有头模式运行（显示浏览器）：

```bash
npm run test:e2e:headed
```

### 运行所有测试

```bash
# 在项目根目录
npm test                    # 运行单元测试
cd frontend && npm run test:e2e  # 运行 E2E 测试
```

## 测试内容

### 单元测试 (`frontend/src/services/__tests__/api.test.ts`)

测试 API 工具函数：

- ✅ `generateAgentId()` - 角色 ID 生成逻辑
  - 名称转换为小写下划线格式
  - 处理特殊字符和数字
  - 强制长度限制（3-50 字符）
  - 幂等性测试

- ✅ `normalizeSkillValue()` - 技能值标准化
  - 1-10 范围转换为 0.0-1.0
  - 边界值处理
  - 值钳位（clamping）

### 集成测试 (`tests/integration/api-characters.test.ts`)

测试角色 API 的完整流程：

- ✅ POST `/api/characters` - 创建角色
  - 正确的 agent_id 生成
  - 技能值标准化
  - 验证错误处理

- ✅ GET `/api/characters` - 列出所有角色
  - 工作区隔离
  - 数据完整性

- ✅ GET `/api/characters/:id` - 获取特定角色
  - 成功检索
  - 404 错误处理

- ✅ PUT `/api/characters/:id` - 更新角色
  - 数据更新正确性
  - 持久化验证

- ✅ DELETE `/api/characters/:id` - 删除角色
  - 成功删除
  - 删除后验证

- ✅ 数据持久化测试
  - 跨请求数据一致性

### E2E 测试

#### 角色创建 (`tests/e2e/character-creation.spec.ts`)

- ✅ 成功创建新角色
- ✅ 验证错误显示（输入无效时）
- ✅ 取消创建流程
- ✅ 页面刷新后数据持久化
- ✅ 角色详情正确显示
- ✅ 网络错误处理
- ✅ API 失败时显示后备角色
- ✅ 无角色时显示空状态

#### 叙事生成 (`tests/e2e/narrative-generation.spec.ts`)

- ✅ 成功启动叙事生成
- ✅ 暂停和恢复生成
- ✅ 停止生成
- ✅ 完成生成并显示结果
- ✅ 显示进度指示器
- ✅ 错误处理
- ✅ 防止多重生成
- ✅ 实时内容更新
- ✅ 生成结果持久化

## CI/CD

测试会在每次推送和 Pull Request 时自动运行（通过 GitHub Actions）。

查看 `.github/workflows/tests.yml` 了解详细配置。

## 故障排除

### 端口已被占用

如果测试失败并显示端口错误：

```bash
# Windows
netstat -ano | findstr :3000
netstat -ano | findstr :8000
taskkill /F /PID <进程ID>

# Linux/Mac
lsof -i :3000
lsof -i :8000
kill -9 <进程ID>
```

### Playwright 浏览器未安装

```bash
cd frontend
npx playwright install
```

### 测试超时

增加测试超时时间（在测试文件中）：

```typescript
test('my test', async ({ page }) => {
  test.setTimeout(60000); // 60 seconds
  // ...
});
```

### 环境变量问题

确保 `frontend/.env.development` 文件存在并正确配置：

```env
# 开发环境使用空 baseURL 以启用 Vite 代理
VITE_API_BASE_URL=
VITE_ENABLE_GUEST_MODE=true
```

## 最佳实践

1. **在提交前运行测试**：确保所有测试通过
2. **编写可维护的测试**：使用清晰的测试名称和结构
3. **避免脆弱的选择器**：优先使用 `data-testid` 或角色选择器
4. **独立测试**：每个测试应该能独立运行
5. **清理资源**：测试后清理创建的数据

## 贡献

添加新测试时：

1. 遵循现有的测试结构和命名约定
2. 确保测试可重复运行
3. 添加适当的文档注释
4. 更新本 README 文件

## 参考资料

- [Vitest 文档](https://vitest.dev/)
- [Playwright 文档](https://playwright.dev/)
- [测试最佳实践](https://github.com/goldbergyoni/javascript-testing-best-practices)
