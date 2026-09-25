#!/usr/bin/env python3
"""
Offline walkability validator for the Leafy Manor entrance-hall blockout.

Runs on the exact primitives that leafy_manor_build_blockout.py spawns in Unreal
and approximates CharacterMovementComponent rules the same way Recast/NavMesh does:

  * a standing spot needs capsule-height headroom and no obstacle within the capsule
    radius between (MaxStepHeight .. capsule height) above the feet,
  * neighbouring spots connect if the height difference is <= MaxStepHeight
    (props flagged CanCharacterStepUpOn=No always block),
  * anything else that goes down is a ledge (fall).

Checks: every TEST_POINT reachable on foot from the PlayerStart, no ledge that
drops into the void or into a pocket you cannot walk out of, stair risers/slopes
within CharacterMovement limits, doors/headroom large enough for the capsule.

Pure Python 3 (no numpy) so it also runs in Unreal's bundled Python.

    python3 validate_blockout.py                      # defaults from leafy_manor_layout.PLAYER
    python3 validate_blockout.py --radius 42 --half-height 96   # UE template capsule
"""

import argparse
import collections
import math
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "Unreal", "Python"))
import leafy_manor_layout as lm  # noqa: E402

INF = float("inf")


# ---------------------------------------------------------------------------
# Geometry rasterisation
# ---------------------------------------------------------------------------
def _box_axes(rot):
    pitch, yaw, roll = (math.radians(v) for v in rot)
    if abs(roll) > 1e-9:
        raise ValueError("roll is not supported by the validator")
    cp, sp, cy, sy = math.cos(pitch), math.sin(pitch), math.cos(yaw), math.sin(yaw)
    return ((cp * cy, cp * sy, sp), (-sy, cy, 0.0), (-sp * cy, -sp * sy, cp))


class Solid:
    __slots__ = ("prim", "shape", "c", "h", "axes", "bounds", "step_up")

    def __init__(self, p):
        self.prim, self.shape, self.c, self.step_up = p, p.shape, p.center, p.step_up
        self.h = tuple(v / 2 for v in p.size)
        if self.shape == "box":
            self.axes = _box_axes(p.rot)
            ex = [sum(abs(self.axes[a][i]) * self.h[a] for a in range(3)) for i in range(3)]
        else:  # cylinders are upright; yaw only matters for elliptical ones (use the larger radius)
            if abs(p.rot[0]) > 1e-9 or abs(p.rot[2]) > 1e-9:
                raise ValueError("tilted cylinder %s not supported" % p.label)
            self.axes = None
            if abs(p.rot[1]) > 1e-9:
                r = max(self.h[0], self.h[1])
                self.h = (r, r, self.h[2])
            ex = list(self.h)
        self.bounds = tuple((self.c[i] - ex[i], self.c[i] + ex[i]) for i in range(3))

    def column(self, x, y):
        """Vertical interval of this solid at (x, y), or None."""
        cx, cy, cz = self.c
        if self.axes is None:
            rx, ry = self.h[0], self.h[1]
            if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 > 1.0:
                return None
            return cz - self.h[2], cz + self.h[2]
        lo, hi = -INF, INF
        for (e0, e1, e2), h in zip(self.axes, self.h):
            a = (x - cx) * e0 + (y - cy) * e1 - cz * e2
            if abs(e2) < 1e-12:
                if abs(a) > h:
                    return None
                continue
            z1, z2 = (-h - a) / e2, (h - a) / e2
            if z1 > z2:
                z1, z2 = z2, z1
            lo, hi = max(lo, z1), min(hi, z2)
            if lo > hi:
                return None
        return lo, hi


