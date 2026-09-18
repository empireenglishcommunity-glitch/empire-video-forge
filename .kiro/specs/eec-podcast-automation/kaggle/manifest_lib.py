# ==========================================================================
# EEC "Two Worlds" — SHARED MANIFEST LIBRARY
# --------------------------------------------------------------------------
# The single source of truth for episode assembly and Human-in-the-Loop
# selective re-generation. Imported by BOTH synth notebooks (ar / en) and by
# the server-side assembler and the Streamlit review app.
#
# WHY A MANIFEST (not just filenames / a per-pass timeline):
#   * The two synth passes run in SEPARATE Kaggle kernels and are downloaded as
#     two zips. A per-pass timeline.json gets CLOBBERED when the second zip
#     extracts over the first (this actually bit us on Ep1). The manifest is
#     built from the FULL script every time and MERGES per-slot, so combining
#     two partial manifests yields one complete, authoritative order.
#   * Filenames alone rely on lexicographic sort. Zero-padding (line001..line276)
#     fixes ordering, but the manifest is still the authority: it records idx,
#     speaker, lang, engine, exact synth params, a text fingerprint, and a
#     per-line status (rendered / pending / failed) — everything the assembler
#     and the review UI need.
#
# TEXT FINGERPRINT (text_hash): lets the review app detect when a line's text
# was edited and therefore its audio is stale and must be re-generated — the
# "fix one clip only, no full re-synth" loop (industry-standard, cf. Deepgram
# batch-TTS pipeline & fingerprint-cache audiobook generators).
# ==========================================================================
import os, re, json, hashlib

SCHEMA_VERSION = 2


def line_filename(idx, speaker):
    """Deterministic, zero-padded, sort-safe per-line filename.

    3-digit zero padding is enough for episodes up to 999 lines and keeps a
    plain lexicographic sort numerically correct (line002 before line010)."""
    safe = re.sub(r"[^A-Za-z0-9]+", "", str(speaker)) or "Speaker"
    return f"line{int(idx):03d}_{safe}.wav"


def text_hash(text):
    """Stable fingerprint of the *synthesized* text of a line.

    Normalizes whitespace so cosmetic edits don't churn, but any real wording
    change flips the hash -> the review UI marks that clip stale."""
    norm = re.sub(r"\s+", " ", (text or "").strip())
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]


def build_skeleton(script):
    """Build a fresh, all-'pending' manifest covering EVERY line in the script.

    Called at the start of every pass. Line indices are 1-based GLOBAL indices
    into script['lines'] — the same numbers baked into the zero-padded
    filenames and used by the assembler as the master order."""
    entries = []
    for i, ln in enumerate(script.get("lines", []), 1):
        lang = ln.get("lang")
        if lang not in ("ar", "en"):
            continue
        spk = ln["speaker"]
        entries.append({
            "idx": i,
            "section": ln.get("section"),
            "speaker": spk,
            "lang": lang,
            "file": line_filename(i, spk),
            "text": ln["text"],
            "text_hash": text_hash(ln["text"]),
            "status": "pending",       # pending -> rendered | failed
            "engine": None,            # voicetut | chatterbox (set on render)
            "voice": None,             # cast voice / reference used
            "params": {},              # exact synth params (for reproducible regen)
            "duration": 0.0,
            "synth_pass": None,        # ar | en
        })
    return {
        "schema": SCHEMA_VERSION,
        "episode": script.get("episode"),
        "title": script.get("title"),
        "phrase_of_episode": script.get("phrase_of_episode"),
        "shorts_highlight_hint": script.get("shorts_highlight_hint"),
        "lines": entries,
    }


def load_or_init(path, script):
    """Load an existing manifest and RECONCILE it against the current script,
    or create a fresh skeleton.

    SOURCE-OF-TRUTH RULE:
      Once a line exists in the manifest, the MANIFEST owns its text and render
      state — an edit made through the review app (mark(text=...) + re-render)
      is authoritative and is never reverted by the script. The script only
      SEEDS lines that the manifest has never seen (new/added lines) and
      supplies structural fields (section/speaker/lang) if the manifest lacks
      them. Re-generating an episode upstream is a separate, explicit action
      that resets the manifest (see reset_from_script); it does not silently
      fight the manifest here.

    This keeps the review loop stable: editing a line's text in the app and
    regenerating it makes the manifest the truth, and a later reload preserves
    exactly that — no spurious 'stale' flips.
    """
    skel = build_skeleton(script)
    if not os.path.exists(path):
        return skel
    try:
        prev = json.load(open(path, encoding="utf-8"))
    except Exception:
        return skel
    prev_by_idx = {e["idx"]: e for e in prev.get("lines", [])}
    for e in skel["lines"]:
        old = prev_by_idx.get(e["idx"])
        if not old:
            continue  # new line not in the manifest yet -> keep script seed (pending)
        # manifest wins for existing lines: carry EVERYTHING forward
        for k in ("status", "engine", "voice", "params", "duration", "synth_pass",
                  "text", "text_hash"):
            if k in old:
                e[k] = old[k]
    return skel


def reset_from_script(path, script):
    """Explicit upstream reset: rebuild the manifest from a freshly generated
    script, marking every line 'pending'. Call this (not load_or_init) when the
    episode SCRIPT was re-generated and you want the whole thing re-synthesized.
    Kept separate so a routine reload never wipes rendered work."""
    skel = build_skeleton(script)
    save(skel, path)
    return skel


def merge_pass(base, other):
    """Merge a partial manifest produced by ONE pass into a base manifest.

    Only slots the other pass actually touched (status != 'pending') overwrite
    the base — so combining the ar-pass and en-pass manifests never clobbers
    the opposite language's work. Idempotent and order-independent."""
    base_by_idx = {e["idx"]: e for e in base["lines"]}
    for e in other.get("lines", []):
        if e.get("status") in ("rendered", "failed") and e["idx"] in base_by_idx:
            base_by_idx[e["idx"]].update({
                "status": e["status"], "engine": e.get("engine"),
                "voice": e.get("voice"), "params": e.get("params", {}),
                "duration": e.get("duration", 0.0), "synth_pass": e.get("synth_pass"),
                "text_hash": e.get("text_hash"),
            })
    return base


def mark(manifest, idx, **fields):
    """Update one line's render record in place (called after synthesizing it)."""
    for e in manifest["lines"]:
        if e["idx"] == idx:
            e.update(fields)
            return e
    return None


def save(manifest, path):
    json.dump(manifest, open(path, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)


def summary(manifest):
    lines = manifest["lines"]
    rendered = [e for e in lines if e["status"] == "rendered"]
    failed = [e for e in lines if e["status"] == "failed"]
    pending = [e for e in lines if e["status"] == "pending"]
    total_dur = round(sum(e.get("duration", 0) for e in rendered), 1)
    return {
        "total": len(lines), "rendered": len(rendered),
        "failed": len(failed), "pending": len(pending),
        "duration_sec": total_dur, "duration_min": round(total_dur / 60, 1),
        "failed_idx": [e["idx"] for e in failed],
        "pending_idx": [e["idx"] for e in pending],
    }
