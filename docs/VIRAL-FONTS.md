# Viral Caption Fonts — the rotating mix

> For high-volume posting, using one caption font on every clip looks
> templated. This sets up a **rotating pool of viral, Arabic-capable fonts**
> so each video gets a different look automatically. Proven end-to-end on
> real Arabic footage 2026-09-03.

## Why not "Foda Kufi" (the one the reference creator used)

The look the owner wanted came from **Foda Kufi** — a thick rounded Kufi
display font. But Foda Kufi is a **commercial font** ([MyFonts](https://www.myfonts.com/fonts/fo-da/foda-kufi/)),
and the "free" copies circulating on Arabic font sites are typically the paid
font redistributed without a licence. Using that in **monetised** content is a
real legal risk. So we use **free, SIL Open Font License (OFL) fonts that are
commercial-safe** and give the same bold/viral vibe. If the owner ever wants
the exact Foda Kufi, buy it and drop the `.ttf` into the fonts dir — the
rotation picks it up by name.

## The pool (all OFL / free / commercial-OK, all verified via libass)

Verified rendering Arabic correctly through libass (the real subtitle engine),
not just ffmpeg drawtext (which mis-shapes Arabic and gave false "tofu" in an
early preview — ignore drawtext for Arabic).

| Font | Vibe | Google Fonts source |
|---|---|---|
| **Tajawal Black** | Heaviest, most "viral hook" — closest to the Foda look | `ofl/tajawal/Tajawal-Black.ttf` |
| **Cairo** | Clean modern (variable, use Black/ExtraBold) | `ofl/cairo/Cairo[slnt,wght].ttf` |
| **Lalezar** | Rounded, chunky, playful | `ofl/lalezar/Lalezar-Regular.ttf` |
| **Lemonada** | Soft rounded, distinctive slant | `ofl/lemonada/Lemonada[wght].ttf` |
| **Changa** | Modern Kufi | `ofl/changa/Changa[wght].ttf` |
| **Reem Kufi** | Geometric Kufi | `ofl/reemkufi/ReemKufi[wght].ttf` |
| **Marhey** | Bold rounded, friendly | `ofl/marhey/Marhey[wght].ttf` |

## Install (on the Kaggle box, in the setup phase)

```bash
mkdir -p /usr/share/fonts/truetype/viral && cd /usr/share/fonts/truetype/viral
B='https://github.com/google/fonts/raw/main/ofl'
wget -q "$B/cairo/Cairo%5Bslnt,wght%5D.ttf"   -O Cairo.ttf
wget -q "$B/tajawal/Tajawal-Black.ttf"         -O Tajawal-Black.ttf
wget -q "$B/lalezar/Lalezar-Regular.ttf"       -O Lalezar.ttf
wget -q "$B/lemonada/Lemonada%5Bwght%5D.ttf"   -O Lemonada.ttf
wget -q "$B/changa/Changa%5Bwght%5D.ttf"       -O Changa.ttf
wget -q "$B/reemkufi/ReemKufi%5Bwght%5D.ttf"   -O ReemKufi.ttf
wget -q "$B/marhey/Marhey%5Bwght%5D.ttf"       -O Marhey.ttf
# also grab the matching OFL.txt licences into the same dir (compliance)
fc-cache -f
```

## Rotation (patch to OpenShorts `subtitles.py`)

`AUTO_CAPTION_STYLE` hardcodes one `font_name`. We make it dynamic: a pool +
a per-run picker. Because each `python main.py` run is a fresh process,
**per-run `random.choice` yields a different font per video** — exactly the
"varied feed" goal. `EMPIRE_FONT=<name>` forces a specific one.

```python
import random  # add near the top imports

VIRAL_FONT_POOL = [
    ("Tajawal Black", 52), ("Cairo", 52), ("Lalezar", 54),
    ("Lemonada", 50), ("Changa", 54), ("Reem Kufi", 54), ("Marhey", 52),
]

def _pick_viral_font():
    forced = os.environ.get("EMPIRE_FONT", "").strip()
    if forced:
        for name, size in VIRAL_FONT_POOL:
            if name.lower() == forced.lower():
                return name, size
        return forced, 52
    return random.choice(VIRAL_FONT_POOL)

_EMPIRE_FONT_NAME, _EMPIRE_FONT_SIZE = _pick_viral_font()
# ...then in AUTO_CAPTION_STYLE:
#   "font_name": _EMPIRE_FONT_NAME,
#   "font_size": _EMPIRE_FONT_SIZE,
```

Verified: 5 consecutive imports picked Lemonada, Reem Kufi, Cairo, Tajawal
Black, Lalezar — i.e. it rotates. A real render with `EMPIRE_FONT="Tajawal
Black"` produced the thick, yellow-highlight viral caption the owner approved.

## Style kept from the proven caption look

White text, **yellow (`#FFE500`) highlight on the active word**, heavy black
outline (`border_width` 6), "pop" karaoke effect, bottom alignment. Only the
font name + size rotate; the rest stays consistent so the brand still feels
coherent across the varied fonts.

## Compliance note

All seven are OFL — free for commercial use. Keep each font's `OFL.txt` in the
fonts directory. Do **not** substitute pirated "free Foda" copies; if the exact
Foda Kufi is wanted, purchase a licence.
