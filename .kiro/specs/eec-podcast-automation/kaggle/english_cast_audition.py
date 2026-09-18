# ==========================================================================
# EEC "Two Worlds" — ENGLISH CAST audition (Chatterbox) before the full run
# --------------------------------------------------------------------------
# We validated the Arabic cast thoroughly; we must do the same for ENGLISH
# before producing a 50-min episode. This renders a few REAL Ep1 lines per
# English voice so the owner confirms they sound right + distinct:
#   Macal (accented learner), Nour (clear/warm), and the guests (TaxiDriver/
#   Official/Landlord = male ref, Barista = female ref).
# If good -> we produce the full episode. If a voice is off -> we swap its ref.
#
# Requires: Kaggle GPU = T4, Internet ON. Fresh notebook.
# --------------------------------------------------------------------------
# CELL 1 (install + restart):
#   !pip install -q git+https://github.com/resemble-ai/chatterbox.git
#   !pip uninstall -q -y torchvision
#   !pip install -q "numpy==1.26.4"
#   import os; os._exit(0)
#
# CELL 2 (this file) — after restart.
# ==========================================================================
import os, urllib.request, traceback
import torch, soundfile as sf
from chatterbox.mtl_tts import ChatterboxMultilingualTTS

dev = "cuda" if torch.cuda.is_available() else "cpu"
try:
    cb = ChatterboxMultilingualTTS.from_pretrained(device=dev, t3_model="v3")
except TypeError:
    cb = ChatterboxMultilingualTTS.from_pretrained(device=dev)
print("Chatterbox loaded, sr", cb.sr)

RAW = ("https://raw.githubusercontent.com/empireenglishcommunity-glitch/"
       "empire-video-forge/podcast-v2-arabic-test/.kiro/specs/eec-podcast-automation/voice-refs/")
os.makedirs("/kaggle/refs", exist_ok=True)
def ref(name):
    p = "/kaggle/refs/" + name
    try:
        urllib.request.urlretrieve(RAW + name, p); return p
    except Exception as e:
        print("ref miss", name, str(e)[:50]); return None

# (character, ref clip, exaggeration, cfg, a real Ep1 line)
CAST = [
    ("Macal",      "macal_ref.wav",    0.5, 0.5, "I just need to reach the blue building on Zayed Road. Please give me two minutes to find my card."),
    ("Nour",       "nour_ref.wav",     0.6, 0.5, "Macal! Over here! You made it. Come on, let's get you settled in."),
    ("TaxiDriver", "guest_m1_ref.wav", 0.5, 0.5, "Look, man, I don't want to argue. But don't worry — it's a small city. You will be fine."),
    ("Official",   "guest_m1_ref.wav", 0.4, 0.5, "Welcome to Dubai, sir. The taxis are just outside those doors. Good luck!"),
    ("Landlord",   "guest_m1_ref.wav", 0.5, 0.5, "The rent is due on the first of each month. Any questions, you call me."),
    ("Barista",    "guest_f1_ref.wav", 0.6, 0.5, "Hi there! What can I get started for you today? Our coffee is the best in the city!"),
]

for name, rf, ex, cfg, line in CAST:
    r = ref(rf)
    try:
        w = cb.generate(line, language_id="en", audio_prompt_path=r,
                        exaggeration=ex, cfg_weight=cfg)
        out = "/kaggle/working/EN_" + name + ".wav"
        sf.write(out, w.squeeze().cpu().numpy(), cb.sr)
        print("wrote", out)
    except Exception:
        print(name, "FAILED:"); traceback.print_exc()

print("\nDONE - download EN_*.wav. Confirm each English voice sounds good + distinct:")
print("  Macal (learner), Nour (warm guide), TaxiDriver/Official/Landlord (male guests),")
print("  Barista (female). If all good -> we produce the full 50-min Episode 1.")
