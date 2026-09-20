# ==========================================================================
# EEC "Yalla Fluent" — VOICE AUDITION notebook (Phase B, task B.4)
# --------------------------------------------------------------------------
# Renders CANDIDATE voices for every Season-1 English character using
# Qwen3-TTS **VoiceDesign** (invent-a-voice-from-text), so the owner (casting
# director) can listen and PICK one per character (B.6). The winning take
# becomes that character's canonical reference WAV for VoiceClone in production
# (Option B — "Voice Design then Clone", per qwen3-tts-verification.md).
#
# Output: /kaggle/working/audition/<Character>__<candidate>.wav  (+ a zip +
# an index.html contact-sheet with the description + line under each clip).
#
# This audition is ENGLISH ONLY. Mahmoud (Arabic) stays on VoiceTut — not here.
#
# ⚠️ HARDWARE: Kaggle GPU = **T4** (Turing, SM75), Internet ON, fresh notebook.
#    The T4 CANNOT run FlashAttention-2 (needs Ampere+). We load with
#    attn_implementation="sdpa" and DO NOT install flash-attn. (Verified: see
#    .kiro/specs/eec-podcast-automation/qwen3-tts-verification.md, V5.)
# --------------------------------------------------------------------------
# CELL 1 (install + restart) — copy EXACTLY, run, wait for the kernel to restart:
#
#   !pip install -q -U qwen-tts soundfile
#   import os; os._exit(0)
#
#   (Do NOT install flash-attn on a T4 — it will fail to build / won't load.)
#
# CELL 2 (this file) — after the restart. Just run it.
# ==========================================================================
import os, json, time, traceback, zipfile, html

# --- config ---------------------------------------------------------------
MODEL_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"   # the design model (B.1/V1)
LANG     = "English"
OUT      = "/kaggle/working/audition"
os.makedirs(OUT, exist_ok=True)

# How many candidates per character to render. The specs list up to 3-4; we
# render the first N (the 🎯 default first). Bump if the owner wants more choice.
N_CANDIDATES = 3

