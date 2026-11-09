"""Draw the ЯedactR app icon (palette: #312C51, #48426D, #F0C38E, #F1AA9B) -> packaging/redactr.ico"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
S = 512


def font(size):
    for f in ("seguibl.ttf", "segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle([16, 16, S - 16, S - 16], radius=110, fill="#312C51")
d.rounded_rectangle([64, 64, S - 64, S - 64], radius=80, fill="#48426D")
# redaction bars
d.rounded_rectangle([110, 330, 300, 368], radius=19, fill="#F0C38E")
d.rounded_rectangle([110, 390, 400, 428], radius=19, fill="#F1AA9B")
# the mirrored R
f = font(300)
text = "Я"
bbox = d.textbbox((0, 0), text, font=f)
w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
d.text(((S - w) / 2 - bbox[0], 92 - bbox[1]), text, font=f, fill="#F0C38E")

img.save(os.path.join(HERE, "redactr.ico"), sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
img.save(os.path.join(HERE, "redactr.png"))
print("icon written")
