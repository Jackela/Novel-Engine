# Novel-Engine 外包项目文档中心

## 项目总览

本项目包含4个并行外包项目，采用文档驱动交付模式。

```
projects/
├── PROJECT_OFFICE.md           # 项目总控中心 (PMO Dashboard)
├── README.md                   # 本文档
├── templates/                  # 通用文档模板
│   ├── requirements_template.md
│   └── acceptance_template.md
│
├── project-a-testing/          # Project A: 测试覆盖率提升
│   ├── VP_AGENT_1_BRIEF.md     # VP Agent 1 工作说明书
│   ├── docs/
│   │   └── requirements.md     # 项目需求文档
│   ├── templates/
│   │   └── acceptance_template.md
│   └── deliverables/           # 交付物目录 (待填充)
│
├── project-b-mypy/             # Project B: MyPy类型修复
│   ├── VP_AGENT_2_BRIEF.md
│   ├── docs/
│   │   └── requirements.md
│   ├── templates/
│   │   └── acceptance_template.md
│   └── deliverables/
│
├── project-c-features/         # Project C: 新功能开发
│   ├── VP_AGENT_3_BRIEF.md
│   ├── docs/
│   │   └── requirements.md
│   ├── templates/
│   │   └── acceptance_template.md
│   └── deliverables/
│
└── project-d-refactor/         # Project D: 重构优化
    ├── VP_AGENT_4_BRIEF.md
    ├── docs/
    │   └── requirements.md
    ├── templates/
    │   └── acceptance_template.md
    └── deliverables/
```

## 项目详情

| 项目 | 编号 | 名称 | 预算 | 期限 | 负责人 |
|------|------|------|------|------|--------|
| A | NE-2024-001 | 核心模块测试覆盖率提升 | 4周 | 2周 | VP Agent 1 |
| B | NE-2024-002 | Python类型系统全面修复 | 3周 | 2周 | VP Agent 2 |
| C | NE-2024-003 | Events & Rumors 系统扩展 | 2周 | 1周 | VP Agent 3 |
| D | NE-2024-004 | 技术债务清理与架构优化 | 2周 | 1周 | VP Agent 4 |

## 快速链接

- [项目总控中心](PROJECT_OFFICE.md)
- [项目A需求](project-a-testing/docs/requirements.md) | [VP Agent 1 任务书](project-a-testing/VP_AGENT_1_BRIEF.md)
- [项目B需求](project-b-mypy/docs/requirements.md) | [VP Agent 2 任务书](project-b-mypy/VP_AGENT_2_BRIEF.md)
- [项目C需求](project-c-features/docs/requirements.md) | [VP Agent 3 任务书](project-c-features/VP_AGENT_3_BRIEF.md)
- [项目D需求](project-d-refactor/docs/requirements.md) | [VP Agent 4 任务书](project-d-refactor/VP_AGENT_4_BRIEF.md)

## 使用流程

### 对于VP Agents

1. **接收任务**: 阅读对应项目的 `VP_AGENT_X_BRIEF.md`
2. **理解需求**: 阅读 `docs/requirements.md`
3. **组建团队**: 招募开发人员
4. **制定计划**: 在 `deliverables/` 目录创建详细计划
5. **执行开发**: 按计划进行开发
6. **提交验收**: 填写 `templates/acceptance_template.md` 并提交

### 对于CTO Office

1. **分派任务**: 将VP Agent任务书发送给各Agent
2. **监控进度**: 查看 `PROJECT_OFFICE.md` 和各项目状态
3. **验收交付**: 使用验收模板审核交付物
4. **批准合并**: 验收通过后批准代码合并

## 文档标准

### 命名规范
- 需求文档: `docs/requirements.md`
- 验收报告: `templates/acceptance_template.md`
- 交付物: `deliverables/[deliverable_name]/`
- 状态报告: `status.md`

### 状态标记
- ⬜ 待开始 / 未交付
- 🔄 进行中 / 审核中
- ✅ 已完成 / 已通过
- ❌ 需修改 / 已拒绝

## 沟通协议

- **每日状态**: 18:00前发送简短更新
- **周报告**: 每周五更新状态文档
- **风险升级**: 重大问题即时上报
- **最终验收**: 交付时提交完整报告

---

**文档版本**: v1.0  
**创建日期**: 2024-03-04  
**维护者**: CTO Office
