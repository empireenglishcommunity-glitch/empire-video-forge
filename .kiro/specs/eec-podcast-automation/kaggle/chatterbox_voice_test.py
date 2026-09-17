# ==========================================================================
# EEC "Two Worlds" — Chatterbox voice test (Kaggle GPU)
# --------------------------------------------------------------------------
# HOW TO USE (owner):
#  1. Go to kaggle.com -> Create -> New Notebook.
#  2. Settings (right panel): Accelerator = GPU T4 x2 (or any GPU).
#     Also turn Internet = ON (needed to pip install + download the model).
#  3. Paste this whole file into ONE cell (or upload as a notebook).
#  4. Run All. First run downloads the model (~a couple minutes).
#  5. When done, the audio files appear in the right panel under
#     "Output" (/kaggle/working). Download the .mp3 files and send them back.
#
# This generates native-American English samples for Macal + Nour using
# Chatterbox (Resemble AI) — the model that beats ElevenLabs in ~65% of
# blind tests. MIT-licensed (commercial-safe).
# ==========================================================================

# --- 1. Install (Kaggle has torch+CUDA preinstalled; we add chatterbox) ---
import subprocess, sys
def sh(cmd):
    print("»", cmd)
    subprocess.run(cmd, shell=True, check=False)

sh(f"{sys.executable} -m pip install -q chatterbox-tts soundfile")

# --- 2. Load the model on GPU ---
import torch, soundfile as sf, time
from chatterbox.tts import ChatterboxTTS

device = "cuda" if torch.cuda.is_available() else "cpu"
print("Device:", device)
t0 = time.time()
model = ChatterboxTTS.from_pretrained(device=device)
print("Model loaded in", round(time.time() - t0, 1), "s")

# --- 3. The real "Two Worlds" lines (native American English) ---
# exaggeration controls emotional intensity (0.3-0.7 typical); cfg_weight ~0.5
jobs = [
    # (filename, text, exaggeration, cfg_weight)  -- MACAL candidates (male-ish default voice)
    ("macal_takeA.mp3",
     "Hey everyone, welcome back to Two Worlds. Today, we're going to make your English sound way more natural. Let's get into it.",
     0.5, 0.5),
    ("macal_takeB_energetic.mp3",
     "Hey everyone, welcome back to Two Worlds. Today, we're going to make your English sound way more natural. Let's get into it.",
     0.7, 0.4),
    # NOUR candidates (warm, encouraging) -- Chatterbox default voice; we vary delivery
    ("nour_takeA.mp3",
     "Hi there! Don't worry if it feels hard at first. Stick with me, and you will get there. I promise.",
     0.5, 0.5),
    ("nour_takeB_warm.mp3",
     "Hi there! Don't worry if it feels hard at first. Stick with me, and you will get there. I promise.",
     0.6, 0.5),
    # A longer natural paragraph to judge flow / breath / realism
    ("sample_paragraph.mp3",
     "So here's the thing about learning English. It's not about memorizing a thousand rules. "
     "It's about using the language every single day, making mistakes, and slowly getting better. "
     "That's exactly what we're going to do together, one real conversation at a time.",
     0.5, 0.5),
]

for fname, text, ex, cfg in jobs:
    t = time.time()
    wav = model.generate(text, exaggeration=ex, cfg_weight=cfg)
    # chatterbox returns a torch tensor at model.sr
    import numpy as np
    audio = wav.squeeze().cpu().numpy()
    sf.write(f"/kaggle/working/{fname}", audio, model.sr)
    print(f"{fname}: {len(audio)/model.sr:.1f}s audio, generated in {time.time()-t:.1f}s")

print("\nDONE. Download the .mp3 files from the Output panel (/kaggle/working) and send them back.")

# --- NOTE on voice cloning (optional, for later) ---
# Chatterbox can clone a specific voice from a ~10s reference clip:
#   model.generate(text, audio_prompt_path="reference_voice.wav")
# If you have a preferred American voice sample, we can lock an exact voice
# per character (Macal / Nour / guests) for perfect consistency across episodes.
