"""Minimal helpers for hand-authoring Bodymovin (Lottie) JSON.

Conventions: colours are hex strings; positions are [x, y]; keyframes are lists of
(frame, value) or (frame, value, ease) tuples, where ease is a named curve. A property
given a plain value is static. Everything is rounded to keep files small.
"""
import json
import math
import os

EASE = {
    "linear": ((0.0, 0.0), (1.0, 1.0)),
    "inout": ((0.42, 0.0), (0.58, 1.0)),
    "out": ((0.0, 0.0), (0.58, 1.0)),
    "in": ((0.42, 0.0), (1.0, 1.0)),
    "sine": ((0.37, 0.0), (0.63, 1.0)),
    "back": ((0.2, 0.0), (0.3, 1.45)),  # overshoot
}


def _r(v, nd=2):
    if isinstance(v, (list, tuple)):
        return [_r(x, nd) for x in v]
    if isinstance(v, float):
        v = round(v, nd)
        return int(v) if v == int(v) else v
    return v


def hexc(h, a=1.0):
    h = h.lstrip("#")
    return [round(int(h[i:i + 2], 16) / 255, 3) for i in (0, 2, 4)] + [a]


def prop(v, nd=2):
    """Static value, or animated from [(t, value[, ease]), ...]."""
    if isinstance(v, list) and v and isinstance(v[0], tuple):
        kfs = []
        for i, kf in enumerate(v):
            t, val = kf[0], kf[1]
            ease = kf[2] if len(kf) > 2 else "inout"
            val = val if isinstance(val, (list, tuple)) else [val]
            k = {"t": _r(float(t)), "s": _r(list(map(float, val)), nd)}
            if i < len(v) - 1:
                (ox, oy), (ix, iy) = EASE[ease]
                k["o"] = {"x": [ox], "y": [oy]}
                k["i"] = {"x": [ix], "y": [iy]}
            kfs.append(k)
        return {"a": 1, "k": kfs}
    return {"a": 0, "k": _r(v if not isinstance(v, tuple) else list(v), nd)}


def transform(p=(0, 0), a=(0, 0), s=(100, 100), r=0, o=100):
    return {"o": prop(o), "r": prop(r), "p": prop(p), "a": prop(a), "s": prop(s)}


def tr_shape(p=(0, 0), a=(0, 0), s=(100, 100), r=0, o=100):
    return {"ty": "tr", "p": prop(p), "a": prop(a), "s": prop(s), "r": prop(r), "o": prop(o),
            "sk": prop(0), "sa": prop(0)}


def group(items, nm="g", **tr):
    return {"ty": "gr", "nm": nm, "it": list(items) + [tr_shape(**tr)]}


def ellipse(size, p=(0, 0)):
    return {"ty": "el", "p": prop(p), "s": prop(size), "d": 1}


def rect(size, p=(0, 0), r=0):
    return {"ty": "rc", "p": prop(p), "s": prop(size), "r": prop(r), "d": 1}


def star(points, outer, inner, p=(0, 0), r=0, roundness=0):
    return {"ty": "sr", "sy": 1, "d": 1, "pt": prop(points), "p": prop(p), "r": prop(r),
            "ir": prop(inner), "or": prop(outer), "is": prop(roundness), "os": prop(roundness)}


def path(vertices, closed=True, tangents=None, nd=1, nd_t=0):
    """Polygon (or smooth path when tangents=(ins, outs) given). Tangent handles are
    stored with nd_t decimals (whole pixels by default) to keep files small."""
    n = len(vertices)
    ins, outs = tangents if tangents else ([[0, 0]] * n, [[0, 0]] * n)
    return {"ty": "sh", "ks": {"a": 0, "k": {"c": closed, "v": _r([list(map(float, v)) for v in vertices], nd),
                                             "i": _r([list(map(float, v)) for v in ins], nd_t),
                                             "o": _r([list(map(float, v)) for v in outs], nd_t)}}}


