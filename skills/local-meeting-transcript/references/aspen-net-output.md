---
name: aspen-net-output
description: Where ASPEN-NET meeting transcripts (local) and summaries (Outline wiki) go, and their formats.
---

# ASPEN-NET meeting output

Two deliverables per meeting:

| What | Where | Audience |
|---|---|---|
| Transcript + raw files | Local: `<out>/YYYY-MM-DD <Meeting title>/`, where `<out>` is `meetings/` under the project root | Whoever ran the skill / their agents |
| Summary | Outline wiki (`wiki.quantum-aspen.net`), via the outline MCP | The team |

## 1. Check what's already done

A meeting counts as done if any of these exist for its recording date (from `recording_datetime.txt`, step 2):

- a folder in `<out>`
- a summary on the wiki. Search the outline MCP for the date.
- a transcript anywhere else the user keeps them. Check their project instructions and memory, since some people have older transcripts in personal notes. Leave those where they are.

If a transcript exists but no wiki summary does, ask the user whether to write the summary from it. The audio doesn't need re-transcribing.

## 2. Local transcript folder

```
<out>/YYYY-MM-DD <Meeting title>/
  transcript.md      # clean_transcript.py output plus the header below
  transcript.srt     # raw whisper output
  transcript.txt     # raw, one timestamped line per segment
  meta.json          # {url, recording_datetime, zoom_title, duration_s, attendees, wiki_url}
```

Use the recording date, not today's. Name the meeting from its content and match the existing series (e.g. "Software stack meeting", "Attosecond layer deep dive with Krister Shalm"). Zoom's own title is always something like "Virginia (Gina) Lorenz's Zoom Meeting", which says nothing. Delete `meeting.mp4`/`meeting.wav` once transcribed (step 8). Don't keep media here.

`transcript.md` header:

```markdown
---
date: YYYY-MM-DD
title: <Meeting title>
source: Zoom cloud recording — illinois.zoom.us
transcription: faster-whisper large-v3-turbo (int8), run locally; no speaker labels
attendees: [<names inferred from content>]
summary: <wiki URL, filled in after publishing>
---

# YYYY-MM-DD <Meeting title> — transcript

## Known transcription errors

| Transcript says | Means |
|---|---|
| ... | **...** |

---

<clean_transcript.py output: `H:MM:SS` paragraphs>
```

### Known-errors table

Build it for each meeting by scanning the transcript. Substitutions seen so far:

| Transcript says | Means |
|---|---|
| "add a second layer", "out of second", "autosecond", "Adosecond" | **attosecond** (layer) |
| "time tiger", "time tigers", "time takers" | **Time Tagger** (Swabian) |
| "Aspenet", "AspenNet", "Aspen.net", "us Bennett" | **ASPEN-NET** |
| "PQM", "PQ and" | **PQN** |
| "christer", "Chris or" | **Krister** (Shalm) |
| "CMQ" | **ZeroMQ / ZMQ** |
| "NetCasm" | **NetQASM** |
| "pgas", "fbga" | **FPGA(s)** |
| "hungamandel", "hung mandel" | **Hong-Ou-Mandel** |
| "endnotes" | **nodes** |
| "QKV" | **QKD** |
| "third-lapse" | **Thorlabs** |
| "Kirby", "Curvy" | **CURBy** (CU) |
| "ghc", "gsg", "GG states" | **GHZ** states |
| "placal cells", "POCLE cells" | **Pockels cells** |
| "add-a-second", "add to second", "auto second" | **attosecond** (layer) |
| "stephan" | **Stefan** (Krastanov) |
| "gino" | **Gina** |

Add new recurring ones here. Regular attendees: Gina Lorenz, Marcos Frenkel, Mike Mazurek, Krister Shalm, Jasper.

## 3. Wiki summary

**Before writing:** read the wiki's [Agents Must Read This First](https://wiki.quantum-aspen.net/doc/agents-must-read-this-first-Nr6Ca5XEu4) and [Formatting Help](https://wiki.quantum-aspen.net/doc/formatting-help-TGrn2qSbfr). The rules that bite: no H1 in the body (the title is its own field), callouts are `:::info` / `:::warning` blocks, diagrams use ```` ```mermaidjs ````, edit existing docs with `patch`.

**Where:** the [Meetings](https://wiki.quantum-aspen.net/collection/meetings-ihBQ9Vrjrg) collection. Fetch the collection and follow its "Adding a summary" steps. Each summary is a child of its series page (e.g. *Software stack meeting*, which includes its deep dives and guest sessions, or *ASPEN-NET In-Person Retreat — Nov 5–6, 2026* for retreat planning), titled `YYYY-MM-DD <Meeting title>`, and gets a row in that series page's table. Create it from the **Meeting summary** template: run `list_templates` with the Meetings collection id, take its body, fill it in, and pass the result as `text` to `create_document` with `parentDocumentId` set to the series page. In the template, `!!…!!` marks a placeholder. Replace every one, and don't leave any `!!` markers in the published page. That template overrides the body sketch below wherever they differ. If no series fits, ask the user before starting a new one.

**Title:** `YYYY-MM-DD <Meeting title>`. **Body:** the template. Leave out its first `:::tip` (it's an instruction to the person filling the template in).

**Speaker attribution — the rule that matters most.** Transcripts have no reliable speaker labels, and naming the wrong person as the source of an idea does real damage. Name someone only when:

- they're presenting their own work (e.g. a guest describing their lab, or someone presenting their own system);
- they introduce themselves, or someone addresses them by name, in the exchange in question;
- an action item is assigned to them by name.

Otherwise don't attribute. Write "it was raised that…" or "one view was…", and leave quotes unattributed. Don't write per-person "positions" sections. If two views conflicted, present both without names. When unsure, leave the name out.

**Metadata:**

- **Header → Recording:** the Zoom share link the user gave you.
- **Attendees and action-item owners:** @mention them (`@[Name](mention://user/<id>)`, with ids from `list_users`) on new summaries, so names link to profiles and owners get notified. Don't @mention on backfilled summaries of old meetings, because the notifications would just be noise. Use plain names there. People without wiki accounts get plain names.
- **Notes by:** "AI from recording". The connector posts as the user, so this row and the warning callout are what tell readers an AI wrote it.

Style: numbered `###` topics, short unattributed quotes in italics, explicit **Ask:** lines, and owners on action items. Link related wiki docs (e.g. the [Glossary](https://wiki.quantum-aspen.net/doc/glossary-LbZyBPLZu5)) where a topic touches them. Read earlier summaries in the series first so cross-references are real. Don't link to local transcript paths, because nobody else can open them.

Publishing posts to a shared team space, so show the user the summary and the target location before the first `create_document` of a batch. After publishing, put the doc URL into `meta.json` and the `summary:` field of `transcript.md`.
