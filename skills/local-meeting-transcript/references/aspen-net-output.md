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
  chat.json          # chat.py output (Zoom links): timed messages, ai: commands
  frames/            # only the screenshots used in the summary
  meta.json          # {url, recording_datetime, zoom_title, duration_s, attendees, wiki_url}
```

Use the recording date, not today's. Name the meeting from its content and match the existing series (e.g. "Software stack meeting", "Attosecond layer deep dive with Krister Shalm"). Zoom's own title is always something like "Virginia (Gina) Lorenz's Zoom Meeting", which says nothing. Delete `meeting.mp4`/`share.mp4`/`meeting.wav` once transcribed (step 9). Don't keep media here.

`transcript.md` header:

```markdown
---
date: YYYY-MM-DD
title: <Meeting title>
source: Zoom cloud recording — illinois.zoom.us
transcription: faster-whisper large-v3-turbo (int8), run locally; no speaker labels
attendees: [<names inferred from content, spelled as on the wiki roster>]
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
| "christer", "Chris or" | **Krister** |
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
| "stephan" | **Stefan** |
| "gino" | **Gina** |

Add new recurring ones here, first names only. Who's who comes from the wiki (below).

### Names come from the wiki

The team roster is the wiki's user list, so this skill doesn't keep one. Always check it
before writing names: use `team.json` in the working directory if it's there (the
transcription service writes it: `[{name, id}]`), otherwise the Outline MCP's `list_users`.
Use it to:
- resolve misheard names to a real person, e.g. "christer" → Krister → Krister Shalm;
- spell full names, and get the user ids for @mentions.

Names that aren't on the roster are fine: guests, collaborators, people talked about.
Transcribe them as your best guess at what was said. Being on the roster doesn't mean
someone attended, and the attendees list still follows the evidence rules below.

## 3. Wiki summary

**Before writing:** read the wiki's [Agents Must Read This First](https://wiki.quantum-aspen.net/doc/agents-must-read-this-first-Nr6Ca5XEu4) and [Formatting Help](https://wiki.quantum-aspen.net/doc/formatting-help-TGrn2qSbfr). The rules that bite: no H1 in the body (the title is its own field), callouts are `:::info` / `:::warning` blocks, diagrams use ```` ```mermaidjs ````, edit existing docs with `patch`.

**Where:** the [Meetings](https://wiki.quantum-aspen.net/collection/meetings-ihBQ9Vrjrg) collection. Fetch the collection and follow its "Adding a summary" steps. Each summary is a child of its series page (e.g. *Software stack meeting*, which includes its deep dives and guest sessions, or *ASPEN-NET In-Person Retreat — Nov 5–6, 2026* for retreat planning), titled `YYYY-MM-DD <Meeting title>`, and gets a row in that series page's table. Create it from the **Meeting summary** template: run `list_templates` with the Meetings collection id, take its body, fill it in, and pass the result as `text` to `create_document` with `parentDocumentId` set to the series page. In the template, `!!…!!` marks a placeholder. Replace every one, and don't leave any `!!` markers in the published page. That template overrides the body sketch below wherever they differ. If no series fits, ask the user before starting a new one. In unattended mode, fail the job instead.

**Title:** `YYYY-MM-DD <Meeting title>`. **Body:** the template. Leave out its first `:::tip` (it's an instruction to the person filling the template in).

**Speaker attribution — the rule that matters most.** Transcripts have no reliable speaker labels, and naming the wrong person as the source of an idea does real damage. Name someone only when:

- they're presenting their own work (e.g. a guest describing their lab, or someone presenting their own system);
- they introduce themselves, or someone addresses them by name, in the exchange in question;
- an action item is assigned to them by name.

Otherwise don't attribute. Write "it was raised that…" or "one view was…", and leave quotes unattributed. Don't write per-person "positions" sections. If two views conflicted, present both without names. When unsure, leave the name out.

**Action-item owners** follow the same rule, and it's where summaries most often go wrong. Give an owner only when the exchange itself names them taking the task: "Marcos, can you…" and they agree, or they say they'll do it and are named in that exchange. Otherwise the owner is **TBD**. Don't infer an owner from:
- who posted something related in chat;
- whose system or document it concerns;
- who seemed to be speaking.

A wrong owner is worse than TBD: people act on it, or assume someone else has it.

**Due dates** work the same way: give one only if it was said in the meeting ("by Friday", "next week"). Otherwise it's TBD. Don't derive one from other wiki pages, such as an upcoming retreat.

**Metadata:**

- **Header → Recording:** the Zoom share link the user gave you.
- **Attendees and action-item owners:** @mention them (`@[Name](mention://user/<id>)`, with ids from `list_users`) on new summaries, so names link to profiles and owners get notified. Don't @mention on backfilled summaries of old meetings, because the notifications would just be noise. Use plain names there. People without wiki accounts get plain names.
- **Notes by:** "AI from recording". The connector posts as the user, so this row and the warning callout are what tell readers an AI wrote it.

**Chat:** add a `### Chat` section near the end listing the meeting's chat messages from `chat.json`, with time and sender. Sender names come from Zoom, so these are attributed. Leave out `ai:` commands that were carried out (they show up as screenshots or notes instead), and any messages inside an off-record span. Mention any command you couldn't interpret.

**Screenshots:** upload each kept frame and place it inline at the topic it belongs to, captioned per `chat-commands.md`. Requested screenshots always go in. Scene frames go in only where they show something the summary discusses. Uploading is two steps: `create_attachment` (name, `image/png`, size in bytes) returns an `uploadUrl`, its form fields and the attachment URL. Then POST the file there, e.g. `curl -sf -X POST "$uploadUrl" -F key=value … -F file=@frame.png` with every returned field before `file`. Embed the attachment URL as `![caption](url)`.

Style: numbered `###` topics, short unattributed quotes in italics, explicit **Ask:** lines, and owners on action items. Link related wiki docs (e.g. the [Glossary](https://wiki.quantum-aspen.net/doc/glossary-LbZyBPLZu5)) where a topic touches them. Read earlier summaries in the series first so cross-references are real. Don't link to local transcript paths, because nobody else can open them.

Publishing posts to a shared team space, so show the user the summary and the target location before the first `create_document` of a batch. In unattended mode (the transcription service), publish directly. After publishing, put the doc URL into `meta.json` and the `summary:` field of `transcript.md`.
