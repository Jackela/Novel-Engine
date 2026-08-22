const KEY_PATTERN = /^[A-Za-z_][A-Za-z0-9_]*$/;

/**
 * Parse `.env.local` content into a flat key→value map: one KEY=VALUE per
 * line, optional `export ` prefixes, full-line comments, blank lines, and
 * matching single or double quotes around values. Inline comments and
 * multi-line values are out of the configuration contract.
 */
export function parseEnvFile(text: string): Record<string, string> {
  const values: Record<string, string> = {};
  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (line === "" || line.startsWith("#")) {
      continue;
    }
    const assignment = line.startsWith("export ") ? line.slice("export ".length) : line;
    const separator = assignment.indexOf("=");
    if (separator <= 0) {
      continue;
    }
    const key = assignment.slice(0, separator).trim();
    if (!KEY_PATTERN.test(key)) {
      continue;
    }
    values[key] = unquote(assignment.slice(separator + 1).trim());
  }
  return values;
}

function unquote(value: string): string {
  if (value.length >= 2) {
    for (const quote of ['"', "'"] as const) {
      if (value.startsWith(quote) && value.endsWith(quote)) {
        return value.slice(1, -1);
      }
    }
  }
  return value;
}
