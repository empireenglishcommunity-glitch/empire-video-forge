#!/usr/bin/env python3
"""
Render 4 distinct creative Arabic caption STYLES as preview stills (1080x1920),
on a clean dark cinematic gradient, using a real Arabic phrase. Lets the owner
pick a style before we animate it. RTL handled by raqm (direction=rtl).
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

OUT="/opt/eec-editor/work/caption_styles"; os.makedirs(OUT, exist_ok=True)
W,H=1080,1920
PHRASE="النظام بيعمل لك بوش"   # real words from the clip
ACTIVE="بوش"                    # the "current" highlighted word

FONTS={
 "tajawal":"/usr/share/fonts/truetype/eec/Tajawal-Black.ttf",
 "cairo":"/usr/share/fonts/truetype/eec/Cairo.ttf",
 "changa":"/usr/share/fonts/truetype/eec/Changa.ttf",
}
def F(name,size): return ImageFont.truetype(FONTS[name],size)

def bg():
    im=Image.new("RGB",(W,H)); px=im.load()
    for y in range(H):
        t=y/H; r=int(12+18*t); g=int(14+16*t); b=int(30+40*t)
        for x in range(W): px[x,y]=(r,g,b)
    return im

def rtl(d,xy,txt,font,fill,anchor="mm",stroke=0,sc=(0,0,0)):
    d.text(xy,txt,font=font,fill=fill,anchor=anchor,direction="rtl",language="ar",
           stroke_width=stroke,stroke_fill=sc)

def words(): return PHRASE.split()

# ---- Style 1: "Karaoke Pop" — white words, active word BIG gold with glow box
def style1():
    im=bg(); d=ImageDraw.Draw(im); f=F("tajawal",92); y=H//2
    ws=words(); 
    # measure total width (rtl: draw as one string but color active differently -> draw word by word positioned)
    # simple: draw whole line white, then redraw active bigger gold centered above
    rtl(d,(W//2,y),PHRASE,f,(255,255,255),stroke=8,sc=(0,0,0))
    # highlight pill behind active word (approx center)
    fa=F("tajawal",110)
    d.rounded_rectangle([W//2-230,y-260,W//2+230,y-120],40,fill=(245,197,24))
    rtl(d,(W//2,y-190),ACTIVE,fa,(10,10,10),stroke=0)
    im.save(f"{OUT}/style1_karaoke_pop.jpg","JPEG",quality=90)

# ---- Style 2: "Word-by-word reveal" — only 1-2 words, HUGE, centered, gold active
def style2():
    im=bg(); d=ImageDraw.Draw(im); f=F("changa",150)
    rtl(d,(W//2,H//2),ACTIVE,f,(245,197,24),stroke=10,sc=(0,0,0))
    # small context above
    fc=F("cairo",44); rtl(d,(W//2,H//2-180),"النظام بيعمل لك",fc,(180,190,210))
    im.save(f"{OUT}/style2_bigword.jpg","JPEG",quality=90)

# ---- Style 3: "Boxed subtitle" — modern box bg, clean, active word underlined gold
def style3():
    im=bg(); d=ImageDraw.Draw(im); f=F("cairo",78); y=H-520
    # rounded dark box
    d.rounded_rectangle([80,y-90,W-80,y+90],36,fill=(0,0,0,255))
    d.rounded_rectangle([80,y-90,W-80,y+90],36,outline=(245,197,24),width=5)
    rtl(d,(W//2,y),PHRASE,f,(255,255,255))
    # gold underline under active (approx right side for rtl first word)
    d.rectangle([W//2+120,y+50,W//2+320,y+60],fill=(245,197,24))
    im.save(f"{OUT}/style3_boxed.jpg","JPEG",quality=90)

# ---- Style 4: "Cinematic lower-third" — elegant, thin gold line, smaller refined text
def style4():
    im=bg(); d=ImageDraw.Draw(im); f=F("tajawal",72); y=H-360
    d.rectangle([0,y-120,W,y+120],fill=(0,0,0))
    d.rectangle([0,y-120,W,y-114],fill=(245,197,24))
    rtl(d,(W//2,y),PHRASE,f,(255,255,255))
    fc=F("cairo",38); d.text((W//2,y+90),"EMPIRE ENGLISH",font=fc,fill=(245,197,24),anchor="mm")
    im.save(f"{OUT}/style4_lowerthird.jpg","JPEG",quality=90)

for s in (style1,style2,style3,style4):
    try: s()
    except Exception as e: print("err",s.__name__,e)
print("done"); 
for f in sorted(os.listdir(OUT)): print(f)
