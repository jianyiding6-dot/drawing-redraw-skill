"""Render the original drawing and fit scan <-> model coordinates from control points.

config.json:
  scan      original PDF or image
  dpi       render DPI for a PDF (default 300)
  sheet     {"x0": left, "y1": top, "width": width}: model extents of the redraw PDF page
  points    [[scan_px_x, scan_px_y, model_x, model_y], ...]  at least 4, spread over the sheet

usage: calibrate.py config.json outdir
"""
import json, os, sys
import numpy as np
import pymupdf
from PIL import Image

cfg_path, out = sys.argv[1:3]
os.makedirs(out, exist_ok=True)
with open(cfg_path, encoding="utf-8") as f:
    cfg = json.load(f)
scan_png = os.path.join(out, "scan.png")
if cfg["scan"].lower().endswith(".pdf"):
    doc = pymupdf.open(cfg["scan"])
    page = doc[0]
    print("embedded images", len(page.get_images()), " vector drawings", len(page.get_drawings()), " text chars", len(page.get_text()))
    page.get_pixmap(dpi=cfg.get("dpi", 300), colorspace=pymupdf.csGRAY).save(scan_png)
else:
    Image.open(cfg["scan"]).convert("L").save(scan_png)
pts = np.array(cfg["points"], dtype=float)
if len(pts) < 4:
    sys.exit("need at least 4 control points")
M = np.c_[pts[:, 2:4], np.ones(len(pts))]
sol = np.linalg.lstsq(M, pts[:, :2], rcond=None)[0].T
A, t = sol[:, :2], sol[:, 2]
err = np.linalg.norm((np.c_[pts[:, 2:4]] @ A.T + t) - pts[:, :2], axis=1)
Ai = np.linalg.inv(A)
mm = np.linalg.norm((pts[:, :2] - t) @ Ai.T - pts[:, 2:4], axis=1)
with open(os.path.join(out, "calibration.json"), "w", encoding="utf-8") as f:
    json.dump({"scan_png": scan_png, "sheet": cfg["sheet"], "model_to_scan": {"A": A.tolist(), "t": t.tolist()}}, f, indent=1)
print(f"control points {len(pts)}  mean error {mm.mean():.2f}  max error {mm.max():.2f} (model units)")
for i in np.argsort(-mm)[:3]:
    print(f"  worst point {i}: {mm[i]:.2f}  {pts[i].tolist()}")
