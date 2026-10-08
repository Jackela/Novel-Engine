# ACP implementation design

The Owner-approved trade-offs are recorded in
[ADR-0011](../../../docs/adr/0011-owner-acp-proxy.md).

## Ownership and transport

Shared application ports define the generic proxy's launch and connection
behavior. Shared infrastructure owns child processes and token files; the shared
interface owns the WebSocket upgrade and message framing. The existing CLI root
injects these implementations. Generic proxy startup never opens Studio SQLite.

`/acp` authenticates the upgrade using `Authorization: Bearer <token>`.
The first JSON-RPC `initialize` carries
`_meta["novel-engine/acp-proxy"] = { command, args, cwd }`.
The proxy removes only that extension before forwarding. Each UTF-8 WebSocket
text message carries one JSON-RPC object; stdio uses newline-delimited objects.
Batch/binary/invalid/oversized messages terminate the connection. The initial
limits are 1 MiB per message and 8 MiB queued data.

Default listener is loopback port 8710. Tokens are independent, file-backed,
mode 0600, and never passed through URL parameters or inherited child variables.
One connection owns one child, with bounded buffers and process-tree cleanup.

## Novel Engine integration

`acp` is a closed Provider identifier. Server configuration controls proxy URL,
token file, executable, argument array, writable materials root, and optional
model override. Unknown catalog model is null; actual task model comes from
confirmed session configuration, not another provider's default.

The AI application port adds optional execution callbacks and cancellation to
structured and streamed generation. SDK session updates are classified before
reaching Studio: text enters structured parsing or the chapter delta parser;
tools and permissions enter the operation channel. The proxy's generic client
launch extension never enters a Studio request body.

The Owner opens a project-scoped operation event subscription before submitting
an AI request carrying `X-AI-Operation-Id`. The subscription's ready event
establishes the scope. Permission decisions identify both operation and pending
permission and use the normal Owner/CSRF checks. Operations are app-owned and
request-scoped, with bounded waiting and terminal cleanup; restart is not a
promise to restore a waiting permission.

ACP Proposal streams emit an initial operation frame before waiting for prose,
so headers and heartbeat activity do not depend on first model text. Structured
Review and Lore operations use the same separate observation channel while
retaining their existing final response.

Native Grok permissions remain active. Client-delegated filesystem/terminal
actions enforce the materials root and protected runtime paths. Native CLI
tool behavior is exercised separately; an isolated cwd is not evidence of
kernel isolation. The system uses explicit errors when a permission cannot be
answered, and never silently retries a possibly side-effecting submitted prompt.

## Review input

Review uses the already captured ordered source, with chapter bodies and
revision identifiers inside the existing untrusted-manuscript boundary.
The shared bounded prompt writer rejects over-budget input before calling the
provider. Existing empty/thin chapter metadata stays available to the trial
provider. Later edits cannot change the source associated with the stored Review.
