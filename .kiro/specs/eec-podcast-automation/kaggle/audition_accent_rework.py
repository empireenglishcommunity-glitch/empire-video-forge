# ==========================================================================
# EEC "Yalla Fluent" — ACCENT-REWORK audition (Phase B, task B.6b)
# --------------------------------------------------------------------------
# The B.5 audition proved Qwen3-TTS *VoiceDesign* collapses a DESCRIBED accent
# to near-native American. Macal (Egyptian-English) and Ravi (Indian-English)
# had no accent. This notebook A/B/C-tests three ways to actually GET the accent,
# so the owner can pick per character (B.6c). All commercial-safe / ~$0 / in-stack.
#
# For MACAL (Egyptian-English) and RAVI (Indian-English), render:
#   (A) C1  — Qwen VoiceDesign as a *native Arabic / native Hindi speaker*
#             speaking English (accent from L1 timbre, not a description).
#   (B) PIPER — real accented English from the **L2-ARCTIC** Piper voice
#             (24 non-native speakers; Arabic + Hindi L1s), the accent baked in.
#   (C) PIPER->QWEN CLONE — clone the Piper accented clip THROUGH Qwen VoiceClone
#             (authentic accent + Qwen's audio quality). Usually the winner.
#
# L2-ARCTIC speaker -> L1 map (from the corpus docs):
#   Arabic: ABA(M) SKA(F) YBAA(M) ZHAA(F)   |  Hindi: ASI(M) RRBI(M) SVBI(F) TNI(F)
#
# ⚠️ LICENSING NOTE: the Piper voice is redistributed in rhasspy/piper-voices, but
# its training data (L2-ARCTIC) is research-licensed. Treat Piper output here as an
# AUDITION + as an ACCENT REFERENCE to clone from — final commercial use of a
# Piper-derived voice is CONFIRMED SEPARATELY before locking (B.7). The C1 route
# (Qwen-only) has no such caveat.
#
# ⚠️ HARDWARE: Kaggle GPU = T4, Internet ON, fresh notebook. No flash-attn (Turing).
# --------------------------------------------------------------------------
# CELL 1 (install + restart) — copy EXACTLY, run, wait for the kernel to restart:
#
#   !pip install -q -U qwen-tts soundfile piper-tts
#   import os; os._exit(0)
#
# CELL 2 (this file) — after the restart. Just run it.
# ==========================================================================
import os, json, time, traceback, zipfile, html, urllib.request, wave

OUT = "/kaggle/working/accent_rework"; os.makedirs(OUT, exist_ok=True)
LANG = "English"

# --- the two problem characters + a real Season-1 line each ----------------
# Macal: use his STAGE-1 line (strongest accent needed). Ravi: his taxi line.
TARGETS = {
    "Macal_S1": {
        "line": "Hello, Mama. I am in Dubai. Everything is good. Everything is... very good.",
        "l1": "Arabic",
        # C1 VoiceDesign prompts: native ARABIC speaker whose English carries the accent
        "c1": [
            "Adult male, late twenties, a native Arabic speaker from Alexandria Egypt. Arabic is his mother tongue; he is speaking English with a clear natural Egyptian-Arabic accent - pharyngeal warmth, tapped r, emphatic hard t and d, pure un-reduced vowels, syllable-timed rhythm. Earnest, warm, a little hesitant.",
            "A young Egyptian man, mother tongue Arabic, speaking English carefully and with an audible Arabic accent - the sounds of someone who thinks in Arabic. Deliberate pace, sincere.",
        ],
        # Piper L2-ARCTIC Arabic-L1 speakers to try
        "piper_speakers": ["ABA", "YBAA", "ZHAA", "SKA"],
    },
    "TaxiDriver_Ravi": {
        "line": "Traffic is heavy today, my friend. But I know a short way.",
        "l1": "Hindi",
        "c1": [
            "Adult male, early forties, a native Hindi speaker from Kerala India. Hindi/Malayalam is his mother tongue; he speaks English with a clear natural Indian accent - retroflex t and d, rolled r, melodic sing-song intonation, syllable-timed rhythm, monophthong vowels. Warm, chatty, easygoing.",
            "A middle-aged Indian man, mother tongue an Indian language, speaking English with a strong natural Indian accent and gentle sing-song melody. Friendly working-man warmth.",
        ],
        "piper_speakers": ["ASI", "RRBI", "TNI", "SVBI"],
    },
}
PIPER_MODEL = "en_US-l2arctic-medium"
PIPER_URL = ("https://huggingface.co/rhasspy/piper-voices/resolve/main/"
             "en/en_US/l2arctic/medium/")

