# SuperClaude Command Plan for AI Novel System Refactor

## 🎯 执行策略
按照Phase顺序执行，每个阶段完成后验证结果再进入下一阶段。

## Phase 1: 系统清理与重置 (本周)

### 🧹 清理虚假系统
```bash
/cleanup @ai_testing --focus 'template_systems,fake_generation' --archive-to legacy/ --wave-mode systematic --validate
```
**目标**: 将所有模板生成器移动到legacy/目录
**预期输出**: 
- event_types_expansion.py → legacy/template_systems/
- advanced_repetition_detector.py → legacy/template_systems/ 
- content_variation_system.py → legacy/template_systems/
- 标记legacy系统不再使用

### 🏗️ 建立新架构
```bash
/architect @ai_testing --design 'llm_driven_generation' --structure 'core,models,generators,quality' --wave-mode progressive
```
**目标**: 创建真正的AI生成系统架构
**预期输出**: 
- 新目录结构: core/, models/, generators/, quality/
- 基础文件框架和import结构
- 新架构文档和设计说明

### ⚡ LLM集成实现
```bash
/implement @ai_testing/core/llm_client.py --integrate 'gemini-2.0-flash' --test-generation --wave-mode force --all-mcp
```
**目标**: 完成真正的LLM客户端集成
**预期输出**: 
- 工作的Gemini API集成
- 基本的对话生成测试
- 错误处理和重试机制
- 使用量监控和成本跟踪

### 📊 移除虚假指标
```bash
/cleanup @ai_testing --remove 'ngram_analysis,repetition_detection,template_metrics' --focus quality_metrics
```
**目标**: 删除基于模板的假指标系统
**预期输出**: 
- 删除n-gram重复率分析
- 删除模板多样性检测
- 清理相关测试和报告

## Phase 2: AI优先重建 (下周)

### 🤖 角色驱动系统
```bash
/implement @ai_testing/models/character.py --focus 'personality_vectors,emotional_dynamics' --wave-mode adaptive --seq
```
**目标**: 实现AI驱动的角色系统
**预期输出**: 
- 动态性格向量系统
- 情感状态模型
- 角色记忆和关系图

### 🎬 事件生成革命
```bash
/implement @ai_testing/generators/event_generator.py --replace-templates --llm-driven --wave-mode systematic --c7
```
**目标**: 用LLM生成替代所有模板事件
**预期输出**: 
- 基于故事上下文的事件生成
- 角色状态影响事件类型
- 情节连贯性保持

### 💬 对话生成系统
```bash
/implement @ai_testing/generators/dialogue_generator.py --character-aware --context-sensitive --wave-mode progressive
```
**目标**: 基于角色性格的动态对话生成
**预期输出**: 
- 性格特征影响对话风格
- 情感状态影响语调
- 关系状态影响交互

## Phase 3: 质量与创意 (第三周)

### 📈 真实质量指标
```bash
/implement @ai_testing/quality/authenticity_metrics.py --focus 'coherence,creativity,consistency' --wave-mode enterprise
```
**目标**: 建立真正的创意和质量评估
**预期输出**: 
- 语义连贯性评分
- 创意新颖度测量
- 角色一致性检查

### 🔄 创意增强循环
```bash
/implement @ai_testing/quality/enhancement_pipeline.py --multi-pass --self-critique --wave-mode adaptive
```
**目标**: 多轮生成改进系统
**预期输出**: 
- 生成→批评→重生成循环
- 风格一致性保持
- 陈词滥调检测和避免

## 🧪 验证与测试

### 集成测试
```bash
/test @ai_testing --integration --focus 'real_generation,no_templates' --validate mvp_criteria
```
**目标**: 验证整个系统工作正常
**测试内容**: 
- 10段不同角色对话，体现性格差异
- 零模板依赖
- 故事上下文保持连贯
- LLM成本控制在预算内

### 质量验证
```bash
/analyze @ai_testing --quality-assessment --compare 'old_vs_new_system' --generate-report
```
**目标**: 对比新旧系统的质量差异
**分析内容**: 
- 创意度对比（模板选择 vs AI生成）
- 角色一致性评分
- 故事连贯性测量
- 读者满意度预测

## 📋 执行检查清单

### Phase 1 完成标准
- [ ] 所有模板系统移至legacy/
- [ ] 新架构目录结构创建完成
- [ ] LLM客户端可以成功生成内容
- [ ] 虚假指标系统完全移除
- [ ] 基础测试全部通过

### Phase 2 完成标准  
- [ ] 角色性格影响对话生成
- [ ] 事件生成基于故事上下文
- [ ] 情感状态动态影响内容
- [ ] 故事连贯性在多轮生成中保持
- [ ] 集成测试通过

### Phase 3 完成标准
- [ ] 真实质量指标实现
- [ ] 创意增强循环工作正常
- [ ] MVP标准全部达成
- [ ] 系统准备用于V1.0开发

## ⚠️ 执行注意事项

### 依赖管理
```bash
# 确保环境变量已设置
echo $GEMINI_API_KEY
echo $OPENAI_API_KEY  
echo $ANTHROPIC_API_KEY

# 安装必要依赖
pip install google-generativeai tiktoken numpy scikit-learn
```

### 成本控制
- 开发阶段LLM调用总成本控制在$20以内
- 使用temperature=0.1进行基础测试
- 实现缓存机制避免重复调用

### 质量保证
- 每个Phase完成后进行全面测试
- 保留旧系统作为fallback直到新系统稳定
- 记录所有重构决策和理由

---

**执行建议**: 按照Phase顺序逐步执行，每个命令执行后验证结果。如果某个阶段出现问题，可以回退到前一阶段的稳定状态。

**风险缓解**: 所有旧代码都移至legacy/而不是删除，确保可以回滚。新系统采用渐进式开发，确保每个步骤都有明确的验证标准。