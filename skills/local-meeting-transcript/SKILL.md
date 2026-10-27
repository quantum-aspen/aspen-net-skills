---
name: local-meeting-transcript
description: Locally transcribe Zoom meeting recordings, with speaker ID.
user-invocable: true
allowed-tools: Bash, Read, Write
metadata:
  version: "2026-08-31"
---

# Local Meeting Transcript

Downloads a meeting recording (Zoom share links work without login) and transcribes it entirely on-device with faster-whisper. Use this whenever the user shares a Zoom/meeting recording link or file and wants a transcript — especially if they mention privacy/local-only processing.

**Speaker diarization is opt-in, not default.** sherpa-onnx diarization has failed QC on every real Zoom recording tried so far — see `references/diarization-reliability.md` for the data (talk-time imbalance, mid-sentence splitting, bogus extra speakers). Default to shipping the plain transcript (step 6) without attempting diarization at all. Only run the diarize/QC steps (4-5) if the user explicitly asks for speaker identification — and when you do, set expectations up front: mention the track record and that labels will be dropped if the QC gate fails, so a plain transcript isn't a surprising downgrade.

**The same caution applies to any summary written from a transcript.** Don't attribute ideas or quotes to named people unless it's unambiguous: they're presenting their own work, they're named on the recording, or an action is assigned to them by name. Inferring speakers from content misattributes ideas as often as diarization does.

## Prerequisites

`ffmpeg`, `yt-dlp`, `uv` on PATH. Install them with whatever toolchain manager the machine uses (e.g. `mise use ffmpeg yt-dlp uv`). No GPU needed; runs fine on 4 CPU cores at ~6-9x realtime for whisper and ~15-20x realtime for diarization.

## Paths

This skill uses no fixed paths. Resolve these placeholders at the start:

| Placeholder | Meaning |
|---|---|
| `<skill>` | This skill's base directory. All scripts live in `<skill>/scripts/`. |
| `<tools>` | Venv, diarization models, and the whisper model (`<tools>/hf`, downloaded on first transcribe), shared across meetings (~2GB, one-time). Downloads go in `<tools>/scratch/` unless the session has a disk-backed scratch dir. Don't use a RAM-backed `/tmp` (tmpfs) for 500MB+ recordings. `$MEETING_TOOLS_DIR` if set, else `.meeting-tools/` in the project root (the directory holding `.claude/`). `<venv>` is `<tools>/.venv`. |
| `<scratch>` | Per-meeting working dir for the download and raw whisper output. Use the session's scratch/temp directory if there is one, else `<tools>/scratch/<meeting>`. Delete after step 8. |
| `<out>` | Where the finished transcript goes. Set by the team's output reference (see below). If there isn't one, use `meetings/` under the project root (the directory holding this `.claude/`). |

## Team output conventions

Where transcripts and summaries end up, and how they're formatted, is team-specific. It lives in a `references/<team>-output.md` file, e.g. `references/aspen-net-output.md`. If the user's meetings belong to a team with such a file, follow it, including its check for already-processed meetings before fetching anything. To adapt this skill for another team, copy that file and edit it. If no file applies, write the transcript to `<out>` and ask the user where any summary should go.

## Pipeline

1. **Setup (once per machine):** `<skill>/scripts/setup.sh <tools>`
   Creates a uv venv with `faster-whisper` + `sherpa-onnx`, downloads the pyannote segmentation model and WeSpeaker CAM++ embedding model from k2-fsa's sherpa-onnx GitHub releases (MIT-licensed ONNX re-hosts, no HuggingFace token gate). Installs both even though diarization is opt-in, since setup is one-time and cheap either way.

2. **Fetch + check for existing captions:** `<skill>/scripts/fetch.sh "<url>" <scratch>`
   Runs `yt-dlp --list-subs` first — if a *real* language track exists (not just a `chapter` track, which is just screen-share on/off markers), grab that directly with `yt-dlp --write-subs` and skip straight to formatting; don't transcribe from audio. Zoom share links have not exposed real captions via yt-dlp in any run so far — but yt-dlp only ever surfaces the `chapter` track and never Zoom's native speaker-labeled "Audio Transcript" feature even when one exists. If the user is specifically asking whether Zoom provides per-speaker transcripts, don't rely on yt-dlp's silence as proof either way — query Zoom's own player API directly per `references/zoom-native-transcript-check.md` (cheap, no video download) for the authoritative `hasTranscript` flag.
   Also extracts the actual recording date from the resolved CDN URL (`GMT20260827-171318_Recording...` pattern) since yt-dlp's own `upload_date`/`timestamp` fields are null for Zoom — use this for naming the output.
   Downloads the video and extracts a 16kHz mono WAV (what faster-whisper wants).

