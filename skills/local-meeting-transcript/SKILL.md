---
name: local-meeting-transcript
description: Locally transcribe Zoom meeting recordings, pull out the in-meeting chat, `ai:` chat commands and screenshots, and write the team's meeting summary.
user-invocable: true
allowed-tools: Bash, Read, Write
metadata:
  version: "2026-10-27"
---

# Local Meeting Transcript

Downloads a meeting recording (Zoom share links work without login) and transcribes it entirely on-device with faster-whisper. For Zoom links it also pulls the in-meeting chat, the `ai:` commands people typed into it, and screenshots of the shared screen. Use this whenever the user shares a Zoom/meeting recording link or file and wants a transcript or summary — especially if they mention privacy/local-only processing.

**Speaker diarization is opt-in, not default.** sherpa-onnx diarization has failed QC on every real Zoom recording tried so far — see `references/diarization-reliability.md` for the data (talk-time imbalance, mid-sentence splitting, bogus extra speakers). Default to shipping the plain transcript (step 4) without attempting diarization at all. Only run the diarize/QC steps (6-8) if the user explicitly asks for speaker identification — and when you do, set expectations up front: mention the track record and that labels will be dropped if the QC gate fails, so a plain transcript isn't a surprising downgrade.

**The same caution applies to any summary written from a transcript.** Don't attribute ideas or quotes to named people unless it's unambiguous: they're presenting their own work, they're named on the recording, or an action is assigned to them by name. Inferring speakers from content misattributes ideas as often as diarization does. Chat is the exception: Zoom records who sent each message, so chat attribution is reliable.

## Prerequisites

`ffmpeg`, `yt-dlp`, `uv`, `jq` on PATH. Install them with whatever toolchain manager the machine uses (e.g. `mise use ffmpeg yt-dlp uv jq`). No GPU needed; runs fine on 4 CPU cores at ~6-9x realtime for whisper and ~15-20x realtime for diarization.

## Paths

This skill uses no fixed paths. Resolve these placeholders at the start:

| Placeholder | Meaning |
|---|---|
| `<skill>` | This skill's base directory. All scripts live in `<skill>/scripts/`. |
| `<tools>` | Venv, diarization models, and the whisper model (`<tools>/hf`, downloaded on first transcribe), shared across meetings (~2GB, one-time). Downloads go in `<tools>/scratch/` unless the session has a disk-backed scratch dir. Don't use a RAM-backed `/tmp` (tmpfs) for 500MB+ recordings. `$MEETING_TOOLS_DIR` if set, else `.meeting-tools/` in the project root (your working directory). `<venv>` is `<tools>/.venv`. |
| `<scratch>` | Per-meeting working dir for the download and raw whisper output. Use the session's scratch/temp directory if there is one and it's disk-backed, else `<tools>/scratch/<meeting>`. Delete after step 9. |
| `<out>` | Where the finished transcript goes. Set by the team's output reference (see below). If there isn't one, use `meetings/` under the project root. |

## Team output conventions

Where transcripts and summaries end up, and how they're formatted, is team-specific. It lives in a `references/<team>-output.md` file, e.g. `references/aspen-net-output.md`. If the user's meetings belong to a team with such a file, follow it, including its check for already-processed meetings before fetching anything. To adapt this skill for another team, copy that file and edit it. If no file applies, write the transcript to `<out>` and ask the user where any summary should go.

## Unattended mode

When `MEETING_UNATTENDED=1` is set (the transcription service sets it), nobody is there to answer questions:

- Never ask. Where this skill or the team reference says to ask or confirm, take the conservative default and note it in the summary or the run log.
- Never diarize. Steps 6-8 need a person to request them.
- Publish the summary directly. The "show the user first" step in the team reference is skipped; the AI-authorship row and callout stay.
- If a meeting can't be matched to an existing series, don't start a new one. Fail the job with a clear message instead.

## Pipeline

1. **Setup (once per machine):** `<skill>/scripts/setup.sh <tools>`
   Creates a uv venv with `faster-whisper` + `sherpa-onnx`, downloads the pyannote segmentation model and WeSpeaker CAM++ embedding model from k2-fsa's sherpa-onnx GitHub releases (MIT-licensed ONNX re-hosts, no HuggingFace token gate). Installs both even though diarization is opt-in, since setup is one-time and cheap either way.

2. **Fetch + check for existing captions:** `<skill>/scripts/fetch.sh "<url>" <scratch>`
   For Zoom links it first saves Zoom's player info (`play_info.json`, via `zoom_play_info.py`) and the in-meeting chat (`chat.json`, `chat.md`, via `chat.py`), and takes the recording date from the player info's `fileStartTime` (for other links, from the resolved CDN filename, e.g. `GMT20260827-171318_Recording...`). Write it to `recording_datetime.txt` and use it for naming the output — yt-dlp's own date fields are null for Zoom.
   Runs `yt-dlp --list-subs` — if a *real* language track exists (not just a `chapter` track, which is just screen-share on/off markers), grab that directly with `yt-dlp --write-subs` and skip straight to formatting; don't transcribe from audio. yt-dlp never surfaces Zoom's native speaker-labeled "Audio Transcript", so check `hasTranscript` in `play_info.json` too (see `references/zoom-native-transcript-check.md`).
   Downloads the video (`meeting.mp4`), the screen-share-only stream (`share.mp4`) if Zoom recorded one, and extracts a 16kHz mono WAV (what faster-whisper wants).

