import type {
  DocumentKind,
  Project,
  ProviderInfo,
  Revision,
  Session,
  SessionKind,
  SetupStatus,
  StudioDocument,
} from '@/app/types/studio';

export class ApiContractError extends Error {
  constructor(label: string) {
    super(`Invalid ${label}`);
    Object.setPrototypeOf(this, ApiContractError.prototype);
  }
}

type JsonRecord = Record<string, unknown>;

const documentKinds = ['chapter', 'outline', 'character', 'world', 'note'] as const;
const sessionKinds = ['owner', 'guest'] as const;

export function fail(label: string): never {
  throw new ApiContractError(label);
}

export function objectValue(value: unknown, label: string): JsonRecord {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) fail(label);
  return value as JsonRecord;
}

export function field(source: JsonRecord, key: string, parent: string): unknown {
  if (!Object.prototype.hasOwnProperty.call(source, key)) fail(`${parent}.${key}`);
  return source[key];
}

export function stringValue(value: unknown, label: string): string {
  return typeof value === 'string' ? value : fail(label);
}

export function stringField(source: JsonRecord, key: string, parent: string): string {
  return stringValue(field(source, key, parent), `${parent}.${key}`);
}

export function nullableString(value: unknown, label: string): string | null {
  return value === null ? null : stringValue(value, label);
}

export function nullableStringField(
  source: JsonRecord,
  key: string,
  parent: string,
): string | null {
  return nullableString(field(source, key, parent), `${parent}.${key}`);
}

export function numberField(source: JsonRecord, key: string, parent: string): number {
  const value = field(source, key, parent);
  return typeof value === 'number' && Number.isFinite(value) ? value : fail(`${parent}.${key}`);
}

export function booleanField(source: JsonRecord, key: string, parent: string): boolean {
  const value = field(source, key, parent);
  return typeof value === 'boolean' ? value : fail(`${parent}.${key}`);
}

export function recordField(
  source: JsonRecord,
  key: string,
  parent: string,
): Record<string, unknown> {
  return objectValue(field(source, key, parent), `${parent}.${key}`);
}

export function arrayValue<T>(
  value: unknown,
  label: string,
  parseItem: (item: unknown, index: number) => T,
): T[] {
  return Array.isArray(value) ? value.map(parseItem) : fail(label);
}

export function arrayField<T>(
  source: JsonRecord,
  key: string,
  parent: string,
  parseItem: (item: unknown, index: number) => T,
): T[] {
  return arrayValue(field(source, key, parent), `${parent}.${key}`, parseItem);
}

export function literalValue<T extends readonly string[]>(
  value: unknown,
  allowed: T,
  label: string,
): T[number] {
  return typeof value === 'string' && allowed.includes(value) ? (value as T[number]) : fail(label);
}

export function literalField<T extends readonly string[]>(
  source: JsonRecord,
  key: string,
  parent: string,
  allowed: T,
): T[number] {
  return literalValue(field(source, key, parent), allowed, `${parent}.${key}`);
}

function parseDocument(value: unknown, label = 'document'): StudioDocument {
  const item = objectValue(value, label);
  return {
    id: stringField(item, 'id', label),
    project_id: stringField(item, 'project_id', label),
    kind: literalField(item, 'kind', label, documentKinds) as DocumentKind,
    title: stringField(item, 'title', label),
    position: numberField(item, 'position', label),
    current_revision_id: stringField(item, 'current_revision_id', label),
    content_markdown: stringField(item, 'content_markdown', label),
    metadata: recordField(item, 'metadata', label),
    revision_source: stringField(item, 'revision_source', label),
    word_count: numberField(item, 'word_count', label),
    created_at: stringField(item, 'created_at', label),
    updated_at: stringField(item, 'updated_at', label),
  };
}

