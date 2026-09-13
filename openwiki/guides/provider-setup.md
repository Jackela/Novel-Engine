# Provider setup

Novel Engine generates text through a **provider** — the AI service that turns
your instructions into proposals. This guide explains how to configure one
with Docker Compose, with exact environment-variable examples for DashScope
and for any OpenAI-compatible endpoint (DeepSeek used as the worked example).

If you just want to try the studio, you do not need this page yet: the
built-in trial provider (`mock`) writes real, deterministic prose with no API
key and no account anywhere, and every feature — Copilot, whole-book
generation, review — works with it.

## How providers are selected

Each project picks its provider in the project's **Settings** panel. The
panel lists every provider type — `mock`, DashScope, and
OpenAI-compatible — but only the ones whose API key the server has been
given (see below) can generate successfully; selecting an unconfigured
provider makes every generation fail. Until you configure a key, keep the
project on the built-in trial provider (`mock`).

## How configuration reaches the container

The studio container reads its configuration from environment variables. With
Docker Compose, the simplest way to set them is the `.env` file next to
`compose.yaml`: Compose reads that file automatically and passes provider
settings through to the container, so putting a key in `.env` and re-running
`docker compose up -d` is all it takes. The file is yours to edit and is not
part of the studio code, so an [upgrade](upgrading.md) never overwrites it.

Create a file named `.env` in the folder that contains `compose.yaml` (a
fresh download ships only the `.env.example` template; keep using your
existing `.env` if you already have one) and add your settings as plain
`NAME=value` lines:

```bash
LLM_PROVIDER=dashscope
DASHSCOPE_API_KEY=sk-your-key-here
```

Then apply the change:

```bash
docker compose up -d
```

`up -d` recreates the container with the new environment; a plain restart is
not enough after editing the file.

Alternatively, a `compose.override.yaml` file next to `compose.yaml` works
too — Compose merges it over the main file, which is useful when you need
structural changes such as a different port. Settings go inside the
`environment` block:

```yaml
services:
  novel-engine:
    environment:
      LLM_PROVIDER: dashscope
      DASHSCOPE_API_KEY: sk-your-key-here
```

Notes:

- Settings exported in your shell (`export DASHSCOPE_API_KEY=...`) win over
  the `.env` file; both reach the container through the same pass-through.
- Values are never echoed into logs or error messages.

## DashScope

DashScope is Alibaba Cloud's model service (the Qwen model family).

1. Sign in to the DashScope console (Bailian / Model Studio) at
   `https://bailian.console.aliyun.com/` — international users:
   `https://modelstudio.console.alibabacloud.com/`. Activate the model service
   if asked (billing is pay-per-token).
2. Open **API-KEY** management in the console, create a key, and copy it.
3. Put the key in the `.env` file next to `compose.yaml`:

   ```bash
   LLM_PROVIDER=dashscope
   DASHSCOPE_API_KEY=sk-your-key-here
   ```

4. Run `docker compose up -d`, then open your project's **Settings** and
   select **DashScope**.

Optional additions:

| Variable | Purpose |
|---|---|
| `DASHSCOPE_MODEL` | Generation model. Defaults to `qwen3.5-flash`. |
| `DASHSCOPE_REVIEW_MODEL` | Separate model for AI review runs; falls back to the generation model. |
| `DASHSCOPE_API_BASE` | Custom API base URL, only for gateways that mirror the DashScope API. |
| `DASHSCOPE_TRANSPORT_MODE` | `multimodal_generation` (default), `text_generation`, or `responses`. |

## OpenAI-compatible endpoints (DeepSeek as the example)

Any service that speaks the OpenAI chat-completions API works through the
`openai_compatible` provider. You need three values from the provider: the
API base URL, an API key, and a model name.

### DeepSeek, step by step

1. Sign in at `https://platform.deepseek.com/` and top up a small amount of
   credit (billing is pay-per-token).
2. Open **API keys** in the left menu, press **Create new API key**, and copy
   the key (you cannot view it again later).
3. Put the values in the `.env` file next to `compose.yaml`:

   ```bash
   LLM_PROVIDER=openai_compatible
   OPENAI_API_KEY=sk-your-deepseek-key
   OPENAI_API_BASE=https://api.deepseek.com/v1
   OPENAI_COMPATIBLE_MODEL=deepseek-chat
   ```

4. Run `docker compose up -d`, then open your project's **Settings** and
   select **OpenAI-compatible**.

### Other OpenAI-compatible services

The same three variables work for any compatible endpoint — the studio
accepts `LLM_API_KEY`/`LLM_API_BASE` as the canonical names and
`OPENAI_API_KEY`/`OPENAI_API_BASE` as aliases (either spelling works):

```bash
LLM_PROVIDER=openai_compatible
LLM_API_KEY=sk-your-key
LLM_API_BASE=https://api.openai.com/v1
OPENAI_COMPATIBLE_MODEL=gpt-4o-mini
```

The model name must be one the endpoint actually serves; if you omit it, the
studio falls back to `gpt-4o-mini` (or `LLM_MODEL` when set).

## Checking that it works

1. Open a project, select the provider in **Settings**, create or open a
   chapter, and run a Copilot **Continue**. A streaming proposal is the
   end-to-end proof that the key, base URL, and model all work.
2. If generation fails, look at the server log for the specific provider
   error:

   ```bash
   docker compose logs novel-engine
   ```

   Typical causes: the key was copied with a stray space, `up -d` was not run
   after editing `.env`, the model name does not exist at that
   endpoint, or the account is out of credit.
3. For a deeper database-and-configuration health report, the `doctor`
   command runs inside the container — it needs the studio stopped first; the
   exact stop/run/start sequence is in
   [backup and restore](backup-and-restore.md#running-cli-commands-in-docker).

## Back to trial mode

Set `LLM_PROVIDER=mock` in your `.env` (or delete the `LLM_PROVIDER` line)
and run `docker compose up -d`. Projects then run on the trial provider
again; your manuscripts are unaffected either way.
