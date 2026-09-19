# Two Worlds — Kaggle synth notebooks (free GPU)

These are the **production** synthesizers. The cast + voice engines are LOCKED:
- **Arabic** → VoiceTut (Egyptian voices, Coach = "Sayed") through the shared
  Egyptian pronunciation lexicon.
- **English** → Chatterbox (each character's locked ~10s reference clip).

VoiceTut and Chatterbox clash on `transformers`/`torch` in one kernel, so the two
passes run as **separate notebooks**. Both write per-line WAVs + update the shared
`manifest.json` (the single source of truth), which the server assembler stitches.

## Files here
| File | Role |
|------|------|
| `synth_episode_ar.py` | Arabic pass — VoiceTut + shared lexicon, manifest-driven. |
| `synth_episode_en.py` | English pass — Chatterbox + character refs, manifest-driven. |
| `synth_arabic_qa.py`  | Arabic synth + ASR-QA that auto-flags words to add to the lexicon. |
| `manifest_lib.py`     | Shared source of truth (line order, per-line status, text hash). Fetched at runtime by the notebooks; a byte-identical copy lives in `pipeline/` for the server. |

## How to run (per pass)
1. **kaggle.com** → New Notebook → **Accelerator = GPU T4**, **Internet = ON**.
2. Paste the entire contents of `synth_episode_ar.py` (or `_en.py`) into one cell.
3. **Run All.** First run installs + downloads the model (a few minutes).
   The notebook fetches `script.json`, `cast.json`, `egyptian_lexicon.json`, the
   voice-refs, and `manifest_lib.py` from this repo
   (branch `main`) automatically.
4. When it finishes, download the `epNN/` folder from `/kaggle/working` (per-line
   WAVs + `manifest.<pass>.json`) — or push it to Drive `raw-audio`.
5. Run the other pass the same way. The server merges both manifests and assembles
   `epNN_audio_plain.m4a` via `pipeline/assemble_audio.py --plain`.

## Fixing a mispronounced Arabic word (permanent)
Add the word (fully voweled Egyptian form) to `pipeline/egyptian_lexicon.json`, then
re-run `synth_episode_ar.py` for the affected line(s). One fix → every cast voice
says it right, forever. `synth_arabic_qa.py` auto-flags candidate words during synth.

> Troubleshooting: if an install errors on a dependency, retry the pip line with
> `--no-deps` and then install the missing libs explicitly. If GPU shows
> unavailable, re-check Accelerator = GPU in Settings and restart the runtime.
