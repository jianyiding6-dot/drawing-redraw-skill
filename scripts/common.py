"""Shared helpers: scan <-> model calibration and same-frame crops."""
import json
import numpy as np
import pymupdf
from PIL import Image


def load_cal(path):
    with open(path, encoding="utf-8") as f:
        c = json.load(f)
    c["A"] = np.array(c["model_to_scan"]["A"])
    c["t"] = np.array(c["model_to_scan"]["t"])
    return c


def model_to_scan(cal, x, y):
    return cal["A"] @ np.array([x, y]) + cal["t"]


def crop_scan(cal, im, x0, x1, y0, y1, ppm):
    """Scan region resampled into model axes (x right, y up) at ppm pixels per model unit."""
    w, h = int((x1 - x0) * ppm), int((y1 - y0) * ppm)
    A, o = cal["A"], model_to_scan(cal, x0, y1)
    return im.transform((w, h), Image.AFFINE, (A[0, 0] / ppm, -A[0, 1] / ppm, o[0], A[1, 0] / ppm, -A[1, 1] / ppm, o[1]),
                        Image.BICUBIC, fillcolor=255)


def crop_redraw(cal, page, x0, x1, y0, y1, ppm):
    """Same region from the redraw PDF. sheet = model extents covered by the PDF page."""
    s = cal["sheet"]
    k = page.rect.width / s["width"]
    w, h = int((x1 - x0) * ppm), int((y1 - y0) * ppm)
    clip = pymupdf.Rect((x0 - s["x0"]) * k, (s["y1"] - y1) * k, (x1 - s["x0"]) * k, (s["y1"] - y0) * k)
    p = page.get_pixmap(matrix=pymupdf.Matrix(ppm / k, ppm / k), clip=clip)
    return Image.frombytes("RGB", (p.width, p.height), p.samples).resize((w, h))


def parse_zone(text):
    """name,x0,x1,y0,y1[,ppm]"""
    v = text.split(",")
    return v[0], float(v[1]), float(v[2]), float(v[3]), float(v[4]), float(v[5]) if len(v) > 5 else 5.0
