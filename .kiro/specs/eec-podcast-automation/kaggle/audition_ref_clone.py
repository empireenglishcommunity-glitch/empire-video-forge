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

# ==========================================================================
# STEP 1 — SOURCE real reference clips from Common Voice (streaming) --------
# ==========================================================================
from datasets import load_dataset

def pull_refs(config, split, accent_needles, want, label):
    """Stream a CV config; keep clean clips whose accent matches any needle
    (or ANY clip if accent_needles is None, e.g. the Arabic-language config)."""
    picked = []
    print(f"\n[{label}] streaming {CV}:{config} ({split}) ...", flush=True)
    try:
        ds = load_dataset(CV, config, split=split, streaming=True)
    except Exception as e:
        print(f"  could not open {config}:{split} — {str(e)[:100]}", flush=True)
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
        a = row.get("audio")
        if not a or "array" not in a:
            continue
        arr = np.asarray(a["array"], dtype="float32"); sr = a["sampling_rate"]
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

# RAVI: English clips tagged an Indian / South-Asian accent
ravi_refs = pull_refs("en", "validated",
                      ["india", "indian", "south asia", "south-asia"], N_REF, "Ravi")

# MACAL: a real Arabic speaker's voice. First try en clips tagged an Arabic-region
# accent; if none, fall back to the Arabic-language config (genuine Arabic timbre,
# cloned cross-lingually to speak English).
macal_refs = pull_refs("en", "validated",
                       ["arab", "egypt", "middle east", "levant"], N_REF, "Macal")
if not macal_refs:
    macal_refs = pull_refs("ar", "validated", None, N_REF, "Macal")

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
    for attempt in range(1, 3):
        try:
            arr, _ = sf.read(ref["file"])
            prompt = clone.create_voice_clone_prompt(ref_audio=(arr, ref["sr"]),
                                                     ref_text=ref["text"] or None)
            wavs, sr = clone.generate_voice_clone(text=text, language=LANG, voice_clone_prompt=prompt)
            sf.write(out, wavs[0], sr)
            rendered.append({"name": name, "tag": tag, "file": os.path.basename(out), "note": note})
            print(f"  OK {tag}", flush=True); return
        except Exception as e:
            print(f"  .. {tag} attempt {attempt}: {str(e)[:80]}", flush=True); time.sleep(3)
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
