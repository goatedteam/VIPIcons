"""Trace a raster sprite into flat-colour Lottie shape groups, one group list per body part.

The sprite is quantised to a small palette (sorted dark -> light), cleaned, and each
colour region of each part is traced with OpenCV and simplified. Every part gets an
ink-coloured silhouette underneath (the art's outline colour) so seams between colour
regions read as linework, and optional "backfill" regions fill what a moving part
reveals.
"""
import cv2
import numpy as np
from PIL import Image, ImageDraw

import lottie_kit as K


def quantise(rgba, k, alpha_min, seed=3, smooth=9):
    """Edge-preserving smooth, then k-means in Lab (so small but distinct hues such as
    skin survive), clusters sorted dark -> light. Returns (labels, RGB palette, opaque)."""
    a = rgba[..., 3]
    opaque = a >= alpha_min
    rgb = np.ascontiguousarray(rgba[..., :3])
    if smooth:
        rgb = cv2.bilateralFilter(rgb, smooth, 40, smooth)
    lab_img = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    px = lab_img[opaque].astype(np.float32)
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.5)
    cv2.setRNGSeed(seed)
    _, lab, cent = cv2.kmeans(px, k, None, crit, 4, cv2.KMEANS_PP_CENTERS)
    lum = cent[:, 0]
    order = np.argsort(lum)
    remap = np.empty_like(order)
    remap[order] = np.arange(k)
    labels = np.full(a.shape, 255, np.uint8)
    labels[opaque] = remap[lab.ravel()].astype(np.uint8)
    pal_lab = cent[order].astype(np.uint8).reshape(1, -1, 3)
    pal = cv2.cvtColor(pal_lab, cv2.COLOR_LAB2RGB).reshape(-1, 3).astype(np.float32)
    # mode-ish cleanup: median of luminance-sorted indices
    cleaned = cv2.medianBlur(labels, 7)
    cleaned[~opaque] = 255
    return cleaned, pal, opaque


def hexof(rgb):
    return "#%02x%02x%02x" % tuple(int(round(c)) for c in rgb)


def poly_mask(shape, polys, scale):
    m = Image.new("L", (shape[1], shape[0]), 0)
    d = ImageDraw.Draw(m)
    for p in polys:
        d.polygon([(x * scale, y * scale) for x, y in p], fill=255)
    return np.asarray(m) > 0


def contours_to_paths(mask, scale, eps, min_area, offset=(0, 0), smooth=False):
    """Outer + hole contours of a boolean mask -> list of Lottie path items (even-odd fill)."""
    m = mask.astype(np.uint8) * 255
    cs, hier = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    out = []
    for c in cs:
        if cv2.contourArea(c) < min_area:
            continue
        ap = cv2.approxPolyDP(c, eps, True)
        if len(ap) < 3:
            continue
        pts = [((x + 0.5) / scale - offset[0], (y + 0.5) / scale - offset[1]) for [[x, y]] in ap]
        out.append(K.smooth_path(pts, tension=0.45, nd=1) if smooth and len(pts) > 4 else K.path(pts, nd=1))
    return out


def trace_part(labels, pal, part_mask, scale, ink_idx, eps=2.8, min_area=140, offset=(0, 0), backfill=None,
               smooth=True, detail=None, grow=3):
    """Shape items for one part, top-most first. Colour regions are painted big-first and
    grown by `grow` px so no dark gaps open between them; inside the optional `detail`
    mask (faces, hands, small props) contours are traced finer."""
    items = []
    present = [c for c in range(len(pal)) if ((labels == c) & part_mask).sum() > 20]
    present.sort(key=lambda c: ((labels == c) & part_mask).sum(), reverse=True)  # big first (painted lower)
    k5 = np.ones((5, 5), np.uint8)
    kg = np.ones((2 * grow + 1, 2 * grow + 1), np.uint8)
    for c in present:
        if c == ink_idx:
            continue
        m = ((labels == c) & part_mask).astype(np.uint8)
        paths = []
        if detail is not None:
            md = cv2.morphologyEx(m & detail.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
            md = cv2.dilate(md, np.ones((3, 3), np.uint8)) & part_mask.astype(np.uint8)
            paths += contours_to_paths(md > 0, scale, eps * 0.6, 18, offset, False)
            m = m & (~detail).astype(np.uint8)
        m = cv2.morphologyEx(cv2.morphologyEx(m, cv2.MORPH_OPEN, k5), cv2.MORPH_CLOSE, k5)
        m = cv2.dilate(m, kg) & part_mask.astype(np.uint8)
        paths = contours_to_paths(m > 0, scale, eps, min_area, offset, smooth) + paths
        if paths:
            items.insert(0, K.group(paths + [K.fill(hexof(pal[c]), rule=2)], nm=f"c{c}"))
    sil = contours_to_paths(cv2.dilate((part_mask & (labels != 255)).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0,
                            scale, eps, min_area, offset)
    items.append(K.group(sil + [K.fill(hexof(pal[ink_idx]), rule=2)], nm="ink"))
    if backfill is not None:
        mask, colour = backfill
        bf = contours_to_paths(mask, scale, eps, min_area, offset)
        if bf:
            items.append(K.group(bf + [K.fill(colour, rule=2)], nm="backfill"))
    return items
