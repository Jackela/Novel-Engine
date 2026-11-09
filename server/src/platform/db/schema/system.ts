/**
 * Installation metadata: values that describe the database itself rather than
 * any author's content.
 *
 * `fts_tokenizer_version` is the load-bearing one. The Chinese segmentation
 * scheme is part of the index format: changing it without rebuilding the index
 * yields a database whose search silently returns nothing. Storing the version
 * lets startup detect the mismatch and refuse to serve search instead of
 * pretending it works.
 */

import { sqliteTable, text } from "drizzle-orm/sqlite-core";

export const APP_META_KEYS = {
  schemaVersion: "schema_version",
  ftsTokenizerVersion: "fts_tokenizer_version",
  dataEpoch: "data_epoch",
} as const;

export const appMeta = sqliteTable("app_meta", {
  key: text("key").primaryKey(),
  value: text("value").notNull(),
});