# ==========================================================================
# THE CAST (embedded so the notebook is self-contained — mirrors
# voice-design-specs.md, task B.2, as signed off in B.3). Each character:
#   line     = a REAL Season-1 line the candidate reads (so the owner hears it
#              in-context, in the character's own words)
#   voices   = ordered candidate VoiceDesign `instruct` descriptions
# Macal is auditioned as THREE stage voices (one identity, evolving). Every
# minor role (Official / Friend_M / Friend_F) gets its OWN voice (owner B.3).
# ==========================================================================
CAST = [
    # ---- Macal — 3 stages (the make-or-break; listen here first & hardest) --
    {"name": "Macal_S1", "line": "Hello, Mama. I am in Dubai. Everything is good. Everything is... very good.",
     "voices": [
        "Young adult male, late twenties, native Arabic speaker from Alexandria Egypt speaking English as a second language. Clear Egyptian L2 accent: lightly rolled/tapped r's, crisp fully-released T sounds, pure un-reduced vowels (little schwa), syllable-timed Arabic rhythm. Deliberate, slightly slow pacing with small hesitations; earnest, warm, a little nervous. Avoids contractions.",
        "Egyptian man, about 27, speaking careful English. Noticeable Arabic-transfer accent: tapped r, hard T and D, p drifting toward b, emphatic dark consonants, flat even stress. Speaks slowly and thoughtfully, as if translating in his head. Sincere and hopeful.",
        "Warm young Egyptian male voice speaking English with a mild, clear non-native accent and gentle hesitation. Understandable and likeable, slightly formal, avoids slang. Earnest tone.",
     ]},
    {"name": "Macal_S2", "line": "Okay. Okay, I'm coming. I mean - I'm on my way down right now.",
     "voices": [
        "The same young Egyptian man, now more fluent in English. Accent softening - some flap-T and linking appear, contractions used naturally, occasional quick self-correction. Faster, more relaxed rhythm but still a light Egyptian colouring. Growing confidence, warm.",
        "Young Egyptian male, upper-intermediate English. Mostly smooth with occasional first-language-transfer rhythm on longer sentences; comfortable, conversational, mildly accented. Optimistic and steady.",
        "Warm young Egyptian-accented male voice, clearly more confident than a beginner, natural contractions, easy pace, sincere.",
     ]},
    {"name": "Macal_S3", "line": "Okay, okay. So at Dune and Co., we were gonna miss a big deadline, right?",
     "voices": [
        "The same man, now confident and near-native in English. Rhythm close to General American - natural reductions like gonna and wanna, smooth linking, native-like stress and intonation - with only a faint trace of his Egyptian origin. Can joke, persuade, negotiate. Assured, warm, grounded.",
        "Young Egyptian-American-sounding male, fluent and expressive English, subtle warmth of a non-native origin nearly polished away. Relaxed, charismatic, emotional range from playful to sincere.",
        "Confident young male voice, near-native American English with a faint international warmth, smooth and persuasive.",
     ]},
    # ---- Nour — native General American (the taught target) ----------------
    {"name": "Nour", "line": "Macal? You look like you just saw a ghost. What happened?",
     "voices": [
        "Adult female, 29, born and raised in Chicago USA. Warm, confident, clear General American accent - natural flap-T (water sounds like wader), full linking and reductions, relaxed native rhythm. Encouraging, friendly, articulate; the kind of voice you'd trust to teach you.",
        "Confident young American woman, Midwestern General American accent, warm midrange, expressive and natural. Professional but approachable - a supportive colleague.",
        "Warm, bright American female voice, clear neutral US accent, easy conversational pace, genuine and reassuring.",
     ]},
    # ---- Tarek — polished Egyptian rival -----------------------------------
    {"name": "Tarek", "line": "Ah, of course you know the receptionist here too. Everyone loves Tarek.",
     "voices": [
        "Adult male, 30, Egyptian from Cairo, highly fluent and polished English with only a faint accent. Fast, articulate, charismatic and a little slick - a confident presenter who loves the room. Warm surface, competitive underneath.",
        "Confident Egyptian man, near-native English, quick smooth delivery, persuasive and charming, subtle Cairo colouring. Impressive but guarded.",
        "Smooth, energetic male voice, cosmopolitan lightly-accented English, salesman-charming, crisp and quick.",
     ]},
    # ---- Interviewer / Farida — Emirati Gulf English -----------------------
    {"name": "Interviewer_Farida", "line": "Dune and Company. We need your answer by Friday. Are you still with us?",
     "voices": [
        "Adult female, 40, Emirati from the Gulf, professional English with a light Gulf-Arabic accent - measured, precise, slightly clipped. Dry, composed, quietly authoritative; unimpressed by flattery. A senior executive who has heard every rehearsed answer.",
        "Composed Gulf-Arab businesswoman, clear accented English, calm and direct with a hint of dry humor. Professional, discerning.",
        "Mature female voice, subtle Middle-Eastern English accent, poised and measured, authoritative but not cold.",
     ]},
    # ---- Barista / Aisha — Filipino English --------------------------------
    {"name": "Barista_Aisha", "line": "Hello, sir. What can I get for you today?",
     "voices": [
        "Young female, 24, Filipina from Manila, friendly Filipino English accent - clear syllable-timed rhythm, crisp consonants, gently melodic intonation, occasional rising tone. Bright, upbeat, eager to please, slightly apologetic.",
        "Cheerful young Filipina, clear Filipino-accented English, warm and helpful, quick friendly pace.",
        "Bright young female voice, light Southeast-Asian English accent, sunny and polite service tone.",
     ]},
    # ---- Landlord / Qureshi — Pakistani English ----------------------------
    {"name": "Landlord_Qureshi", "line": "Macal, I'm not raising the rent because I want to. The building costs more now.",
     "voices": [
        "Older male, 55, Pakistani, speaking English with a Pakistani Urdu accent - retroflex t and d, rolled r, deliberate measured delivery, formal older-generation phrasing. Steady, mature, a bit stern but not unkind; a man used to being obeyed.",
        "Mature Pakistani man, clear South-Asian English accent, slow authoritative pace, formal and firm with underlying warmth.",
        "Older male voice, Urdu-accented English, grave and steady, patriarchal.",
     ]},
    # ---- TaxiDriver / Ravi — Indian English (Kerala) -----------------------
    {"name": "TaxiDriver_Ravi", "line": "Traffic is heavy today, my friend. But I know a short way.",
     "voices": [
        "Adult male, 42, Indian from Kerala, warm Indian English accent - retroflex consonants, rolled or tapped r, melodic sing-song intonation, syllable-timed rhythm, monophthong vowels. Friendly, chatty, easygoing working-man warmth.",
        "Middle-aged South-Indian man, clear Indian English accent, relaxed talkative and kind, gentle humor.",
        "Warm male voice, Indian English accent with Kerala colouring, easygoing and good-natured.",
     ]},
    # ---- Friend_F — minor female friend (its OWN voice, owner B.3) ---------
    {"name": "Friend_F", "line": "You double-booked my suite. I flew fourteen hours for this. Fourteen!",
     "voices": [
        "Young adult female, warm friendly English with a light international expat accent, natural conversational pace, upbeat and supportive peer.",
        "Bright young woman, neutral mildly-accented English, casual and warm.",
        "Friendly female voice, clear English, relaxed and encouraging.",
     ]},
    # ---- Official — minor role (its OWN voice, owner B.3) ------------------
    {"name": "Official", "line": "Mr. Macal? This is Dune and Company. Thank you for your voice note. It was good.",
     "voices": [
        "Adult male, composed formal English with a light Gulf accent, polite and businesslike, neutral authority.",
        "Mature male voice, professional accented English, courteous and efficient.",
        "Calm male voice, clear neutral English, formal and measured.",
     ]},
    # ---- Friend_M — minor male friend (its OWN voice, owner B.3) -----------
    {"name": "Friend_M", "line": "Bro, that was Tarek. He says the team is watching. Do not embarrass us.",
     "voices": [
        "Young adult male, casual friendly English with a light expat accent, easygoing peer tone.",
        "Relaxed young man, neutral mildly-accented English, warm and informal.",
        "Friendly young male voice, clear English, laid-back and familiar.",
     ]},
]

