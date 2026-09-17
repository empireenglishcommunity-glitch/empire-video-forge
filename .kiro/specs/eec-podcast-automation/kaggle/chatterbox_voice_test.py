# ==========================================================================
# EEC "Two Worlds" — Chatterbox voice test (Kaggle GPU)
# --------------------------------------------------------------------------
# IMPORTANT: run this as TWO separate cells (the numpy pin + kernel restart
# avoids the "numpy.dtype size changed" crash on Kaggle's image).
#
# SETUP (right panel): Accelerator = GPU T4, Internet = ON.
#
#  CELL 1  -> paste, Run. It installs, pins numpy, and RESTARTS the kernel
#             (you'll see "kernel died/restarted" — that is EXPECTED/intended).
#  CELL 2  -> after the restart, paste + Run. Do NOT re-run Cell 1.
#  Then download the .mp3 files from the Output panel (/kaggle/working).
# ==========================================================================

# ==================== CELL 1 (install + restart) ==========================
# !pip install -q chatterbox-tts
# !pip install -q "numpy==1.26.4"
# import os; os._exit(0)     # forces a clean kernel restart so pinned numpy loads

# ==================== CELL 2 (generate — run after restart) ================
import torch, soundfile as sf, numpy as np, time
from chatterbox.tts import ChatterboxTTS

device = "cuda" if torch.cuda.is_available() else "cpu"
print("Device:", device, "| numpy:", np.__version__)
t0 = time.time()
model = ChatterboxTTS.from_pretrained(device=device)
print("Model loaded in", round(time.time() - t0, 1), "s")

# Real "Two Worlds" lines, native American English.
# exaggeration = emotional intensity (0.3-0.7), cfg_weight ~0.5
jobs = [
    ("macal_takeA.mp3",
     "Hey everyone, welcome back to Two Worlds. Today, we're going to make your English sound way more natural. Let's get into it.",
     0.5, 0.5),
    ("macal_takeB_energetic.mp3",
     "Hey everyone, welcome back to Two Worlds. Today, we're going to make your English sound way more natural. Let's get into it.",
     0.7, 0.4),
    ("nour_takeA.mp3",
     "Hi there! Don't worry if it feels hard at first. Stick with me, and you will get there. I promise.",
     0.5, 0.5),
    ("nour_takeB_warm.mp3",
     "Hi there! Don't worry if it feels hard at first. Stick with me, and you will get there. I promise.",
     0.6, 0.5),
    ("sample_paragraph.mp3",
     "So here's the thing about learning English. It's not about memorizing a thousand rules. "
     "It's about using the language every single day, making mistakes, and slowly getting better. "
     "That's exactly what we're going to do together, one real conversation at a time.",
     0.5, 0.5),
]
for fname, text, ex, cfg in jobs:
    t = time.time()
    wav = model.generate(text, exaggeration=ex, cfg_weight=cfg)
    sf.write(f"/kaggle/working/{fname}", wav.squeeze().cpu().numpy(), model.sr)
    print(f"{fname}: {len(wav.squeeze())/model.sr:.1f}s audio, gen {time.time()-t:.1f}s")

print("\nDONE. Download the .mp3 files from the Output panel (/kaggle/working) and send them back.")

# --- Optional: exact voice cloning from a ~10s reference clip (for later) ---
#   model.generate(text, audio_prompt_path="reference_voice.wav")
