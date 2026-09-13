# FAQ

Short answers to the questions self-hosting authors ask most. Deeper pages:
[getting started](getting-started.md),
[provider setup](provider-setup.md),
[writing guide](writing-guide.md),
[backup and restore](backup-and-restore.md).

## Where are my manuscripts stored?

In one SQLite file on your machine, inside the Docker volume
`novel-engine-data`. Nothing is stored on any external server. You can copy
that file, back it up, or export your projects to Markdown/DOCX/EPUB and take
your writing anywhere — see
[backup and restore](backup-and-restore.md#where-your-data-physically-lives).

## Can I change the AI model?

Yes. The provider and its model are set through environment variables and
selected per project in Settings. DashScope (Qwen models) and any
OpenAI-compatible endpoint (DeepSeek, OpenAI, and similar) are supported;
[provider setup](provider-setup.md) has the exact variables. Each project can
use a different provider.

## Does it work offline?

Yes, with the built-in trial provider (`mock`): it needs no key and no
internet, and every feature works with it. Real providers (DashScope,
DeepSeek, and so on) need internet access because they are external services.

## Do I need an API key? What does it cost?

Not to try: the trial provider is free and complete. To generate with a real
model you need a key from that provider, and providers bill per usage
(typically small for novel-length experiments; watch the studio's **Usage**
tab).

## Who can read my drafts?

Only you. The studio runs on your machine with a single Owner account, and
nothing reports elsewhere. The one exception is inherent to AI generation:
the text you send to a generation request travels to the AI provider you
configured, under that provider's terms. With the trial provider, nothing
leaves your machine at all.

## How do I move my writing to a new computer?

Back up, copy the backup file, restore:
[backup and restore](backup-and-restore.md). Install Docker Desktop and
Novel Engine on the new machine, then restore the backup there — projects,
chapters, and history come across in one file.

## I stopped the container / restarted my computer — is my writing safe?

Yes. Manuscripts are written to the database as you type (autosave), and the
data volume survives stops, crashes, reboots, and upgrades. The container is
configured to come back on its own (`restart: unless-stopped`); after a
deliberate `docker compose stop`, start it again with `docker compose up -d`.

## Can several people write together?

No. Novel Engine is deliberately a single-author studio with one Owner
account. For a second author, run a second instance — each with its own data
volume — on another machine or another port.
