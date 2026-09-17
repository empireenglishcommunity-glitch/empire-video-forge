# ==========================================================================
# EEC "Two Worlds" — Chatterbox v2: DISTINCT voices per character
# --------------------------------------------------------------------------
# The default Chatterbox voice is MALE — that's why Nour sounded male.
# Fix: give each character a short REFERENCE clip (~7-10s) and Chatterbox
# clones that voice. This also locks CONSISTENT voices across every episode.
#
# Run order (same as before): Cell 1 (install + restart) already done.
# This is the generate cell — run after the kernel restart.
#
# You provide reference clips as Kaggle "Input" datasets, OR the notebook
# downloads free reference voices (URLs below — replace with your picks).
# ==========================================================================
import torch, soundfile as sf, numpy as np, urllib.request, os
from chatterbox.tts import ChatterboxTTS

device = "cuda" if torch.cuda.is_available() else "cpu"
print("Device:", device, "| numpy", np.__version__)
model = ChatterboxTTS.from_pretrained(device=device)

os.makedirs("/kaggle/working/refs", exist_ok=True)

# --- REFERENCE VOICES ---------------------------------------------------
# Put a male ref for Macal and a female ref for Nour here.
# EITHER: upload clips as a Kaggle Dataset and point these paths at them,
# OR: set direct URLs to short (~10s) clean American voice clips.
REFS = {
    # "macal": "/kaggle/input/eec-voices/macal_ref.wav",
    # "nour":  "/kaggle/input/eec-voices/nour_ref.wav",
}

# If no refs provided, generate: Macal = default (male, you liked it),
# Nour = we still need a female ref. This block shows both paths.
jobs = [
    ("macal", "macal_v2.mp3",
     "Hey everyone, welcome back to Two Worlds. Today, we're going to make your English sound way more natural. Let's get into it.",
     0.5, 0.5),
    ("nour", "nour_v2_female.mp3",
     "Hi there! Don't worry if it feels hard at first. Stick with me, and you will get there. I promise.",
     0.5, 0.5),
]

for who, fname, text, ex, cfg in jobs:
    ref = REFS.get(who)
    if ref and os.path.exists(ref):
        wav = model.generate(text, audio_prompt_path=ref, exaggeration=ex, cfg_weight=cfg)
        tag = f"(cloned from {who} ref)"
    else:
        wav = model.generate(text, exaggeration=ex, cfg_weight=cfg)
        tag = "(DEFAULT voice — male; provide a ref to change)"
    sf.write(f"/kaggle/working/{fname}", wav.squeeze().cpu().numpy(), model.sr)
    print(f"wrote {fname} {tag}")

print("DONE")
