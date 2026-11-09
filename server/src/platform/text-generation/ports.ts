/**
 * 文本生成端口（platform 层）：generation 切片唯一可见的上游模型契约。
 *
 * 相对旧实现（`contexts/ai/application/ports/text_generation.ts` 及其 3,001 行适配库）的三处取舍：
 *
 * 1. 去掉 `UnconfiguredProvider`：旧工厂凭据为空时返回假 provider，只在首次 pull 才失败，于是「有没有
 *    能力」与「配没配置」被压进同一个对象；新端口由工厂直接抛 `unconfigured`，能力只看方法在不在。
 * 2. 错误分类结构化：旧实现靠四个 class 的布尔字段 + 文案前缀判三档超时，改一个字就可能改行为；
 *    新端口用判别联合，种类即判定依据，文案不进联合。
 * 3. 协议模式收敛成描述符（旧实现把请求形状/取文本/终结帧/错误帧摊在四个文件），描述符属于适配器。
 *
 * 本文件只有类型与字面量集合，没有实现；不依赖 Fastify / Drizzle / Node API。
 */

/** 客户端只选 provider，永不选模型；模型由服务端解析链决定。 */
export const PROVIDER_NAMES = ["mock", "dashscope", "openai_compatible"] as const;

export type ProviderName = (typeof PROVIDER_NAMES)[number];

/** provider 面向的步骤词汇，闭集；应用层在此把 operation 翻译成 step，适配器遇到集合外的值必须抛错不得回显。 */
export const PROVIDER_STEPS = [
  "chapter_draft",
  "chapter_revision",
  "editorial_review",
  "lore_extract",
] as const;

export type ProviderStep = (typeof PROVIDER_STEPS)[number];

/** `text` 的读法：散文步骤是可直接落正文的 markdown，JSON 步骤是已收敛、可直接 `JSON.parse` 的文本。 */
export type StepTextKind = "prose" | "json";

/** 每个 step 的 `text` 形状，是「结构化任务 vs 自由文本」的唯一判定处：调用方查表，不按名字面量分支。 */
export const STEP_TEXT_KIND = {
  chapter_draft: "prose",
  chapter_revision: "prose",
  editorial_review: "json",
  lore_extract: "json",
} as const satisfies Readonly<Record<ProviderStep, StepTextKind>>;

export type ProseStep = {
  readonly [K in ProviderStep]: (typeof STEP_TEXT_KIND)[K] extends "prose" ? K : never;
}[ProviderStep];

export type StructuredStep = Exclude<ProviderStep, ProseStep>;

/** 生成语言闭集（DR-023）；缺省按 `en` 处理，以免旧任务形状换掉行为。 */
export const WRITING_LANGUAGES = ["en", "zh"] as const;

export type WritingLanguage = (typeof WRITING_LANGUAGES)[number];

/** 用量证据。`null` 表示「provider 没给证据」而非 0：null 走估算，0 会被当成真实计量。 */
export interface ProviderUsage {
  readonly promptTokens: number | null;
  readonly completionTokens: number | null;
}

/** 是谁、用哪个模型、上游怎么称呼这次请求——只作诊断取证，不参与任何判定。 */
export interface ProviderProvenance {
  readonly provider: ProviderName;
  /** 解析链最终选定的模型；不是任务里声明的期望值。 */
  readonly model: string;
  /** 上游响应携带的请求标识（响应头或 body id）；上游不给时缺省。 */
  readonly upstreamRequestId?: string;
}

export interface TextGenerationResult {
  /** 回显本次调用的 step，供落地层与用量表按「步骤 × provider」归账。 */
  readonly step: ProviderStep;
  /**
   * 正文文本。散文步骤：已解包、**未净化**的 markdown（净化属应用层）；JSON 步骤：**已提取并按 schema
   * 收敛**的 JSON，`JSON.parse` 必然成功。括号扫描、围栏剥除、捞对象、数组/整数化收敛、裸散文兜底都在
   * 适配器内，落地层不得退化成裸 parse。
   */
  readonly text: string;
  readonly usage: ProviderUsage;
  readonly provenance: ProviderProvenance;
}