class Grid:
    def __init__(self, prims, cell, bounds):
        (self.x0, x1), (self.y0, y1) = bounds
        self.cell = cell
        self.nx = int(math.ceil((x1 - self.x0) / cell))
        self.ny = int(math.ceil((y1 - self.y0) / cell))
        # spans[idx] = list of (lo, hi, step_up)
        self.spans = [None] * (self.nx * self.ny)
        for p in prims:
            if p.collision == "none" or p.shape not in ("box", "cyl"):
                continue
            s = Solid(p)
            (bx0, bx1), (by0, by1), _ = s.bounds
            i0, i1 = max(0, int((bx0 - self.x0) / cell)), min(self.nx - 1, int((bx1 - self.x0) / cell))
            j0, j1 = max(0, int((by0 - self.y0) / cell)), min(self.ny - 1, int((by1 - self.y0) / cell))
            # Thin solids (door leaves, rails, blockers) could slip between cell centres:
            # sample a 3x3 pattern inside the cell and keep the union (conservative).
            thin = min(bx1 - bx0, by1 - by0) < 3 * cell
            offs = [(-0.45 * cell, -0.45 * cell), (-0.45 * cell, 0), (-0.45 * cell, 0.45 * cell),
                    (0, -0.45 * cell), (0, 0), (0, 0.45 * cell),
                    (0.45 * cell, -0.45 * cell), (0.45 * cell, 0), (0.45 * cell, 0.45 * cell)] if thin else [(0, 0)]
            for i in range(i0, i1 + 1):
                x = self.x0 + (i + 0.5) * cell
                for j in range(j0, j1 + 1):
                    y = self.y0 + (j + 0.5) * cell
                    iv = None
                    for ox, oy in offs:
                        r = s.column(x + ox, y + oy)
                        if r is not None:
                            iv = r if iv is None else (min(iv[0], r[0]), max(iv[1], r[1]))
                    if iv is None:
                        continue
                    k = i * self.ny + j
                    if self.spans[k] is None:
                        self.spans[k] = []
                    self.spans[k].append((iv[0], iv[1], s.step_up))
        # merge touching spans per cell (a merged span is step-up-able only if all parts are)
        for k, sp in enumerate(self.spans):
            if not sp:
                continue
            sp.sort()
            merged = [list(sp[0])]
            for lo, hi, su in sp[1:]:
                m = merged[-1]
                if lo <= m[1] + 0.5:
                    m[1] = max(m[1], hi)
                    m[2] = m[2] and su
                else:
                    merged.append([lo, hi, su])
            self.spans[k] = [tuple(m) for m in merged]

    def xy(self, i, j):
        return self.x0 + (i + 0.5) * self.cell, self.y0 + (j + 0.5) * self.cell

    def ij(self, x, y):
        return int((x - self.x0) / self.cell), int((y - self.y0) / self.cell)


# ---------------------------------------------------------------------------
# Walkability
# ---------------------------------------------------------------------------
def analyse(prims, radius, half_height, step, cell, bounds, z_top=INF):
    g = Grid(prims, cell, bounds)
    height = 2.0 * half_height
    nx, ny = g.nx, g.ny
    rc = int(math.ceil(radius / cell))
    disk = [(di, dj) for di in range(-rc, rc + 1) for dj in range(-rc, rc + 1)
            if math.hypot(di * cell, dj * cell) <= radius]

    # candidate standing surfaces: span tops with enough headroom
    surf = [None] * (nx * ny)      # per cell: list of surface heights
    for k, sp in enumerate(g.spans):
        if not sp:
            continue
        tops = []
        for n, (lo, hi, _) in enumerate(sp):
            nxt = sp[n + 1][0] if n + 1 < len(sp) else INF
            if nxt - hi >= height and hi < z_top:   # ignore the roof top
                tops.append(hi)
        if tops:
            surf[k] = tops

    # capsule radius erosion
    valid = [None] * (nx * ny)
    for i in range(nx):
        for j in range(ny):
            k = i * ny + j
            if surf[k] is None:
                continue
            ok = []
            for t in surf[k]:
                blocked = False
                for di, dj in disk:
                    ii, jj = i + di, j + dj
                    if not (0 <= ii < nx and 0 <= jj < ny):
                        continue
                    sp = g.spans[ii * ny + jj]
                    if not sp:
                        continue
                    for lo, hi, su in sp:
                        if lo < t + height and hi > t + (step if su else 0.5):
                            blocked = True
                            break
                    if blocked:
                        break
                if not blocked:
                    ok.append(t)
            if ok:
                valid[k] = ok

    def node_near(x, y, z, search=40.0, ztol=30.0):
        i0, j0 = g.ij(x, y)
        r = int(search / cell)
        best = None
        for di in range(-r, r + 1):
            for dj in range(-r, r + 1):
                i, j = i0 + di, j0 + dj
                if not (0 <= i < nx and 0 <= j < ny) or valid[i * ny + j] is None:
                    continue
                for t in valid[i * ny + j]:
                    if abs(t - z) <= ztol:
                        d = math.hypot(di, dj) + abs(t - z) / cell
                        if best is None or d < best[0]:
                            best = (d, (i, j, t))
        return best[1] if best else None

    def neighbours(i, j, t):
        """Yield ('walk', node) / ('fall', node, drop) / ('void', (i,j), None)."""
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ii, jj = i + di, j + dj
            if not (0 <= ii < nx and 0 <= jj < ny):
                yield ("void", (ii, jj), None)
                continue
            k = ii * ny + jj
            cand = [u for u in (valid[k] or ()) if abs(u - t) <= step]
            if cand:
                yield ("walk", (ii, jj, min(cand, key=lambda u: abs(u - t))))
                continue
            sp = g.spans[k] or ()
            if any(lo < t + height and hi > t - step for lo, hi, _ in sp):
                continue  # wall / obstacle / invalid standing spot at our level
            below = [hi for lo, hi, _ in sp if hi <= t - step]
            if not below:
                yield ("void", (ii, jj), None)
                continue
            land = max(below)
            if valid[k] and land in valid[k]:
                yield ("fall", (ii, jj, land), t - land)
            else:
                yield ("fall_bad", (ii, jj, land), t - land)

    return g, valid, node_near, neighbours