rendered = []   # {name, method, tag, file, note}

# ==========================================================================
# STEP 1 — PIPER (real accented English from L2-ARCTIC) --------------------
# ==========================================================================
def dl(url, dst):
    if not os.path.exists(dst):
        urllib.request.urlretrieve(url, dst)
    return dst

print("Downloading Piper L2-ARCTIC voice...", flush=True)
onnx = dl(PIPER_URL + f"{PIPER_MODEL}.onnx", f"/kaggle/working/{PIPER_MODEL}.onnx")
cfg  = dl(PIPER_URL + f"{PIPER_MODEL}.onnx.json", f"/kaggle/working/{PIPER_MODEL}.onnx.json")

piper_clips = {}   # (name, speaker) -> wav path, for the clone step
try:
    from piper import PiperVoice, SynthesisConfig
    voice = PiperVoice.load(onnx, config_path=cfg)
    spk_map = voice.config.speaker_id_map or {}
    for name, spec in TARGETS.items():
        for spk in spec["piper_speakers"]:
            tag = f"{name}__B_piper_{spk}"
            out = os.path.join(OUT, f"{tag}.wav")
            try:
                sid = spk_map.get(spk)
                if sid is None:
                    print(f"  .. {tag}: speaker '{spk}' not in map, skipping", flush=True)
                    continue
                syn = SynthesisConfig(speaker_id=int(sid))
                with wave.open(out, "wb") as wf:
                    voice.synthesize_wav(spec["line"], wf, syn_config=syn)
                piper_clips[(name, spk)] = out
                rendered.append({"name": name, "method": "B_piper", "tag": tag,
                                 "file": os.path.basename(out),
                                 "note": f"Piper L2-ARCTIC speaker {spk} ({spec['l1']}-L1)"})
                print(f"  OK {tag}", flush=True)
            except Exception as e:
                print(f"  !! {tag}: {str(e)[:80]}", flush=True)
except Exception:
    print("Piper synth failed (will still do Qwen steps):", flush=True); traceback.print_exc()

# ==========================================================================
# STEP 2 — QWEN VoiceDesign (C1: native-L1-speaker-speaking-English) -------
# ==========================================================================
import torch, soundfile as sf
from qwen_tts import Qwen3TTSModel

def load_qwen(model_id):
    try:
        return Qwen3TTSModel.from_pretrained(model_id, device_map="cuda:0",
                    dtype=torch.bfloat16, attn_implementation="sdpa")
    except Exception:
        print("bf16 failed, trying fp16...", flush=True)
        return Qwen3TTSModel.from_pretrained(model_id, device_map="cuda:0",
                    dtype=torch.float16, attn_implementation="sdpa")

print("\nLoading Qwen3-TTS VoiceDesign...", flush=True)
design = load_qwen("Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign")
SR = None
c1_refs = {}   # name -> (wav_array, sr, ref_text) best C1 take, for the clone step
for name, spec in TARGETS.items():
    for i, instruct in enumerate(spec["c1"], 1):
        tag = f"{name}__A_c1_{i}"
        out = os.path.join(OUT, f"{tag}.wav")
        try:
            wavs, sr = design.generate_voice_design(text=spec["line"], language=LANG, instruct=instruct)
            sf.write(out, wavs[0], sr); SR = sr
            rendered.append({"name": name, "method": "A_c1", "tag": tag,
                             "file": os.path.basename(out),
                             "note": f"Qwen VoiceDesign as native {spec['l1']} speaker (cand {i})"})
            c1_refs.setdefault(name, (wavs[0], sr, spec["line"]))
            print(f"  OK {tag} (sr={sr})", flush=True)
        except Exception as e:
            print(f"  !! {tag}: {str(e)[:80]}", flush=True)

del design
try:
    import gc; gc.collect(); torch.cuda.empty_cache()
except Exception:
    pass

# ==========================================================================
# STEP 3 — QWEN VoiceClone of the ACCENTED refs (C: Piper->Qwen, and C1->Qwen)
# ==========================================================================
print("\nLoading Qwen3-TTS Base (clone)...", flush=True)
clone = load_qwen("Qwen/Qwen3-TTS-12Hz-1.7B-Base")