# ==========================================================================
# LOAD the VoiceDesign model (T4-safe) and render every candidate.
# ==========================================================================
import torch, soundfile as sf
from qwen_tts import Qwen3TTSModel

print("Loading Qwen3-TTS VoiceDesign (first load downloads a few GB — 2-4 min; "
      "do NOT interrupt)...", flush=True)
try:
    model = Qwen3TTSModel.from_pretrained(
        MODEL_ID, device_map="cuda:0", dtype=torch.bfloat16,
        attn_implementation="sdpa",     # T4 = Turing: sdpa, NOT flash_attention_2
    )
except Exception:
    # last-resort dtype fallback if bf16 op complains on T4
    print("bf16 load failed, retrying float16...", flush=True); traceback.print_exc()
    model = Qwen3TTSModel.from_pretrained(
        MODEL_ID, device_map="cuda:0", dtype=torch.float16,
        attn_implementation="sdpa",
    )
print("Model ready. Rendering audition clips...\n", flush=True)

rendered, SR = [], None
for role in CAST:
    name, line, voices = role["name"], role["line"], role["voices"][:N_CANDIDATES]
    for i, instruct in enumerate(voices, 1):
        tag = f"{name}__cand{i}"
        out = os.path.join(OUT, f"{tag}.wav")
        for attempt in range(1, 4):
            try:
                wavs, sr = model.generate_voice_design(text=line, language=LANG, instruct=instruct)
                sf.write(out, wavs[0], sr); SR = sr
                rendered.append({"name": name, "cand": i, "file": os.path.basename(out),
                                 "line": line, "instruct": instruct})
                print(f"  OK {tag}  (sr={sr})", flush=True)
                break
            except Exception as e:
                print(f"  .. {tag} attempt {attempt} failed: {str(e)[:80]}", flush=True)
                time.sleep(4 * attempt)
        else:
            print(f"  !! {tag} GAVE UP after 3 tries", flush=True)

print(f"\nRendered {len(rendered)} clips at sr={SR} into {OUT}", flush=True)

# ==========================================================================
# CONTACT SHEET (index.html) — clips grouped by character, each with its
# description + line, so the owner can listen and pick. + a zip of everything.
# ==========================================================================
groups = {}
for r in rendered:
    groups.setdefault(r["name"], []).append(r)

rows = []
for name, cands in groups.items():
    rows.append(f"<h2>{html.escape(name)}</h2>")
    rows.append(f"<p><em>Line:</em> &ldquo;{html.escape(cands[0]['line'])}&rdquo;</p>")
    for r in cands:
        rows.append(
            f"<div style='margin:8px 0;padding:8px;border:1px solid #ccc;border-radius:6px'>"
            f"<b>Candidate {r['cand']}</b><br>"
            f"<audio controls src='{html.escape(r['file'])}'></audio><br>"
            f"<small>{html.escape(r['instruct'])}</small></div>")
index = ("<html><head><meta charset='utf-8'><title>Yalla Fluent — voice audition</title>"
         "<style>body{font-family:sans-serif;max-width:820px;margin:24px auto;padding:0 12px}"
         "h1{color:#b8860b}h2{margin-top:28px;border-bottom:2px solid #b8860b}</style></head><body>"
         "<h1>Yalla Fluent — Season 1 voice audition</h1>"
         "<p>Listen and pick ONE candidate per character. Macal has 3 stages "
         "(S1/S2/S3) — approve the whole arc. Then tell Kiro your picks (B.6).</p>"
         + "\n".join(rows) + "</body></html>")
with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
    f.write(index)

zip_path = "/kaggle/working/yalla_fluent_audition.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for fn in sorted(os.listdir(OUT)):
        z.write(os.path.join(OUT, fn), fn)

# machine-readable index too (so B.7 can map picks -> descriptions)
with open(os.path.join(OUT, "audition_index.json"), "w", encoding="utf-8") as f:
    json.dump({"sr": SR, "model": MODEL_ID, "clips": rendered}, f, ensure_ascii=False, indent=2)

print(f"\nDONE. Download: {zip_path}")
print(f"Open audition/index.html to listen. {len(groups)} characters, {len(rendered)} clips.")
print("Then tell Kiro your pick per character (and Macal's 3-stage arc) — that's B.6.")