def flood(start, neighbours):
    seen = {start}
    queue = collections.deque([start])
    falls = []
    while queue:
        i, j, t = queue.popleft()
        for kind, node, *extra in neighbours(i, j, t):
            if kind == "walk":
                if node not in seen:
                    seen.add(node)
                    queue.append(node)
            else:
                falls.append((kind, (i, j, t), node, extra[0] if extra else None))
    return seen, falls


# ---------------------------------------------------------------------------
# PNG map
# ---------------------------------------------------------------------------
def write_png(path, w, h, pix):
    raw = b"".join(b"\x00" + bytes(pix[y * w * 3:(y + 1) * w * 3]) for y in range(h))

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def render_map(path, g, valid, reach, falls, points, z_split, px=3):
    nx, ny = g.nx, g.ny
    gap = 12
    w, h = (ny * 2) * px + gap, nx * px
    pix = bytearray([18, 18, 24] * (w * h))
    zmax = lm.Z_GALLERY * lm.LM_SCALE

    def put(panel, i, j, col):
        x0 = panel * (ny * px + gap) + j * px
        y0 = (nx - 1 - i) * px  # north up
        for yy in range(y0, y0 + px):
            base = (yy * w + x0) * 3
            for xx in range(px):
                pix[base + xx * 3:base + xx * 3 + 3] = bytes(col)

    for i in range(nx):
        for j in range(ny):
            k = i * ny + j
            sp = g.spans[k]
            for panel in (0, 1):
                lo_z, hi_z = (-INF, z_split) if panel == 0 else (z_split, INF)
                col = None
                vs = [t for t in (valid[k] or ()) if lo_z <= t < hi_z]
                rs = [t for t in vs if (i, j, t) in reach]
                if rs:
                    t = max(rs)
                    if t < -5:
                        col = (40, 150, 150)
                    elif t < 20:
                        col = (60, 170, 80)
                    else:
                        f = min(1.0, t / zmax)
                        col = (int(60 + 40 * f), int(170 - 60 * f), int(80 + 175 * f))
                elif vs:
                    col = (230, 140, 30)
                elif sp and any(lo_z <= hi < hi_z for _, hi, _ in sp):
                    col = (75, 75, 85)
                if col:
                    put(panel, i, j, col)
    for kind, src, dst, drop in falls:
        i, j, t = src
        put(0 if t < z_split else 1, i, j, (255, 40, 40) if kind != "void" else (255, 0, 255))
    for name, (i, j, t), ok in points:
        col = (255, 255, 255) if ok else (255, 0, 200)
        panel = 0 if t < z_split else 1
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                if 0 <= i + di < nx and 0 <= j + dj < ny:
                    put(panel, i + di, j + dj, col)
    write_png(path, w, h, pix)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main(argv=None):
    P = lm.PLAYER
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--radius", type=float, default=P["capsule_radius_cm"])
    ap.add_argument("--half-height", type=float, default=P["capsule_half_height_cm"])
    ap.add_argument("--step", type=float, default=P["max_step_height_cm"])
    ap.add_argument("--walkable-angle", type=float, default=P["walkable_floor_angle_deg"])
    ap.add_argument("--scale", type=float, default=lm.LM_SCALE)
    ap.add_argument("--cell", type=float, default=10.0, help="grid cell size in cm")
    ap.add_argument("--out", default=os.path.join(HERE, "..", "Docs", "Validation"))
    ap.add_argument("--tag", default="", help="suffix for output file names")
    a = ap.parse_args(argv)

    S = a.scale
    prims = lm.build(S)
    errors, warnings, lines = [], [], []

    def log(msg=""):
        lines.append(msg)
        print(msg)

    log("Leafy Manor blockout validation")
    log("  scale %.3f | capsule r=%.1f hh=%.1f (height %.1f) | MaxStepHeight %.1f | walkable %.2f deg | cell %.0f cm"
        % (S, a.radius, a.half_height, 2 * a.half_height, a.step, a.walkable_angle, a.cell))
    log("  primitives: %d (%d collidable)" % (len(prims), sum(p.collision != "none" for p in prims)))

    # ---- static metrics -------------------------------------------------------
    for name, rise, tread in lm.STAIR_SPECS:
        r, t = rise * S, tread * S
        ang = math.degrees(math.atan2(rise, tread))
        log("  %-12s riser %.1f cm, tread %.1f cm, slope %.1f deg" % (name, r, t, ang))
        if r > a.step:
            errors.append("%s riser %.1f cm > MaxStepHeight %.1f" % (name, r, a.step))
        if ang > a.walkable_angle:
            errors.append("%s slope %.1f deg > walkable angle" % (name, ang))
    for p in prims:
        if p.collision != "none" and abs(p.rot[0]) > a.walkable_angle:
            errors.append("%s pitch %.1f deg is not walkable" % (p.label, p.rot[0]))
    clear = {
        "front arch width": 2 * lm.ARCH_HW * S,
        "front arch height": lm.ARCH_H * S,
        "headroom under galleries": (lm.Z_GALLERY - lm.GALLERY_SLAB) * S,
        "gallery walkway (minus rail)": (lm.GAL_D - lm.RAIL_D) * S,
        "grand stair width": lm.STAIR_W * S - 2 * 20 * S,
    }
    for k, v in clear.items():
        need = 2 * a.half_height if ("height" in k or "headroom" in k) else 2 * a.radius
        log("  %-30s %6.1f cm (capsule needs %.1f)" % (k, v, need))
        if v < need * 1.5:
            (errors if v < need else warnings).append("%s only %.1f cm" % (k, v))

    # ---- walkability ----------------------------------------------------------
    nb = lm.NAV_BOUNDS
    bounds = ((nb[0][0] * S - 50, nb[0][1] * S + 50), (nb[1][0] * S - 50, nb[1][1] * S + 50))
    g, valid, node_near, neighbours = analyse(prims, a.radius, a.half_height, a.step, a.cell, bounds,
                                              z_top=lm.Z_CEIL * S - 1.0)
    sx, sy, sz = lm.scaled_point(lm.PLAYER_START, S)
    start = node_near(sx, sy, sz)
    if start is None:
        errors.append("no valid standing spot at PlayerStart")
        reach, falls = set(), []
    else:
        reach, falls = flood(start, neighbours)
    area = len(reach) * a.cell * a.cell / 1e4
    log("  walkable area reachable from PlayerStart: %.1f m2 (%d cells)" % (area, len(reach)))

    points = []
    for name, x, y, z in lm.TEST_POINTS:
        n = node_near(x * S, y * S, z * S, search=max(40.0, a.radius + 15), ztol=max(25.0, a.step))
        ok = n is not None and n in reach
        if n is None:
            n = (*g.ij(x * S, y * S), z * S)
        points.append((name, n, ok))
        log("  [%s] %-20s (%7.1f, %7.1f, %6.1f)" % ("OK " if ok else "BAD", name, x * S, y * S, z * S))
        if not ok:
            errors.append("test point %s is not reachable on foot" % name)

    # ledges
    agg = collections.defaultdict(lambda: [0, 0.0, None])
    for kind, src, dst, drop in falls:
        if kind == "fall" and dst in reach:
            key = "recoverable drop"
        elif kind == "void":
            key = "fall into VOID"
        elif kind == "fall_bad":
            key = "fall onto non-standable geometry"
        else:
            key = "fall into pocket with no walk-back"
        e = agg[key]
        e[0] += 1
        e[1] = max(e[1], drop or 0.0)
        e[2] = e[2] or g.xy(src[0], src[1])
    for key, (n, mx, where) in sorted(agg.items()):
        msg = "%s: %d edge cells, max drop %.0f cm, e.g. near (%.0f, %.0f)" % (key, n, mx, where[0], where[1])
        (warnings if key == "recoverable drop" else errors).append(msg)

    unreachable = sum(1 for k, v in enumerate(valid) if v for t in v
                      if (k // g.ny, k % g.ny, t) not in reach)
    log("  standable-but-unreachable cells (tops of props/rails, not reachable on foot): %d" % unreachable)

    os.makedirs(a.out, exist_ok=True)
    tag = ("_" + a.tag) if a.tag else ""
    png = os.path.join(a.out, "walkability_map%s.png" % tag)
    render_map(png, g, valid, reach, falls, points, z_split=200.0)
    log("  map: %s" % os.path.relpath(png, os.getcwd()))

    log("")
    for w in warnings:
        log("WARNING: " + w)
    for e in errors:
        log("ERROR:   " + e)
    log("RESULT: %s (%d errors, %d warnings)" % ("PASS" if not errors else "FAIL", len(errors), len(warnings)))
    with open(os.path.join(a.out, "validation_report%s.txt" % tag), "w") as f:
        f.write("\n".join(lines) + "\n")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
