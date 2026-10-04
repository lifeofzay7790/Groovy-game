"""Draw the 'Crafted' kit texture sheet: text banners, navy/gold rugs, gold metal and fringe.

usage: python crafted_textures.py
Writes LeafyManor/Models/Textures/T_LM_Kit_Crafted_{BaseColor.jpg, Normal.png, ORM.jpg} (4096 px atlas).
REGIONS (pixels, origin top-left) is shared with build_crafted.py, which maps the models' UVs onto it.
"""
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "Models", "Textures")
FONT = os.path.join(HERE, "fonts", "Cinzel.ttf")
SIZE = 4096
SS = 2                                    # supersampling for the gold masks

REGIONS = {                               # name: (x0, y0, x1, y1)
    "banner_plants": (0, 0, 1024, 2048),
    "banner_higher": (1024, 0, 2048, 2048),
    "rug_leaf": (2048, 0, 4096, 1882),    # 740 x 680 cm rug
    "rug_crown": (0, 2048, 2048, 4096),
    "gold": (2048, 2048, 3072, 3072),
    "fringe": (3072, 2048, 4096, 2560),
}
BANNER_SIDE = 3.0 / 3.7                  # fraction of the banner height where the V point starts (matches the mesh)

NAVY = np.array([20, 28, 74], float)
NAVY_DEEP = np.array([10, 14, 42], float)
GOLD = np.array([212, 165, 78], float)
GOLD_HI = np.array([250, 222, 150], float)
GOLD_LO = np.array([128, 86, 30], float)


# ---------------------------------------------------------------- shapes (drawn into an 'L' gold mask)
def leaflet(cx, cy, ang, length, width, serr=16):
    pts = []
    for side in (1, -1):
        rng = range(0, 61) if side == 1 else range(60, -1, -1)
        for k in rng:
            t = k / 60
            w = width * math.sin(math.pi * min(1, t * 1.05)) ** 0.75
            w *= 1 + 0.16 * ((t * serr) % 1 - 0.5) * (t > 0.08)
            x, y = t * length, side * w / 2
            pts.append((cx + x * math.cos(ang) - y * math.sin(ang), cy + x * math.sin(ang) + y * math.cos(ang)))
    return pts


def leaf(d, cx, cy, s, fill=255):
    """Seven-leaflet leaf (as on the master sheet), tip up, centred on (cx, cy), about s px tall."""
    base_y = cy + s * 0.32
    for a, ln, wd in ((-90, 0.62, 0.15), (-55, 0.55, 0.14), (-125, 0.55, 0.14), (-22, 0.42, 0.12), (-158, 0.42, 0.12),
                      (12, 0.26, 0.09), (168, 0.26, 0.09)):
        d.polygon(leaflet(cx, base_y, math.radians(a), ln * s, wd * s), fill=fill)
    d.line([(cx, base_y), (cx, base_y + s * 0.2)], fill=fill, width=max(2, int(s * 0.025)))


def crown(d, cx, cy, w, fill=255, cut=0):
    """Five-point crown, base centred at (cx, cy), w px wide."""
    h = w * 0.62
    band = [(cx - w / 2, cy), (cx + w / 2, cy), (cx + w / 2, cy - h * 0.22), (cx - w / 2, cy - h * 0.22)]
    d.polygon(band, fill=fill)
    pts = [(cx - w / 2, cy - h * 0.22)]
    for k in range(5):
        x = cx - w / 2 + w * (k + 0.5) / 5
        tip = h * (1.0 if k == 2 else 0.82 if k in (1, 3) else 0.7)
        pts += [(x - w * 0.06, cy - h * 0.5), (x, cy - tip), (x + w * 0.06, cy - h * 0.5)]
    pts += [(cx + w / 2, cy - h * 0.22)]
    d.polygon(pts, fill=fill)
    for k in range(5):
        x = cx - w / 2 + w * (k + 0.5) / 5
        tip = h * (1.0 if k == 2 else 0.82 if k in (1, 3) else 0.7)
        r = w * 0.045
        d.ellipse([x - r, cy - tip - r * 1.6, x + r, cy - tip + r * 0.4], fill=fill)
    for k in range(3):                    # jewels cut into the band
        x = cx - w * 0.25 + w * 0.25 * k
        r = w * 0.035
        d.ellipse([x - r, cy - h * 0.11 - r, x + r, cy - h * 0.11 + r], fill=cut)


