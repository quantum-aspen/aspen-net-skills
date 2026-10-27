"""Speaker diarization on a WAV file using sherpa-onnx (pyannote segmentation
+ WeSpeaker CAM++ embeddings). Fully local, no HF token needed.

Usage: python diarize.py <wav> <out_tsv> [limit_seconds]
  NUM_CLUSTERS=<n> env var pins the speaker count (recommended if you know
    how many people were on the call — auto-clustering is unreliable, see
    qc_diarization.py).
  THRESH=<float> env var (default 0.7) sets the auto-clustering distance
    threshold when NUM_CLUSTERS is unset/0.

Output: tab-separated <start>\t<end>\tSPEAKER_NN lines, sorted by start time.
"""
import sys, wave, time
import numpy as np, sherpa_onnx

wav_path, out_path = sys.argv[1], sys.argv[2]
limit = float(sys.argv[3]) if len(sys.argv) > 3 else 0
# Models live beside the venv that setup.sh created (<tools>/.venv, <tools>/models);
# MEETING_TOOLS_DIR overrides that.
import os
TOOLS = os.environ.get("MEETING_TOOLS_DIR") or os.path.dirname(sys.prefix)
M = os.path.join(TOOLS, "models/sherpa-onnx-pyannote-segmentation-3-0/model.onnx")
E = os.path.join(TOOLS, "models/wespeaker_en_voxceleb_CAM++.onnx")


def _clustering():
    import os
    n = int(os.environ.get("NUM_CLUSTERS", "0"))
    if n > 0:
        print(f"clustering: pinned to {n} speakers", flush=True)
        return sherpa_onnx.FastClusteringConfig(num_clusters=n)
    t = float(os.environ.get("THRESH", "0.7"))
    print(f"clustering: auto, threshold={t}", flush=True)
    return sherpa_onnx.FastClusteringConfig(num_clusters=-1, threshold=t)

cfg = sherpa_onnx.OfflineSpeakerDiarizationConfig(
    segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
        pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(model=M),
        num_threads=4,
    ),
    embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=E, num_threads=4),
    clustering=_clustering(),
    min_duration_on=0.3,
    min_duration_off=0.5,
)
assert cfg.validate(), "bad diarization config"
sd = sherpa_onnx.OfflineSpeakerDiarization(cfg)

with wave.open(wav_path) as w:
    assert w.getframerate() == sd.sample_rate, (w.getframerate(), sd.sample_rate)
    samples = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
samples = samples.astype(np.float32) / 32768.0
if limit:
    samples = samples[: int(limit * sd.sample_rate)]
print(f"loaded {len(samples)/sd.sample_rate:.0f}s", flush=True)

t0 = time.time()
last = [0]
def prog(processed, total):
    pct = int(processed / total * 100)
    if pct >= last[0] + 10:
        last[0] = pct
        print(f"  diarize {pct}% | {(time.time()-t0)/60:.1f}min", flush=True)
    return 0

segs = sd.process(samples, callback=prog).sort_by_start_time()
with open(out_path, "w") as f:
    for s in segs:
        f.write(f"{s.start:.3f}\t{s.end:.3f}\tSPEAKER_{s.speaker:02d}\n")
spk = sorted({s.speaker for s in segs})
print(f"DIARIZE_DONE: {len(segs)} turns, {len(spk)} speakers in {(time.time()-t0)/60:.1f} min", flush=True)
