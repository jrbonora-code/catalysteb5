#!/usr/bin/env python3
"""
Turn the photos in source-photos/ into the responsive files the site serves.

Run once after adding or swapping a photo:   python3 tools-process-images.py
Requires Pillow (pip install pillow). The Netlify build does NOT run this;
the processed files in static/img/ are committed to the repo.

Every output is center-cropped (around a focal point) to the aspect its slot
needs and written as WebP at several widths, plus one JPEG fallback.
Naming follows the catalystcd.com convention:  static/img/<slug>/<role>-<width>.webp
"""
import json, os
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "source-photos")
OUT = os.path.join(ROOT, "static", "img")

HERO = ((16, 9), [800, 1400, 2200])
CARD = ((4, 3), [400, 800, 1400])

# slug: (source file, {role: ((aspect), widths, focal_x, focal_y)})
PICKS = {
    "liberty":       ("pexels-niccolo-chiamori-37401699-16153075.jpg",
                      {"hero": (*HERO, .5, .32), "card": (*CARD, .45, .4)}),
    "flags":         ("pexels-thuanvo09-8175116.jpg",
                      {"hero": (*HERO, .5, .45), "card": (*CARD, .55, .45)}),
    "cranes":        ("pexels-aimee-14619056-6309085.jpg",
                      {"hero": (*HERO, .5, .4), "card": (*CARD, .3, .45)}),
    "earthwork":     ("pexels-robertkso-14484352.jpg",
                      {"hero": (*HERO, .5, .6), "card": (*CARD, .4, .6)}),
    "draw-review":   ("pexels-rdne-7821541.jpg",
                      {"hero": (*HERO, .45, .55), "card": (*CARD, .4, .55)}),
    "documents":     ("pexels-karola-g-7681200.jpg",
                      {"hero": (*HERO, .5, .55), "card": (*CARD, .5, .55)}),
    "family":        ("pexels-shotpot-7705708.jpg",
                      {"card": (*CARD, .5, .38)}),
    "main-street":   ("pexels-drew-anderson-1821361-6322070.jpg",
                      {"hero": (*HERO, .5, .42), "card": (*CARD, .55, .42)}),
    "capitol-day":   ("pexels-ben-kelsey-2155337245-38466093.jpg",
                      {"hero": (*HERO, .5, .42), "card": (*CARD, .5, .5)}),
    "capitol-night": ("pexels-jayson-gomes-1455414-4705378.jpg",
                      {"hero": (*HERO, .5, .4), "card": (*CARD, .5, .42)}),
}

# Deck thumbnails and portraits are already small, so they are emitted at
# their native size only.
DECK = os.path.join(SRC, "deck")
TEAM = os.path.join(SRC, "team")


def portrait_bw(im):
    """Black and white with matched tone, so portraits shot in different light
    read as a set: grayscale, clip 0.5% at each end, then pull the mean to a
    common mid-tone."""
    from PIL import ImageOps, ImageStat
    g = ImageOps.autocontrast(ImageOps.grayscale(im), cutoff=0.5)
    mean = ImageStat.Stat(g).mean[0] / 255
    target = 0.47
    if 0.02 < mean < 0.98:
        import math
        gamma = math.log(target) / math.log(mean)
        g = g.point(lambda v: round(255 * (v / 255) ** gamma))
    return g.convert("RGB")


def crop(im, aspect, fx, fy):
    w, h = im.size
    aw, ah = aspect
    target = aw / ah
    if w / h > target:
        nw, nh = int(h * target), h
    else:
        nw, nh = w, int(w / target)
    x = min(max(int(fx * w - nw / 2), 0), w - nw)
    y = min(max(int(fy * h - nh / 2), 0), h - nh)
    return im.crop((x, y, x + nw, y + nh))


def save_set(im, folder, role, widths):
    os.makedirs(folder, exist_ok=True)
    done = []
    for wd in widths:
        if wd > im.size[0]:
            continue
        r = im.resize((wd, round(wd * im.size[1] / im.size[0])), Image.LANCZOS)
        r.save(os.path.join(folder, f"{role}-{wd}.webp"), "WEBP", quality=80, method=6)
        done.append(wd)
    if not done:  # source narrower than every requested width
        wd = im.size[0]
        im.save(os.path.join(folder, f"{role}-{wd}.webp"), "WEBP", quality=82, method=6)
        done.append(wd)
    fb = done[-1]
    im.resize((fb, round(fb * im.size[1] / im.size[0])), Image.LANCZOS).save(
        os.path.join(folder, f"{role}-{fb}.jpg"), "JPEG", quality=82, optimize=True, progressive=True)
    return {"widths": done, "fallback": fb}


def main():
    manifest = {}
    for slug, (fname, roles) in PICKS.items():
        im = Image.open(os.path.join(SRC, fname)).convert("RGB")
        manifest[slug] = {}
        for role, (aspect, widths, fx, fy) in roles.items():
            c = crop(im, aspect, fx, fy)
            m = save_set(c, os.path.join(OUT, slug), role, widths)
            m["source"] = fname
            manifest[slug][role] = m

    # Team portraits: black and white, levels matched, cropped to the 4:5 card.
    for fname in sorted(os.listdir(TEAM)):
        if not fname.lower().endswith((".jpg", ".jpeg", ".png")):
            continue
        slug = os.path.splitext(fname)[0]
        im = Image.open(os.path.join(TEAM, fname)).convert("RGB")
        im = portrait_bw(crop(im, (4, 5), .5, .42))
        m = save_set(im, os.path.join(OUT, "team"), slug, [400, 480, 640])
        m["source"] = f"team/{fname}"
        manifest.setdefault("team", {})[slug] = m

    for fname in sorted(os.listdir(DECK)):
        if not fname.lower().endswith(".jpg"):
            continue
        slug = fname[:-4]
        im = Image.open(os.path.join(DECK, fname)).convert("RGB")
        group = "team" if im.size[1] > im.size[0] else "loans"
        m = save_set(im, os.path.join(OUT, group), slug, [im.size[0]])
        m["source"] = f"deck/{fname}"
        manifest.setdefault(group, {})[slug] = m

    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
    n = sum(len(v) for v in manifest.values())
    print(f"Processed {n} image roles -> static/img/")


if __name__ == "__main__":
    main()
