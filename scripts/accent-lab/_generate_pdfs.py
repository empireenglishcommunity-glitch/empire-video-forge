# -*- coding: utf-8 -*-
"""Render Accent Lab scripts as PIL image pages -> multi-page PDF.
Uses raqm (PIL) for correct Arabic shaping + RTL. No reshaper/bidi needed."""
import os
from PIL import Image, ImageDraw, ImageFont
from accent_lab_scripts import EPISODES, PROD_NOTES, SERIES, BRAND

FDIR = "/projects/sandbox/fonts"
OUT = "/projects/sandbox/empire-video-forge/scripts/accent-lab"
os.makedirs(OUT, exist_ok=True)

# A4 at 150 DPI
W, H = 1240, 1754
MARGIN = 90
GOLD = (198, 157, 52)
DARK = (24, 24, 28)
GREY = (110, 110, 122)
BAND = (18, 18, 22)

BODY = FDIR + "/Tajawal-Bold.ttf"   # static, Arabic-capable
HEAD = FDIR + "/Cairo-Bold.ttf"     # variable but PIL renders it fine as raster


def strip_emoji(s):
    out = []
    for c in str(s):
        o = ord(c)
        # drop emoji/symbol/pictograph ranges + variation selectors + dingbats
        if (0x1F000 <= o <= 0x1FAFF) or (0x2600 <= o <= 0x27BF) or (0x2190 <= o <= 0x21FF) \
           or o in (0xFE0F, 0xFE0E, 0x2B50, 0x20E3) or (0x2B00 <= o <= 0x2BFF):
            continue
        out.append(c)
    return "".join(out).strip()


def font(path, size):
    return ImageFont.truetype(path, size)


class Page:
    def __init__(self):
        self.img = Image.new("RGB", (W, H), (255, 255, 255))
        self.d = ImageDraw.Draw(self.img)
        self.y = MARGIN

    def rtl(self, txt, size=30, path=BODY, fill=DARK, gap=14, x=None, center=False):
        txt = strip_emoji(txt)
        if not txt:
            self.y += gap
            return
        f = font(path, size)
        if center:
            self.d.text((W // 2, self.y), txt, font=f, fill=fill, anchor="ma",
                        direction="rtl", language="ar")
        else:
            self.d.text((W - MARGIN, self.y), txt, font=f, fill=fill, anchor="ra",
                        direction="rtl", language="ar")
        self.y += size + gap

    def ltr(self, txt, size=22, path=BODY, fill=GREY, gap=10):
        txt = strip_emoji(txt)
        f = font(path, size)
        self.d.text((MARGIN, self.y), txt, font=f, fill=fill, anchor="la")
        self.y += size + gap

    def section(self, label):
        self.y += 8
        self.rtl(label, size=34, path=HEAD, fill=GOLD, gap=8)
        self.d.line([(MARGIN, self.y), (W - MARGIN, self.y)], fill=GOLD, width=2)
        self.y += 18

    def header(self, text):
        self.d.rectangle([0, 0, W, 70], fill=BAND)
        f = font(HEAD, 34)
        self.d.text((W // 2, 18), strip_emoji(text), font=f, fill=GOLD, anchor="ma",
                    direction="rtl", language="ar")
        self.y = 110


def render_episode(pages, ep):
    p = Page()
    p.header(f"{SERIES}  |  {ep['topic']}")
    p.rtl(ep["title_ar"], size=40, path=HEAD, fill=DARK, gap=40)
    p.ltr("YouTube title:  " + strip_emoji(ep["yt_title"]), size=20, fill=GREY, gap=8)
    p.ltr("Topic:  " + ep["topic"], size=20, fill=GREY, gap=20)

    p.section("الهوك (0:00 - 0:03)")
    p.rtl(ep["hook"], size=38, path=HEAD, fill=DARK, gap=40)
    p.ltr(strip_emoji(ep["hook_en"]), size=20, fill=GREY, gap=16)

    p.section("المشكلة")
    for l in ep["problem"]:
        p.rtl(l, size=30)

    p.section("الحل + التقنية")
    for l in ep["fix"]:
        p.rtl(l, size=30)

    p.section("تمرين سريع")
    for l in ep["drill"]:
        p.rtl(l, size=34, path=HEAD, fill=DARK)

    p.section("دعوة للتفاعل (CTA)")
    p.rtl(ep["cta"], size=30)

    p.section("نص على الشاشة (On-screen)")
    for l in ep["onscreen"]:
        p.rtl("• " + l, size=26, fill=GREY)

    p.section("أزواج للتدريب (Minimal pairs)")
    p.ltr(ep["minimal_pairs"], size=26, fill=DARK, gap=10)
    pages.append(p.img)


def render_prod():
    p = Page()
    p.header("Accent Lab  |  ملاحظات التصوير")
    p.section("ملاحظات التصوير (لكل الحلقات)")
    for l in PROD_NOTES:
        p.rtl("• " + l, size=26, gap=16)
    p.y += 20
    p.rtl("Forged in Language. Crowned in Mastery.", size=28, path=HEAD, fill=GOLD, center=True)
    p.rtl(BRAND, size=24, fill=GREY, center=True)
    return p.img


def cover():
    img = Image.new("RGB", (W, H), BAND)
    d = ImageDraw.Draw(img)
    d.text((W // 2, H // 2 - 120), "Accent Lab", font=font(HEAD, 90), fill=GOLD, anchor="ma")
    d.text((W // 2, H // 2 - 10), strip_emoji("مختبر النطق"), font=font(HEAD, 70), fill=(240, 240, 245),
           anchor="ma", direction="rtl", language="ar")
    d.text((W // 2, H // 2 + 110), strip_emoji("سلسلة سكربتات — Empire English Community"),
           font=font(BODY, 34), fill=(200, 200, 210), anchor="ma", direction="rtl", language="ar")
    d.text((W // 2, H // 2 + 175), strip_emoji("6 حلقات · جاهزة للتصوير"),
           font=font(BODY, 30), fill=GOLD, anchor="ma", direction="rtl", language="ar")
    return img


# per-episode PDFs
for ep in EPISODES:
    pages = []
    render_episode(pages, ep)
    pages.append(render_prod())
    fn = f"{OUT}/AccentLab_{ep['num']:02d}_{ep['topic'].replace(' ', '').replace('/', '-')}.pdf"
    pages[0].save(fn, save_all=True, append_images=pages[1:], resolution=150.0)
    print("wrote", os.path.basename(fn))

# combined
allp = [cover()]
for ep in EPISODES:
    render_episode(allp, ep)
allp.append(render_prod())
allp[0].save(f"{OUT}/AccentLab_ALL_EPISODES.pdf", save_all=True, append_images=allp[1:], resolution=150.0)
print("wrote AccentLab_ALL_EPISODES.pdf  (pages:", len(allp), ")")
print("done ->", OUT)
