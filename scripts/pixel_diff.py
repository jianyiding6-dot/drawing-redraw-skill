"""Find ink that exists on only one side.
RED  = in the original, nothing in the redraw within tolerance (missing)
BLUE = in the redraw, nothing in the original within tolerance (extra or misplaced)
Grey = agreement. Text font differences show up too, so read the map; never trust the count alone.

usage: pixel_diff.py calibration.json redraw.pdf outdir [--tol 1.6] name,x0,x1,y0,y1[,ppm] ...
"""
import os, sys
import numpy as np
import pymupdf
from PIL import Image, ImageFilter
from common import load_cal, crop_scan, crop_redraw, parse_zone

args = sys.argv[1:]
tol = 1.6
if "--tol" in args:
    i = args.index("--tol")
    tol = float(args[i + 1])
    del args[i:i + 2]
cal = load_cal(args[0])
page = pymupdf.open(args[1])[0]
out = args[2]
os.makedirs(out, exist_ok=True)
im = Image.open(cal["scan_png"]).convert("L")


def grow(mask, px):
    """Dilate a boolean mask by px pixels; repeated small filters keep large radii fast."""
    img = Image.fromarray((mask * 255).astype("uint8"))
    while px > 0:
        step = min(px, 3)
        img = img.filter(ImageFilter.MaxFilter(step * 2 + 1))
        px -= step
    return np.asarray(img) > 0


for z in args[3:]:
    name, x0, x1, y0, y1, ppm = parse_zone(z)
    scan = crop_scan(cal, im, x0, x1, y0, y1, ppm)
    A = np.asarray(scan, dtype=float)
    bg = np.asarray(scan.filter(ImageFilter.BoxBlur(40)), dtype=float)   # paper shading on old scans
    speck = np.asarray(Image.fromarray(((bg - A) > 45).astype("uint8") * 255).filter(ImageFilter.MinFilter(3)), dtype=bool)
    ink = grow(speck, 1)
    B = np.asarray(crop_redraw(cal, page, x0, x1, y0, y1, ppm).convert("L")) < 140
    t = max(int(tol * ppm), 1)
    miss = ink & ~grow(B, t)
    extra = B & ~grow(ink, t)
    c = np.full(A.shape + (3,), 255, dtype="uint8")
    c[ink] = (205, 205, 205)
    c[B] = (120, 120, 120)
    c[miss] = (230, 0, 0)
    c[extra] = (0, 70, 255)
    p = os.path.join(out, name + "_diff.png")
    Image.fromarray(c).save(p)
    print(f"{p}  missing {int(miss.sum())} px  extra {int(extra.sum())} px")
