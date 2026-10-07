import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api, HttpError } from "@/app/api";
import type { ProviderInfo } from "@/app/types/studio";
import { createMountHarness } from "@/test/harness";

import { useStudioProviders } from "./useStudioProviders";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: { ...actual.api, providers: vi.fn<typeof actual.api.providers>() },
  };
});

const harness = createMountHarness();
const FALLBACK_PROVIDERS = ["mock", "dashscope", "openai_compatible"];

afterEach(() => {
  harness.cleanup();
  vi.unstubAllGlobals();
});

function renderHook<T>(useHook: () => T): { result: { current: T } } {
  const result = { current: undefined as unknown as T };

  function Wrapper() {
    result.current = useHook();
    return null;
  }

  harness.mount(<Wrapper />);

  return { result };
}

describe("useStudioProviders", () => {
  it("returns fallback providers before the API responds", () => {
    vi.mocked(api.providers).mockResolvedValue({ providers: [] });

    const { result } = renderHook(() => useStudioProviders());

    expect(result.current.map((item: ProviderInfo) => item.provider)).toEqual([
      "mock",
      "dashscope",
      "openai_compatible",
    ]);
  });

  it("replaces fallback providers with API results once loaded", async () => {
    vi.mocked(api.providers).mockResolvedValue({
      providers: [
        {
          provider: "openai_compatible",
          configured: true,
          model: "gpt-4o",
          is_default: true,
        },
        { provider: "mock", configured: true, model: null, is_default: false },
      ],
    });

    const { result } = renderHook(() => useStudioProviders());

    await act(async () => {
      await Promise.resolve();
    });

    expect(result.current.map((item: ProviderInfo) => item.provider)).toEqual([
      "openai_compatible",
      "mock",
    ]);
  });

  it("keeps fallback providers when the API fails", async () => {
    vi.mocked(api.providers).mockRejectedValue(new Error("offline"));

    const { result } = renderHook(() => useStudioProviders());

    await act(async () => {
      await Promise.resolve();
    });

    expect(result.current.map((item: ProviderInfo) => item.provider)).toEqual([
      "mock",
      "dashscope",
      "openai_compatible",
    ]);
  });
});

describe("useStudioProviders diagnostics", () => {
  it("keeps the fallback catalog without reporting an error status the read already degrades for", async () => {
    const reportError = vi.fn();
    vi.stubGlobal("reportError", reportError);
    vi.mocked(api.providers).mockRejectedValue(new HttpError("Service unavailable", 503));

    const { result } = renderHook(() => useStudioProviders());

    await act(async () => {
      await Promise.resolve();
    });

    expect(result.current.map((item: ProviderInfo) => item.provider)).toEqual(FALLBACK_PROVIDERS);
    expect(reportError).not.toHaveBeenCalled();
  });

  it("keeps the fallback catalog without reporting a browser transport failure", async () => {
    const reportError = vi.fn();
    vi.stubGlobal("reportError", reportError);
    vi.mocked(api.providers).mockRejectedValue(
      new Error("The server is unreachable.", { cause: new TypeError("fetch failed") }),
    );

    const { result } = renderHook(() => useStudioProviders());

    await act(async () => {
      await Promise.resolve();
    });

    expect(result.current.map((item: ProviderInfo) => item.provider)).toEqual(FALLBACK_PROVIDERS);
    expect(reportError).not.toHaveBeenCalled();
  });

  it("reports an unexpected failure while still keeping the fallback catalog", async () => {
    const reportError = vi.fn();
    vi.stubGlobal("reportError", reportError);
    vi.mocked(api.providers).mockRejectedValue(new Error("providers payload drifted"));

    const { result } = renderHook(() => useStudioProviders());

    await act(async () => {
      await Promise.resolve();
    });

    expect(result.current.map((item: ProviderInfo) => item.provider)).toEqual(FALLBACK_PROVIDERS);
    expect(reportError).toHaveBeenCalledTimes(1);
    expect(reportError).toHaveBeenCalledWith(
      expect.objectContaining({ message: "providers payload drifted" }),
    );
  });
});
