# Local CI Testing with ACT

## 概述

[ACT](https://github.com/nektos/act) 是一个在本地运行 GitHub Actions 工作流的工具。使用 ACT，开发者可以在 push 到远程之前本地验证 CI 工作流，节省时间和资源。

## 安装

### 通过 Makefile 安装 (推荐)

```bash
make act-setup
```

### 手动安装

**macOS:**
```bash
brew install act
```

**Linux:**
```bash
# 使用官方安装脚本
curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# 或使用包管理器 (Arch Linux)
sudo pacman -S act
```

**Windows:**
```powershell
# 使用 winget
winget install nektos.act

# 或使用 chocolatey
choco install act-cli
```

**Docker:**
```bash
docker pull nektos/act-environments-ubuntu:18.04
```

## 配置

### 1. 复制 Secrets 模板

```bash
cp .github/act-secrets.sample .github/act-secrets
```

### 2. 编辑 `.github/act-secrets`

添加你的 GitHub Token 和其他必要的 secrets：

```bash
# 访问 https://github.com/settings/tokens 创建 Token
# 需要的权限: repo, workflow
GITHUB_TOKEN=ghp_your_token_here

# 可选：Codecov Token (用于覆盖率报告)
CODECOV_TOKEN=your_codecov_token_here
```

### 3. 验证 ACT 配置

```bash
# 检查 ACT 版本
act --version

# 列出可用的工作流和 jobs
make act-list
```

## 使用方法

### 列出可用工作流

```bash
make act-list
# 或
act -l
```

### 运行 CI 工作流

```bash
# 运行完整的 CI 工作流
make act-ci

# 运行特定的 job
act -W .github/workflows/ci.yml -j unit-tests

# 运行 Python 测试工作流
act -W .github/workflows/python-tests.yml
```

### 运行特定 Job

```bash
# 只运行单元测试
act -W .github/workflows/ci.yml -j unit-tests

# 只运行 Python 测试
act -W .github/workflows/python-tests.yml -j python-test

# 只运行集成测试
act -W .github/workflows/ci.yml -j integration-tests
```

### 快速模式（预览）

```bash
# Dry-run 模式：显示将要执行的内容但不实际运行
make act-ci-dry

# 或
act -W .github/workflows/ci.yml -n
```

### 详细日志

```bash
# 使用 verbose 模式查看详细输出
act -W .github/workflows/ci.yml --verbose

# 查看 job 的 graph 结构
act -W .github/workflows/ci.yml --graph
```

## Makefile 命令参考

| 命令 | 说明 |
|------|------|
| `make act-setup` | 检查并设置 ACT 环境 |
| `make act-list` | 列出所有可用的工作流和 jobs |
| `make act-ci` | 运行完整的 CI 工作流 |
| `make act-python` | 运行 Python 测试工作流 |
| `make act-ci-dry` | Dry-run 模式（预览） |
| `make act-clean` | 清理 ACT 容器和 artifacts |

## 故障排除

### 内存不足

如果遇到内存不足问题，可以使用更小的镜像：

```bash
# 编辑 .actrc，修改为更小的镜像
-P ubuntu-latest=catthehacker/ubuntu:act-20.04
```

### 镜像下载慢

```bash
# 配置 Docker 镜像加速器（中国大陆用户）
# 编辑 ~/.docker/daemon.json
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com"
  ]
}
```

### 网络代理

```bash
# 如果需要代理，设置环境变量
export HTTP_PROXY=http://proxy:port
export HTTPS_PROXY=http://proxy:port
act ...
```

### Docker 未运行

```bash
# 检查 Docker 状态
docker info

# 如果 Docker 未运行，启动 Docker Desktop 或服务
# macOS/Windows: 启动 Docker Desktop
# Linux: sudo systemctl start docker
```

### Secrets 未找到

```bash
# 确保 .github/act-secrets 文件存在且格式正确
ls -la .github/act-secrets

# 验证文件内容格式
cat .github/act-secrets
```

### 权限问题

```bash
# 如果 ACT 需要 sudo，可以将用户添加到 docker 组
sudo usermod -aG docker $USER
# 然后重新登录
```

## 最佳实践

1. **本地优先**: 对于复杂的改动，先使用 ACT 本地验证 CI 工作流再 push

2. **快速反馈循环**:
   ```bash
   # 1. 快速检查
   make ci-check
   
   # 2. ACT 完整验证
   make act-ci
   
   # 3. 推送
   git push
   ```

3. **资源管理**:
   ```bash
   # 定期清理 ACT 容器和 artifacts
   make act-clean
   
   # 清理 Docker 缓存
   docker system prune -f
   ```

4. **工作流开发**:
   ```bash
   # 修改工作流文件后，先用 dry-run 验证
   act -W .github/workflows/ci.yml -n
   
   # 确认无误后运行实际测试
   act -W .github/workflows/ci.yml -j tests
   ```

5. **调试技巧**:
   ```bash
   # 进入容器手动调试
   act -W .github/workflows/ci.yml --reuse
   
   # 使用 verbose 模式
   act --verbose
   ```

## 配置文件说明

### `.actrc`

项目级的 ACT 配置文件，包含：
- 默认镜像设置
- 默认工作流路径
- Secrets 文件位置
- 环境变量文件
- Artifact 存储路径

### `.github/act-secrets`

本地 secrets 文件（已加入 `.gitignore`），包含：
- GitHub Token
- Codecov Token
- 其他工作流需要的 secrets

## 相关文档

- [ACT GitHub Repository](https://github.com/nektos/act)
- [ACT Documentation](https://nektosact.com/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- 项目 CI 配置: `.github/workflows/ci.yml`