def heart(d, cx, cy, s, fill=255):
    pts = []
    for k in range(120):
        t = 2 * math.pi * k / 120
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((cx + x * s / 34, cy - y * s / 34))
    d.polygon(pts, fill=fill)


def diamond(d, cx, cy, r, fill=255):
    d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=fill)


def outline(d, pts, width, fill=255):
    d.line(pts + [pts[0]], fill=fill, width=width, joint="curve")


def text_line(d, cx, y, txt, size, spacing=0.12, fill=255):
    f = ImageFont.truetype(FONT, size)
    f.set_variation_by_name("Bold")
    widths = [d.textlength(c, font=f) for c in txt]
    total = sum(widths) + spacing * size * (len(txt) - 1)
    x = cx - total / 2
    for c, w in zip(txt, widths):
        d.text((x, y), c, font=f, fill=fill)
        x += w + spacing * size


# ---------------------------------------------------------------- region designs (mask at SS x resolution)
def banner_mask(w, h, lines, emblem):
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    side = h * BANNER_SIDE
    for inset, width in ((w * 0.045, int(w * 0.018)), (w * 0.075, int(w * 0.006))):
        tip = h - inset * 1.6
        outline(d, [(inset, inset), (w - inset, inset), (w - inset, side - inset * 0.4), (w / 2, tip),
                    (inset, side - inset * 0.4)], width)
    crown(d, w / 2, h * 0.135, w * 0.34)
    d.line([(w * 0.2, h * 0.16), (w * 0.8, h * 0.16)], fill=255, width=int(w * 0.006))
    y = h * 0.19
    for txt, size in lines:
        text_line(d, w / 2, y, txt, int(size * w))
        y += size * w * 1.32
    diamond(d, w / 2, y + w * 0.02, w * 0.025)
    if emblem == "heart":
        heart(d, w / 2, y + w * 0.14, w * 0.13)
        y += w * 0.2
    leaf(d, w / 2, (y + w * 0.1 + side) / 2, w * 0.52)
    diamond(d, w / 2, h - w * 0.2, w * 0.03)
    return m


def border_leaves(d, x0, y0, x1, y1, band, step):
    """Small leaves along a rectangular band."""
    for (ax, ay, bx, by, ang) in ((x0, y0, x1, y0, 0), (x1, y0, x1, y1, 90), (x1, y1, x0, y1, 180), (x0, y1, x0, y0, 270)):
        n = max(2, int(math.hypot(bx - ax, by - ay) / step))
        for k in range(1, n):
            t = k / n
            cx, cy = ax + (bx - ax) * t, ay + (by - ay) * t
            if k % 2:
                diamond(d, cx, cy, band * 0.16)
            else:
                for s in (-1, 1):
                    a = math.radians(ang + 90 * s - 90)
                    d.polygon(leaflet(cx, cy, math.radians(ang) + s * 0.5 + math.pi * (s < 0), band * 0.42,
                                      band * 0.18), fill=255)


