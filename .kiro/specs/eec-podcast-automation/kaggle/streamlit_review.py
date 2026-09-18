# ==========================================================================
# EEC "Two Worlds" — HUMAN-IN-THE-LOOP REVIEW DASHBOARD (Streamlit)
# --------------------------------------------------------------------------
# The owner's review remote-control. Runs INSIDE Colab/Kaggle next to the GPU
# (option B) so "Regenerate" is instant — no round-trip to a separate machine.
#
# Flow:
#   1. Reads manifest.json (the single source of truth) + the lineNNN_*.wav.
#   2. Lists every line grouped by section (cold_open, act1, coach_break1...).
#   3. Per line: play the clip, read/edit the text, see a status badge.
#   4. Edit text -> line goes STALE (pending). Hit "Regenerate this clip" ->
#      RegenEngine re-synthesizes ONLY that clip on the GPU, updates the manifest.
#   5. Hit "Re-assemble episode" -> ffmpeg stitches the whole episode from the
#      current clips (seconds, lossless concat + one loudnorm pass).
#
# Everything is driven by the manifest; this file holds NO synthesis logic of
# its own (that lives in regen_engine.py) and NO ordering logic (manifest_lib).
# ==========================================================================
import os, json, glob, subprocess, tempfile
import streamlit as st

import manifest_lib
from regen_engine import RegenEngine

# ---- config from env (the launcher notebook sets these) ------------------
WORK = os.environ.get("EEC_WORK", "/kaggle/working/ep01")
SCRIPT_PATH = os.environ.get("EEC_SCRIPT", "/kaggle/working/script.json")
CAST_PATH = os.environ.get("EEC_CAST", "/kaggle/working/cast.json")
LEX_PATH = os.environ.get("EEC_LEX", "/kaggle/working/lex.json")
REFS_DIR = os.environ.get("EEC_REFS", "/kaggle/refs")
MANIFEST_PATH = os.path.join(WORK, "manifest.json")
SR = 24000

STATUS_BADGE = {
    "rendered": "🟢 rendered",
    "pending": "🟡 needs regen",
    "failed": "🔴 failed",
}

st.set_page_config(page_title="Two Worlds — Review", layout="wide")


# ---- cached resources ----------------------------------------------------
@st.cache_resource(show_spinner=False)
def get_engine():
    script = json.load(open(SCRIPT_PATH, encoding="utf-8"))
    cast = json.load(open(CAST_PATH, encoding="utf-8"))
    lex = json.load(open(LEX_PATH, encoding="utf-8"))
    return RegenEngine(WORK, script, cast, lex, REFS_DIR), script


def load_manifest():
    _, script = get_engine()
    # reconcile against the script so edits made elsewhere flip stale clips
    return manifest_lib.load_or_init(MANIFEST_PATH, script)


def reassemble():
    """Lossless-concat all rendered clips in manifest order, one loudnorm pass.
    Runs entirely inside this environment (ffmpeg must be installed)."""
    manifest = load_manifest()
    placed = [e for e in manifest["lines"]
              if e["status"] == "rendered" and os.path.exists(os.path.join(WORK, e["file"]))]
    if not placed:
        return None, "no rendered clips to assemble"
    tmp = tempfile.mkdtemp(prefix="reasm_")
    # normalize each clip to a uniform rate/mono so concat -c copy is valid
    parts = []
    for i, e in enumerate(placed):
        norm = os.path.join(tmp, f"c{i:03d}.wav")
        subprocess.run(["ffmpeg", "-y", "-i", os.path.join(WORK, e["file"]),
                        "-ar", str(SR), "-ac", "1", norm],
                       check=True, capture_output=True)
        parts.append(norm)
    listf = os.path.join(tmp, "list.txt")
    with open(listf, "w") as f:
        for p in parts:
            f.write(f"file '{p}'\n")
    speech = os.path.join(tmp, "speech.wav")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listf,
                    "-ar", str(SR), "-ac", "1", speech], check=True, capture_output=True)
    out = os.path.join(WORK, f"ep{manifest.get('episode') or 1:02d}_audio_plain.m4a")
    subprocess.run(["ffmpeg", "-y", "-i", speech,
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000",
                    "-ar", "48000", "-c:a", "aac", "-b:a", "160k", out],
                   check=True, capture_output=True)
    return out, None


