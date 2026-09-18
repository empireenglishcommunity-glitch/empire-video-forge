# ==========================================================================
# EEC "Two Worlds" — ENGLISH BATCH SYNTHESIZER (Chatterbox, cloned voices)
# --------------------------------------------------------------------------
# Turns committed episode scripts into per-line WAVs + a timeline, in each
# character's OWN cloned voice. This is the BATCH engine (run periodically on
# Kaggle GPU), not a live per-episode call — Kaggle sessions expire, so we
# process every pending episode in one pass and download the results.
#
# INPUT  (pulled from the repo, raw GitHub):
#   episodes/epNN/script.json      (the contract from gen_script.py)
#   voice-refs/*.wav               (locked reference clips, one per character)
# OUTPUT (in /kaggle/working/, download from the Output panel):
#   epNN/lineMMM_<speaker>.wav     (one WAV per ENGLISH line, in order)
#   epNN/timeline.en.json          (durations + order for the assembly step)
#
# The Arabic Coach lines are SKIPPED here — they are synthesized separately by
# synth_coach.py (Gemini "Kore") on the server. Both timelines are merged at
# the audio-assembly stage. This split is the locked, owner-approved design.
#
# --------------------------------------------------------------------------
# CELL 1 (install + restart) — run FIRST, wait for "Kernel Restarting" -> Ok:
#   !pip install -q chatterbox-tts
#   !pip uninstall -q -y torchvision
#   !pip install -q "numpy==1.26.4"
#   import os; os._exit(0)
#
# CELL 2 (this file) — run AFTER the kernel restarts.
# Requires: GPU accelerator = T4, Internet = ON.
# ==========================================================================
import os, json, urllib.request, urllib.error
import torch, soundfile as sf, numpy as np
from chatterbox.tts import ChatterboxTTS

# ---- config --------------------------------------------------------------
REPO_BRANCH = "main"   # refs + scripts are read from this branch of the repo
RAW = ("https://raw.githubusercontent.com/empireenglishcommunity-glitch/"
       f"empire-video-forge/{REPO_BRANCH}/.kiro/specs/eec-podcast-automation/")

# Which episodes to synthesize this run. Add episode numbers as scripts land.
EPISODES = [1]

# Locked reference clips (character -> ref filename in voice-refs/).
REFS = {
    "macal_ref.wav":    None,
    "nour_ref.wav":     None,
    "guest_m1_ref.wav": None,
    "guest_f1_ref.wav": None,
}

# Speaker -> (reference clip, exaggeration, cfg_weight).
# Recurring characters are explicit. Guests are resolved by role/gender below.
CAST = {
    "Macal": ("macal_ref.wav", 0.5, 0.5),
    "Nour":  ("nour_ref.wav",  0.6, 0.5),   # a touch more expressive
}
# Guest voice library — reused by role so the world feels populated without
# an infinite number of reference clips. A script may use any guest_* id
# (guest_m1, guest_driver, guest_barista, guest_f2, ...); we map it to one of
# these locked refs by a simple gender heuristic on the id.
GUEST_LIB = {
    "m": ("guest_m1_ref.wav", 0.5, 0.5),
    "f": ("guest_f1_ref.wav", 0.5, 0.5),
}
FEMALE_HINTS = ("_f", "female", "woman", "lady", "girl", "nour", "sara", "her",
                "barista", "receptionist", "hostess", "waitress")


def resolve_voice(speaker):
    """Map any script speaker id -> (ref filename, exaggeration, cfg_weight)."""
    if speaker in CAST:
        return CAST[speaker]
    s = speaker.lower()
    gender = "f" if any(h in s for h in FEMALE_HINTS) else "m"
    return GUEST_LIB[gender]


# ---- fetch reference clips ----------------------------------------------
os.makedirs("/kaggle/refs", exist_ok=True)
for ref in REFS:
    dst = f"/kaggle/refs/{ref}"
    try:
        urllib.request.urlretrieve(RAW + "voice-refs/" + ref, dst)
        REFS[ref] = dst
        print("got ref:", ref)
    except Exception as e:
        print("REF MISSING:", ref, str(e)[:80])


def ref_path(ref):
    return REFS.get(ref) if REFS.get(ref) and os.path.exists(REFS[ref]) else None


# ---- load model ----------------------------------------------------------
device = "cuda" if torch.cuda.is_available() else "cpu"
print("Device:", device, "| numpy", np.__version__)
if device != "cuda":
    print("WARNING: no GPU — enable T4 accelerator for usable speed/quality.")
model = ChatterboxTTS.from_pretrained(device=device)


def fetch_script(ep):
    url = RAW + f"episodes/ep{ep:02d}/script.json"
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def synth_episode(ep):
    print(f"\n=== Episode {ep:02d} ===")
    try:
        script = fetch_script(ep)
    except Exception as e:
        print(f"SKIP ep{ep:02d}: cannot fetch script ({str(e)[:80]})")
        return

    outdir = f"/kaggle/working/ep{ep:02d}"
    os.makedirs(outdir, exist_ok=True)
    timeline = {"episode": ep, "title": script.get("title"), "lang": "en", "lines": []}

    idx = 0
    for ln in script["lines"]:
        if ln.get("lang") != "en":
            continue  # Arabic Coach lines are handled by synth_coach.py
        idx += 1
        speaker = ln["speaker"]
        ref, ex, cfg = resolve_voice(speaker)
        rp = ref_path(ref)
        text = ln["text"].strip()

        # fail-soft: retry once, then skip the line (never abort the whole batch)
        wav = None
        for attempt in (1, 2):
            try:
                if rp:
                    wav = model.generate(text, audio_prompt_path=rp,
                                         exaggeration=ex, cfg_weight=cfg)
                else:
                    wav = model.generate(text, exaggeration=ex, cfg_weight=cfg)
                break
            except Exception as e:
                print(f"  line {idx} attempt {attempt} failed: {str(e)[:80]}")
        if wav is None:
            print(f"  line {idx} ({speaker}) SKIPPED after retries")
            continue

        audio = wav.squeeze().cpu().numpy()
        dur = round(len(audio) / model.sr, 3)
        fname = f"line{idx:03d}_{speaker}.wav"
        sf.write(os.path.join(outdir, fname), audio, model.sr)
        timeline["lines"].append({
            "idx": idx, "section": ln.get("section"), "speaker": speaker,
            "lang": "en", "ref": ref if rp else None,
            "file": fname, "sr": model.sr, "duration": dur,
            "text": text,
        })
        tag = f"cloned:{ref}" if rp else "DEFAULT(no ref)"
        print(f"  line {idx:>3} {speaker:14} {dur:>6}s  {tag}")

    with open(os.path.join(outdir, "timeline.en.json"), "w", encoding="utf-8") as f:
        json.dump(timeline, f, ensure_ascii=False, indent=2)
    total = round(sum(l["duration"] for l in timeline["lines"]), 1)
    print(f"  -> {len(timeline['lines'])} EN lines, ~{total}s -> {outdir}/timeline.en.json")


for ep in EPISODES:
    synth_episode(ep)

print("\nDONE. Download the ep* folders from the Output panel "
      "(WAVs + timeline.en.json), commit them to the repo, then run the "
      "server-side audio assembly.")
