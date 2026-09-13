# Getting started (Docker)

This guide takes you from nothing to your first AI-assisted chapter using
Docker Desktop. It is written for writers, not system administrators: every
step happens on your own computer, and every step can be undone.

One thing to know up front: Novel Engine is **self-hosted**. Your manuscripts
are a single database file on your machine — not rows in somebody's cloud.
There is no external server that stores, reads, or controls your writing, and
no subscription is required. You can back up or export your work and walk away
with it at any time.

## What you need

- **Docker Desktop** (Windows, macOS, or Linux), installed and running. Get it
  from `https://www.docker.com/products/docker-desktop/`.
- **Chrome or Firefox** as your browser. Both work fully. Safari can open the
  studio but has a known rendering limitation in the frosted-glass visual
  style, so it is not recommended.
- Roughly 10 minutes for the first start. The very first launch builds the
  application image, which can take a few minutes; every later start is fast.

## Step 1: Get the code

Choose either option:

- **Clone** the repository if you have Git installed:

  ```bash
  git clone https://github.com/Jackela/Novel-Engine.git
  cd Novel-Engine
  ```

- **Download** without Git: on the GitHub page of the repository, use the
  green **Code** button, then **Download ZIP**, and unzip it. Open a terminal
  in the unzipped folder — the folder that contains `compose.yaml`.

## Step 2: Start the studio

From the folder containing `compose.yaml`, run:

```bash
docker compose up -d
```

The first run builds the application image and can take a few minutes. When
the prompt returns, the studio is running as a background service that Docker
restarts automatically after a crash or a machine reboot (unless you stopped
it yourself).

To follow the startup progress, run `docker compose logs -f novel-engine` and
press Ctrl+C to stop watching (this does not stop the studio).

## Step 3: Open the studio and create your account

Open `http://localhost:8000` in Chrome or Firefox. The first screen is the
setup screen: choose a username and password and create the local **Owner**
account, then log in. There is exactly one Owner account — Novel Engine is a
single-author studio, and the account exists only on your machine.

If the page does not open, see
[troubleshooting](troubleshooting.md#the-studio-does-not-open-on-localhost8000).

## Step 4: Write your first chapter with AI help

The studio ships with a built-in **trial provider** (`mock`): it writes real,
deterministic prose without any API key, so you can try every feature before
paying anything to anyone.

1. On the project library, enter a title under **New project** and press
   **Create project**.
2. In the left navigation, click **Add** next to **Manuscript** to create a
   chapter, then type a few sentences in the editor. Text saves automatically.
3. In the right-hand **Copilot** panel, type an instruction such as
   "Continue this scene with a quieter, more ominous tone" and press
   **Continue**. A proposal streams in as a preview.
4. Press **Accept** to apply it to the manuscript, or **Reject** to discard
   it. Copilot never changes your text until you accept.

For a full tour of the editor, see the [writing guide](writing-guide.md).

## Where your data lives

Everything you write — projects, chapters, revisions, settings — is stored in
one SQLite file inside a Docker **named volume** called `novel-engine-data`,
on your machine. Stopping or upgrading the studio never touches it; only an
explicit `docker compose down -v` would delete it (don't). To copy your work
out of the container, see [backup and restore](backup-and-restore.md).

## Day-to-day: stopping and starting

```bash
docker compose stop      # stop the studio (data is kept)
docker compose up -d     # start it again
```

After a `stop`, repeat `docker compose up -d` in the same folder to bring the
studio back. Your manuscripts and login session survive restarts.

## Next steps

- [Provider setup](provider-setup.md): connect a real AI provider such as
  DashScope or DeepSeek when you outgrow the trial provider.
- [Writing guide](writing-guide.md): the whole authoring workflow, including
  the whole-book generator.
- [Exporting](exporting.md): turn a project into Markdown, DOCX, or EPUB.
- [FAQ](faq.md): short answers to common questions.
