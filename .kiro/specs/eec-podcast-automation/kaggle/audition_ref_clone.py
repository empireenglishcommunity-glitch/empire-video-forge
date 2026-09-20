# ==========================================================================
# EEC "Yalla Fluent" — REAL-REFERENCE clone audition (Phase B, task B.6d/e)
# --------------------------------------------------------------------------
# All SYNTHETIC accent routes failed (B.5 describe; B.6c native-L1-design / Piper /
# clone-of-those). So we now clone a REAL human reference — the one method that
# transfers authentic accent acoustics — sourced RIGHTS-CLEAN from Mozilla
# Common Voice (CC0 public domain), via the non-gated HF mirror
# `fixie-ai/common_voice_17_0`.
#
# Flow:
#   1) STREAM Common Voice, pick clean candidate REAL clips:
#        - RAVI  = English clips tagged an INDIAN / South-Asian accent
#        - MACAL = Arabic-language clips (`ar`) — a genuine Arabic speaker's timbre;
#                  we clone that identity and have it speak ENGLISH (Qwen clones the
#                  voice/accent cross-lingually), so Macal carries a real Egyptian/
#                  Arabic colour.  (Also try `en` clips tagged an Arabic-region accent.)
#   2) CLONE each ref through Qwen `-Base` reading a REAL Season-1 line.
#        - Macal: 3 STAGES from ONE ref — identity fixed by the clip; fluency travels
#          via the script + speaking rate (length_scale-ish via the line itself).
#   3) Owner listens + picks the ref that sounds most authentic & natural (B.6e).
#
# ✅ Commercial-safe: Common Voice = CC0.  ✅ $0.  ✅ Qwen = Apache-2.0.
# ⚠️ Kaggle GPU=T4, Internet ON, fresh notebook. No flash-attn (Turing → sdpa).
# --------------------------------------------------------------------------
# CELL 1 (install + restart) — copy EXACTLY, run, wait for the restart:
#
#   !pip install -q -U qwen-tts soundfile "datasets>=2.18" librosa
#   import os; os._exit(0)
#
# CELL 2 (this file) — after the restart. Just run it.
# ==========================================================================
import os, json, time, traceback, zipfile, html, io

OUT = "/kaggle/working/ref_clone"; os.makedirs(OUT, exist_ok=True)
REFS = os.path.join(OUT, "refs"); os.makedirs(REFS, exist_ok=True)
LANG = "English"
CV = "fixie-ai/common_voice_17_0"     # CC0 Common Voice mirror (non-gated)
N_REF = 3                              # candidate refs to pull per character

# real Season-1 lines the clone will read back (so owner hears it in-character)
MACAL_LINES = {
    "S1": "Hello, Mama. I am in Dubai. Everything is good. Everything is... very good.",
    "S2": "Okay. Okay, I'm coming. I mean - I'm on my way down right now.",
    "S3": "Okay, okay. So at Dune and Co., we were gonna miss a big deadline, right?",
}
RAVI_LINE = "Traffic is heavy today, my friend. But I know a short way."

# ref length window (seconds) — Qwen clones from ~3-15s; aim clean & mid-length
REF_MIN, REF_MAX = 4.0, 14.0

import soundfile as sf
import numpy as np

def save_ref(arr, sr, path):
    sf.write(path, arr, sr); return path

def dur_ok(arr, sr):
    d = len(arr) / float(sr)
    return REF_MIN <= d <= REF_MAX

def extract_audio(a):
    """Return (float32 mono np.array, sr) from a datasets 'audio' cell, robust across
    versions: old dict {'array','sampling_rate'}, new torchcodec AudioDecoder, or a
    path/bytes. Returns (None, None) if it can't be read."""
    if a is None:
        return None, None
    # 1) old-style dict
    if isinstance(a, dict):
        if a.get("array") is not None and a.get("sampling_rate"):
            arr = np.asarray(a["array"], dtype="float32")
            return _mono(arr), int(a["sampling_rate"])
        # dict may carry a path or raw bytes instead of a decoded array
        if a.get("path") and os.path.exists(a["path"]):
            return _read_path(a["path"])
        if a.get("bytes"):
            return _read_bytes(a["bytes"])
        return None, None
    # 2) new torchcodec AudioDecoder (datasets >= ~3.x): has get_all_samples()
    if hasattr(a, "get_all_samples"):
        try:
            s = a.get_all_samples()
            arr = np.asarray(s.data, dtype="float32"); sr = int(s.sample_rate)
            return _mono(arr), sr
        except Exception:
            pass
    # 3) a plain path or bytes
    if isinstance(a, str) and os.path.exists(a):
        return _read_path(a)
    if isinstance(a, (bytes, bytearray)):
        return _read_bytes(a)
    return None, None

