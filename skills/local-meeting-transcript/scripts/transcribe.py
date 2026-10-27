"""Transcribe a WAV file locally with faster-whisper.

Usage: python transcribe.py <wav> <model_name> <out_base>
  e.g. python transcribe.py meeting.wav large-v3-turbo transcript
Produces <out_base>.txt (timestamped lines) and <out_base>.srt.

Model choice: large-v3-turbo is the sweet spot for CPU int8 — ~9x realtime
on a 4-core box, near-large-v3 accuracy. Drop to 'medium' or 'small' if
memory/CPU is tighter; bump cpu_threads to match available cores.
"""
import os, sys, time, datetime

# Keep the ~1.6GB whisper model with the other models in <tools>/hf rather
# than ~/.cache, which may be small or quota-limited. HF_HOME overrides.
TOOLS = os.environ.get("MEETING_TOOLS_DIR") or os.path.dirname(sys.prefix)
os.environ.setdefault("HF_HOME", os.path.join(TOOLS, "hf"))

from faster_whisper import WhisperModel

wav, model_name, out_base = sys.argv[1], sys.argv[2], sys.argv[3]

def ts(s):
    return str(datetime.timedelta(seconds=int(s)))

def srt_ts(s):
    h, r = divmod(s, 3600); m, r = divmod(r, 60); sec = int(r)
    return f"{int(h):02}:{int(m):02}:{sec:02},{int((r-sec)*1000):03}"

print(f"loading {model_name} (int8, 4 threads)...", flush=True)
model = WhisperModel(model_name, device="cpu", compute_type="int8", cpu_threads=4)
print("loaded, transcribing...", flush=True)

t0 = time.time()
segments, info = model.transcribe(
    wav, beam_size=5, vad_filter=True,
    vad_parameters=dict(min_silence_duration_ms=500),
    condition_on_previous_text=False,
)
print(f"lang={info.language} ({info.language_probability:.2f}) dur={info.duration:.0f}s", flush=True)

txt, srt = open(out_base + ".txt", "w"), open(out_base + ".srt", "w")
n = 0
for seg in segments:
    n += 1
    line = seg.text.strip()
    txt.write(f"[{ts(seg.start)}] {line}\n"); txt.flush()
    srt.write(f"{n}\n{srt_ts(seg.start)} --> {srt_ts(seg.end)}\n{line}\n\n"); srt.flush()
    if n % 50 == 0:
        el = time.time() - t0
        print(f"  seg {n} @ {ts(seg.start)} | {el/60:.1f}min | {seg.end/el:.1f}x realtime", flush=True)
txt.close(); srt.close()
print(f"WHISPER_DONE: {n} segments in {(time.time()-t0)/60:.1f} min", flush=True)