/**
 * 三档超时。它们不是同一个数的三种写法：
 * - `firstByteMs`：open 成功后到首帧的静默上限，唯一兜住「连通但不开口」的那档。
 * - `idleMs`：相邻两帧之间的静默上限，每帧重新起算，最紧的一档。
 * - `deadlineMs`：派发起算、**每帧 rearm**（DR-026），约束「派发 + 静默」而非健康流总墙钟；四个
 *   长文 step 由组合根抬到 ≥180s。
 */
export interface ProviderTimeoutConfig {
  readonly deadlineMs: number;
  readonly firstByteMs: number;
  readonly idleMs: number;
}

export interface TextGenerationTask {
  readonly step: ProviderStep;
  readonly systemPrompt: string;
  readonly userPrompt: string;
  readonly language?: WritingLanguage;
  /** 解析链产物；适配器只透传，不改写、不校验。 */
  readonly model: string;
  readonly timeouts: ProviderTimeoutConfig;
  /** 仅 JSON 步骤需要：期望的顶层字段与类型。散文步骤省略该字段。 */
  readonly responseSchema?: Record<string, unknown>;
}

export interface ProviderStreamOptions {
  /** 中止入口：abort 后已 yield 的增量仍有效，但不再有返回值。 */
  readonly signal?: AbortSignal;
}

/**
 * 流正常结束时的证据。须把生成器读到 `done` 才拿得到：提前 break 或 abort 视为无 outcome，单次
 * `gen.next()` 不算数。
 */
export type ProviderStreamOutcome = Omit<TextGenerationResult, "step" | "text">;

/** 一次请求一个实例，不得跨请求复用（复用会把超时、取消、用量证据串到另一次请求上）。 */
export interface TextGenerationProvider {
  /** 一次生成。任何预期失败都抛 `ProviderFailure`，不降级、不返回半成品；实现错误不包装。 */
  generate(task: TextGenerationTask): Promise<TextGenerationResult>;
  /** 可选流式：逐帧增量，拼接必须逐字节等于 `generate().text`；解包不可放宽成透传（会漏转义碎片）。 */
  generateStreaming?(
    task: TextGenerationTask,
    options?: ProviderStreamOptions,
  ): AsyncGenerator<string, ProviderStreamOutcome, void>;
  /** 请求级清理：只释放本次请求的资源，不改变生成结果；清理失败只上报观测，不升级为生成失败。 */
  dispose?(): Promise<void>;
}

/**
 * 构造一次请求的 provider。工厂在组合根注入，import 期不得构造实例。未配置时必须**直接抛**
 * `{ kind: "unconfigured" }`，而不是返回「一调用才失败」的假 provider：伪 provider 会让能力探测、
 * 目录端点、可用性判断各自猜一次「能不能用」。抛出点是唯一事实来源。
 */
export type TextGenerationProviderFactory = (name: ProviderName) => TextGenerationProvider;

/**
 * 重试与超时策略。**响应体内容永不参与重试决策**，只看 `retryable`；且重试只覆盖首帧之前
 * （open 阶段）——首帧一旦进入解包就永不再试，重放会打乱增量解包状态并产出错乱散文（DR-006）。
 * 这里的 `timeouts` 只是组合根算出的默认值：适配器**只读 `task.timeouts`**，否则 180s 长文下限会被覆盖。
 */
export interface TextGenerationConfig {
  readonly timeouts: ProviderTimeoutConfig;
  /** 总尝试次数（含首次），不是重试次数；旧实现夹在 1..3。 */
  readonly maxAttempts: number;
  /** 重试基数延迟：第 n 次重试等待 `retryBaseDelayMs * 2^(n-1)`。 */
  readonly retryBaseDelayMs: number;
}