def _mono(arr):
    arr = np.asarray(arr, dtype="float32")
    if arr.ndim > 1:                       # (channels, samples) or (samples, channels)
        ax = 0 if arr.shape[0] < arr.shape[-1] else -1
        arr = arr.mean(axis=ax)
    return np.ascontiguousarray(arr.reshape(-1))

def _read_path(p):
    import soundfile as _sf
    arr, sr = _sf.read(p, dtype="float32"); return _mono(arr), int(sr)

def _read_bytes(b):
    import soundfile as _sf
    arr, sr = _sf.read(io.BytesIO(bytes(b)), dtype="float32"); return _mono(arr), int(sr)

# ==========================================================================
# STEP 1 — SOURCE real reference clips from Common Voice (streaming) --------
# ==========================================================================
from datasets import load_dataset

def pull_refs(config, split, accent_needles, want, label):
    """Stream a CV config; keep clean clips whose accent matches any needle
    (or ANY clip if accent_needles is None, e.g. the Arabic-language config)."""
    picked = []
    # `split` may be one name or a list of candidates — try each until one opens
    # (configs differ: some call it 'validated', others 'validation'/'train').
    split_candidates = split if isinstance(split, (list, tuple)) else [split]
    ds = None
    for sp in split_candidates:
        print(f"\n[{label}] streaming {CV}:{config} ({sp}) ...", flush=True)
        try:
            ds = load_dataset(CV, config, split=sp, streaming=True)
            try:
                from datasets import Audio
                ds = ds.cast_column("audio", Audio(decode=True))
            except Exception:
                pass
            break
        except Exception as e:
            print(f"  could not open {config}:{sp} — {str(e)[:90]}", flush=True)
            ds = None
    if ds is None:
        return picked
    seen = 0
    for row in ds:
        seen += 1
        if seen > 6000:            # safety bound on streaming scan
            break
        acc = (row.get("accent") or "").lower()
        if accent_needles is not None and not any(n in acc for n in accent_needles):
            continue
        if (row.get("down_votes") or 0) > 0:      # prefer clean, upvoted clips
            continue
        arr, sr = extract_audio(row.get("audio"))
        if arr is None or sr is None or len(arr) == 0:
            continue
        if not dur_ok(arr, sr):
            continue
        idx = len(picked) + 1
        p = save_ref(arr, sr, os.path.join(REFS, f"{label}_ref{idx}.wav"))
        picked.append({"file": p, "sr": sr, "text": (row.get("sentence") or "").strip(),
                       "accent": row.get("accent") or "", "locale": row.get("locale") or config})
        print(f"  + {label}_ref{idx}: [{row.get('accent')}] {(row.get('sentence') or '')[:50]}", flush=True)
        if len(picked) >= want:
            break
    if not picked:
        print(f"  (no matching clips found for {label} in {config}:{split})", flush=True)
    return picked

SPLITS = ["validated", "validation", "train"]   # try in order; configs differ

# RAVI: English clips tagged an Indian / South-Asian accent
ravi_refs = pull_refs("en", SPLITS,
                      ["india", "indian", "south asia", "south-asia"], N_REF, "Ravi")

# MACAL: we need a real Arabic/Egyptian colour. Common Voice has very few en clips
# tagged an Arab accent, so the RELIABLE source is the Arabic-language config `ar`
# (a genuine Arabic speaker's timbre) — Qwen clones the voice cross-lingually and
# has it speak ENGLISH, carrying the Arabic colour. Try `ar` FIRST now, then fall
# back to any en clip tagged an Arab/Egyptian/Middle-East/Gulf/Levant accent.
macal_refs = pull_refs("ar", SPLITS, None, N_REF, "Macal")
if not macal_refs:
    macal_refs = pull_refs("en", SPLITS,
                           ["arab", "egypt", "middle east", "levant", "gulf",
                            "north africa", "saudi", "emirat"], N_REF, "Macal")

# ==========================================================================
# STEP 2 — CLONE each ref through Qwen, reading real Season-1 lines ---------
# ==========================================================================
import torch
from qwen_tts import Qwen3TTSModel

print("\nLoading Qwen3-TTS Base (clone)...", flush=True)
try:
    clone = Qwen3TTSModel.from_pretrained("Qwen/Qwen3-TTS-12Hz-1.7B-Base",
                device_map="cuda:0", dtype=torch.bfloat16, attn_implementation="sdpa")
except Exception:
    print("bf16 failed, trying fp16...", flush=True)
    clone = Qwen3TTSModel.from_pretrained("Qwen/Qwen3-TTS-12Hz-1.7B-Base",
                device_map="cuda:0", dtype=torch.float16, attn_implementation="sdpa")

