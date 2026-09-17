# Chatterbox Voice Test on Kaggle (free GPU)

Goal: hear **Chatterbox** — the open model that beats ElevenLabs in ~65% of blind
tests — say our real "Two Worlds" lines in a **natural native-American** voice, using
Kaggle's **free GPU**. This is the quality test before we lock the English voice engine.

## Steps (≈10 minutes)
1. Go to **kaggle.com** → sign in (free account) → **Create → New Notebook**.
2. In the right-hand panel:
   - **Accelerator** → **GPU T4 x2** (or any GPU option).
   - **Internet** → **ON** (required to install + download the model).
3. Delete the default cell. Paste the **entire** contents of
   `chatterbox_voice_test.py` into one cell.
4. Click **Run All** (▶▶). First run takes a few minutes (installs + downloads model).
5. When it prints **DONE**, open the **Output** panel (right side, `/kaggle/working`).
   You'll see:
   - `macal_takeA.mp3`, `macal_takeB_energetic.mp3`
   - `nour_takeA.mp3`, `nour_takeB_warm.mp3`
   - `sample_paragraph.mp3`
6. **Download those .mp3 files** and send them back (or drop them in the Drive folder).

## What we're judging
- Does it sound **genuinely native-American and natural** (not robotic like Kokoro/Edge)?
- Which take/delivery fits **Macal** and **Nour**?

## If quality is great (expected)
We then design the **sustainable architecture** so you don't babysit Kaggle:
- Generate a **batch** of episodes' English audio in one GPU session, push to Drive.
- The server pipeline picks up ready audio → assembles video → auto-publishes.
- Arabic Coach stays on **Gemini (Kore)**. This is the split-engine plan.

## Optional next step: exact voice cloning
Chatterbox can lock an **exact** voice per character from a ~10s reference clip
(`audio_prompt_path=...`). If you want specific American voices for Macal/Nour/guests,
we provide reference clips and get perfectly consistent voices across every episode.

> Troubleshooting: if `chatterbox-tts` install errors on a dependency, add a cell:
> `!pip install -q chatterbox-tts --no-deps` then `!pip install -q librosa transformers accelerate safetensors`.
> If GPU shows as unavailable, re-check Accelerator = GPU in Settings and restart.
