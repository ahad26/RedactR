"""Draw the start-up splash image -> packaging/splash.png
Palette: #312C51 midnight, #48426D dusk, #F0C38E gold, #F1AA9B coral.
The bottom strip is left empty: the live "Loading ..." text is drawn there at run time."""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 620, 340
MIDNIGHT, DUSK, GOLD, CORAL, INK, MUTED = "#312C51", "#48426D", "#F0C38E", "#F1AA9B", "#F7F4FB", "#C9C3E3"


def font(size, bold=False):
    names = (["seguibl.ttf", "segoeuib.ttf", "arialbd.ttf"] if bold else ["segoeui.ttf", "arial.ttf"])
    for f in names + ["DejaVuSans.ttf"]:
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


img = Image.new("RGB", (W, H), MIDNIGHT)
d = ImageDraw.Draw(img)

# card
d.rounded_rectangle([18, 18, W - 18, H - 62], radius=26, fill=DUSK)

# logo tile (same motif as the app icon)
d.rounded_rectangle([46, 50, 186, 190], radius=30, fill=MIDNIGHT)
fl = font(96, bold=True)
bb = d.textbbox((0, 0), "Я", font=fl)
d.text((116 - (bb[2] - bb[0]) / 2 - bb[0], 60 - bb[1] + 4), "Я", font=fl, fill=GOLD)
d.rounded_rectangle([68, 150, 130, 162], radius=6, fill=GOLD)
d.rounded_rectangle([68, 168, 160, 180], radius=6, fill=CORAL)

# name + tagline
fx, fy = 214, 62
ft = font(46, bold=True)
d.text((fx, fy), "Я", font=ft, fill=CORAL)
rx = fx + d.textlength("Я", font=ft)
d.text((rx, fy), "edactR", font=ft, fill=INK)
d.text((fx + 2, fy + 64), "Sanitize confidential documents", font=font(17), fill=MUTED)
d.text((fx + 2, fy + 88), "before you share them with AI", font=font(17), fill=MUTED)

# chips
chips = [("100% offline", GOLD), ("Reversible", CORAL), ("OCR built in", GOLD)]
cx = fx + 2
fc = font(13, bold=True)
for label, col in chips:
    tw = d.textlength(label, font=fc)
    d.rounded_rectangle([cx, 206, cx + tw + 24, 232], radius=13, fill=col)
    d.text((cx + 12, 210), label, font=fc, fill=MIDNIGHT)
    cx += tw + 34

# loading strip (text is written over this area at run time)
d.rounded_rectangle([34, H - 46, 40, H - 40], radius=3, fill=GOLD)   # status bullet next to the live text
d.line([34, H - 14, W - 34, H - 14], fill=DUSK, width=2)

img.save(os.path.join(HERE, "splash.png"))
print("splash written")