rendered = []
def do_clone(ref, text, tag, note, name):
    out = os.path.join(OUT, f"{tag}.wav")
    arr, _ = sf.read(ref["file"])
    # attempt 1: with ref_text (best quality). attempt 2: x_vector-only (no ref_text)
    # — robust when the ref is Arabic and we generate English (cross-lingual clone).
    attempts = [
        dict(ref_audio=(arr, ref["sr"]), ref_text=ref.get("text") or None),
        dict(ref_audio=(arr, ref["sr"]), x_vector_only_mode=True),
    ]
    for i, kw in enumerate(attempts, 1):
        try:
            prompt = clone.create_voice_clone_prompt(**kw)
            wavs, sr = clone.generate_voice_clone(text=text, language=LANG, voice_clone_prompt=prompt)
            sf.write(out, wavs[0], sr)
            rendered.append({"name": name, "tag": tag, "file": os.path.basename(out), "note": note})
            print(f"  OK {tag}" + ("" if i == 1 else " (x-vector mode)"), flush=True); return
        except Exception as e:
            print(f"  .. {tag} attempt {i}: {str(e)[:80]}", flush=True); time.sleep(2)
    print(f"  !! {tag} failed", flush=True)

# Ravi: one clone per candidate ref, reading his line
for i, ref in enumerate(ravi_refs, 1):
    do_clone(ref, RAVI_LINE, f"Ravi__ref{i}", f"CV ref {i} [{ref['accent']}] -> Ravi line", "Ravi")

# Macal: for each candidate ref, render the 3 stage lines (arc via the script)
for i, ref in enumerate(macal_refs, 1):
    for stg, line in MACAL_LINES.items():
        do_clone(ref, line, f"Macal_{stg}__ref{i}",
                 f"CV ref {i} [{ref['accent'] or ref['locale']}] -> Macal {stg}", "Macal")

# ==========================================================================
# CONTACT SHEET + zip (incl. the raw refs so the owner can hear the source) -
# ==========================================================================
groups = {}
for r in rendered:
    groups.setdefault(r["name"], []).append(r)
rows = []
for name, items in groups.items():
    rows.append(f"<h2>{html.escape(name)}</h2>")
    for r in items:
        rows.append(f"<div style='margin:6px 0;padding:8px;border:1px solid #ccc;border-radius:6px'>"
                    f"<audio controls src='{html.escape(r['file'])}'></audio><br>"
                    f"<small>{html.escape(r['note'])}</small></div>")
# also list the raw source refs
rows.append("<h2>Raw source refs (Common Voice, CC0)</h2>")
for lbl, refs in (("Ravi", ravi_refs), ("Macal", macal_refs)):
    for i, ref in enumerate(refs, 1):
        rel = os.path.relpath(ref["file"], OUT)
        rows.append(f"<div style='margin:6px 0'><b>{lbl} ref{i}</b> [{html.escape(ref['accent'] or ref['locale'])}]"
                    f"<br><audio controls src='{html.escape(rel)}'></audio>"
                    f"<br><small>{html.escape((ref['text'] or '')[:80])}</small></div>")
index = ("<html><head><meta charset='utf-8'><title>Yalla Fluent — real-ref clones</title>"
         "<style>body{font-family:sans-serif;max-width:820px;margin:24px auto;padding:0 12px}"
         "h1{color:#b8860b}h2{margin-top:26px;border-bottom:2px solid #b8860b}</style></head><body>"
         "<h1>Yalla Fluent — Macal &amp; Ravi from REAL references (CC0)</h1>"
         "<p>Each clip = a real Common Voice speaker's voice cloned by Qwen, reading a "
         "Season-1 line. Pick the ref that sounds most authentically Egyptian (Macal) / "
         "Indian (Ravi) AND natural. Tell Kiro the winner (name + ref number).</p>"
         + "\n".join(rows) + "</body></html>")
open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(index)
json.dump({"ravi_refs": [{k: v for k, v in r.items() if k != "file"} for r in ravi_refs],
           "macal_refs": [{k: v for k, v in r.items() if k != "file"} for r in macal_refs],
           "clips": rendered}, open(os.path.join(OUT, "ref_clone_index.json"), "w"),
          ensure_ascii=False, indent=2)

zip_path = "/kaggle/working/yalla_fluent_ref_clone.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk(OUT):
        for fn in files:
            fp = os.path.join(root, fn)
            z.write(fp, os.path.relpath(fp, OUT))

print(f"\nDONE. {len(rendered)} clones. Download: {zip_path}")
print(f"Ravi refs found: {len(ravi_refs)} | Macal refs found: {len(macal_refs)}")
print("Open ref_clone/index.html — pick the most authentic + natural ref per character.")
if not ravi_refs or not macal_refs:
    print("\n⚠️ Some accents had NO matching clips in the scanned window. Tell Kiro which "
          "came up empty — we widen the accent filter / try another CV config or corpus.")
