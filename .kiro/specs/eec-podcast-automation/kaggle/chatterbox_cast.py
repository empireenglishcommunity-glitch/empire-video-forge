# ==========================================================================
# EEC "Two Worlds" — Chatterbox CHARACTER CAST (cloned voices)
# --------------------------------------------------------------------------
# Generates each character in their OWN voice by cloning a reference clip.
# Fixes the "everyone sounds male" issue (that was Chatterbox's default voice).
#
# CELL 1 (install + restart) — run first, wait for "Kernel Restarting" -> Ok:
#   !pip install -q chatterbox-tts
#   !pip uninstall -q -y torchvision
#   !pip install -q "numpy==1.26.4"
#   import os; os._exit(0)
#
# CELL 2 (this) — run after restart. It pulls the reference clips straight
# from the GitHub repo (no Kaggle Dataset needed) and clones each voice.
# ==========================================================================
import torch, soundfile as sf, numpy as np, urllib.request, os
from chatterbox.tts import ChatterboxTTS

device = "cuda" if torch.cuda.is_available() else "cpu"
print("Device:", device, "| numpy", np.__version__)
model = ChatterboxTTS.from_pretrained(device=device)

# --- fetch character reference clips from the repo (raw GitHub) ----------
RAW = ("https://raw.githubusercontent.com/empireenglishcommunity-glitch/"
       "empire-video-forge/podcast-voice-cast/.kiro/specs/eec-podcast-automation/voice-refs/")
os.makedirs("/kaggle/refs", exist_ok=True)
for r in ["macal_ref.wav", "nour_ref.wav", "guest_m1_ref.wav", "guest_f1_ref.wav"]:
    try:
        urllib.request.urlretrieve(RAW + r, f"/kaggle/refs/{r}")
        print("got ref:", r)
    except Exception as e:
        print("REF MISSING:", r, str(e)[:80])

# --- character -> reference + delivery settings --------------------------
cast = {
    "macal":   ("macal_ref.wav",   0.5, 0.5),
    "nour":    ("nour_ref.wav",    0.6, 0.5),   # a touch more expressive
    "guest_m": ("guest_m1_ref.wav",0.5, 0.5),
    "guest_f": ("guest_f1_ref.wav",0.5, 0.5),
}

# --- test lines per character (real Two Worlds tone) ---------------------
lines = [
    ("macal",   "macal_v3.mp3",   "Hey everyone, welcome back to Two Worlds. Today, we're going to make your English sound way more natural."),
    ("nour",    "nour_v3_FEMALE.mp3", "Hi there! Don't worry if it feels hard at first. Stick with me, and you will get there. I promise."),
    ("guest_m", "guest_m_v3.mp3", "Good morning. Please, have a seat. So, tell me a little about your experience."),
    ("guest_f", "guest_f_v3.mp3", "Welcome in! What can I get started for you today?"),
]

for who, fname, text in lines:
    ref, ex, cfg = cast[who]
    refpath = f"/kaggle/refs/{ref}"
    if os.path.exists(refpath):
        wav = model.generate(text, audio_prompt_path=refpath, exaggeration=ex, cfg_weight=cfg)
        tag = f"(cloned {who})"
    else:
        wav = model.generate(text, exaggeration=ex, cfg_weight=cfg)
        tag = "(DEFAULT male - ref missing)"
    sf.write(f"/kaggle/working/{fname}", wav.squeeze().cpu().numpy(), model.sr)
    print(f"wrote {fname} {tag}")

print("DONE - download the mp3s from the Output panel")
