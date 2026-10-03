import { fireEvent, getByRole, queryByRole } from "@testing-library/dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { createMountHarness } from "@/test/harness";

import { StudioNavigatorSearch } from "./StudioNavigatorSearch";

/** DR-029: zero-result hint, honest count, more affordance, and hit clicks. */

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
});

type SearchResult = Parameters<typeof StudioNavigatorSearch>[0]["searchResults"][number];

function renderSearch(
  overrides: Partial<Parameters<typeof StudioNavigatorSearch>[0]> = {},
): HTMLDivElement {
  const defaults: Parameters<typeof StudioNavigatorSearch>[0] = {
    search: "willowquill",
    isSearching: false,
    searchResults: [],
    searchTotal: 0,
    hasMoreResults: false,
    isLoadingMore: false,
    searchedEmpty: false,
    onSearchChange: vi.fn(),
    onSearchSubmit: vi.fn(),
    onLoadMore: vi.fn(),
    onSelectResult: vi.fn(),
  };
  const { container } = harness.mount(<StudioNavigatorSearch {...defaults} {...overrides} />);
  return container;
}

const result: SearchResult = {
  document_id: "doc-1",
  title: "Opening",
  excerpt: "…willowquill…",
  match_term: "willowquill",
};

describe("StudioNavigatorSearch (DR-029)", () => {
  it("renders the zero-result hint only for a completed empty search", () => {
    const empty = renderSearch({ searchedEmpty: true });
    expect(empty.querySelector('[role="status"]')?.textContent).toBe("No matching documents.");

    const idle = renderSearch({ searchedEmpty: false });
    expect(idle.querySelector('[role="status"]')).toBeNull();
  });

  it("renders the honest match count and pluralizes it", () => {
    const many = renderSearch({ searchResults: [result], searchTotal: 35 });
    expect(many.querySelector(".studio-nav__search-count")?.textContent).toBe("35 results");

    const one = renderSearch({ searchResults: [result], searchTotal: 1 });
    expect(one.querySelector(".studio-nav__search-count")?.textContent).toBe("1 result");
  });

  it("renders the more affordance only while further pages exist and reports its click", () => {
    const onLoadMore = vi.fn();
    const withMore = renderSearch({
      searchResults: [result],
      searchTotal: 35,
      hasMoreResults: true,
      onLoadMore,
    });
    fireEvent.click(getByRole(withMore, "button", { name: "Load more results" }));
    expect(onLoadMore).toHaveBeenCalledOnce();

    const withoutMore = renderSearch({ searchResults: [result], searchTotal: 1 });
    expect(queryByRole(withoutMore, "button", { name: "Load more results" })).toBeNull();
  });

  it("keeps the more button busy while a page is loading", () => {
    const container = renderSearch({
      searchResults: [result],
      searchTotal: 35,
      hasMoreResults: true,
      isLoadingMore: true,
    });
    const button = getByRole(container, "button", { name: "Load more results" });
    expect(button).toBeDisabled();
  });

  it("hands the clicked hit (with its locate term) to the result callback", () => {
    const onSelectResult = vi.fn();
    const container = renderSearch({ searchResults: [result], searchTotal: 1, onSelectResult });

    fireEvent.click(getByRole(container, "button", { name: "Open Opening" }));

    expect(onSelectResult).toHaveBeenCalledWith(result);
  });
});
