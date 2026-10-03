import {
  arrayField,
  nonnegativeIntegerField,
  nullableNumberField,
  objectValue,
  stringField,
} from "./apiContract";

/**
 * One ranked search page (DR-029): every hit carries its locate term, `total`
 * is the server's honest project-wide match count, and `next_offset` walks
 * the remaining pages (null when every match has been delivered).
 */
export function parseSearch(value: unknown): {
  results: Array<{ document_id: string; title: string; excerpt: string; match_term: string }>;
  total: number;
  next_offset: number | null;
} {
  const item = objectValue(value, "search response");
  return {
    results: arrayField(item, "results", "search response", (entry, index) => {
      const result = objectValue(entry, `results[${index}]`);
      return {
        document_id: stringField(result, "document_id", `results[${index}]`),
        title: stringField(result, "title", `results[${index}]`),
        excerpt: stringField(result, "excerpt", `results[${index}]`),
        match_term: stringField(result, "match_term", `results[${index}]`),
      };
    }),
    total: nonnegativeIntegerField(item, "total", "search response"),
    next_offset: nullableNumberField(item, "next_offset", "search response"),
  };
}
