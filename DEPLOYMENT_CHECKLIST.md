# 部署检查清单

**项目：** Novel Engine  
**版本：** v2.0.0  
**日期：** 2026-03-06  
**状态：** 生产就绪 ✅

---

## 1. 预部署验证

### 1.1 代码验证

- [x] 代码审查完成
- [x] 单元测试通过
- [x] 集成测试通过（核心流程）
- [x] 安全扫描通过（Bandit）
- [x] Lint检查通过（Ruff）
- [x] 类型检查完成（MyPy）
- [x] A+合规报告生成

### 1.2 版本控制

- [x] 版本号更新（v2.0.0）
- [x] CHANGELOG更新
- [x] Tag创建
- [x] 发布分支合并

---

## 2. 环境配置

### 2.1 基础设施

- [ ] 服务器资源确认（CPU/Memory/Storage）
- [ ] 数据库实例准备
- [ ] Redis/缓存配置
- [ ] 负载均衡器配置
- [ ] SSL证书安装

### 2.2 应用配置

```bash
# 必须环境变量
ENVIRONMENT=production
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
SECRET_KEY=<generated-secret>
JWT_SECRET=<jwt-secret>
API_RATE_LIMIT=1000

# 可选配置
LOG_LEVEL=INFO
ENABLE_METRICS=true
ENABLE_TRACING=true
```

### 2.3 安全配置

- [ ] 生产环境密钥生成
- [ ] 数据库凭据配置
- [ ] API密钥轮换
- [ ] CORS配置验证
- [ ] 防火墙规则配置

---

## 3. 数据库准备

### 3.1 迁移验证

```bash
# 生成迁移脚本
alembic revision --autogenerate -m "v2.0.0 migration"

# 验证迁移
alembic upgrade --sql head > migration_preview.sql

# 执行迁移
alembic upgrade head
```

- [ ] 迁移脚本审查
- [ ] 数据备份
- [ ] 迁移测试（staging）
- [ ] 回滚计划准备

### 3.2 种子数据

- [ ] 系统配置数据
- [ ] 默认用户/角色
- [ ] 初始内容数据

---

## 4. 应用部署

### 4.1 后端部署

```bash
# 安装依赖
pip install -r requirements.txt

# 运行迁移
alembic upgrade head

# 启动服务
gunicorn src.api.main_api_server:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile - \
  --capture-output \
  --enable-stdio-inheritance
```

- [ ] 依赖安装
- [ ] 数据库迁移
- [ ] 健康检查端点验证
- [ ] 日志输出验证

### 4.2 前端部署

```bash
cd frontend
npm ci
npm run build
# 部署dist目录到CDN/Web服务器
```

- [ ] 构建产物验证
- [ ] 静态资源上传
- [ ] CDN刷新
- [ ] 前端路由配置

### 4.3 容器部署（可选）

```bash
# 构建镜像
docker build -t novel-engine:v2.0.0 .

# 推送镜像
docker push registry/novel-engine:v2.0.0

# 部署
kubectl apply -f k8s/
```

---

## 5. 验证测试

### 5.1 健康检查

```bash
# API健康检查
curl https://api.novel-engine.com/health

# 预期响应
{
  "status": "healthy",
  "version": "v2.0.0",
  "timestamp": "2026-03-06T..."
}
```

- [ ] API健康检查
- [ ] 数据库连接检查
- [ ] 缓存连接检查
- [ ] 外部服务检查

### 5.2 功能验证

- [ ] 用户登录/注册
- [ ] 角色创建流程
- [ ] 叙事生成功能
- [ ] 世界状态查询
- [ ] SSE流功能

### 5.3 性能基准

- [ ] API响应时间 < 200ms
- [ ] 并发用户支持 > 100
- [ ] 内存使用 < 2GB
- [ ] CPU使用 < 70%

---

## 6. 监控配置

### 6.1 日志监控

- [ ] 结构化日志配置
- [ ] 日志收集（ELK/Loki）
- [ ] 告警规则配置
- [ ] 错误率监控

### 6.2 指标监控

- [ ] Prometheus指标暴露
- [ ] Grafana仪表板配置
- [ ] 关键指标告警
  - [ ] 错误率 > 1%
  - [ ] 响应时间 > 500ms
  - [ ] CPU > 80%
  - [ ] 内存 > 85%

### 6.3 链路追踪

- [ ] OpenTelemetry配置
- [ ] Jaeger/Zipkin集成
- [ ] 采样率配置（10%）

---

## 7. 备份与恢复

### 7.1 数据备份

```bash
# 数据库备份
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# 配置备份
tar czvf config_backup_$(date +%Y%m%d).tar.gz config/
```

- [ ] 自动备份任务配置
- [ ] 备份验证
- [ ] 恢复流程文档

### 7.2 灾难恢复

- [ ] RTO < 1小时
- [ ] RPO < 15分钟
- [ ] 恢复演练完成

---

## 8. 文档更新

- [ ] API文档发布
- [ ] 用户手册更新
- [ ] 运维手册更新
- [ ] 故障处理手册

---

## 9. 发布沟通

- [ ] 发布通知发送
- [ ] 更新日志发布
- [ ] 用户沟通完成
- [ ] 支持团队培训

---

## 10. 回滚计划

### 10.1 回滚触发条件

- 错误率 > 5%
- 响应时间 > 2s
- 关键功能不可用
- 安全事件发生

### 10.2 回滚步骤

```bash
# 1. 停止新流量
kubectl scale deployment novel-engine --replicas=0

# 2. 数据库回滚（如需要）
alembic downgrade -1

# 3. 切换版本
kubectl set image deployment/novel-engine novel-engine=registry/novel-engine:v1.x.x

# 4. 验证回滚
curl https://api.novel-engine.com/health

# 5. 恢复流量
kubectl scale deployment novel-engine --replicas=4
```

---

## 签署

| 角色 | 姓名 | 日期 | 签名 |
|------|------|------|------|
| 技术负责人 | | | |
| QA负责人 | | | |
| 运维负责人 | | | |
| 产品负责人 | | | |

---

*部署清单版本: v2.0.0*  
*最后更新: 2026-03-06*
