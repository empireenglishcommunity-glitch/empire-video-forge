# -*- coding: utf-8 -*-
"""Accent Lab — generate premium HTML per episode (+ combined) for Chrome->PDF.
Design: warm off-white, charcoal header, gold accents, card layout, RTL-correct.
No inline emojis (CSS symbols instead) to avoid tofu in headless-Chrome PDF."""
import os, html

OUT_HTML = "/projects/sandbox/al_html"
os.makedirs(OUT_HTML, exist_ok=True)

SERIES = "Accent Lab · مختبر النطق"
BRAND = "Empire English Community"
TAG = "Forged in Language. Crowned in Mastery."

# ---- content (upgraded: 30-35s, kinetic hooks, PVSS framing, research-backed) ----
EPISODES = [
    {
        "n": 1, "topic": "P vs B", "topic_ar": "حرف P",
        "title": "حرف الـ P — بتقول «Bebsi» ولا «Pepsi»؟",
        "yt": "بتقول Bebsi ولا Pepsi؟ سر حرف P",
        "hook": "«بيبسي»؟ لأ — الكلمة دي مالهاش وجود في الإنجليزي أصلًا!",
        "hook_move": "Kinetic open: hold a Pepsi can up to camera, shake your head \"no.\"",
        "problem": "في العربي مفيش حرف P خالص — عندنا الباء بس. فمخّك بيحوّل كل P لـ B من غير ما تحس.",
        "pairs_wrong": [("Bebsi","Pepsi"),("Bark","Park"),("Bencil","Pencil")],
        "fix": [
            "الفرق كله في <b>نفخة الهوا</b>: الـ P فيها نفخة، والـ B لأ.",
            "الإثبات في ثانية: حط <b>ورقة صغيّرة</b> قدام بقك.",
            "قول «B» والورقة ثابتة. قول «P» والورقة تترمي بالهوا.",
        ],
        "drill": ["Pepsi","Park","Pencil","People"],
        "cta": "قولّي في الكومنتات: كنت بتقول <b>Bebsi</b> ولا <b>Pepsi</b>؟",
        "cues": [("Bebsi","Pepsi"),("P = puff of air", None),("B = no air", None)],
        "minimal": "pin/bin · pack/back · cap/cab · rope/robe",
    },
    {
        "n": 2, "topic": "F vs V", "topic_ar": "حرف V",
        "title": "حرف الـ V — «فان» ولا «Van»؟",
        "yt": "«فان» ولا Van؟ سر حرف V",
        "hook": "لو بتقول «فان» بدل Van.. إنت مش لوحدك — بس النهاردة هنصلّحها في ٣٠ ثانية!",
        "hook_move": "Kinetic open: point at a van / write \"VAN\" big on screen, cross it out to \"FAN\".",
        "problem": "العربي فيه فاء بس مفيهوش V، فبنحوّل كل V لـ F من غير ما ناخد بالنا.",
        "pairs_wrong": [("Fan","Van"),("Seffen","Seven"),("Fery","Very")],
        "fix": [
            "نفس مكان الـ F بالظبط: سنانك على شفتك التحتانية.",
            "الفرق الوحيد: في الـ V الحبال الصوتية <b>بتهتز</b>.",
            "حط إيدك على رقبتك — لو حسّيت رجرجة، يبقى نطقت V صح.",
        ],
        "drill": ["Van","Very","Seven","Love"],
        "cta": "قولّي كلمة فيها V كنت بتغلط فيها زمان؟",
        "cues": [("Fan","Van"),("F = no buzz", None),("V = throat buzzes", None)],
        "minimal": "fan/van · fine/vine · few/view · leaf/leave",
    },
    {
        "n": 3, "topic": "TH", "topic_ar": "صوت TH",
        "title": "صوت الـ TH — «Think» مش «Sink»!",
        "yt": "Think مش Sink! سر صوت TH",
        "hook": "لو بتقول «سينك» بدل Think.. لسانك واقف في المكان الغلط تمامًا!",
        "hook_move": "Kinetic open: point to your mouth / show tongue between teeth in close-up.",
        "problem": "صوت TH مالوش مقابل في العربي، فبنستبدله بـ S أو T: Think تبقى Sink، وThree تبقى Sree.",
        "pairs_wrong": [("Sink","Think"),("Sree","Three"),("Tin","Thin")],
        "fix": [
            "السر: طرف لسانك يطلع <b>بين سنانك</b> — مش وراهم.",
            "TH بلا صوت (think): لسانك بره شوية وتنفخ هوا.",
            "TH بصوت (this): نفس الوضع + اهتزاز الحبال الصوتية.",
            "بص في المراية — لو مش شايف طرف لسانك، يبقى غلط.",
        ],
        "drill": ["Think","Three","This","That"],
        "cta": "قولّي: كنت بتنطق Think إزاي قبل الفيديو ده؟",
        "cues": [("Sink","Think"),("Tongue between teeth", None),("Mirror check", None)],
        "minimal": "think/sink · three/tree · thin/tin · they/day",
    },
    {
        "n": 4, "topic": "American R", "topic_ar": "الـ R الأمريكاني",
        "title": "الـ R الأمريكاني — مش الراء العربي!",
        "yt": "سر الـ R الأمريكاني (مش الراء العربي!)",
        "hook": "الـ R الأمريكاني مش الراء بتاعتنا — لو بتلفّها، إنت بتغلط!",
        "hook_move": "Kinetic open: exaggerate a rolled Arabic \"rrr\" then stop dead — \"لأ كده غلط\".",
        "problem": "الراء العربي بيترجّرج على سقف الحلق. الأمريكاني عكسه: لسانك ما بيلمسش أي حاجة!",
        "pairs_wrong": [("(rolled) Car","Car"),("(rolled) Red","Red"),("(rolled) Girl","Girl")],
        "fix": [
            "اسحب لسانك لورا وشيله لفوق شوية — <b>من غير ما يلمس</b> سقف بقك.",
            "الشفايف تتقرّب لبعض شوية (زي شكل الـ W الخفيف).",
            "مفيش رجرجة خالص — الصوت جوّه، من غير لمس.",
        ],
        "drill": ["Car","Red","Sorry","Girl"],
        "cta": "قولّي: أصعب كلمة فيها R بالنسبالك إيه؟",
        "cues": [("Arabic raa (rolled)","American R"),("Tongue touches nothing", None),("Lips like soft W", None)],
        "minimal": "car · red · sorry · girl · world · four",
    },
    {
        "n": 5, "topic": "Consonant clusters", "topic_ar": "الحروف الساكنة",
        "title": "ليه بتقول «iSchool» و«iStreet»؟",
        "yt": "بتقول iSchool ولا School؟ سر الحروف الساكنة",
        "hook": "لو بتقول «إسكول» بدل School.. إنت بتزوّد حرف مش موجود أصلًا!",
        "hook_move": "Kinetic open: type \"iSchool\" on screen, then delete the \"i\" with a swipe.",
        "problem": "العربي مبيبدأش كلمة بساكنين ورا بعض، فمخّك بيزوّد صوت «إ» قبلها عشان يسهّلها.",
        "pairs_wrong": [("iSchool","School"),("iStreet","Street"),("iSpeak","Speak")],
        "fix": [
            "ابدأ الكلمة بالصوتين <b>ملزوقين</b> — من غير أي «إ» قبلهم.",
            "قول الـ S قصيّرة جدًا وعدّي على اللي بعدها على طول: s-kool.",
            "ابدأ بطيء وزوّد السرعة بالتكرار.",
        ],
        "drill": ["School","Street","Speak","Stop"],
        "cta": "قولّي كلمة كنت بتزوّد فيها «إ» في الأول؟",
        "cues": [("iSchool","School"),("No \"i\" at the start", None),("s-kool not i-skool", None)],
        "minimal": "school · street · speak · stop · spring · student",
    },
    {
        "n": 6, "topic": "Short vs long vowels", "topic_ar": "حروف العلة",
        "title": "«Ship» ولا «Sheep»؟ الفرق اللي بيغيّر المعنى",
        "yt": "Ship ولا Sheep؟ الفرق اللي بيغيّر المعنى",
        "hook": "كلمة واحدة غلط ممكن تخلّيك تقول «خروف» وإنت قصدك «مركب»!",
        "hook_move": "Kinetic open: show a ship image, then a sheep image, side by side.",
        "problem": "في الإنجليزي فيه فرق بين حرف علة قصير وطويل — ولو نطقتهم زي بعض، المعنى بيتغيّر!",
        "pairs_wrong": [("Ship","Sheep"),("Bit","Beat"),("Live","Leave")],
        "fix": [
            "القصيرة /ɪ/: بق مرتخي وصوت سريع — ship, bit.",
            "الطويلة /iː/: بق مبتسم شوية وصوت أطول — sheep, beat.",
            "ابتسم وإنت بتقول الطويلة — هتفرق معاك فورًا.",
        ],
        "drill": ["Ship / Sheep","Bit / Beat","Live / Leave"],
        "cta": "قولّي: قدرت تسمع الفرق؟ اكتب Ship ولا Sheep؟",
        "cues": [("Ship","Sheep"),("short = relaxed mouth", None),("long = smile", None)],
        "minimal": "ship/sheep · bit/beat · live/leave · fit/feet",
    },
]