def smooth_path(vertices, closed=True, tension=0.5, nd=1):
    """Catmull-Rom style tangents through the vertices."""
    n = len(vertices)
    ins, outs = [], []
    for i in range(n):
        p0 = vertices[(i - 1) % n] if (closed or i > 0) else vertices[i]
        p2 = vertices[(i + 1) % n] if (closed or i < n - 1) else vertices[i]
        tx, ty = (p2[0] - p0[0]) * tension / 3, (p2[1] - p0[1]) * tension / 3
        ins.append([-tx, -ty])
        outs.append([tx, ty])
    return path(vertices, closed, (ins, outs), nd)


def fill(color, o=100, rule=1):
    return {"ty": "fl", "c": prop(hexc(color) if isinstance(color, str) else color, 3), "o": prop(o), "r": rule}


def stroke(color, w, o=100):
    return {"ty": "st", "c": prop(hexc(color), 3), "o": prop(o), "w": prop(w), "lc": 2, "lj": 2}


def radial(stops, start=(0, 0), end=(100, 0), o=100):
    """Radial gradient fill. stops: [(pos, '#hex', alpha), ...]."""
    cols, alph = [], []
    for pos, c, a in stops:
        cols += [pos] + hexc(c)[:3]
        alph += [pos, a]
    return {"ty": "gf", "t": 2, "o": prop(o), "r": 1, "s": prop(start), "e": prop(end),
            "h": prop(0), "a": prop(0), "g": {"p": len(stops), "k": prop(cols + alph, 3)}}


class Comp:
    def __init__(self, nm, w, h, frames, fr=30):
        self.d = {"v": "5.7.4", "fr": fr, "ip": 0, "op": frames, "w": w, "h": h, "nm": nm, "ddd": 0,
                  "assets": [], "layers": [], "markers": []}
        self.frames = frames

    def _layer(self, ty, nm, ks, ip=0, op=None, parent=None, **extra):
        lay = {"ddd": 0, "ind": len(self.d["layers"]) + 1, "ty": ty, "nm": nm, "sr": 1, "ks": ks, "ao": 0,
               "ip": ip, "op": self.frames if op is None else op, "st": 0, "bm": 0}
        if parent:
            lay["parent"] = parent
        lay.update(extra)
        # layers are listed top-most first; append keeps call order = stacking order (first = top)
        self.d["layers"].append(lay)
        return lay["ind"]

    def shape(self, nm, shapes, ks=None, **kw):
        return self._layer(4, nm, ks or transform(), shapes=shapes, **kw)

    def null(self, nm, ks=None, **kw):
        return self._layer(3, nm, ks or transform(), **kw)

    def precomp_layer(self, nm, ref, w, h, ks=None, st=0, **kw):
        ind = self._layer(0, nm, ks or transform(), refId=ref, w=w, h=h, **kw)
        self.d["layers"][-1]["st"] = st
        return ind

    def image_layer(self, nm, ref, ks=None, **kw):
        return self._layer(2, nm, ks or transform(), refId=ref, **kw)

    def add_precomp(self, ref, layers):
        self.d["assets"].append({"id": ref, "layers": layers})

    def add_image_asset(self, ref, w, h, filename):
        self.d["assets"].append({"id": ref, "w": w, "h": h, "u": "", "p": filename, "e": 0})

    def save(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.d, f, separators=(",", ":"))
        return os.path.getsize(path)


def sub_comp(frames, w, h):
    """A throwaway Comp used to build layer lists for precomp assets."""
    return Comp("sub", w, h, frames)


def osc(frames, period, lo, hi, phase=0.0, ease="sine"):
    """Keyframes for a looping oscillation between lo and hi (period must divide frames)."""
    kfs = []
    half = period / 2
    t = 0.0
    start_hi = (phase % 1.0) >= 0.5
    while t <= frames + 1e-6:
        kfs.append((round(t, 2), hi if start_hi else lo, ease))
        start_hi = not start_hi
        t += half
    # shift by phase within half a period by trimming isn't needed for seamless loops
    return kfs


def deg(x):
    return math.degrees(x)
