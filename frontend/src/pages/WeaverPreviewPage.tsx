import { WeaverNode } from '@/features/weaver/components/nodes/WeaverNode';

const previewNodes = [
  { id: 'node-idle', label: 'Idle', status: 'idle' as const },
  { id: 'node-active', label: 'Active', status: 'active' as const },
  { id: 'node-loading', label: 'Loading', status: 'loading' as const },
  { id: 'node-error', label: 'Error', status: 'error' as const },
];

export function WeaverPreviewPage() {
  return (
    <main id="main-content" className="min-h-screen bg-slate-950 px-6 py-10 text-slate-100">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-8">
        <header className="space-y-2">
          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
            Weaver Visual QA
          </p>
          <h1 className="text-3xl font-semibold">Weaver Node State Matrix</h1>
          <p className="text-sm text-slate-300">
            Dev-only preview for idle, active, loading, and error node treatments.
          </p>
        </header>
        <section className="grid gap-6 md:grid-cols-2">
          {previewNodes.map((node) => (
            <WeaverNode
              key={node.id}
              nodeId={node.id}
              nodeType="preview"
              status={node.status}
              className="min-h-[140px] p-4"
            >
              <div className="space-y-3">
                <h2 className="text-lg font-semibold">{node.label}</h2>
                <p className="text-sm text-slate-300">
                  Status: <span className="font-medium text-slate-100">{node.status}</span>
                </p>
              </div>
            </WeaverNode>
          ))}
        </section>
      </div>
    </main>
  );
}