PROD_NOTES = [
    "أول ٣ ثواني هي كل حاجة: افتح على الهوك فورًا بحركة (kinetic) — مفيش مقدمة ولا لوجو في البداية.",
    "خلي البراند (اللوجو + اسم القناة) في <b>الآخر</b> مش الأول — عشان ما يكسرش الاستمرارية.",
    "الطول المثالي للتعليم: <b>٣٠–٤٠ ثانية</b>، والهدف نسبة مشاهدة +٨٠٪.",
    "اعرض التقنية الجسدية (ورقة / مراية / إيد على الرقبة) <b>قريّب من الكاميرا</b> — دي اللحظة اللي بتتشير وتترابط.",
    "احرق الكابشن العربي — أغلب الناس بتتفرّج من غير صوت.",
    "اقفل بجملة تربط للحلقة الجاية عشان يتابعوا السلسلة.",
    "لما ترفع الكليب على الدرايف، الـ pipeline هيكتب العنوان والوصف والهاشتاجات والكومنت تلقائيًا — تقدر تستبدل العنوان بالمقترح لكل حلقة.",
]

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&family=Inter:wght@400;600;700&display=swap');
@page { size:A4; margin:0; }
*{ margin:0; padding:0; box-sizing:border-box; }
:root{ --ink:#1a1c22; --ink-soft:#4a4e5a; --gold:#c69d34; --gold-deep:#a6801f;
  --bg:#faf9f6; --card:#fff; --line:#e7e3d8; --charcoal:#16171c; --en:#6b7280; }
html,body{ background:var(--bg); color:var(--ink); font-family:'Cairo',sans-serif; -webkit-font-smoothing:antialiased; }
.page{ width:210mm; min-height:297mm; padding:0 0 24mm; position:relative; page-break-after:always; }
.page:last-child{ page-break-after:auto; }
.band{ background:var(--charcoal); color:#fff; padding:20px 24mm 18px; display:flex; align-items:center; justify-content:space-between; }
.band .series{ font-weight:900; font-size:19px; color:var(--gold); }
.band .ep{ direction:ltr; font-family:'Inter',sans-serif; font-size:13px; color:#c9c9d2; font-weight:600; }
.goldrule{ height:4px; background:linear-gradient(90deg,var(--gold),var(--gold-deep)); }
.wrap{ padding:22px 24mm 0; }
.h1{ font-size:29px; font-weight:900; line-height:1.4; }
.meta{ direction:ltr; text-align:left; font-family:'Inter',sans-serif; font-size:12px; color:var(--en); margin-top:8px; }
.meta b{ color:var(--ink-soft); font-weight:600; }
.yt{ font-size:15px; color:var(--ink-soft); margin-top:3px; font-weight:600; }
.pill{ display:inline-block; direction:ltr; font-family:'Inter',sans-serif; font-size:11px; font-weight:700;
  color:var(--gold-deep); border:1.5px solid var(--gold); border-radius:20px; padding:3px 12px; margin-top:10px; }
.card{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:15px 20px; margin-top:14px; }
.card.hook{ border-color:var(--gold); background:linear-gradient(180deg,#fffdf5,#fff); }
.sec-h{ display:flex; align-items:center; gap:10px; margin-bottom:9px; }
.sec-h .dot{ width:9px; height:9px; border-radius:50%; background:var(--gold); flex:none; }
.sec-h .t{ font-size:16px; font-weight:900; }
.sec-h .time{ font-family:'Cairo','Inter',sans-serif; font-size:11px; font-weight:700; color:#fff;
  background:var(--gold-deep); border-radius:6px; padding:2px 9px; }
.line{ font-size:17px; line-height:1.95; }
.line.big{ font-size:22px; font-weight:700; line-height:1.6; }
.en{ direction:ltr; text-align:left; font-family:'Inter','Cairo',sans-serif; font-size:12.5px; color:var(--en); margin-top:8px; font-style:italic; }
ul.clean{ list-style:none; }
ul.clean li{ font-size:16px; line-height:2; padding-right:20px; position:relative; }
ul.clean li::before{ content:""; position:absolute; right:2px; top:12px; width:7px; height:7px; background:var(--gold); border-radius:2px; }
.chips{ direction:ltr; display:flex; flex-wrap:wrap; gap:8px; margin-top:4px; }
.chip{ font-family:'Inter',sans-serif; font-weight:700; font-size:14px; background:#f3efe2; color:var(--ink);
  border:1px solid var(--line); border-radius:8px; padding:5px 12px; }
.chip .arw{ display:inline-block; width:14px; height:8px; margin:0 6px; position:relative; }
.chip .arw::after{ content:""; position:absolute; left:0; top:3px; width:11px; height:2px; background:var(--ink-soft); }
.chip .arw::before{ content:""; position:absolute; right:0; top:0; width:7px; height:7px; border-top:2px solid var(--ink-soft); border-right:2px solid var(--ink-soft); transform:rotate(45deg); }
.chip .x{ color:#b23b2e; text-decoration:line-through; }
.chip .ok{ color:var(--gold-deep); } .chip .ar{ color:var(--ink); }
.cues{ display:flex; flex-wrap:wrap; gap:8px; }
.cue{ direction:ltr; font-family:'Inter','Cairo',sans-serif; font-size:13px; font-weight:600; background:var(--charcoal);
  color:#fff; border-radius:8px; padding:6px 12px; }
.cue .x{ color:#ff8a7a; text-decoration:line-through; } .cue .g{ color:var(--gold); }
.footer{ position:absolute; bottom:12mm; left:24mm; right:24mm; display:flex; justify-content:space-between;
  align-items:center; border-top:1px solid var(--line); padding-top:8px; }
.footer .brand{ direction:ltr; font-family:'Inter',sans-serif; font-size:11px; color:var(--en); font-weight:600; }
.footer .tag{ font-family:'Inter',sans-serif; font-size:11.5px; color:var(--gold-deep); font-weight:700; }
/* cover */
.cover{ background:var(--charcoal); color:#fff; height:297mm; display:flex; flex-direction:column;
  align-items:center; justify-content:center; text-align:center; page-break-after:always; }
.cover h1{ font-size:64px; font-weight:900; color:var(--gold); font-family:'Inter',sans-serif; letter-spacing:1px; }
.cover .ar{ font-size:44px; font-weight:900; margin-top:6px; }
.cover .sub{ font-size:20px; color:#c9c9d2; margin-top:22px; }
.cover .cnt{ font-size:16px; color:var(--gold); margin-top:10px; font-weight:700; }
.cover .line2{ width:120px; height:4px; background:var(--gold); margin:26px auto; border-radius:2px; }
.toc{ margin-top:20px; font-size:15px; color:#d7d7dd; line-height:2.1; }
"""

def esc(s): return s  # content is trusted (our own)

def wrong_chip(w, r):
    return f'<span class="chip"><span class="x">{esc(w)}</span><span class="arw"></span><span class="ok">{esc(r)}</span></span>'

def cue_box(a, b):
    if b is None:
        return f'<span class="cue">{esc(a)}</span>'
    return f'<span class="cue"><span class="x">{esc(a)}</span> &nbsp; <span class="g">{esc(b)}</span></span>'

def episode_html(ep):
    pairs = "".join(wrong_chip(w, r) for w, r in ep["pairs_wrong"])
    fixes = "".join(f"<li>{f}</li>" for f in ep["fix"])
    drill = "".join(f'<span class="chip">{esc(d)}</span>' for d in ep["drill"])
    cues = "".join(cue_box(a, b) for a, b in ep["cues"])
    return f"""
<div class="page">
  <div class="band"><div class="series">{SERIES}</div><div class="ep">Episode {ep['n']} / 6</div></div>
  <div class="goldrule"></div>
  <div class="wrap">
    <div class="h1">{ep['title']}</div>
    <div class="meta"><b>Suggested YouTube title (AR):</b></div>
    <div class="yt">{ep['yt']}</div>
    <div class="meta"><b>Format:</b> Short &middot; <b>Target:</b> 30–40s &middot; <b>Retention goal:</b> 80%+</div>
    <span class="pill">TOPIC: {ep['topic']} &middot; Pronunciation</span>

    <div class="card hook">
      <div class="sec-h"><span class="dot"></span><span class="t">الهوك — أول ٣ ثواني</span><span class="time">0:00–0:03</span></div>
      <div class="line big">{ep['hook']}</div>
      <div class="en">{ep['hook_move']}</div>
    </div>

    <div class="card">
      <div class="sec-h"><span class="dot"></span><span class="t">المشكلة</span></div>
      <div class="line">{ep['problem']}</div>
      <div class="chips">{pairs}</div>
    </div>

    <div class="card">
      <div class="sec-h"><span class="dot"></span><span class="t">الحل + التقنية</span></div>
      <ul class="clean">{fixes}</ul>
    </div>

    <div class="card">
      <div class="sec-h"><span class="dot"></span><span class="t">تمرين سريع</span><span class="time">قول معايا</span></div>
      <div class="chips">{drill}</div>
    </div>

    <div class="card">
      <div class="sec-h"><span class="dot"></span><span class="t">دعوة للتفاعل</span></div>
      <div class="line">{ep['cta']}</div>
    </div>

    <div class="card">
      <div class="sec-h"><span class="dot"></span><span class="t">نص على الشاشة</span></div>
      <div class="cues">{cues}</div>
    </div>

    <div class="card">
      <div class="sec-h"><span class="dot"></span><span class="t">أزواج للتدريب</span></div>
      <div class="line" style="direction:ltr;text-align:left;font-family:'Inter',sans-serif;font-size:15px;font-weight:600">{ep['minimal']}</div>
    </div>
  </div>
  <div class="footer"><span class="brand">{BRAND} — Accent Lab · Ep.{ep['n']}</span><span class="tag">{TAG}</span></div>
</div>
"""

def prod_html():
    notes = "".join(f"<li>{n}</li>" for n in PROD_NOTES)
    return f"""
<div class="page">
  <div class="band"><div class="series">{SERIES}</div><div class="ep">Production Notes</div></div>
  <div class="goldrule"></div>
  <div class="wrap">
    <div class="card">
      <div class="sec-h"><span class="dot"></span><span class="t">ملاحظات التصوير — لكل الحلقات</span></div>
      <ul class="clean" style="line-height:2.2">{notes}</ul>
    </div>
  </div>
  <div class="footer"><span class="brand">{BRAND} — Accent Lab</span><span class="tag">{TAG}</span></div>
</div>
"""

def cover_html():
    toc = "<br>".join(f"{e['n']}. {e['topic']} — {e['topic_ar']}" for e in EPISODES)
    return f"""
<div class="cover">
  <h1>Accent Lab</h1>
  <div class="ar">مختبر النطق</div>
  <div class="line2"></div>
  <div class="sub">سلسلة سكربتات النطق — {BRAND}</div>
  <div class="cnt">6 حلقات · جاهزة للتصوير</div>
  <div class="toc">{toc}</div>
</div>
"""

def doc(inner):
    return f"<!DOCTYPE html><html lang='ar' dir='rtl'><head><meta charset='UTF-8'><style>{CSS}</style></head><body>{inner}</body></html>"

# per-episode files
for ep in EPISODES:
    open(f"{OUT_HTML}/ep{ep['n']}.html", "w", encoding="utf-8").write(doc(episode_html(ep) + prod_html()))
# combined
combined = cover_html() + "".join(episode_html(e) for e in EPISODES) + prod_html()
open(f"{OUT_HTML}/all.html", "w", encoding="utf-8").write(doc(combined))
print("wrote", len(EPISODES), "episode HTML files + all.html ->", OUT_HTML)
