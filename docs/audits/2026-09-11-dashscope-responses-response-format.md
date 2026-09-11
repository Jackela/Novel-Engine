# DashScope Responses-mode `response_format` 容忍性审计（#386）

- 日期：2026-09-11
- 性质：一手文档审计（非服务端实证）。结论依据 Alibaba Cloud / DashScope
  官方文档原文，来源 URL 逐条附列；调研由只读 research 子代理执行，
  主会话整合验收。
- 关联：issue #386（原 needs-info：DashScope Responses-mode 对顶层
  `response_format` 的容忍性三向对照实证）、
  `server/src/contexts/ai/infrastructure/providers/dashscope_protocol.ts`、
  issue #386 决策矩阵（容忍 → 补 `docs/audits/` 记录；拒绝 → 改载荷）。
- 基线 commit：`6a568f0c`（main）。

## 0. 结论

**文档层面容忍分支成立**：DashScope OpenAI 兼容 Responses API 的官方参数表
（共 15 个：`model` `input` `instructions` `previous_response_id`
`conversation` `stream` `store` `tools` `tool_choice` `temperature` `top_p`
`enable_thinking` `reasoning` `ocr_options` `max_output_tokens`）**不含**
`response_format`，且文档 Core Principle 明文规定（英文站）：

> "Only the parameters explicitly listed in this document are processed. Any
> OpenAI parameters not mentioned are ignored."

（中文站对应："请求将仅处理本文档明确列出的参数，任何未提及的 OpenAI 参数
都会被忽略。"）

因此本仓库 Responses 模式发送的顶层 `response_format: { type:
"json_object" }`（`dashscope_protocol.ts` Responses 分支）按文档会被
**静默忽略——不报错，但也不生效**。错误码页不存在任何"未知顶层参数被
拒绝"的条目，与该规则自洽。

## 1. 处置

按 #386 决策矩阵的"容忍"分支：**保持现状，不改载荷**。JSON 正确性的实际
保障链维持为：

1. `provider_json.ts` 系统提示中的 "Return valid JSON only." 约束
   （满足 Chat Completions 侧 json_object 对 prompt 含 "json" 关键字的要求，
   且对 Responses 侧是唯一的 JSON 约束来源）；
2. 下游 `payloadFromResponseText` 解析容错；
3. #497 起流式路径的增量解包器（`stream_json_unwrap.ts`）。

注意：Responses 模式下**不存在文档化的结构化输出参数**（structured output
专页全文未提及 `/responses` 端点，Responses 参考页亦无 JSON 输出参数；
Chat Completions 侧的 `response_format` 与 DashScope 原生侧
`parameters.response_format` 均不适用于 Responses 端点）。若未来需要服务端
强约束，只能等官方为 Responses 端点补充参数或迁移端点。

## 2. 附带发现：legacy 路径（独立 issue 处理）

文档原文（URL 直引见上方来源；路径按仓库 hygiene 门禁惯例以段片段书写，
`api` 根 + `v2` 版本段）：

> "The legacy URL path …`api`/`v2`/`apps`/`protocols`/`compatible-mode`/
> `v1`/`responses` for the OpenAI-compatible Responses API is no longer
> maintained and its functionality is no longer guaranteed. Migrate to the
> new path `/compatible-mode/v1/responses` as soon as possible."

即：legacy 路径 = `api` 根下的 `v2` 段 + `apps/protocols/compatible-mode` +
`v1` 段 + `/responses`（源码中由 `DASHSCOPE_API_PATH_SEGMENTS` 段片段拼出，
`dashscope_protocol.ts` 的 `DEFAULT_DASHSCOPE_RESPONSES_API_BASE`）；迁移
目标为 `/compatible-mode/v1/responses`。

本仓库 Responses 模式默认 base 即该 legacy 路径，且 `normalizeResponsesBase`
会把**任何**注入的 `apiBase` 强制改写回 legacy 路径——即使配置新路径也会被
覆盖。这意味着上述"忽略"规则在仓库实际使用的旧路径上连"不再保证"都适用。
该问题超出 #386 范围，另开 issue #502 单独决策（涉及 base URL 可配置性与
`normalizeResponsesBase` 的强制改写行为）。

## 3. 若未来提供 DashScope key，实证 probe 断言清单

1. **容忍性**：向 Responses 端点发送与 `buildRequestPayload` 完全一致的载荷
   （含顶层 `response_format`），断言 HTTP 200 且 `output[].type ===
   "message"`；若 400/InvalidParameter 则切换"拒绝 → 改载荷"分支。
2. **效力差分**：同 task 分别发送含/不含顶层 `response_format` 各 N 次，
   统计非法 JSON（`JSON.parse` 失败或含 ```json 围栏）频率；无显著差异则
   实证确认"忽略、不生效"。
3. **路径对照**：legacy 与新路径各发同一请求断言可用性，并实测
   `normalizeResponsesBase` 对注入新路径的强制改写行为。

## 4. 来源

- Responses API（英文站）：
  https://www.alibabacloud.com/help/en/model-studio/qwen-api-via-openai-responses
- Responses API（中文站）：
  https://help.aliyun.com/zh/model-studio/qwen-api-via-openai-responses
- 结构化输出（Chat Completions / 原生 `parameters.response_format`）：
  https://www.alibabacloud.com/help/en/model-studio/qwen-structured-output
- DashScope 原生 API：
  https://www.alibabacloud.com/help/en/model-studio/qwen-api-via-dashscope
- 错误码（400-InvalidParameter 类）：
  https://help.aliyun.com/zh/model-studio/error-code