def rug_mask(w, h, centre):
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    s = min(w, h)
    for inset, width in ((s * 0.02, int(s * 0.012)), (s * 0.075, int(s * 0.006)), (s * 0.095, int(s * 0.004))):
        d.rectangle([inset, inset, w - inset, h - inset], outline=255, width=width)
    border_leaves(d, s * 0.047, s * 0.047, w - s * 0.047, h - s * 0.047, s * 0.055, s * 0.055)
    for cx, cy, sx, sy in ((s * 0.095, s * 0.095, 1, 1), (w - s * 0.095, s * 0.095, -1, 1),
                           (s * 0.095, h - s * 0.095, 1, -1), (w - s * 0.095, h - s * 0.095, -1, -1)):
        d.polygon(leaflet(cx, cy, math.atan2(sy, sx), s * 0.13, s * 0.045), fill=255)
        for a in (0.0, math.pi / 2):
            diamond(d, cx + sx * s * 0.05 * math.cos(a) + sx * s * 0.012, cy + sy * s * 0.05 * math.sin(a) + sy * s * 0.012,
                    s * 0.01)
    cx, cy = w / 2, h / 2
    for r, width in ((s * 0.3, int(s * 0.008)), (s * 0.275, int(s * 0.003))):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=255, width=width)
    for k in range(16):
        a = 2 * math.pi * k / 16
        rx, ry = cx + math.cos(a) * s * 0.33, cy + math.sin(a) * s * 0.33
        if k % 2:
            diamond(d, rx, ry, s * 0.012)
        else:
            d.polygon(leaflet(rx, ry, a, s * 0.08, s * 0.03), fill=255)
    if centre == "leaf":
        leaf(d, cx, cy - s * 0.02, s * 0.44)
    else:
        crown(d, cx, cy + s * 0.09, s * 0.36, cut=0)
        diamond(d, cx, cy + s * 0.16, s * 0.02)
    return m


def damask(w, h, step, seed):
    """Low-contrast tone-on-tone leaf lattice for the navy fabric."""
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    for j in range(-1, int(h / step) + 2):
        for i in range(-1, int(w / step) + 2):
            x = i * step + (step / 2 if j % 2 else 0)
            y = j * step
            leaf(d, x, y, step * 0.5, fill=255)
            diamond(d, x + step / 2, y, step * 0.05)
    return m


