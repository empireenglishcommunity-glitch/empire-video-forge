# ==========================================================================
# EEC "Two Worlds" — SELECTIVE RE-GENERATION ENGINE
# --------------------------------------------------------------------------
# The GPU-side worker behind the Human-in-the-Loop review loop. Given a line's
# global idx, it re-synthesizes ONLY that one clip using the SAME engine, voice,
# and params recorded in the manifest — then updates the manifest in place
# (status -> rendered, new duration, fresh text_hash). No full re-synthesis.
#
# Mirrors the synth notebooks EXACTLY so a regenerated clip is indistinguishable
# from an original one:
#   * Arabic -> VoiceTut + shared Egyptian lexicon (add_lexicon) via prepare_ar()
#   * English -> Chatterbox multilingual (character ref + exaggeration/cfg)
#
# Models are loaded LAZILY and cached: the first regen of a language pays the
# load cost once, subsequent regens are fast. Both fit sequentially on a T4;
# if you only ever fix Arabic lines, Chatterbox is never loaded (saves VRAM).
#
# Used by: streamlit_review.py (the review UI) and as a CLI for scripted fixes.
# ==========================================================================
import os, re, json, traceback

# manifest_lib is fetched alongside this file in the launcher notebook
import manifest_lib


class RegenEngine:
    def __init__(self, work_dir, script, cast, lexicon, refs_dir="/kaggle/refs"):
        """work_dir: dir holding the lineNNN_*.wav + manifest.json
        script/cast/lexicon: the same JSON the synth pass loaded
        refs_dir: where English voice-reference wavs live"""
        self.work = work_dir
        self.script = script
        self.cast = cast
        self.lex = lexicon
        self.refs_dir = refs_dir
        self.manifest_path = os.path.join(work_dir, "manifest.json")

        # engines, loaded on demand
        self._vt = None          # VoiceTut (Arabic)
        self._cb = None          # Chatterbox (English)
        self._sf = None          # soundfile (imported lazily too)

        # role -> Arabic voice map (same resolution the synth used)
        self.role_voice = {}
        for name, spec in cast.get("cast", {}).items():
            if spec.get("engine") == "voicetut":
                self.role_voice[name] = spec.get("voice", "Sayed")
        for name, spec in cast.get("arabic_recurring_cast", {}).items():
            if isinstance(spec, dict) and spec.get("voice"):
                self.role_voice[name] = spec["voice"]
        self.default_ar_voice = "Sayed"
        self.en_cast = {n: s for n, s in cast.get("cast", {}).items()
                        if s.get("engine") == "chatterbox"}

    # ---- shared pronunciation brain (identical to the synth notebooks) ----
    def prepare_ar(self, text):
        lex = self.lex["lexicon"]
        for w in sorted(lex, key=len, reverse=True):
            text = re.sub(r"(?<!\w)" + re.escape(w) + r"(?!\w)", lex[w], text)
        return text

    # ---- lazy model loaders ----------------------------------------------
    @property
    def sf(self):
        if self._sf is None:
            import soundfile as sf
            self._sf = sf
        return self._sf

    def _load_voicetut(self):
        if self._vt is None:
            from voicetut_tts import VoiceTutTTS
            vt = VoiceTutTTS.from_pretrained("mohammedaly22/VoiceTut-TTS")
            try:
                vt.add_lexicon(self.lex["lexicon"])
                if self.lex.get("names_en_ar") and hasattr(vt, "add_names"):
                    vt.add_names(self.lex["names_en_ar"])
            except Exception:
                traceback.print_exc()
            self._vt = vt
        return self._vt

    def _load_chatterbox(self):
        if self._cb is None:
            import torch
            from chatterbox.mtl_tts import ChatterboxMultilingualTTS
            dev = "cuda" if torch.cuda.is_available() else "cpu"
            try:
                self._cb = ChatterboxMultilingualTTS.from_pretrained(device=dev, t3_model="v3")
            except TypeError:
                self._cb = ChatterboxMultilingualTTS.from_pretrained(device=dev)
        return self._cb

    def _en_ref(self, spec):
        r = spec.get("voice_ref")
        if not r:
            return None
        p = os.path.join(self.refs_dir, r)
        return p if os.path.exists(p) else None

    # ---- the core: regenerate ONE line -----------------------------------
    def regenerate(self, idx, new_text=None):
        """Re-synthesize the single line `idx`. If new_text is given it replaces
        the line's text (the edit-and-fix path); otherwise the current text is
        re-rolled (useful to re-try a bad render). Returns the updated manifest
        entry dict. Updates manifest.json (+ manifest.<pass>.json) on disk."""
        manifest = manifest_lib.load_or_init(self.manifest_path, self.script)
        entry = next((e for e in manifest["lines"] if e["idx"] == idx), None)
        if entry is None:
            raise ValueError(f"line idx {idx} not in manifest")

        text = new_text if new_text is not None else entry["text"]
        lang = entry["lang"]
        spk = entry["speaker"]
        out = os.path.join(self.work, entry["file"])
        params = dict(entry.get("params") or {})

        if lang == "ar":
            vt = self._load_voicetut()
            voice = entry.get("voice") or self.role_voice.get(spk, self.default_ar_voice)
            p = {"num_step": params.get("num_step", 64),
                 "guidance_scale": params.get("guidance_scale", 2.5),
                 "speed": params.get("speed", 1.0)}
            vt.synthesize(self.prepare_ar(text), speaker=voice, output=out, **p)
            engine, used_voice, used_params = "voicetut", voice, p
        elif lang == "en":
            cb = self._load_chatterbox()
            spec = self.en_cast.get(spk, {})
            ref = self._en_ref(spec)
            p = {"exaggeration": params.get("exaggeration", spec.get("exaggeration", 0.5)),
                 "cfg_weight": params.get("cfg_weight", spec.get("cfg_weight", 0.5))}
            w = cb.generate(text, language_id="en", audio_prompt_path=ref,
                            exaggeration=p["exaggeration"], cfg_weight=p["cfg_weight"])
            self.sf.write(out, w.squeeze().cpu().numpy(), cb.sr)
            engine, used_voice, used_params = "chatterbox", spec.get("voice_ref"), p
        else:
            raise ValueError(f"unsupported lang {lang!r} for line {idx}")

        # measure duration
        try:
            data, sr = self.sf.read(out)
            dur = round(len(data) / sr, 3)
        except Exception:
            dur = 0.0

        # persist: text (if edited), fresh hash, rendered status, new duration
        manifest_lib.mark(manifest, idx,
                          text=text, text_hash=manifest_lib.text_hash(text),
                          status="rendered", engine=engine, voice=used_voice,
                          params=used_params, duration=dur,
                          synth_pass=entry.get("synth_pass") or ("ar" if lang == "ar" else "en"))
        manifest_lib.save(manifest, self.manifest_path)
        # keep the pass-tagged copy in sync so a later re-download still merges right
        pass_tag = "ar" if lang == "ar" else "en"
        manifest_lib.save(manifest, os.path.join(self.work, f"manifest.{pass_tag}.json"))
        return next(e for e in manifest["lines"] if e["idx"] == idx)


# ------------------------------- CLI ---------------------------------------
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Regenerate one podcast line by idx")
    ap.add_argument("--work", required=True, help="dir with wavs + manifest.json")
    ap.add_argument("--idx", type=int, required=True)
    ap.add_argument("--text", default=None, help="new text (edit-and-fix); omit to re-roll")
    ap.add_argument("--script", required=True)
    ap.add_argument("--cast", required=True)
    ap.add_argument("--lexicon", required=True)
    ap.add_argument("--refs", default="/kaggle/refs")
    a = ap.parse_args()
    eng = RegenEngine(a.work, json.load(open(a.script, encoding="utf-8")),
                      json.load(open(a.cast, encoding="utf-8")),
                      json.load(open(a.lexicon, encoding="utf-8")), a.refs)
    e = eng.regenerate(a.idx, a.text)
    print(f"regenerated line {e['idx']} [{e['lang']}/{e['speaker']}] -> "
          f"{e['file']} ({e['duration']}s, status={e['status']})")
