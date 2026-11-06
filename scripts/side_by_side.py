"""Original (left) and redraw (right) in the same frame, one PNG per zone.

usage: side_by_side.py calibration.json redraw.pdf outdir name,x0,x1,y0,y1[,ppm] ...
"""
import os, sys
import pymupdf
from PIL import Image, ImageDraw, ImageOps
from common import load_cal, crop_scan, crop_redraw, parse_zone

cal = load_cal(sys.argv[1])
page = pymupdf.open(sys.argv[2])[0]
out = sys.argv[3]
os.makedirs(out, exist_ok=True)
im = Image.open(cal["scan_png"]).convert("L")
for z in sys.argv[4:]:
    name, x0, x1, y0, y1, ppm = parse_zone(z)
    a = ImageOps.autocontrast(crop_scan(cal, im, x0, x1, y0, y1, ppm), cutoff=1).convert("RGB")
    b = crop_redraw(cal, page, x0, x1, y0, y1, ppm)
    w, h = a.size
    c = Image.new("RGB", (w * 2 + 20, h + 24), (255, 255, 255))
    c.paste(a, (0, 24))
    c.paste(b, (w + 20, 24))
    d = ImageDraw.Draw(c)
    d.text((4, 6), name + " ORIGINAL", fill=(200, 0, 0))
    d.text((w + 24, 6), name + " REDRAW", fill=(0, 0, 200))
    p = os.path.join(out, name + ".png")
    c.save(p)
    print(p, c.size)
