"""QC gate for a diarization run — decide whether speaker labels are
trustworthy enough to ship, or should be dropped in favor of a plain
paragraph transcript.

This codifies checks that were done ad-hoc (by eyeballing) in earlier runs,
both of which turned out to have unreliable diarization:
  - one speaker cluster absorbing the large majority of talk time while
    another gets a handful of sub-2-second fragments (noise/crosstalk
    misclassified as a "speaker", not a real participant)
  - a high fraction of speaker "switches" happening with near-zero gap
    (<0.3s), which is the signature of one continuous sentence being
    split across two spurious speaker labels rather than real turn-taking

Usage: python qc_diarization.py <speakers.tsv> [expected_num_speakers]
Exits 0 and prints "QC: PASS" if the run looks trustworthy, exits 1 and
prints "QC: FAIL" with reasons otherwise. Always prints the stats so a
human/agent can make the final call regardless of exit code.
"""
import sys
from collections import defaultdict

tsv = sys.argv[1]
expected_n = int(sys.argv[2]) if len(sys.argv) > 2 else None

turns = []
for line in open(tsv):
    a, b, c = line.rstrip("\n").split("\t")
    turns.append((float(a), float(b), c))
turns.sort()

tot, cnt = defaultdict(float), defaultdict(int)
for a, b, c in turns:
    tot[c] += b - a
    cnt[c] += 1

total_speech = sum(tot.values()) or 1.0
n_speakers = len(tot)

print(f"=== diarization QC: {tsv} ===")
print(f"speakers found: {n_speakers}" + (f" (expected {expected_n})" if expected_n else ""))
for spk, t in sorted(tot.items(), key=lambda x: -x[1]):
    pct = 100 * t / total_speech
    print(f"  {spk}: {t/60:.1f} min ({pct:.0f}%), {cnt[spk]} turns")

# Tiny-gap switch ratio: fraction of consecutive-turn speaker changes with
# under 0.3s of gap between them (mid-utterance splitting signature).
switches, tiny_gap = 0, 0
for i in range(1, len(turns)):
    prev_end, prev_spk = turns[i-1][1], turns[i-1][2]
    cur_start, cur_spk = turns[i][0], turns[i][2]
    if cur_spk != prev_spk:
        switches += 1
        if cur_start - prev_end < 0.3:
            tiny_gap += 1
tiny_gap_ratio = tiny_gap / switches if switches else 0.0
print(f"speaker switches: {switches}, tiny-gap (<0.3s): {tiny_gap} ({tiny_gap_ratio:.0%})")

reasons = []
if expected_n and n_speakers != expected_n:
    reasons.append(f"found {n_speakers} speakers, expected {expected_n}")
# Any speaker with under ~30s total or under 1% of talk time is likely noise,
# not a real participant.
for spk, t in tot.items():
    if t < 30 and (100 * t / total_speech) < 2:
        reasons.append(f"{spk} has only {t:.0f}s total ({cnt[spk]} turns) — likely noise, not a speaker")
# One cluster dominating >75% of speech with 2+ other speakers usually means
# under-segmentation (one or more real speakers folded into the dominant one).
if n_speakers >= 3:
    top_pct = max(tot.values()) / total_speech
    if top_pct > 0.75:
        reasons.append(f"one speaker has {top_pct:.0%} of total talk time — likely absorbed other speakers")
if tiny_gap_ratio > 0.4:
    reasons.append(f"{tiny_gap_ratio:.0%} of speaker switches have <0.3s gap — likely mid-sentence splitting")

if reasons:
    print("QC: FAIL")
    for r in reasons:
        print(f"  - {r}")
    print("\nRecommendation: do not ship these speaker labels. Try a different")
    print("NUM_CLUSTERS/THRESH, or drop diarization and ship a plain transcript,")
    print("noting any speaker names inferable from self-introduction in the text.")
    sys.exit(1)
else:
    print("QC: PASS")
    sys.exit(0)
