"""Merge a Whisper .srt with a diarization .tsv into a speaker-labeled
markdown transcript. Only use this if qc_diarization.py passed — otherwise
prefer clean_transcript.py.

Usage: python merge.py <speakers.tsv> <transcript.srt> <out.md> [title]
"""
import datetime, re, sys

tsv = sys.argv[1] if len(sys.argv) > 1 else "speakers.tsv"
srt_path = sys.argv[2] if len(sys.argv) > 2 else "transcript.srt"
out = sys.argv[3] if len(sys.argv) > 3 else "transcript-diarized.md"
title = sys.argv[4] if len(sys.argv) > 4 else "Meeting transcript"

def ts(s):
    return str(datetime.timedelta(seconds=int(s)))

turns = []
for line in open(tsv):
    a, b, c = line.rstrip("\n").split("\t")
    turns.append((float(a), float(b), c))

def p(t):
    h, mn, rest = t.split(":"); s, ms = rest.split(",")
    return int(h)*3600 + int(mn)*60 + int(s) + int(ms)/1000

blocks, cur = [], []
for line in open(srt_path):
    line = line.rstrip("\n")
    if line == "":
        if len(cur) >= 3:
            m = re.match(r"(\S+) --> (\S+)", cur[1])
            blocks.append((p(m.group(1)), p(m.group(2)), " ".join(cur[2:]).strip()))
        cur = []
    else:
        cur.append(line)

def speaker_for(st, en):
    best, best_ov = None, 0.0
    for a, b, spk in turns:
        ov = min(en, b) - max(st, a)
        if ov > best_ov:
            best, best_ov = spk, ov
    return best or "SPEAKER_??"

res, prev, buf, bstart = [], None, [], 0.0
for st, en, text in blocks:
    spk = speaker_for(st, en)
    if spk != prev and buf:
        res.append((bstart, prev, " ".join(buf)))
        buf, bstart = [], st
    if not buf:
        bstart = st
    buf.append(text); prev = spk
if buf:
    res.append((bstart, prev, " ".join(buf)))

with open(out, "w") as f:
    f.write(f"# {title}\n\n")
    for start, spk, text in res:
        f.write(f"**{spk}** · `{ts(start)}`\n\n{text}\n\n")
print(f"MERGE_DONE: {len(res)} speaker blocks -> {out}", flush=True)
