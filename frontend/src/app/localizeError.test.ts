import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

import { ApiContractError } from "./apiContract";
import { HttpError } from "./httpClient";
import { ERROR_CODE_MESSAGE_KEYS, localizeError } from "./localizeError";

/**
 * DR-021 mapping-table regression: the stable envelope code is the only
 * contract the localized surface may rely on, so every code in the server
 * catalog must resolve per language, the raw server/provider prose must never
 * surface as the primary message, and the raw text must stay reachable as the
 * technical detail.
 */

const FALLBACK = "Fallback.";

function httpError(code: string, message: string, details?: unknown): HttpError {
  return new HttpError(message, 500, details, code);
}

/** The server SSOT catalog read verbatim, so the frontend table cannot drift. */
function serverCatalogCodes(): string[] {
  const source = readFileSync(
    resolve(process.cwd(), "../server/src/shared/domain/error_codes.ts"),
    "utf8",
  );
  return [...source.matchAll(/^\s{2}([A-Z_]+): "[A-Z_]+",$/gm)].map((match) => match[1] as string);
}

describe("localizeError", () => {
  it("stays in lockstep with the server error-code catalog by name", () => {
    const codes = serverCatalogCodes();
    expect(codes.length).toBeGreaterThanOrEqual(21);
    for (const code of codes) {
      expect(Object.hasOwn(ERROR_CODE_MESSAGE_KEYS, code), code).toBe(true);
    }
  });

  it("resolves every mapped code in both languages and withholds the raw prose", () => {
    for (const code of Object.keys(ERROR_CODE_MESSAGE_KEYS)) {
      for (const language of ["en", "zh"] as const) {
        const raw = `Server prose for ${code} quoting project_settings_bytes.`;
        const presentation = localizeError(httpError(code, raw), FALLBACK, language);
        expect(presentation.message, `${language}:${code}`).not.toBe("");
        expect(presentation.message, `${language}:${code}`).not.toBe(FALLBACK);
        expect(presentation.message, `${language}:${code}`).not.toContain("project_settings_bytes");
        if (code.startsWith("PROVIDER_")) {
          expect(presentation.technical, `${language}:${code}`).toBe(raw);
        } else {
          expect(presentation.technical, `${language}:${code}`).toBeNull();
        }
      }
    }
  });

  it.each([
    [
      "UNAUTHORIZED",
      "Owner session required.",
      undefined,
      "Your session has expired. Sign in again to continue.",
      "登录状态已过期，请重新登录后继续。",
    ],
    [
      "FORBIDDEN",
      "Forbidden.",
      undefined,
      "You do not have permission to do this.",
      "你没有执行这个操作的权限。",
    ],
    [
      "SETUP_TOKEN_INVALID",
      "Setup from a non-loopback address requires the one-time x-setup-token header.",
      undefined,
      "This first start needs the one-time setup token from the server log.",
      "这次首启需要服务器日志中的一次性 setup token。",
    ],
    [
      "CSRF_TOKEN_MISSING",
      "CSRF token missing.",
      undefined,
      "This change was blocked because its security token was missing. Reload the page and retry.",
      "这次修改被拦截：缺少安全令牌。请刷新页面后重试。",
    ],
    [
      "CSRF_TOKEN_INVALID",
      "CSRF token invalid.",
      undefined,
      "This change was blocked because its security token was stale. Sign in again and retry.",
      "这次修改被拦截：安全令牌已失效。请重新登录后重试。",
    ],
    [
      "RATE_LIMIT_EXCEEDED",
      "Rate limit exceeded.",
      { retry_after_seconds: 30 },
      "Too many attempts. Try again in 30 seconds.",
      "尝试过于频繁，请在 30 秒后重试。",
    ],
    [
      "VALIDATION_ERROR",
      "Request validation failed.",
      { errors: [{}, {}, {}] },
      "Some submitted fields were rejected (3). Check them and resubmit.",
      "有 3 个字段未通过校验，请检查后重新提交。",
    ],
    [
      "FST_ERR_CTP_BODY_TOO_LARGE",
      "Request body is too large",
      undefined,
      "This chapter is too large to save. Split it into smaller chapters — your draft stays in the editor.",
      "这一章过大，无法保存。请拆分为更小的章节——草稿仍保留在编辑器中。",
    ],
    [
      "STRUCTURE_CAPACITY_EXCEEDED",
      "Authoring structure capacity exceeded: project_settings_bytes limit 16384.",
      { resource: "project_settings_bytes", limit: 16384, observed: 16385 },
      "The project settings size reached its limit (16384). Remove some structure before retrying.",
      "项目设置大小已达上限（16384）。请先删减部分结构后重试。",
    ],
    [
      "REVISION_CONFLICT",
      "Document changed since the requested base revision.",
      { current_revision_id: "revision-b" },
      "This document changed since it was loaded. Load the latest revision and reapply your edit.",
      "这份文档在加载后已被修改。请加载最新修订后重新应用你的修改。",
    ],
    [
      "OPERATION_IN_FLIGHT",
      "The continue operation is already running for this document.",
      { operation: "continue" },
      "The same operation is already running. Wait for it to finish before retrying.",
      "同一操作正在进行中，请等待完成后再试。",
    ],
    [
      "INTERNAL_ERROR",
      "An internal error occurred.",
      { error_id: "req-1" },
      "An unexpected server error occurred. Retry; if it persists, quote error req-1.",
      "服务器发生未预期的错误。请重试；若持续出现，请附上错误编号 req-1。",
    ],
    [
      "PROVIDER_FAILED",
      "DashScope generation failed for step 'chapter_revision': provider returned HTTP 401.",
      undefined,
      "The AI provider request failed (HTTP 401). Check the provider configuration and retry.",
      "AI 服务请求失败（HTTP 401）。请检查 provider 配置后重试。",
    ],
  ])("pins %s in both languages", (code, raw, details, english, chinese) => {
    expect(localizeError(httpError(code, raw, details), FALLBACK, "en").message).toBe(english);
    expect(localizeError(httpError(code, raw, details), FALLBACK, "zh").message).toBe(chinese);
  });

  it("falls back to detail-free variants when the envelope details are unusable", () => {
    const cases: Array<[string, unknown, string, string]> = [
      [
        "RATE_LIMIT_EXCEEDED",
        { retry_after_seconds: "soon" },
        "Too many attempts. Wait a moment and try again.",
        "尝试过于频繁，请稍候再试。",
      ],
      [
        "VALIDATION_ERROR",
        { errors: "none" },
        "Some submitted fields were rejected. Check them and resubmit.",
        "部分字段未通过校验，请检查后重新提交。",
      ],
      [
        "STRUCTURE_CAPACITY_EXCEEDED",
        { resource: "", limit: 10 },
        "This change would exceed the project's structure limit. Remove some structure before retrying.",
        "这次修改会超出项目的结构上限，请先删减部分结构后重试。",
      ],
      [
        "OPERATION_CAPACITY_EXCEEDED",
        undefined,
        "The studio is at its concurrent-work limit. Try again shortly.",
        "工作室的并发任务已达上限，请稍后重试。",
      ],
      [
        "INTERNAL_ERROR",
        undefined,
        "An unexpected server error occurred. Retry; if it persists, check the server log.",
        "服务器发生未预期的错误。请重试；若持续出现，请查看服务器日志。",
      ],
    ];
    for (const [code, details, english, chinese] of cases) {
      expect(
        localizeError(httpError(code, "Raw server prose.", details), FALLBACK, "en").message,
      ).toBe(english);
      expect(
        localizeError(httpError(code, "Raw server prose.", details), FALLBACK, "zh").message,
      ).toBe(chinese);
    }
  });

  it("keeps an unknown code readable and preserves its raw message as technical detail", () => {
    const raw = "Widget flux_capacitor_bytes overflow while summarizing.";
    const presentation = localizeError(httpError("FLUX_CAPACITOR_OVERFLOW", raw), FALLBACK, "zh");

    expect(presentation.message).toBe(
      "请求失败（FLUX_CAPACITOR_OVERFLOW）。请重试；若持续出现，请报告此错误代码。",
    );
    expect(presentation.technical).toBe(raw);
  });

  it("turns a 413 payload refusal into the localized message even without a coded envelope", () => {
    const presentation = localizeError(new HttpError("Payload too large", 413), FALLBACK, "zh");

    expect(presentation.message).toBe(
      "这一章过大，无法保存。请拆分为更小的章节——草稿仍保留在编辑器中。",
    );
    expect(presentation.technical).toBe("Payload too large");
  });

  it("maps contract labels to a localized resource message and keeps the raw label as detail", () => {
    const zhDocument = localizeError(
      new ApiContractError("document.content_markdown"),
      FALLBACK,
      "zh",
    );
    expect(zhDocument.message).toBe("服务器返回的文档数据无法识别，请刷新页面后重试。");
    expect(zhDocument.technical).toBe("Invalid document.content_markdown");

    const zhLore = localizeError(
      new ApiContractError("lore extraction job.result.candidates[0].kind"),
      FALLBACK,
      "zh",
    );
    expect(zhLore.message).toBe("服务器返回的设定提取数据无法识别，请刷新页面后重试。");

    const enDocument = localizeError(
      new ApiContractError("document.content_markdown"),
      FALLBACK,
      "en",
    );
    expect(enDocument.message).toBe(
      "The server returned document data that this screen could not read. Reload the page and try again.",
    );
  });

  it("degrades an unmapped contract label to the generic localized message", () => {
    const presentation = localizeError(new ApiContractError("wibble.foo"), FALLBACK, "zh");

    expect(presentation.message).toBe("服务器返回的数据无法识别，请刷新页面后重试。");
    expect(presentation.technical).toBe("Invalid wibble.foo");
  });

  it("keeps ordinary errors and uncoded transport failures on their own message", () => {
    expect(localizeError(new Error("Unable to reach the studio."), FALLBACK, "zh")).toEqual({
      message: "Unable to reach the studio.",
      technical: null,
    });
    expect(
      localizeError(new HttpError("Request failed with status 502", 502), FALLBACK).message,
    ).toBe("Request failed with status 502");
    expect(localizeError("a plain string", FALLBACK)).toEqual({
      message: FALLBACK,
      technical: null,
    });
    expect(localizeError(undefined, FALLBACK)).toEqual({ message: FALLBACK, technical: null });
  });
});
