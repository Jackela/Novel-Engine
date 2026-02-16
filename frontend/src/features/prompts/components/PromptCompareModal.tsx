/**
 * PromptCompareModal - Side-by-side prompt version comparison
 *
 * BRAIN-021: Frontend: Prompt Comparison View
 * Provides comparison UI for two versions of a prompt template with:
 * - Side-by-side diff view of prompt content
 * - Variable comparison table
 * - Model config diff view
 * - One-click swap for testing
 */

import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  ArrowLeftRight,
  FileText,
  Variable as VariableIcon,
  Settings,
  Info,
  ChevronDown,
  ChevronRight,
  Loader2,
} from 'lucide-react';
import { usePromptCompareAuto } from '../api/promptApi';
import type { PromptSummary, PromptCompareResponse } from '@/types/schemas';
import { cn } from '@/lib/utils';

interface PromptCompareModalProps {
  promptId: string;
  versions: PromptSummary[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function PromptCompareModal({
  promptId,
  versions,
  open,
  onOpenChange,
}: PromptCompareModalProps) {
  // State for selected versions
  const [versionA, setVersionA] = useState<number>(versions[1]?.version ?? 1);
  const [versionB, setVersionB] = useState<number>(versions[0]?.version ?? 1);

  // State for collapsible sections
  const [sections, setSections] = useState({
    content: true,
    variables: true,
    config: true,
    metadata: true,
  });

  // Fetch comparison data
  const {
    data: compareData,
    isLoading,
    error,
  } = usePromptCompareAuto(promptId, versionA, versionB);

  // Swap versions
  const swapVersions = () => {
    const temp = versionA;
    setVersionA(versionB);
    setVersionB(temp);
  };

  // Toggle section
  const toggleSection = (section: keyof typeof sections) => {
    setSections((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  // Get version name/label
  const getVersionLabel = (version: number) => {
    const v = versions.find((v) => v.version === version);
    return v ? `v${version} - ${v.name}` : `v${version}`;
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex h-[85vh] max-w-6xl flex-col">
        <DialogHeader className="pb-4">
          <div className="flex items-center justify-between">
            <div>
              <DialogTitle>Compare Prompt Versions</DialogTitle>
              <DialogDescription>
                See what changed between two versions of your prompt
              </DialogDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={swapVersions}
              className="gap-2"
            >
              <ArrowLeftRight className="h-4 w-4" />
              Swap
            </Button>
          </div>
        </DialogHeader>

        {/* Version Selectors */}
        <div className="flex items-center gap-4 pb-4">
          <div className="flex-1 space-y-2">
            <Label className="text-sm text-muted-foreground">Version A (Old)</Label>
            <Select
              value={String(versionA)}
              onValueChange={(v) => setVersionA(Number(v))}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {versions.map((v) => (
                  <SelectItem key={v.id} value={String(v.version)}>
                    {getVersionLabel(v.version)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center justify-center pt-6">
            <Badge variant="outline" className="text-xs">
              vs
            </Badge>
          </div>

          <div className="flex-1 space-y-2">
            <Label className="text-sm text-muted-foreground">Version B (New)</Label>
            <Select
              value={String(versionB)}
              onValueChange={(v) => setVersionB(Number(v))}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {versions.map((v) => (
                  <SelectItem key={v.id} value={String(v.version)}>
                    {getVersionLabel(v.version)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <Separator />

        {/* Content */}
        {isLoading ? (
          <div className="flex flex-1 items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : error ? (
          <div className="flex flex-1 items-center justify-center text-muted-foreground">
            Failed to load comparison
          </div>
        ) : compareData ? (
          <ScrollArea className="flex-1">
            <div className="space-y-6 p-4">
              {/* Metadata Changes */}
              {sections.metadata && (
                <CollapsibleSection
                  title="Metadata Changes"
                  icon={Info}
                  isOpen={sections.metadata}
                  onToggle={() => toggleSection('metadata')}
                >
                  <MetadataChanges metadata={compareData.metadata} />
                </CollapsibleSection>
              )}

              {/* Content Diff */}
              {sections.content && (
                <CollapsibleSection
                  title="Content Changes"
                  icon={FileText}
                  isOpen={sections.content}
                  onToggle={() => toggleSection('content')}
                >
                  <ContentDiffView diff={compareData.content_diff} />
                </CollapsibleSection>
              )}

              {/* Variables Table */}
              {sections.variables && (
                <CollapsibleSection
                  title="Variables"
                  icon={VariableIcon}
                  isOpen={sections.variables}
                  onToggle={() => toggleSection('variables')}
                  badge={
                    compareData.variables.added.length +
                      compareData.variables.removed.length +
                      compareData.variables.changed.length || 0
                  }
                >
                  <VariablesTable variables={compareData.variables} />
                </CollapsibleSection>
              )}

              {/* Model Config */}
              {sections.config && (
                <CollapsibleSection
                  title="Model Configuration"
                  icon={Settings}
                  isOpen={sections.config}
                  onToggle={() => toggleSection('config')}
                  badge={compareData.model_config.length || 0}
                >
                  <ConfigDiffView changes={compareData.model_config} />
                </CollapsibleSection>
              )}
            </div>
          </ScrollArea>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

// Collapsible Section Component
interface CollapsibleSectionProps {
  title: string;
  icon: React.ElementType;
  isOpen: boolean;
  onToggle: () => void;
  badge?: number;
  children: React.ReactNode;
}

function CollapsibleSection({
  title,
  icon: Icon,
  isOpen,
  onToggle,
  badge,
  children,
}: CollapsibleSectionProps) {
  return (
    <div className="overflow-hidden rounded-lg border">
      <button
        onClick={onToggle}
        className="flex w-full items-center justify-between bg-muted/30 p-3 transition-colors hover:bg-muted/50"
      >
        <div className="flex items-center gap-2">
          {isOpen ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          )}
          <Icon className="h-4 w-4" />
          <span className="font-medium">{title}</span>
          {badge !== undefined && badge > 0 && (
            <Badge variant="secondary" className="ml-2">
              {badge} change{badge > 1 ? 's' : ''}
            </Badge>
          )}
        </div>
      </button>
      {isOpen && <div className="p-4">{children}</div>}
    </div>
  );
}

// Metadata Changes Component
interface MetadataChangesProps {
  metadata?: PromptCompareResponse['metadata'];
}

function MetadataChanges({ metadata }: MetadataChangesProps) {
  if (!metadata || Object.keys(metadata).length === 0) {
    return (
      <div className="py-4 text-center text-sm text-muted-foreground">
        No metadata changes
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {metadata.name && (
        <MetadataField
          label="Name"
          oldValue={metadata.name.old}
          newValue={metadata.name.new}
        />
      )}
      {metadata.description && (
        <MetadataField
          label="Description"
          oldValue={metadata.description.old}
          newValue={metadata.description.new}
        />
      )}
      {metadata.tags && (
        <div>
          <span className="text-sm font-medium">Tags</span>
          <div className="mt-1 flex gap-4">
            {metadata.tags.added.length > 0 && (
              <div className="flex items-center gap-1">
                <Badge
                  variant="outline"
                  className="bg-green-500/10 text-green-700 dark:text-green-400"
                >
                  +{metadata.tags.added.length}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {metadata.tags.added.join(', ')}
                </span>
              </div>
            )}
            {metadata.tags.removed.length > 0 && (
              <div className="flex items-center gap-1">
                <Badge
                  variant="outline"
                  className="bg-red-500/10 text-red-700 dark:text-red-400"
                >
                  -{metadata.tags.removed.length}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {metadata.tags.removed.join(', ')}
                </span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

interface MetadataFieldProps {
  label: string;
  oldValue: string;
  newValue: string;
}

function MetadataField({ label, oldValue, newValue }: MetadataFieldProps) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-24 text-sm font-medium">{label}</span>
      <div className="flex flex-1 items-center gap-2">
        <span className="text-sm text-red-600 line-through dark:text-red-400">
          {oldValue}
        </span>
        <span className="text-muted-foreground">→</span>
        <span className="text-sm text-green-600 dark:text-green-400">{newValue}</span>
      </div>
    </div>
  );
}

// Content Diff View Component
interface ContentDiffViewProps {
  diff: PromptCompareResponse['content_diff'];
}

function ContentDiffView({ diff }: ContentDiffViewProps) {
  if (!diff || diff.length === 0) {
    return (
      <div className="py-4 text-center text-sm text-muted-foreground">
        No content changes
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-4">
      {/* Version A (Old) */}
      <div className="rounded-md border">
        <div className="border-b bg-muted/30 px-3 py-2 text-sm font-medium">
          Version A (Old)
        </div>
        <ScrollArea className="h-[400px]">
          <pre className="whitespace-pre-wrap break-words p-3 font-mono text-sm">
            {diff.map((hunk, index) => (
              <DiffHunkLine key={index} hunk={hunk} side="old" />
            ))}
          </pre>
        </ScrollArea>
      </div>

      {/* Version B (New) */}
      <div className="rounded-md border">
        <div className="border-b bg-muted/30 px-3 py-2 text-sm font-medium">
          Version B (New)
        </div>
        <ScrollArea className="h-[400px]">
          <pre className="whitespace-pre-wrap break-words p-3 font-mono text-sm">
            {diff.map((hunk, index) => (
              <DiffHunkLine key={index} hunk={hunk} side="new" />
            ))}
          </pre>
        </ScrollArea>
      </div>
    </div>
  );
}

interface DiffHunkLineProps {
  hunk: PromptCompareResponse['content_diff'][number];
  side: 'old' | 'new';
}

function DiffHunkLine({ hunk, side }: DiffHunkLineProps) {
  if (hunk.type === 'equal') {
    const lines = side === 'old' ? hunk.old_lines : hunk.new_lines;
    return <>{lines.join('\n')}</>;
  }

  if (hunk.type === 'delete') {
    if (side === 'old') {
      return (
        <span className="bg-red-500/10 text-red-700 dark:text-red-400">
          {hunk.old_lines.join('\n')}
        </span>
      );
    }
    return null;
  }

  if (hunk.type === 'insert') {
    if (side === 'new') {
      return (
        <span className="bg-green-500/10 text-green-700 dark:text-green-400">
          {hunk.new_lines.join('\n')}
        </span>
      );
    }
    return null;
  }

  if (hunk.type === 'replace') {
    if (side === 'old') {
      return (
        <span className="bg-red-500/10 text-red-700 line-through dark:text-red-400">
          {hunk.old_lines.join('\n')}
        </span>
      );
    }
    if (side === 'new') {
      return (
        <span className="bg-green-500/10 text-green-700 dark:text-green-400">
          {hunk.new_lines.join('\n')}
        </span>
      );
    }
  }

  return null;
}

// Variables Table Component
interface VariablesTableProps {
  variables: PromptCompareResponse['variables'];
}

function VariablesTable({ variables }: VariablesTableProps) {
  const hasChanges =
    variables.added.length > 0 ||
    variables.removed.length > 0 ||
    variables.changed.length > 0;

  if (!hasChanges) {
    return (
      <div className="py-4 text-center text-sm text-muted-foreground">
        No variable changes
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Added Variables */}
      {variables.added.length > 0 && (
        <div>
          <span className="text-sm font-medium text-green-600 dark:text-green-400">
            + Added ({variables.added.length})
          </span>
          <div className="mt-2 flex flex-wrap gap-2">
            {variables.added.map((name) => (
              <Badge key={name} variant="outline" className="bg-green-500/10">
                {name}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Removed Variables */}
      {variables.removed.length > 0 && (
        <div>
          <span className="text-sm font-medium text-red-600 dark:text-red-400">
            - Removed ({variables.removed.length})
          </span>
          <div className="mt-2 flex flex-wrap gap-2">
            {variables.removed.map((name) => (
              <Badge key={name} variant="outline" className="bg-red-500/10">
                {name}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Changed Variables */}
      {variables.changed.length > 0 && (
        <div>
          <span className="text-sm font-medium">
            Changed ({variables.changed.length})
          </span>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Default</TableHead>
                <TableHead>Required</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {variables.changed.map((change) => (
                <TableRow key={change.name}>
                  <TableCell className="font-medium">{change.name}</TableCell>
                  <TableCell>
                    <ChangedValue old={change.old.type} new={change.new.type} />
                  </TableCell>
                  <TableCell>
                    <ChangedValue
                      old={String(change.old.default_value ?? 'null')}
                      new={String(change.new.default_value ?? 'null')}
                    />
                  </TableCell>
                  <TableCell>
                    <ChangedValue
                      old={change.old.required ? 'Yes' : 'No'}
                      new={change.new.required ? 'Yes' : 'No'}
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}

interface ChangedValueProps {
  old: string;
  new: string;
}

function ChangedValue({ old, new: newVal }: ChangedValueProps) {
  const isChanged = old !== newVal;
  return (
    <div className="flex items-center gap-2">
      <span className={cn(isChanged && 'text-red-600 line-through dark:text-red-400')}>
        {old}
      </span>
      {isChanged && (
        <>
          <span className="text-muted-foreground">→</span>
          <span className="text-green-600 dark:text-green-400">{newVal}</span>
        </>
      )}
    </div>
  );
}

// Config Diff View Component
interface ConfigDiffViewProps {
  changes: PromptCompareResponse['model_config'];
}

function ConfigDiffView({ changes }: ConfigDiffViewProps) {
  if (!changes || changes.length === 0) {
    return (
      <div className="py-4 text-center text-sm text-muted-foreground">
        No configuration changes
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Setting</TableHead>
          <TableHead>Old Value</TableHead>
          <TableHead>New Value</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {changes.map((change, index) => (
          <TableRow key={index}>
            <TableCell className="font-medium">{change.field}</TableCell>
            <TableCell className="text-red-600 dark:text-red-400">
              {String(change.old)}
            </TableCell>
            <TableCell className="text-green-600 dark:text-green-400">
              {String(change.new)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