# ---- header + summary ----------------------------------------------------
manifest = load_manifest()
s = manifest_lib.summary(manifest)
st.title(f"🎙️ Two Worlds — Ep{manifest.get('episode') or '?'}: {manifest.get('title','')}")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total lines", s["total"])
c2.metric("🟢 Rendered", s["rendered"])
c3.metric("🟡 Needs regen", s["pending"])
c4.metric("Duration (min)", s["duration_min"])

if s["pending"]:
    st.warning(f"{s['pending']} line(s) need regeneration (edited or not yet rendered): "
               f"{s['pending_idx'][:20]}{' …' if len(s['pending_idx'])>20 else ''}")

# ---- top actions ---------------------------------------------------------
colA, colB = st.columns([1, 1])
with colA:
    if st.button("🔁 Regenerate ALL pending clips", use_container_width=True,
                 disabled=s["pending"] == 0):
        eng, _ = get_engine()
        prog = st.progress(0.0)
        pend = list(s["pending_idx"])
        for k, idx in enumerate(pend, 1):
            try:
                eng.regenerate(idx)   # re-roll current text
            except Exception as ex:
                st.error(f"line {idx} failed: {ex}")
            prog.progress(k / len(pend))
        st.success(f"Regenerated {len(pend)} clip(s).")
        st.rerun()
with colB:
    if st.button("🎬 Re-assemble episode (ffmpeg)", use_container_width=True):
        with st.spinner("Stitching episode…"):
            out, err = reassemble()
        if err:
            st.error(err)
        else:
            st.success(f"Assembled → {os.path.basename(out)}")
            st.audio(out)

st.divider()

# ---- section filter ------------------------------------------------------
sections = []
for e in manifest["lines"]:
    if e["section"] not in sections:
        sections.append(e["section"])
pick = st.multiselect("Show sections", sections, default=sections)
only_pending = st.checkbox("Show only lines needing regeneration", value=False)

# ---- per-line review rows ------------------------------------------------
for e in manifest["lines"]:
    if e["section"] not in pick:
        continue
    if only_pending and e["status"] == "rendered":
        continue

    idx = e["idx"]
    with st.container(border=True):
        head, badge = st.columns([4, 1])
        head.markdown(f"**#{idx:03d} · {e['speaker']}** "
                      f"`{e['lang']}` · _{e['section']}_ · {e.get('duration',0)}s")
        badge.markdown(STATUS_BADGE.get(e["status"], e["status"]))

        wav = os.path.join(WORK, e["file"])
        if os.path.exists(wav):
            st.audio(wav)
        else:
            st.caption("⚠️ clip file missing — regenerate to create it")

        new_text = st.text_area("Text", value=e["text"], key=f"txt_{idx}",
                                height=80, label_visibility="collapsed")
        edited = manifest_lib.text_hash(new_text) != e["text_hash"]
        b1, b2 = st.columns([1, 3])
        if b1.button("🎤 Regenerate this clip", key=f"regen_{idx}",
                     type="primary" if edited else "secondary"):
            eng, _ = get_engine()
            with st.spinner(f"Regenerating line {idx} on GPU…"):
                try:
                    r = eng.regenerate(idx, new_text if edited else None)
                    st.success(f"Done — {r['duration']}s")
                    st.rerun()
                except Exception as ex:
                    st.error(f"regen failed: {ex}")
        if edited:
            b2.info("Text changed — this clip is now stale. Regenerate to apply.")