def clone_from(ref_audio, ref_text, text, tag, note, name):
    out = os.path.join(OUT, f"{tag}.wav")
    try:
        prompt = clone.create_voice_clone_prompt(ref_audio=ref_audio, ref_text=ref_text)
        wavs, sr = clone.generate_voice_clone(text=text, language=LANG, voice_clone_prompt=prompt)
        sf.write(out, wavs[0], sr)
        rendered.append({"name": name, "method": "C_clone", "tag": tag,
                         "file": os.path.basename(out), "note": note})
        print(f"  OK {tag}", flush=True); return True
    except Exception as e:
        print(f"  !! {tag}: {str(e)[:80]}", flush=True); return False

for name, spec in TARGETS.items():
    # C: clone the BEST Piper accented clip (authentic accent + Qwen quality)
    first_spk = spec["piper_speakers"][0]
    pc = piper_clips.get((name, first_spk))
    if pc:
        clone_from(pc, spec["line"],
                   f"{name}__C_piperclone_{first_spk}", spec["line"],
                   f"Qwen CLONE of Piper {first_spk} ({spec['l1']}-L1) — authentic accent + Qwen quality",
                   name)
    # C1-clone: clone the C1 VoiceDesign take (fully Qwen, no Piper license question)
    if name in c1_refs:
        arr, sr, rt = c1_refs[name]
        clone_from((arr, sr), rt, f"{name}__C_c1clone", spec["line"],
                   f"Qwen CLONE of the C1 native-{spec['l1']}-speaker design (fully in-stack)",
                   name)

# ==========================================================================
# CONTACT SHEET + zip -------------------------------------------------------
# ==========================================================================
order = {"A_c1": 0, "B_piper": 1, "C_clone": 2}
rendered.sort(key=lambda r: (r["name"], order.get(r["method"], 9), r["tag"]))
groups = {}
for r in rendered:
    groups.setdefault(r["name"], []).append(r)

rows = []
METHOD_LABEL = {"A_c1": "A — Qwen VoiceDesign (native-L1 speaker)",
                "B_piper": "B — Piper L2-ARCTIC (real accent)",
                "C_clone": "C — Qwen clone of an accented ref (usually best)"}
for name, items in groups.items():
    line = TARGETS[name]["line"]; l1 = TARGETS[name]["l1"]
    rows.append(f"<h2>{html.escape(name)} <small>({l1}-accented English)</small></h2>")
    rows.append(f"<p><em>Line:</em> &ldquo;{html.escape(line)}&rdquo;</p>")
    cur = None
    for r in items:
        if r["method"] != cur:
            cur = r["method"]; rows.append(f"<h4>{METHOD_LABEL.get(cur, cur)}</h4>")
        rows.append(f"<div style='margin:6px 0;padding:8px;border:1px solid #ccc;border-radius:6px'>"
                    f"<audio controls src='{html.escape(r['file'])}'></audio><br>"
                    f"<small>{html.escape(r['note'])}</small></div>")
index = ("<html><head><meta charset='utf-8'><title>Yalla Fluent — accent rework</title>"
         "<style>body{font-family:sans-serif;max-width:820px;margin:24px auto;padding:0 12px}"
         "h1{color:#b8860b}h2{margin-top:28px;border-bottom:2px solid #b8860b}h4{margin:14px 0 4px}</style>"
         "</head><body><h1>Yalla Fluent — Macal & Ravi accent rework</h1>"
         "<p>Compare the 3 approaches per character. For each, pick the one that best "
         "carries a REAL Egyptian (Macal) / Indian (Ravi) accent while sounding natural. "
         "Tell Kiro your pick (method + speaker/candidate).</p>"
         + "\n".join(rows) + "</body></html>")
open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(index)
json.dump({"sr": SR, "clips": rendered}, open(os.path.join(OUT, "rework_index.json"), "w"),
          ensure_ascii=False, indent=2)

zip_path = "/kaggle/working/yalla_fluent_accent_rework.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for fn in sorted(os.listdir(OUT)):
        z.write(os.path.join(OUT, fn), fn)

print(f"\nDONE. {len(rendered)} clips. Download: {zip_path}")
print("Open accent_rework/index.html — compare A vs B vs C for Macal & Ravi.")
print("Tell Kiro your pick per character (method + which speaker/candidate).")
