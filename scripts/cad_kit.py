"""Small DXF drawing kit: layers for Chinese GB drawings, and lines that break around text.

Lines and arcs are held back until flush(), then cut around the real glyph outline of every
registered text, because a dimension number must not be crossed by any line.
Also exports the DXF to a vector PDF at an exact sheet size.
"""
import math
import ezdxf
from ezdxf.addons import text2path
from ezdxf.enums import TextEntityAlignment as TA

LAYERS = [("OUT", 50, "Continuous"), ("THIN", 25, "Continuous"), ("CEN", 25, "CENTER"), ("HID", 25, "DASHED"),
          ("DIM", 25, "Continuous"), ("TXT", 25, "Continuous"), ("HATCH", 25, "Continuous"), ("FRAME", 50, "Continuous"),
          ("SYM", 25, "Continuous")]


class Sheet:
    def __init__(self, font="Arial Unicode.ttf", ltscale=6):
        self.doc = ezdxf.new("R2013", setup=True)
        self.doc.header["$LTSCALE"] = ltscale
        self.doc.header["$LWDISPLAY"] = 1
        self.msp = self.doc.modelspace()
        self.doc.styles.new("CN", dxfattribs={"font": font})
        for name, lw, lt in LAYERS:
            self.doc.layers.add(name, color=7, lineweight=lw, linetype=lt)
        self._lines, self._arcs, self._boxes = [], [], []

    def line(self, a, b, layer="OUT"):
        self._lines.append((tuple(a)[:2], tuple(b)[:2], layer))

    def path(self, pts, layer="DIM"):
        for a, b in zip(pts, pts[1:]):
            self.line(a, b, layer)

    def arc(self, c, r, a0, a1, layer="OUT"):
        self._arcs.append((tuple(c)[:2], r, a0, a1, layer))

    def poly(self, pts, layer="OUT", close=False):
        """Frames and section outlines: drawn as-is, never broken."""
        self.msp.add_lwpolyline(pts, close=close, dxfattribs={"layer": layer})

    def circle(self, c, r, layer="OUT"):
        self.msp.add_circle(c, r, dxfattribs={"layer": layer})

    def text(self, s, x, y, h=9, rot=0, align=TA.MIDDLE_CENTER, layer="TXT", breaks=True):
        t = self.msp.add_text(s, height=h, rotation=rot, dxfattribs={"layer": layer, "style": "CN"})
        t.set_placement((x, y), align=align)
        if breaks:
            cs, sn = math.cos(math.radians(rot)), math.sin(math.radians(rot))
            us, vs = [], []
            for p in text2path.make_paths_from_entity(t):
                for v in p.flattening(.05):
                    us.append(v.x * cs + v.y * sn)
                    vs.append(-v.x * sn + v.y * cs)
            if us:
                self._boxes.append((min(us) - 1, max(us) + 1, min(vs) - 1, max(vs) + 1, cs, sn))
        return t

    def arrow(self, tip, ang, length=6.5, half=1.15):
        a = math.radians(ang)
        ux, uy = math.cos(a), math.sin(a)
        bx, by = tip[0] - length * ux, tip[1] - length * uy
        h = self.msp.add_hatch(color=7, dxfattribs={"layer": "DIM"})
        h.paths.add_polyline_path([tip, (bx - half * uy, by + half * ux), (bx + half * uy, by - half * ux)], is_closed=True)

    def hatch(self, pts, scale=.85):
        self.poly(pts, "OUT", True)
        h = self.msp.add_hatch(dxfattribs={"layer": "HATCH"})
        h.paths.add_polyline_path(pts, is_closed=True)
        h.set_pattern_fill("ANSI31", scale=scale)

    def _hit(self, x, y):
        for u0, u1, v0, v1, cs, sn in self._boxes:
            u, v = x * cs + y * sn, -x * sn + y * cs
            if u0 < u < u1 and v0 < v < v1:
                return True
        return False

    def _runs(self, n, f):
        runs, cur = [], None
        for i in range(n + 1):
            if self._hit(*f(i)):
                if cur is not None:
                    runs.append((cur, i - 1))
                    cur = None
            elif cur is None:
                cur = i
        if cur is not None:
            runs.append((cur, n))
        return [r for r in runs if r[1] > r[0]]

    def flush(self):
        for a, b, lay in self._lines:
            n = max(int(math.hypot(b[0] - a[0], b[1] - a[1]) / .25), 1)
            f = lambda i: (a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n)
            for i, j in self._runs(n, f):
                self.msp.add_line(a if i == 0 else f(i), b if j == n else f(j), dxfattribs={"layer": lay})
        for c, r, a0, a1, lay in self._arcs:
            sw = (a1 - a0) % 360 or 360
            n = max(int(math.radians(sw) * r / .25), 2)
            ang = lambda i: a0 + sw * i / n
            f = lambda i: (c[0] + r * math.cos(math.radians(ang(i))), c[1] + r * math.sin(math.radians(ang(i))))
            for i, j in self._runs(n, f):
                self.msp.add_arc(c, r, ang(i), ang(j), dxfattribs={"layer": lay})
        self._lines, self._arcs = [], []

    def save(self, path):
        self.flush()
        self.doc.saveas(path)


def export_pdf(dxf_path, pdf_path, x0, y0, x1, y1, page_mm=(420, 297)):
    """Vector PDF of the sheet (x0,y0)-(x1,y1) on a page of page_mm."""
    from ezdxf.addons.drawing import Frontend, RenderContext, layout, config
    from ezdxf.addons.drawing.pymupdf import PyMuPdfBackend
    doc = ezdxf.readfile(dxf_path)
    cfg = config.Configuration(color_policy=config.ColorPolicy.BLACK, background_policy=config.BackgroundPolicy.WHITE,
                               lineweight_policy=config.LineweightPolicy.ABSOLUTE, min_hatch_line_distance=0.01)
    back = PyMuPdfBackend()
    Frontend(RenderContext(doc), back, config=cfg).draw_layout(doc.modelspace())
    page = layout.Page(page_mm[0], page_mm[1], layout.Units.mm, margins=layout.Margins.all(0))
    data = back.get_pdf_bytes(page, settings=layout.Settings(fit_page=True), render_box=ezdxf.math.BoundingBox2d([(x0, y0), (x1, y1)]))
    with open(pdf_path, "wb") as f:
        f.write(data)