export function parseProject(value: unknown, label = 'project'): Project {
  const item = objectValue(value, label);
  const documents = item.documents;
  return {
    id: stringField(item, 'id', label),
    title: stringField(item, 'title', label),
    description: stringField(item, 'description', label),
    settings: recordField(item, 'settings', label),
    import_hash: nullableStringField(item, 'import_hash', label),
    created_at: stringField(item, 'created_at', label),
    updated_at: stringField(item, 'updated_at', label),
    ...(documents === undefined
      ? {}
      : {
          documents: arrayValue(documents, `${label}.documents`, (entry, index) =>
            parseDocument(entry, `${label}.documents[${index}]`),
          ),
        }),
  };
}

export function parseProjects(value: unknown): { projects: Project[] } {
  const item = objectValue(value, 'projects response');
  return { projects: arrayField(item, 'projects', 'projects response', parseProjectListItem) };
}

function parseProjectListItem(value: unknown, index: number): Project {
  return parseProject(value, `projects[${index}]`);
}

export function parseSetupStatus(value: unknown): SetupStatus {
  const item = objectValue(value, 'setup');
  return {
    owner_configured: booleanField(item, 'owner_configured', 'setup'),
    version: stringField(item, 'version', 'setup'),
  };
}

export function parseOwnerSetup(value: unknown): { id: string; username: string } {
  const item = objectValue(value, 'owner');
  return { id: stringField(item, 'id', 'owner'), username: stringField(item, 'username', 'owner') };
}

export function parseSession(value: unknown): Session {
  const item = objectValue(value, 'session');
  return {
    session_id: stringField(item, 'session_id', 'session'),
    kind: literalField(item, 'kind', 'session', sessionKinds) as SessionKind,
    owner_id: nullableStringField(item, 'owner_id', 'session'),
    expires_at: nullableStringField(item, 'expires_at', 'session'),
  };
}

function parseProvider(value: unknown, label: string): ProviderInfo {
  const item = objectValue(value, label);
  return {
    provider: stringField(item, 'provider', label),
    configured: booleanField(item, 'configured', label),
    model: nullableStringField(item, 'model', label),
    is_default: booleanField(item, 'is_default', label),
  };
}

export function parseProviders(value: unknown): { providers: ProviderInfo[] } {
  const item = objectValue(value, 'providers response');
  return {
    providers: arrayField(item, 'providers', 'providers response', (entry, index) =>
      parseProvider(entry, `providers[${index}]`),
    ),
  };
}

export const parseStudioDocument = parseDocument;

export function parseDocuments(value: unknown): { documents: StudioDocument[] } {
  const item = objectValue(value, 'documents response');
  return {
    documents: arrayField(item, 'documents', 'documents response', (entry, index) =>
      parseDocument(entry, `documents[${index}]`),
    ),
  };
}

function parseRevision(value: unknown, label: string): Revision {
  const item = objectValue(value, label);
  return {
    id: stringField(item, 'id', label),
    document_id: stringField(item, 'document_id', label),
    parent_revision_id: nullableStringField(item, 'parent_revision_id', label),
    revision_number: numberField(item, 'revision_number', label),
    content_markdown: stringField(item, 'content_markdown', label),
    metadata: recordField(item, 'metadata', label),
    source: stringField(item, 'source', label),
    word_count: numberField(item, 'word_count', label),
    created_at: stringField(item, 'created_at', label),
  };
}

export function parseRevisions(value: unknown): { revisions: Revision[] } {
  const item = objectValue(value, 'revisions response');
  return {
    revisions: arrayField(item, 'revisions', 'revisions response', (entry, index) =>
      parseRevision(entry, `revisions[${index}]`),
    ),
  };
}

export function parseSearch(value: unknown): {
  results: Array<{ document_id: string; title: string; excerpt: string }>;
} {
  const item = objectValue(value, 'search response');
  return {
    results: arrayField(item, 'results', 'search response', (entry, index) => {
      const result = objectValue(entry, `results[${index}]`);
      return {
        document_id: stringField(result, 'document_id', `results[${index}]`),
        title: stringField(result, 'title', `results[${index}]`),
        excerpt: stringField(result, 'excerpt', `results[${index}]`),
      };
    }),
  };
}

export function parseVoid(): void {
  return undefined;
}
