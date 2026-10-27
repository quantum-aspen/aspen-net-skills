---
name: diarization-reliability
description: Track record of sherpa-onnx diarization reliability on Zoom audio.
---

# Diarization reliability track record

sherpa-onnx (pyannote segmentation-3.0 + WeSpeaker CAM++ embeddings) has been run on two real multi-speaker Zoom meeting recordings. Both failed the QC checks in `qc_diarization.py`:

## Run 1 — ~74 min meeting, pinned to 5 speakers
- Result: 924 turns, 4 speakers detected (not 5)
- One speaker: 62% of talk time; smallest cluster: <1%
- Shipped as a plain transcript instead of diarized

## Run 2 — ~69 min meeting, pinned to 3 speakers (known count)
- Result: 787 turns, 3 speakers detected (matched expected count)
- SPEAKER_00: 43.1 min (80%), SPEAKER_01: 10.2 min (19%), SPEAKER_02: 0.2 min (0%, 10 turns under 2s each)
- 71% of the 297 speaker "switches" occurred with under 0.3s gap between them — i.e. the model was splitting continuous single-speaker sentences into two labels far more often than it was catching genuine turn-taking
- Auto-clustering (threshold-based, no pinned count) on the same audio produced 36 spurious "speakers"
- Shipped as a plain transcript instead of diarized

## Takeaway

Treat diarization on Zoom recordings as **likely to fail** rather than a reliable default. Always:
1. Pin the speaker count via `NUM_CLUSTERS` if it's knowable — auto-clustering has been far worse both times.
2. Run `qc_diarization.py` and actually read its verdict — don't ship labels on vibes.
3. Have `clean_transcript.py` ready as the real default output; treat a passing diarization QC as the pleasant surprise, not the expectation.
4. If diarization fails, still scan the transcript text for names via self-introduction/direct address (`i'm <Name>`, `this is <Name>`, or the meeting host addressing others by name) and mention them in the output notes — that's often available even when acoustic diarization isn't.

Suspected root cause (untested): short meeting clips, frequent overlapping speech / interruptions typical of small technical-discussion meetings, and/or audio mixed to mono before diarization (which removes any stereo/spatial cues) all work against this segmentation+clustering approach. A commercial diarization API or a fine-tuned model might do better if quality becomes a hard requirement — but that trades away the local/private processing this skill is built around.