# ---------------------------------------------------------------- compose
def fabric(w, h, rng):
    """Navy velvet: soft noise + fine weave, values 0..255 float RGB."""
    n = rng.normal(0, 1, (h // 8 + 1, w // 8 + 1)).astype(np.float32)
    n = np.asarray(Image.fromarray(n).resize((w, h), Image.BICUBIC))
    weave = (np.sin(np.arange(w)[None, :] * 1.7) * np.sin(np.arange(h)[:, None] * 1.7)) * 0.5
    t = np.clip(0.5 + 0.12 * n + 0.04 * weave, 0, 1)[..., None]
    return NAVY_DEEP + (NAVY - NAVY_DEEP) * (0.6 + 0.8 * t)


def compose(mask_ss, w, h, rng, pattern=None):
    """mask (SS x) -> base RGB, height (for normals), metal/rough masks."""
    g = np.asarray(mask_ss.resize((w, h), Image.LANCZOS), np.float32) / 255
    base = fabric(w, h, rng)
    if pattern is not None:
        p = np.asarray(pattern.resize((w, h), Image.LANCZOS), np.float32)[..., None] / 255
        base = base * (1 - 0.3 * p) + (NAVY * 1.5) * 0.3 * p
    hgt = np.asarray(Image.fromarray((g * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2.5)), np.float32) / 255
    # gold shading: lighter on raised centres, darker at edges (embroidered thread look)
    shade = np.clip(hgt * 1.3, 0, 1)[..., None]
    gold = GOLD_LO + (GOLD - GOLD_LO) * np.clip(shade * 1.6, 0, 1) + (GOLD_HI - GOLD) * np.clip(shade - 0.6, 0, 1) * 2
    thread = 0.92 + 0.08 * np.sin(np.arange(w)[None, :] * 2.3 + np.arange(h)[:, None] * 2.3)[..., None]
    a = g[..., None]
    rgb = base * (1 - a) + gold * thread * a
    return rgb, hgt, g


def main():
    rng = np.random.default_rng(7)
    base = np.zeros((SIZE, SIZE, 3), np.float32)
    height = np.zeros((SIZE, SIZE), np.float32)
    metal = np.zeros((SIZE, SIZE), np.float32)
    rough = np.full((SIZE, SIZE), 0.85, np.float32)

    def put(name, rgb, hgt, met, rgh):
        x0, y0, x1, y1 = REGIONS[name]
        base[y0:y1, x0:x1] = rgb
        height[y0:y1, x0:x1] = hgt
        metal[y0:y1, x0:x1] = met
        rough[y0:y1, x0:x1] = rgh

    banners = {
        "banner_plants": ([("GOOD", 0.15), ("PLANTS", 0.15), ("BETTER", 0.15), ("PEOPLE", 0.15)], "leaf"),
        "banner_higher": ([("HIGHER", 0.15), ("TOGETHER", 0.115)], "heart"),
    }
    for name, (lines, emblem) in banners.items():
        x0, y0, x1, y1 = REGIONS[name]
        w, h = x1 - x0, y1 - y0
        m = banner_mask(w * SS, h * SS, lines, emblem)
        rgb, hgt, g = compose(m, w, h, rng, damask(w, h, w * 0.22, 1))
        put(name, rgb, hgt, g, 0.85 - 0.5 * g)
    for name, centre in (("rug_leaf", "leaf"), ("rug_crown", "crown")):
        x0, y0, x1, y1 = REGIONS[name]
        w, h = x1 - x0, y1 - y0
        m = rug_mask(w * SS, h * SS, centre)
        rgb, hgt, g = compose(m, w, h, rng, damask(w, h, min(w, h) * 0.09, 2))
        put(name, rgb, hgt, g * 0.6, 0.95 - 0.4 * g)
    # brushed gold for rods / finials
    x0, y0, x1, y1 = REGIONS["gold"]
    w, h = x1 - x0, y1 - y0
    streak = np.asarray(Image.fromarray(rng.normal(0, 1, (h, 8)).astype(np.float32)).resize((w, h), Image.BICUBIC))
    t = np.clip(0.55 + 0.25 * np.sin(np.linspace(0, 6 * math.pi, h))[:, None] + 0.06 * streak, 0, 1)[..., None]
    put("gold", GOLD_LO + (GOLD_HI - GOLD_LO) * t, np.zeros((h, w)), 1.0, 0.3)
    # fringe: vertical gold threads with dark gaps
    x0, y0, x1, y1 = REGIONS["fringe"]
    w, h = x1 - x0, y1 - y0
    xs = np.arange(w)[None, :]
    thread = (0.5 + 0.5 * np.cos(xs * 2 * math.pi / 14)) ** 0.6
    t = (thread * np.linspace(1.0, 0.75, h)[:, None])[..., None]
    put("fringe", GOLD_LO * 0.4 + (GOLD - GOLD_LO * 0.4) * t, thread[0][None, :].repeat(h, 0) * 0.6, 1.0, 0.4)

    Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).save(os.path.join(OUT, "T_LM_Kit_Crafted_BaseColor.jpg"), quality=92)
    orm = np.stack([np.full_like(rough, 255), rough * 255, metal * 255], -1)
    Image.fromarray(np.clip(orm, 0, 255).astype(np.uint8)).save(os.path.join(OUT, "T_LM_Kit_Crafted_ORM.jpg"), quality=92)
    # normal map from height (DirectX green: +Y down the image)
    gy, gx = np.gradient(height * 6.0)
    n = np.stack([-gx, gy, np.ones_like(gx)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    Image.fromarray(((n * 0.5 + 0.5) * 255).astype(np.uint8)).save(os.path.join(OUT, "T_LM_Kit_Crafted_Normal.png"), optimize=True)
    print("wrote T_LM_Kit_Crafted_{BaseColor.jpg, ORM.jpg, Normal.png}")


if __name__ == "__main__":
    main()