3. **Transcribe (background, ~7-10 min for a 70min meeting):**
   `<venv>/bin/python <skill>/scripts/transcribe.py <scratch>/meeting.wav large-v3-turbo <scratch>/transcript`
   Use `large-v3-turbo` int8 on CPU — best accuracy/speed tradeoff without a GPU. Run as a background process (Bash `run_in_background: true`); wait for the completion notification rather than blocking foreground calls, since foreground timeout is capped well under typical run length. Several meetings can be fetched in parallel, but transcribe them one at a time — each whisper run takes 4 threads and a few GB of memory.

4. **Ship the default deliverable — plain transcript, no speaker labels:**
   `python3 <skill>/scripts/clean_transcript.py <scratch>/transcript.srt <out>/transcript.md`
   This is the default output. Scan the raw `.txt` for self-introductions/named turns (`grep -iE "i'?m [A-Z][a-z]+|this is [A-Z][a-z]+"`) and mention any names that surface in the meeting content in your reply — just don't attribute turn-by-turn without diarization.
   Stop here unless the user has explicitly asked for speaker identification.

5. **Diarize — only if explicitly requested (background, ~3-5 min):** ask the user if they know the speaker count; pinning is strongly preferred (auto-clustering has produced 36 bogus "speakers" on a 3-person call before).
   - If known: `NUM_CLUSTERS=<n> <venv>/bin/python <skill>/scripts/diarize.py <scratch>/meeting.wav <scratch>/speakers.tsv`
   - If unknown: `THRESH=0.7 <venv>/bin/python <skill>/scripts/diarize.py <scratch>/meeting.wav <scratch>/speakers.tsv`, but expect worse results than pinning.

6. **QC gate — mandatory whenever diarization was run, do not skip:**
   `python3 <skill>/scripts/qc_diarization.py <scratch>/speakers.tsv <expected_n>`
   Checks: (a) found-speaker-count vs expected, (b) any speaker with <30s / <2% of total talk time (near-certainly noise/crosstalk, not a real participant), (c) one speaker absorbing >75% of talk time with 2+ others present (signature of under-segmentation), (d) fraction of speaker-switches with <0.3s gap >40% (signature of one sentence split across two spurious labels). Exit 0 = PASS, exit 1 = FAIL with reasons printed either way.
   If it fails, try at most one more clustering config (different `NUM_CLUSTERS`/`THRESH`) — don't loop indefinitely. If still failing, tell the user diarization didn't pan out and that the plain transcript from step 4 remains the deliverable; don't silently keep retrying.

7. **If QC passes, add the speaker-labeled version alongside (not instead of) the plain one:**
   `python3 <skill>/scripts/merge.py <scratch>/speakers.tsv <scratch>/transcript.srt <out>/transcript-diarized.md "<title>"`
   Keep the raw `.srt` and timestamped `.txt` too. If QC fails, keep the labeled-but-unreliable version only if useful for debugging, named clearly (e.g. `transcript-diarized-UNRELIABLE.md`) — the plain transcript from step 4 stays the primary deliverable either way.

8. **Clean up:** delete `meeting.mp4`/`meeting.wav` from the scratch dir once transcribed (250MB+ each) — never leave large media in the project. Keep `<tools>` for reuse next time.

## Naming convention

Output folder: `<out>/YYYY-MM-DD <meeting title>/` — always lead with the recording date (step 2's extracted date, not "today"), since that's what makes transcripts sortable/findable later.

## References

| Topic | Description | Reference |
|-------|-------------|-----------|
| Diarization reliability track record | Why this skill defaults to distrusting diarization, with data from two real runs | [diarization-reliability](references/diarization-reliability.md) |
| Zoom native transcript check | How to tell whether Zoom itself has a speaker-labeled transcript | [zoom-native-transcript-check](references/zoom-native-transcript-check.md) |
| ASPEN-NET output | Local transcript layout, wiki summary format and placement, known-errors table | [aspen-net-output](references/aspen-net-output.md) |