3. **Transcribe (background, ~7-10 min for a 70min meeting):**
   `<venv>/bin/python <skill>/scripts/transcribe.py <scratch>/meeting.wav large-v3-turbo <scratch>/transcript`
   Use `large-v3-turbo` int8 on CPU — best accuracy/speed tradeoff without a GPU. To use a remote whisper server instead (OpenAI-compatible, returning `verbose_json` segment timestamps), set `TRANSCRIBE_URL` and `TRANSCRIBE_MODEL` (plus `TRANSCRIBE_API_KEY` if needed). The outputs are identical; see the script's docstring. Never point it at a server the user hasn't chosen: it uploads the meeting audio. Run as a background process (Bash `run_in_background: true`); wait for the completion notification rather than blocking foreground calls, since foreground timeout is capped well under typical run length. Several meetings can be fetched in parallel, but transcribe them one at a time — each whisper run takes 4 threads and a few GB of memory.

4. **Ship the default deliverable — plain transcript, no speaker labels:**
   `python3 <skill>/scripts/clean_transcript.py <scratch>/transcript.srt <out>/transcript.md`
   This is the default output. Scan the raw `.txt` for self-introductions/named turns (`grep -iE "i'?m [A-Z][a-z]+|this is [A-Z][a-z]+"`) and mention any names that surface in the meeting content in your reply — just don't attribute turn-by-turn without diarization.

5. **Chat, `ai:` commands and screenshots (Zoom links only):** can run while step 3 is going.
   Read `chat.json` and `references/chat-commands.md`, which says what each `ai:` command means. `<video>` is `<scratch>/share.mp4` if it exists, else `<scratch>/meeting.mp4`.
   - `python3 <skill>/scripts/frames.py commands <video> <scratch>/chat.json <scratch>/frames` — a candidate frame per `ai:` command. Keep the ones that are screenshot requests.
   - `python3 <skill>/scripts/frames.py scenes <video> <scratch>/play_info.json <scratch>/frames` (background, ~1.5 min per hour of meeting) — frames where the shared screen changed, plus one every 5 min. Look through them and keep only those that show something the summary discusses (a diagram, a doc, a slide). Don't include them all.
   - `python3 <skill>/scripts/frames.py at <video> <seconds> <out.png>` — any other moment, e.g. for `ai: screenshot 2 min ago`.
   Honour `ai: off record` spans before writing anything: cut those spans out of `transcript.md` and leave them out of the summary.
   Stop after this step unless the user has explicitly asked for speaker identification.

6. **Diarize — only if explicitly requested (background, ~3-5 min):** ask the user if they know the speaker count; pinning is strongly preferred (auto-clustering has produced 36 bogus "speakers" on a 3-person call before).
   - If known: `NUM_CLUSTERS=<n> <venv>/bin/python <skill>/scripts/diarize.py <scratch>/meeting.wav <scratch>/speakers.tsv`
   - If unknown: `THRESH=0.7 <venv>/bin/python <skill>/scripts/diarize.py <scratch>/meeting.wav <scratch>/speakers.tsv`, but expect worse results than pinning.

7. **QC gate — mandatory whenever diarization was run, do not skip:**
   `python3 <skill>/scripts/qc_diarization.py <scratch>/speakers.tsv <expected_n>`
   Checks: (a) found-speaker-count vs expected, (b) any speaker with <30s / <2% of total talk time (near-certainly noise/crosstalk, not a real participant), (c) one speaker absorbing >75% of talk time with 2+ others present (signature of under-segmentation), (d) fraction of speaker-switches with <0.3s gap >40% (signature of one sentence split across two spurious labels). Exit 0 = PASS, exit 1 = FAIL with reasons printed either way.
   If it fails, try at most one more clustering config (different `NUM_CLUSTERS`/`THRESH`) — don't loop indefinitely. If still failing, tell the user diarization didn't pan out and that the plain transcript from step 4 remains the deliverable; don't silently keep retrying.

8. **If QC passes, add the speaker-labeled version alongside (not instead of) the plain one:**
   `python3 <skill>/scripts/merge.py <scratch>/speakers.tsv <scratch>/transcript.srt <out>/transcript-diarized.md "<title>"`
   Keep the raw `.srt` and timestamped `.txt` too. If QC fails, keep the labeled-but-unreliable version only if useful for debugging, named clearly (e.g. `transcript-diarized-UNRELIABLE.md`) — the plain transcript from step 4 stays the primary deliverable either way.

9. **Clean up:** delete `meeting.mp4`/`share.mp4`/`meeting.wav` from the scratch dir once transcribed and the frames are pulled (100MB+ each) — never leave large media in the project. Delete frames you didn't keep. Keep `<tools>` for reuse next time.

## Naming convention

Output folder: `<out>/YYYY-MM-DD <meeting title>/` — always lead with the recording date (step 2's extracted date, not "today"), since that's what makes transcripts sortable/findable later.

## References

| Topic | Description | Reference |
|-------|-------------|-----------|
| Diarization reliability track record | Why this skill defaults to distrusting diarization, with data from two real runs | [diarization-reliability](references/diarization-reliability.md) |
| Zoom native transcript check | How to tell whether Zoom itself has a speaker-labeled transcript | [zoom-native-transcript-check](references/zoom-native-transcript-check.md) |
| `ai:` chat commands | What attendees' `ai:` chat messages mean, timing, and how screenshots go into the summary | [chat-commands](references/chat-commands.md) |
| ASPEN-NET output | Local transcript layout, wiki summary format and placement, known-errors table | [aspen-net-output](references/aspen-net-output.md) |