/**
 * provider 失败的完整分类。**kind 映射到「运行结果」，不是「HTTP 响应」**：同步走 200 + failed run，
 * 流式走 `PROVIDER_FAILED` 帧（即便在首个 delta 之前失败也一样，它在生成器内部就被 catch 成了帧）；
 * 只有 `unconfigured` 直接产 422。不要为任何 kind 新增 HTTP 码：旧契约只承诺既有 code 与 status 稳定。
 * 判定只读 `kind` 与 `retryable`；无 message 字段（文案是渲染层的事），`retryable` 是事实不是策略。
 */
export type ProviderFailure =
  /** 首字节静默超时：可重试——请求可能压根没被受理。 */
  | { readonly kind: "timeout_first_byte"; readonly retryable: boolean; readonly timeoutMs: number }
  /** 帧间静默超时：可重试，但已产出的增量必须丢弃重来，不能续接。 */
  | { readonly kind: "timeout_idle"; readonly retryable: boolean; readonly silenceMs: number }
  /** 整体预算（每帧 rearm 后仍耗尽）：可重试；重试后仍受同一预算约束。 */
  | { readonly kind: "timeout_deadline"; readonly retryable: boolean; readonly deadlineMs: number }
  /** 上游回了非 JSON，或流里出现无法解析的碎片。可重试：多为瞬时截断。 */
  | { readonly kind: "protocol_not_json"; readonly retryable: boolean }
  /** 缺必需字段（如响应体无 `choices`、无 `chapter_markdown`）。不可重试：形状变了。 */
  | { readonly kind: "protocol_missing_field"; readonly retryable: boolean; readonly field: string }
  /** 未知事件类型或未知帧形状。不可重试：上游协议漂移，重发只会再撞一次。 */
  | {
      readonly kind: "protocol_unknown_event";
      readonly retryable: boolean;
      readonly eventType: string;
    }
  /** 流在终结帧之前 EOF：不可重试。`frames`/`bytes` 是定位截断点的事实，不是文案。 */
  | {
      readonly kind: "protocol_stream_truncated";
      readonly retryable: boolean;
      readonly frames: number;
      readonly bytes: number;
    }
  /**
   * 上游非 2xx。可重试白名单与 `provider_http.ts:15` 一致：429 / 500 / 502 / 503 / 504；其余重发无意义。
   * 这里说的是**上游**状态码，不是我们的响应。
   */
  | { readonly kind: "transport_http_status"; readonly retryable: boolean; readonly status: number }
  /**
   * 建连阶段失败（DNS、TLS、TCP 拒绝）：请求体未发出、上游未计费，重试安全。字面量 `true` 是相对旧实现的
   * **有意偏离**——旧分类器不为此类 TypeError 填事实字段，「漏填」被当成了「不可重试」。
   */
  | { readonly kind: "transport_connect"; readonly retryable: true }
  /** 请求已发出后中断：上游可能已计费，重发会重复花钱且结果可能与已显示内容不一致。与旧实现一致。 */
  | { readonly kind: "transport_interrupted"; readonly retryable: false }
  /**
   * 服务端没有该 provider 的可用凭据。不可重试。必须与「调用失败」区分：它是全表里唯一让生成调用本身
   * 返回非 200 的失败——422 `PROVIDER_NOT_CONFIGURED`，流式路径上也不落 job。
   */
  | { readonly kind: "unconfigured"; readonly retryable: boolean; readonly provider: ProviderName }
  /**
   * 模型返回了非正文（套话、脚手架、残留 JSON、过短）。**只有应用层净化闸门构造它，适配器永不产出**；
   * 落地为 failed job，**没有独立 HTTP 码**（旧实现即 200 + failed job）。不可重试：输入同样则输出同样。
   */
  | { readonly kind: "content_not_prose"; readonly retryable: boolean };
