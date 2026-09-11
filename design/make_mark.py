"""Cut the masthead mark out of the supplied artwork.

The supplied file (design/shield-source.png) is a JPEG re-saved as PNG: it carries
compression artefacts, and the shield sits on a blurred dark-green backdrop rather than a
transparent field. Masking the shield by colour does not survive that backdrop -- bright
artefacts scattered across it make a threshold leak, and the result is not something worth
shipping. So the shield is not cut out at all: it is cropped tight and shown in a rounded
tile, which is how it is used in the masthead and as the tab icon.

The crop is anchored on the mark's own cream face -- the biggest flat area in the artwork --
rather than on a bounding box of "bright pixels", which the artefacts inflate.

    python3 design/make_mark.py            # writes assets/img/mark.png + mark-180.png
"""
import os
from collections import deque

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SOURCE = os.path.join(HERE, "shield-source.png")

try:                                    # Pillow renamed the resampling constants
    RESAMPLE = Image.Resampling.LANCZOS
except AttributeError:                  # older Pillow
    RESAMPLE = Image.LANCZOS

# measured from the artwork: the cream face starts ~30% of the way down the shield, and the
# shield is at its widest at the shoulders, just above that face
CREAM = (231, 231, 207)
CREAM_TOL = 20
CREAM_TOP_FRACTION = 0.30
SHOULDER_WIDTH = 1.03     # shoulders a touch wider than the cream face
BREATHING_ROOM = 1.16     # square crop, 8% each side


def largest_cream_component(rgb):
    a = np.asarray(rgb).astype(np.int16)
    cream = np.abs(a - np.array(CREAM, np.int16)).max(axis=2) <= CREAM_TOL
    h, w = cream.shape
    seen = np.zeros((h, w), bool)
    best = []
    ys, xs = np.where(cream)
    for y0, x0 in zip(ys[::max(1, len(ys)//2000)].tolist(), xs[::max(1, len(xs)//2000)].tolist()):
        if seen[y0, x0]:
            continue
        q = deque([(y0, x0)])
        seen[y0, x0] = True
        comp = []
        while q:
            y, x = q.popleft()
            comp.append((y, x))
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and cream[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    q.append((ny, nx))
        if len(comp) > len(best):
            best = comp
    arr = np.array(best)
    return arr[:, 1].min(), arr[:, 1].max(), arr[:, 0].min(), arr[:, 0].max()


def main():
    im = Image.open(SOURCE).convert("RGB")
    x0, x1, y0, y1 = largest_cream_component(im)
    cw, ch = x1 - x0 + 1, y1 - y0 + 1

    shield_h = ch / (1 - CREAM_TOP_FRACTION)
    shield_top = y0 - CREAM_TOP_FRACTION * shield_h
    shield_w = cw * SHOULDER_WIDTH

    side = max(shield_w, shield_h) * BREATHING_ROOM
    cx = (x0 + x1) / 2
    left = cx - side / 2
    top = (shield_top + shield_top + shield_h) / 2 - side / 2

    W, H = im.size
    box = (max(0, int(left)), max(0, int(top)), min(W, int(left + side)), min(H, int(top + side)))
    crop = im.crop(box)
    print(f"cream face {cw}x{ch} at ({x0},{y0}) -> crop {box} ({crop.size[0]}x{crop.size[1]})")

    for size in (512, 180):
        out = os.path.join(REPO, "assets", "img", f"mark{'' if size == 512 else '-' + str(size)}.png")
        crop.resize((size, size), RESAMPLE).save(out)
        print("wrote", os.path.relpath(out, REPO))


main()
