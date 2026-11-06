"""Measure concentric arcs in the original along radial rays.
Prints radius and coverage. About 100% suggests a continuous line; lower suggests dashed or chain lines,
or a band crossed by other lines. Pick angle ranges free of text and leaders, then confirm by eye.

usage: radial_rings.py calibration.json cx cy r_min r_max a0 a1 [--step 0.15] [--prom 18]
"""
import sys
import numpy as np
from PIL import Image
from common import load_cal, model_to_scan

args = sys.argv[1:]
def opt(flag, default):
    if flag in args:
        i = args.index(flag)
        v = float(args[i + 1])
        del args[i:i + 2]
        return v
    return default
step, prom = opt("--step", .15), opt("--prom", 18)
cal = load_cal(args[0])
cx, cy, r0, r1, a0, a1 = map(float, args[1:7])
a = np.asarray(Image.open(cal["scan_png"]).convert("L"), dtype=float)
rs = np.arange(r0, r1, step)
angs = np.arange(a0, a1, .25)
o = np.zeros((len(angs), len(rs)))
for i, d in enumerate(angs):
    th = np.radians(d)
    pts = np.c_[cx + rs * np.cos(th), cy + rs * np.sin(th)]
    px = pts @ cal["A"].T + cal["t"]
    o[i] = 255 - a[np.clip(px[:, 1].round().astype(int), 0, a.shape[0] - 1), np.clip(px[:, 0].round().astype(int), 0, a.shape[1] - 1)]
m = np.median(o, axis=0)
win = max(int(1.5 / step), 2)
found = []
for i in range(win, len(m) - win):
    if m[i] == m[i - win:i + win + 1].max() and m[i] - min(m[i - win:i].min(), m[i + 1:i + win + 1].min()) >= prom:
        if found and rs[i] - rs[found[-1]] < step * 2:
            continue
        found.append(i)
print("radius  coverage")
for i in found:
    print(f"{rs[i]:7.1f}  {(o[:, max(i - 3, 0):i + 4].max(axis=1) > 120).mean() * 100:5.0f}%")
