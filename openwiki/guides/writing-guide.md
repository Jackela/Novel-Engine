# Writing guide

This page walks through the studio the way you meet it while writing: the
project library, the editor and its side panels, Copilot proposals, the
whole-book generator, lore, review, and history. It explains what each surface
does for you as an author — it is not a feature inventory.

## The project library

After logging in you land on the project library. Every novel is one
**project**: create it with a title under **New project**. The library lists
your projects; open one by clicking it, and sign out from the top-right
control. The project title and its AI provider are changed later in the
project's **Settings** section.

## The workspace at a glance

Opening a project shows the writing workbench:

- **Left navigation** moves between sections (Manuscript, Outline,
  Characters, World, Notes), searches the project, and — on the manuscript
  surface — hosts the whole-book generator and the chapter list grouped by
  volume.
- **Center editor** is a Markdown editor with automatic saving. A status
  indicator near the title shows the save state; text you type is stored a
  moment after you stop typing.
- **Right Inspector** holds the tool tabs: **Copilot**, **Review**,
  **History**, **Export**, **Jobs**, and **Usage**. The selected tab follows
  the page address, so you can bookmark or refresh without losing your place.

The project title and the provider it uses are changed in the **Settings**
section.

## Sections: what lives where

Create material with the **Add** button beside each group in the navigation:

| Group | Use it for |
|---|---|
| **Manuscript** | Chapters — the book itself, in reading order. |
| **Outline** | Beat documents: scene sketches, structure notes you plan from. |
| **Characters** | Character sheets: who they are, how they speak. |
| **World** | Places, magic systems, factions, history — everything true about the setting. |
| **Notes** | Anything else: research scraps, TODOs, name ideas. |

Chapters and outline documents can be reordered with the **Move** buttons on
each row. Chapters can also be filed into volumes with the **Move to
volume…** selector on the row; the navigation groups chapters under one
heading per volume in reading order (two levels only: project, then volume).

Each chapter can be linked to one outline beat: open the chapter and use the
beat control in the Copilot tab to type the outline document's title, or
clear the link. The chapter then carries its plan with it, so the prose and
the outline stay connected.

## Copilot: propose, then accept

Copilot is the drafting assistant in the Inspector. The rule is simple:
**Copilot never changes the manuscript until you accept a proposal.**

1. Click into the instruction box and say what you want, e.g. "Continue this
   scene with a quieter, more ominous tone".
2. Press **Continue** to extend the chapter, or **Rewrite** to rework it from
   the top. The proposal streams in as a preview — nothing has been applied
   yet.
3. **Accept** applies the proposal to the manuscript (and creates a history
   revision you can return to), **Reject** throws it away. While a proposal
   is streaming you can **Stop** it; a stopped proposal leaves no trace.

Copilot sees your chapter, your outline, and the relevant character and world
sheets when drafting — see [lore](#lore-your-characters-and-world-feed-the-ai)
below for how to control what it knows.

## The whole-book generator

Below the chapter list sits the whole-book control. Pressing **Generate whole
book** drafts and auto-accepts every chapter that does not yet have an
accepted AI revision, strictly in reading order — each chapter is written
knowing the ones before it, so the book builds coherently. Progress shows
"Generating chapter 3 of 12…", and **Stop generating** halts after the
chapter in flight; chapters already accepted are preserved. Start it again
later and it resumes at the first chapter still missing an accepted revision.

Whole-book runs consume provider tokens chapter by chapter; watch the
**Usage** tab if you are on a metered plan.

## Lore: your characters and world feed the AI

There is no separate lore system to maintain — your **Characters** and
**World** documents *are* the lore. When Copilot drafts a chapter, entries
whose title or aliases appear in the text are injected into the prompt so the
AI keeps names, traits, and setting details straight.

Two controls matter:

- **Titles**: the entry's title is its trigger key, so title character and
  world sheets exactly as the names appear in your prose ("Yan Shuang", not
  "my protagonist").
- **Lifecycle status**: each entry is `draft`, `stable`, or `deprecated`.
  Only **stable**, non-empty entries are shown to the AI. New entries start
  as draft; switch them to stable once you trust them. The status control
  lives under the Copilot tab while an entry is open.

Additional trigger names beyond the title (aliases) are supported by the
underlying API but do not yet have a screen in the studio; titles are the
reliable path today.

If the AI keeps contradicting your setting, the fix is usually a thin or
draft-status world sheet: fill it in and mark it stable.

## Review: a second pair of eyes

The **Review** tab in the right Inspector runs an AI review over the current
manuscript. Press **Run review**; findings come back grouped with severity —
continuity slips, pacing notes, inconsistencies against your lore — and are
kept as a bound snapshot with the manuscript state they describe, so past
reviews stay readable even after you change the text. Reviews use the same
provider as generation (DashScope can use a dedicated review model, see
[provider setup](provider-setup.md#dashscope)).

## History: every version is kept

The **History** tab lists the revision chain of the open document. Saves,
accepted proposals, and restores all create revisions — nothing is ever
overwritten. **Restore** brings an old revision back as a *new* revision, so
restoring is itself undoable. Treat it as a safety net for aggressive
rewrites: accept the Copilot's bold version, then diff against history if it
went too far.

## Jobs, usage, and search

- **Jobs** shows background work — generation runs, exports, retries — with
  their status, and lets you retry a failed one.
- **Usage** totals the tokens your project has consumed per model, with a
  trailing 30-day window, so metered provider plans hold no surprises.
- **Search** (top of the navigation) finds text across all documents in the
  project and jumps straight to the hit.

## When the editor disagrees with the server

If you edit on two tabs or a save collides, the studio never silently drops
text: it offers **Load latest** (take the server's version, discard local) or
**Keep local and retry** (re-submit your text on top of the latest revision).
Your words are the thing the studio is least willing to lose.
