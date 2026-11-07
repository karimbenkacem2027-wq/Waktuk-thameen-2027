from PIL import Image, ImageDraw, ImageFilter
import os, shutil

# Find the app icon deterministically. GitHub uploads may omit root-level assets,
# so fall back to the web app's bundled 512px icon.
CANDIDATES = [
    "icon.png",
    "www/icons/icon-512.png",
    "www/icons/icon-192.png",
]
SRC = next((p for p in CANDIDATES if os.path.isfile(p)), None)
if SRC is None:
    # Last-resort recursive search, excluding generated Android resources.
    for base, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "android"}]
        pngs = sorted(f for f in files if f.lower().endswith(".png"))
        if pngs:
            SRC = os.path.join(base, pngs[0])
            break
if SRC is None:
    raise FileNotFoundError(
        "No PNG app icon found. Add icon.png or www/icons/icon-512.png."
    )
RES = "android/app/src/main/res"
SIZES = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}

im = Image.open(SRC).convert("RGBA")
w, h = im.size

# 1) make the grey corners transparent
px = im.load()
c = int(w * 0.27)
for (x0, y0) in [(0, 0), (w - c, 0), (0, h - c), (w - c, h - c)]:
    for x in range(x0, x0 + c):
        for y in range(y0, y0 + c):
            r, g, b, a = px[x, y]
            if r > 95 and abs(r - g) < 14 and abs(g - b) < 14:
                px[x, y] = (0, 0, 0, 0)
alpha = im.getchannel("A").filter(ImageFilter.MinFilter(5))
im.putalpha(alpha)

# 2) crop to content box and make square on 1024 canvas
bbox = im.getchannel("A").getbbox()
im = im.crop(bbox)
side = max(im.size)
sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
sq.paste(im, ((side - im.width) // 2, (side - im.height) // 2))
master = sq.resize((1024, 1024), Image.LANCZOS)

def circle(img):
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).ellipse((0, 0, img.size[0] - 1, img.size[1] - 1), fill=255)
    out = img.copy()
    out.putalpha(Image.composite(img.getchannel("A"), Image.new("L", img.size, 0), m))
    return out

for d, s in SIZES.items():
    folder = f"{RES}/mipmap-{d}"
    os.makedirs(folder, exist_ok=True)
    small = master.resize((s, s), Image.LANCZOS)
    small.save(f"{folder}/ic_launcher.png")
    circle(small).save(f"{folder}/ic_launcher_round.png")
    small.save(f"{folder}/ic_launcher_foreground.png")

# 3) remove adaptive-icon definitions so the PNGs above are used everywhere
shutil.rmtree(f"{RES}/mipmap-anydpi-v26", ignore_errors=True)
print("icons done")
