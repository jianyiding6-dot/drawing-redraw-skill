"""Clash check on a DXF using real glyph outlines.
Reports text x text, text x line, text inside hatch, and symbols crossed by other lines.
Symbols crossing lines may be correct when the original does the same: judge those against the original.

Layer convention (cad_kit.py): SYM = symbols, HATCH = section hatch, DIM = dimensions and their arrow hatches.
usage: clash_check.py drawing.dxf [padding=0.7]
Exit code 1 when any text clash exists.
"""
import math, sys
import ezdxf
from ezdxf.addons import text2path

PAD = float(sys.argv[2]) if len(sys.argv) > 2 else 0.7
m = ezdxf.readfile(sys.argv[1]).modelspace()


def text_rect(e):
    rot = math.radians(e.dxf.rotation)
    c, s = math.cos(rot), math.sin(rot)
    ps = []
    for p in text2path.make_paths_from_entity(e):
        for v in p.flattening(0.05):
            ps.append((v.x * c + v.y * s, -v.x * s + v.y * c))
    if not ps:
        return None
    us, vs = zip(*ps)
    uc, vc = (min(us) + max(us)) / 2, (min(vs) + max(vs)) / 2
    return dict(t=e.dxf.text, u0=min(us) - PAD, u1=max(us) + PAD, v0=min(vs) - PAD, v1=max(vs) + PAD, c=c, s=s,
                cx=uc * c - vc * s, cy=uc * s + vc * c)


def corners(r):
    return [(u * r["c"] - v * r["s"], u * r["s"] + v * r["c"]) for u, v in [(r["u0"], r["v0"]), (r["u1"], r["v0"]), (r["u1"], r["v1"]), (r["u0"], r["v1"])]]


def seg_hits(r, a, b):
    ax, ay = a[0] * r["c"] + a[1] * r["s"], -a[0] * r["s"] + a[1] * r["c"]
    bx, by = b[0] * r["c"] + b[1] * r["s"], -b[0] * r["s"] + b[1] * r["c"]
    dx, dy = bx - ax, by - ay
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, ax - r["u0"]), (dx, r["u1"] - ax), (-dy, ay - r["v0"]), (dy, r["v1"] - ay)):
        if abs(p) < 1e-12:
            if q < 0:
                return False
        else:
            t = q / p
            if p < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
            if t0 > t1:
                return False
    return True


def rects_overlap(r1, r2):
    A, B = corners(r1), corners(r2)
    for poly in (A, B):
        for i in range(4):
            x1, y1 = poly[i]
            x2, y2 = poly[(i + 1) % 4]
            nx, ny = y2 - y1, x1 - x2
            pa = [nx * x + ny * y for x, y in A]
            pb = [nx * x + ny * y for x, y in B]
            if max(pa) < min(pb) or max(pb) < min(pa):
                return False
    return True


def arc_pts(c, r, a0, a1, step=2.0):
    if a1 < a0:
        a1 += 360
    n = max(2, int((a1 - a0) / step) + 1)
    return [(c[0] + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), c[1] + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


segs = []
for e in m:
    t, lay = e.dxftype(), e.dxf.layer
    if t == "LINE":
        segs.append(((e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y), lay))
    elif t == "LWPOLYLINE":
        pts = [tuple(p) for p in e.get_points("xy")]
        if e.closed:
            pts.append(pts[0])
        segs += [(pts[i], pts[i + 1], lay) for i in range(len(pts) - 1)]
    elif t in ("ARC", "CIRCLE"):
        a0, a1 = (e.dxf.start_angle, e.dxf.end_angle) if t == "ARC" else (0, 360)
        p = arc_pts((e.dxf.center.x, e.dxf.center.y), e.dxf.radius, a0, a1)
        segs += [(p[i], p[i + 1], lay) for i in range(len(p) - 1)]
    elif t == "HATCH" and lay == "DIM":
        for bp in e.paths:
            pts = [tuple(v[:2]) for v in bp.vertices]
            pts.append(pts[0])
            segs += [(pts[i], pts[i + 1], "ARROW") for i in range(len(pts) - 1)]

hatches = [[tuple(v[:2]) for v in bp.vertices] for e in m.query('HATCH[layer=="HATCH"]') for bp in e.paths]


def inside(pt, poly):
    x, y = pt
    c = False
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % len(poly)]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


texts = [r for r in (text_rect(e) for e in m.query("TEXT")) if r]
text_issues = []
for i, r in enumerate(texts):
    for r2 in texts[i + 1:]:
        if rects_overlap(r, r2):
            text_issues.append(f"text x text  {r['t']} @({r['cx']:.0f},{r['cy']:.0f}) ~ {r2['t']} @({r2['cx']:.0f},{r2['cy']:.0f})")
    seen = set()
    for a, b, lay in segs:
        if lay not in seen and seg_hits(r, a, b):
            seen.add(lay)
            text_issues.append(f"text x line  {r['t']} @({r['cx']:.0f},{r['cy']:.0f}) ~ {lay} ({a[0]:.0f},{a[1]:.0f})-({b[0]:.0f},{b[1]:.0f})")
    if any(inside((r["cx"], r["cy"]), h) or any(inside(c, h) for c in corners(r)) for h in hatches):
        text_issues.append(f"text in hatch  {r['t']} @({r['cx']:.0f},{r['cy']:.0f})")


def cross(p1, p2, p3, p4):
    d = (p2[0] - p1[0]) * (p4[1] - p3[1]) - (p2[1] - p1[1]) * (p4[0] - p3[0])
    if abs(d) < 1e-9:
        return False
    t = ((p3[0] - p1[0]) * (p4[1] - p3[1]) - (p3[1] - p1[1]) * (p4[0] - p3[0])) / d
    u = ((p3[0] - p1[0]) * (p2[1] - p1[1]) - (p3[1] - p1[1]) * (p2[0] - p1[0])) / d
    return 0.02 < t < 0.98 and 0.0 <= u <= 1.0


sym = [s for s in segs if s[2] == "SYM"]
others = [s for s in segs if s[2] not in ("SYM", "ARROW")]
sym_issues = sorted({f"symbol x line  ({s[0][0]:.0f},{s[0][1]:.0f})-({s[1][0]:.0f},{s[1][1]:.0f}) ~ {o[2]} ({o[0][0]:.0f},{o[0][1]:.0f})-({o[1][0]:.0f},{o[1][1]:.0f})"
                     for s in sym for o in others if cross(s[0], s[1], o[0], o[1])})
text_issues = sorted(set(text_issues))
print(f"texts {len(texts)}  segments {len(segs)}  text clashes {len(text_issues)}  symbol crossings {len(sym_issues)} (compare these with the original)")
for x in text_issues + sym_issues:
    print(x)
sys.exit(1 if text_issues else 0)
