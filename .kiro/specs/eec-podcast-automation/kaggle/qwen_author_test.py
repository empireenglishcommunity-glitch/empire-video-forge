# ==========================================================================
# EEC "Two Worlds" — QWEN AUTHOR TEST (quota-free script engine on Kaggle GPU)
# --------------------------------------------------------------------------
# Escape Gemini's daily cap: run Qwen (top open Arabic LLM, Apache-2.0) on the
# SAME free Kaggle GPU we use for voices. Unlimited, no quota, ever. This test
# has Qwen write two acts of Episode 1 (a Coach Arabic break + an English story
# act) so we judge whether its bilingual creative writing matches/beats Gemini.
#
# Model: a T4-fittable Qwen instruct (AWQ 4-bit ~ fits 16GB; Kaggle has 2xT4 too).
# If VRAM is tight, use the smaller Qwen below (7B) — still strong at Arabic.
#
# Requires: Kaggle GPU = T4 (or 2xT4), Internet ON. Fresh notebook.
# --------------------------------------------------------------------------
# CELL 1 (install + restart):
#   !pip install -q "transformers>=4.45" accelerate autoawq
#   import os; os._exit(0)
#
# CELL 2 (this file) — after restart.
# ==========================================================================
import torch, json, traceback
from transformers import AutoModelForCausalLM, AutoTokenizer

# T4-fittable Qwen. AWQ 4-bit ~ 9-10GB. If it OOMs, switch MODEL to the 7B.
MODEL = "Qwen/Qwen2.5-14B-Instruct-AWQ"
FALLBACK = "Qwen/Qwen2.5-7B-Instruct"

def load(mid):
    tok = AutoTokenizer.from_pretrained(mid)
    model = AutoModelForCausalLM.from_pretrained(mid, torch_dtype="auto", device_map="auto")
    return tok, model

try:
    tok, model = load(MODEL); print("loaded", MODEL)
except Exception:
    print("primary failed, using fallback"); traceback.print_exc()
    tok, model = load(FALLBACK); print("loaded", FALLBACK)

def chat(prompt, max_new=1200, temp=0.9):
    msgs = [{"role": "user", "content": prompt}]
    text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    inp = tok(text, return_tensors="pt").to(model.device)
    out = model.generate(**inp, max_new_tokens=max_new, temperature=temp, do_sample=True,
                         top_p=0.9, repetition_penalty=1.05)
    return tok.decode(out[0][inp["input_ids"].shape[1]:], skip_special_tokens=True)

COMMON = (
'You are the head writer for "Two Worlds", a serialized bilingual English-learning '
'DRAMA podcast by Empire English Community for Egyptian/Arab learners. Mission: '
'LEARN WITH FUN. Warm, honest, encouraging; never "hack/secret/guaranteed". Coach '
'speaks EGYPTIAN Arabic; story is natural level-A2 English. Characters: Macal '
'(Egyptian learner-hero in Dubai), Nour (settled friend), Coach (Egyptian-Arabic '
'teacher, not in the story), guests (TaxiDriver/Barista/...). Return STRICT JSON only: '
'a list of {"section","speaker","lang","text"} lines. Coach lang="ar", story lang="en".'
)

# Test 1: an English story act (A2, taxi arrival)
p1 = COMMON + '\nWrite ACT 1 (12-16 lines): Macal arrives at Dubai airport, takes a taxi, small talk with the TaxiDriver in natural A2 English. A little funny, human. JSON list only.'
# Test 2: a Coach Arabic break (the hard bilingual case)
p2 = COMMON + '\nWrite a COACH BREAK (4-6 lines, Coach only, EGYPTIAN Arabic): unpack 2 English phrases from a taxi scene (e.g. "How long does it take?" and "Keep the change") + 1 common mistake. Warm teacher energy. JSON list only.'

for tag, p in [("QWEN_act1_en", p1), ("QWEN_coach_ar", p2)]:
    print("\n===== " + tag + " =====")
    try:
        out = chat(p)
        print(out)
        open("/kaggle/working/" + tag + ".txt", "w", encoding="utf-8").write(out)
    except Exception:
        traceback.print_exc()

print("\nDONE. Read QWEN_act1_en (English story) + QWEN_coach_ar (Egyptian Arabic).")
print("Judge: is Qwen's bilingual creative writing as good as / better than Gemini?")
print("If yes -> Qwen becomes our quota-free script engine (writes on the same GPU as voices).")
