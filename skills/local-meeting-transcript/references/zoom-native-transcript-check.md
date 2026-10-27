---
name: zoom-native-transcript-check
description: How to definitively check whether a Zoom recording has a native speaker-labeled transcript, and what that feature actually is.
---

# Does Zoom provide per-speaker transcripts natively?

**Yes, but only if the host/account enabled it, and it's a distinct feature from what `yt-dlp --list-subs` surfaces.**

Zoom has two unrelated caption-ish artifacts on a cloud recording:

| Feature | Contains speaker names? | Created by | Off by default? |
|---|---|---|---|
| **Audio Transcript** (Zoom's own ASR, account setting "Audio Transcript" under Cloud Recording) | **Yes** — labeled per speaker | Automatic, if enabled before the meeting | Yes, opt-in |
| **Closed Captions** (CC file) | No — no speaker labels | Live captioner / Zoom live-caption / 3rd party | Separate opt-in |
| The `chapter` VTT track yt-dlp finds on share links | No — it's just screen-share on/off markers ("Recording Started" etc.), not speech content at all | Automatic | N/A, not a transcript |

`yt-dlp --list-subs` on a Zoom `/rec/play/` or `/rec/share/` URL has, in every run so far (including a live test against a real illinois.zoom.us recording on 2026-09-03), only ever surfaced the `chapter` track — never the Audio Transcript, even on recordings where it might exist. **Don't treat `yt-dlp --list-subs` showing only `chapter` as proof no transcript exists** — check Zoom's own player API directly instead, which is authoritative and much cheaper than downloading the full video first.

## Definitive check (no video download needed)

```sh
python3 <skill>/scripts/zoom_play_info.py "<share or play URL>" <scratch>
jq '{hasTranscript, transcribing, showCcDropDown, useCustomCaption, enableZrSpeakNameTag}' <scratch>/play_info.json
```

`fetch.sh` already runs this for Zoom links, so `play_info.json` is usually in `<scratch>` by now.

The script calls the player-info API Zoom's own web player uses. Share links (`/rec/share/<id>`) no longer redirect to the play page: it loads the share page for cookies, calls `/nws/recording/1.0/play/share-info/<id>` to get `redirectUrl`, loads that play page, takes `fileId` from it, then calls `/nws/recording/1.0/play/info/<fileId>?canPlayFromShare=true&componentName=rec-play`. The same response holds the chat (`xmppList`), the recording start (`fileStartTime`) and the screen-share ranges (`vttRanges.share`).

`hasTranscript: true` means a real speaker-labeled Audio Transcript VTT exists and is worth fetching directly (skip local ASR/diarization entirely — Zoom's own labels will be better than anything sherpa-onnx produces). `hasTranscript: false` means there is none for this recording — the `chapter`-only result from yt-dlp is accurate, and the skill's normal local-whisper pipeline is the only option (diarization on top of it remains unreliable per `diarization-reliability.md`).

## Verified example

Tested live against an illinois.zoom.us share link (2026-09-03): the play/info API returned `hasTranscript: false`, `transcribing: false`, `showCcDropDown: false` with a clean `status: true, errorCode: 0` envelope (not a permission error) — confirming this specific recording's host never enabled Audio Transcript. This matches every prior run of this skill, all of which only found the `chapter` track. No recording tried so far has had `hasTranscript: true`, but the check above is what to run before assuming that's universal — it may just be this account/user's settings.
