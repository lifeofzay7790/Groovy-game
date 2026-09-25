"""
Leafy Manor - Entrance Hall layout (v2: follows the uploaded floor-plan diorama, uses the real model kit).

Pure Python (no `unreal` import). The same data drives:
  * leafy_manor_build_blockout.py   -> builds the level in Unreal (kit models, or cubes when DRESSED is off)
  * ../../Tools/validate_blockout.py -> offline walkability / collision checks

Unreal conventions: +X = North (exterior doors), +Y = East, +Z = Up, centimetres.
Rotations are (pitch, yaw, roll) degrees; +yaw turns +X towards +Y.

Positions are authored in design units (du) and multiplied by LM_SCALE. Kit models keep their real
centimetre size (LeafyManor/Models, see leafy_manor_kit.py) - 1 wall bay = 400 du = 272 cm at LM_SCALE 0.68.

Plan (north up):
    front arch -> porch + night garden
    north gallery over the arch, NW / NE corner landings reached by two 45-degree grand staircases
    west / east galleries over the north half, fireplace lounges mid-wall
    fountain in the centre ringed by planters and two crowned lions, carpet runner on the N-S axis
    south corners: globe / chess table / chests, vestibule + PlayerStart to the south
"""

import math

try:
    from leafy_manor_kit import KIT
except ImportError:  # pragma: no cover
    from .leafy_manor_kit import KIT

# ---------------------------------------------------------------------------
# Player + scale
# ---------------------------------------------------------------------------
PLAYER = {
    "mesh_height_cm": 97.8,              # measured from the character FBX
    "capsule_radius_cm": 28.0,           # ASSUMED - set to your character Blueprint values
    "capsule_half_height_cm": 50.0,
    "max_step_height_cm": 45.0,
    "walkable_floor_angle_deg": 44.765,
}
REFERENCE_HUMAN_CM = 180.0
GRANDEUR = 1.25
LM_SCALE = round(PLAYER["mesh_height_cm"] / REFERENCE_HUMAN_CM * GRANDEUR, 2)  # 0.68

# ---------------------------------------------------------------------------
# Design dimensions (du)
# ---------------------------------------------------------------------------
BAY = 400.0                 # one kit wall bay (272 cm)
WALL_T = 81.0               # kit wall depth (55 cm): back on the outer line, front = room face
SLAB_BOTTOM = -200.0
HALF = 1800.0               # hall interior: X, Y in [-1800, 1800] (9 x 9 bays, 24.5 m)

RISE, TREAD, N_TREADS = 18.0, 30.0, 41          # grand stairs: 12.2 cm risers, 20.4 cm treads
Z_GALLERY = (N_TREADS + 1) * RISE               # 756 du = 514 cm = one kit wall story
GALLERY_SLAB = 40.0
Z_UPPER = Z_GALLERY                             # upper wall row starts here
Z_CORNICE = 2 * Z_GALLERY                       # 1512
Z_CEIL = 1580.0

GAL_D = 350.0
NORTH_GAL_X0 = HALF - GAL_D                     # 1450
SIDE_GAL_X0 = 600.0
GAL_IN = HALF - GAL_D                           # 1450 = |Y| of side gallery inner edge

VEST_X0, VEST_HW = -2600.0, 600.0               # vestibule: X [-2600,-1800], Y [-600,600], one story
PORCH_X1, PORCH_HW = 2600.0, 500.0
ARCH_HW, ARCH_H = 104.0, 522.0                  # walk-through opening of SM_LM_Wall_Arch_01
RAIL_H, RAIL_D = 90.0, 44.0                     # kit balustrade (61 cm tall, 30 cm deep)

STAIR_W = 350.0
STAIR_RUN = N_TREADS * TREAD                    # 1230 du
LANDING = 350.0                                 # 45-degree landing square at each gallery corner
LOUNGE_X = -400.0
FOUNTAIN = (0.0, 0.0)
D2 = math.sqrt(0.5)


# ---------------------------------------------------------------------------
# Primitive container
# ---------------------------------------------------------------------------
class Prim:
    """One actor. Blockout prims are engine cubes/cylinders sized in du; kit prims place a real model
    (`mesh`) at `pivot` (du) with `rot` yaw, and carry its real bounding box (cm) for collision checks.

    collision: 'block' | 'none' | 'invisible' (hidden, blocks pawns, ignores camera)
    proxy:     True = collision-only stand-in for kit walls/stairs; hidden when the level is dressed.
    """

    __slots__ = ("label", "shape", "center", "size", "rot", "mat", "collision", "folder", "kind", "shadow",
                 "step_up", "mesh", "pivot", "offset", "mesh_scale", "proxy")

    def __init__(self, label, shape, center, size, rot=(0.0, 0.0, 0.0), mat="Stone", collision="block",
                 folder="Architecture", kind="", shadow=True, step_up=None, mesh=None, pivot=None, offset=None,
                 mesh_scale=(1.0, 1.0, 1.0), proxy=False):
        self.label, self.shape = label, shape
        self.center = tuple(float(v) for v in center)
        self.size = tuple(float(v) for v in size)
        self.rot = tuple(float(v) for v in rot)
        self.mat, self.collision, self.folder = mat, collision, folder
        self.kind = kind or label.split("_")[0]
        self.shadow = shadow
        self.step_up = (not folder.startswith(("Props", "Furniture"))) if step_up is None else step_up
        self.mesh, self.pivot, self.offset = mesh, pivot, offset
        self.mesh_scale = tuple(mesh_scale)
        self.proxy = proxy

    def scaled(self, s):
        if self.mesh is None:
            return Prim(self.label, self.shape, [v * s for v in self.center], [v * s for v in self.size], self.rot,
                        self.mat, self.collision, self.folder, self.kind, self.shadow, self.step_up, proxy=self.proxy)
        yaw = math.radians(self.rot[1])
        ox, oy, oz = self.offset
        px, py, pz = (v * s for v in self.pivot)
        c = (px + ox * math.cos(yaw) - oy * math.sin(yaw), py + ox * math.sin(yaw) + oy * math.cos(yaw), pz + oz)
        return Prim(self.label, self.shape, c, self.size, self.rot, self.mat, self.collision, self.folder, self.kind,
                    self.shadow, self.step_up, self.mesh, tuple(v * s for v in self.pivot), self.offset,
                    self.mesh_scale, self.proxy)


_OFFSETS = {  # bbox centre relative to the pivot, in model space (front = +Y)
    "bottom_center": lambda W, D, H: (0, 0, H / 2),
    "bottom_center_back": lambda W, D, H: (0, D / 2, H / 2),
    "bottom_center_front": lambda W, D, H: (0, -D / 2, H / 2),
    "top_center": lambda W, D, H: (0, 0, -H / 2),
    "top_center_back": lambda W, D, H: (0, D / 2, -H / 2),
    "back_center": lambda W, D, H: (0, D / 2, 0),
    "center": lambda W, D, H: (0, 0, 0),
    "stair": lambda W, D, H: (W / 2, 0, H / 2),
}


class _Layout:
    def __init__(self):
        self.prims, self._labels = [], set()

    def add(self, label, shape, center, size, **kw):
        if label in self._labels:
            raise ValueError("duplicate label " + label)
        self._labels.add(label)
        self.prims.append(Prim(label, shape, center, size, **kw))

    def box(self, label, x0, x1, y0, y1, z0, z1, **kw):
        x0, x1 = sorted((x0, x1))
        y0, y1 = sorted((y0, y1))
        self.add(label, "box", ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), (x1 - x0, y1 - y0, z1 - z0), **kw)

    def obox(self, label, cx, cy, cz, sx, sy, sz, yaw=0.0, pitch=0.0, **kw):
        self.add(label, "box", (cx, cy, cz), (sx, sy, sz), rot=(pitch, yaw, 0.0), **kw)

    def cyl(self, label, cx, cy, r, z0, z1, shape="cyl", **kw):
        self.add(label, shape, (cx, cy, (z0 + z1) / 2), (2 * r, 2 * r, z1 - z0), **kw)

    def kit(self, label, mesh, x, y, z, facing=0.0, yaw=None, scale=(1.0, 1.0, 1.0), collision=None, shape="box",
            folder="Props", kind=None, **kw):
        """Place kit model `mesh` with its pivot at (x, y, z) du, its front facing `facing` (yaw deg)."""
        k = KIT[mesh]
        W, D, H = (k["size"][i] * scale[i] for i in range(3))
        if collision is None:
            collision = "none" if k["collision"] == "none" else "block"
        kw.setdefault("mat", "Kit")
        self.add(label, shape, (x, y, z), (W, D, H), rot=(0.0, facing - 90.0 if yaw is None else yaw, 0.0),
                 mesh=mesh, pivot=(x, y, z), offset=_OFFSETS[k["pivot"]](W, D, H), mesh_scale=scale,
                 collision=collision, folder=folder, kind=kind or mesh.replace("SM_LM_", ""), **kw)

    def ramp(self, label, bx, by, z0, yaw, run, rise, width, thickness=20.0, **kw):
        """Box whose top face rises `rise` over horizontal `run` from (bx, by, z0) along `yaw`."""
        th = math.atan2(rise, run)
        ln = math.hypot(run, rise)
        c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        mx, mz = run / 2 + thickness / 2 * math.sin(th), z0 + rise / 2 - thickness / 2 * math.cos(th)
        self.obox(label, bx + mx * c, by + mx * s, mz, ln, width, thickness, yaw=yaw, pitch=math.degrees(th), **kw)


# ---------------------------------------------------------------------------
# Walls: kit bays (visual) + collision proxies
# ---------------------------------------------------------------------------
WALLS = {
    # name: (axis the wall runs along, room-face coordinate, facing yaw into the room, span)
    "N": ("y", HALF, 180.0, (-HALF, HALF)),
    "S": ("y", -HALF, 0.0, (-HALF, HALF)),
    "W": ("x", -HALF, 90.0, (-HALF, HALF)),
    "E": ("x", HALF, -90.0, (-HALF, HALF)),
    "VW": ("x", -VEST_HW, 90.0, (VEST_X0, -HALF)),
    "VE": ("x", VEST_HW, -90.0, (VEST_X0, -HALF)),
    "VS": ("y", VEST_X0, 0.0, (-VEST_HW, VEST_HW)),
}


def _bays(span):
    a0, a1 = span
    return [a0 + BAY * (i + 0.5) for i in range(int(round((a1 - a0) / BAY)))]


def _lower(wall, c):
    if wall == "N":
        return "SM_LM_Wall_Arch_01" if abs(c) < 1 else "SM_LM_Wall_Plain_01"
    if wall == "S":
        return None if abs(c) < VEST_HW else "SM_LM_Wall_Plain_01"
    if wall in ("W", "E"):
        return "SM_LM_Wall_DoorSingle_01" if abs(c - 1200) < 1 else "SM_LM_Wall_Plain_01"
    if wall == "VS":
        return "SM_LM_Wall_DoorDouble_01" if abs(c) < 1 else "SM_LM_Wall_Plain_01"
    return "SM_LM_Wall_Plain_01"


def _upper(wall, c):
    if wall.startswith("V"):
        return None                                   # vestibule is one story
    if wall in ("W", "E"):
        if abs(c - 1200) < 1:
            return "SM_LM_Wall_DoorSingle_01"          # gallery door
        return "SM_LM_Wall_Window_01" if c in (-1200.0, -400.0, 400.0) else "SM_LM_Wall_Plain_01"
    return "SM_LM_Wall_Window_01" if abs(abs(c) - 1200) < 1 else "SM_LM_Wall_Plain_01"


def _walls(L):
    for wall, (axis, face, facing, span) in WALLS.items():
        n = (math.cos(math.radians(facing)), math.sin(math.radians(facing)))  # into the room
        back = face - (n[0] if axis == "y" else n[1]) * WALL_T                 # outer line coordinate
        top = Z_UPPER if wall.startswith("V") else Z_CEIL
        for i, c in enumerate(_bays(span)):
            px, py = (back, c) if axis == "y" else (c, back)
            for row, z0, mesh in (("L", 0.0, _lower(wall, c)), ("U", Z_UPPER, _upper(wall, c))):
                if mesh:
                    L.kit("Wall%s_%s%d" % (wall, row, i + 1), mesh, px, py, z0, facing, collision="none",
                          folder="Architecture/Walls", kind="WallBay")
            # collision proxy for the bay (full height, minus openings)
            lo, hi = sorted((face, back))
            a0, a1 = c - BAY / 2, c + BAY / 2
            spans = [(a0, a1, 0.0 if _lower(wall, c) else Z_UPPER, top)]
            if _lower(wall, c) == "SM_LM_Wall_Arch_01":
                spans = [(a0, c - ARCH_HW, 0.0, top), (c + ARCH_HW, a1, 0.0, top), (c - ARCH_HW, c + ARCH_HW, ARCH_H, top)]
            for j, (s0, s1, z0, z1) in enumerate(spans):
                if z1 <= z0:
                    continue
                args = (s0, s1, lo, hi) if axis == "x" else (lo, hi, s0, s1)
                L.box("WallProxy%s_%d%s" % (wall, i + 1, "abc"[j]), *args, SLAB_BOTTOM if z0 == 0 else z0, z1,
                      mat="Wall", folder="Collision/WallProxies", kind="WallProxy", proxy=True)
        # solid backing just behind the kit bays (fills the gaps between bay pieces and above the cornice)
        o0, o1 = sorted((back, back - (n[0] if axis == "y" else n[1]) * 20))
        a0, a1 = span
        if not wall.startswith("V"):                  # run past the corners so they are closed too
            a0, a1 = a0 - WALL_T - 20, a1 + WALL_T + 20
        pieces = [(a0, a1, 0.0, top)]
        if wall == "S":
            pieces = [(a0, -VEST_HW, 0.0, top), (VEST_HW, a1, 0.0, top), (-VEST_HW, VEST_HW, Z_UPPER, top)]
        if wall == "N":
            pieces = [(a0, -ARCH_HW, 0.0, top), (ARCH_HW, a1, 0.0, top), (-ARCH_HW, ARCH_HW, ARCH_H, top)]
        for j, (s0, s1, z0, z1) in enumerate(pieces):
            args = (s0, s1, o0, o1) if axis == "x" else (o0, o1, s0, s1)
            L.box("WallBacking%s_%d" % (wall, j + 1), *args, 0.0 if z0 == 0 else z0, z1 + (40 if top == Z_CEIL else 0),
                  mat="Wall", collision="none", folder="Architecture/WallBacking", kind="WallBacking", shadow=True)
        if not wall.startswith("V"):   # cornice all round the hall
            for i, c in enumerate(_bays(span)):
                px, py = (face, c) if axis == "y" else (c, face)
                L.kit("Cornice%s_%d" % (wall, i + 1), "SM_LM_Cornice_01", px, py, Z_CORNICE, facing, collision="none",
                      folder="Architecture/Trim")
    # corner fillers (outside the room faces, never seen) + vestibule ceiling + hall ceiling
    for sx in (-1, 1):
        for sy in (-1, 1):
            L.box("WallCorner_%s%s" % ("N" if sx > 0 else "S", "E" if sy > 0 else "W"), sx * HALF, sx * (HALF + WALL_T),
                  sy * HALF, sy * (HALF + WALL_T), SLAB_BOTTOM, Z_CEIL, mat="Wall", folder="Collision/WallProxies",
                  kind="WallProxy", proxy=True)
    L.box("Ceiling_Hall", -HALF - WALL_T, HALF + WALL_T, -HALF - WALL_T, HALF + WALL_T, Z_CEIL, Z_CEIL + 40,
          mat="Wall", folder="Architecture/Ceiling", kind="Ceiling")
    L.box("Ceiling_Vestibule", VEST_X0 - WALL_T, -HALF - WALL_T, -VEST_HW - WALL_T, VEST_HW + WALL_T, Z_UPPER, Z_UPPER + 40,
          mat="Wall", folder="Architecture/Ceiling", kind="Ceiling")
    # stacked columns in the four room corners (close the joint between two walls)
    for sx in (-1, 1):
        for sy in (-1, 1):
            for row, z0 in (("L", 0.0), ("U", Z_UPPER)):
                L.kit("CornerColumn_%s%s%s" % ("N" if sx > 0 else "S", "E" if sy > 0 else "W", row), "SM_LM_Column_Plain_01",
                      sx * (HALF - 30), sy * (HALF - 30), z0, 0.0, scale=(1.0, 1.0, Z_UPPER * LM_SCALE / 487.0),
                      folder="Architecture/Columns", kind="Column", step_up=False)
    # columns framing the vestibule opening
    for sy in (-1, 1):
        L.kit("VestibuleColumn_%s" % ("E" if sy > 0 else "W"), "SM_LM_Column_Ornate_01", -HALF + 40, sy * (VEST_HW + 40), 0,
              0.0, scale=(1.0, 1.0, Z_UPPER * LM_SCALE / 487.0), folder="Architecture/Columns")


# ---------------------------------------------------------------------------
# Floors, galleries, stairs
# ---------------------------------------------------------------------------
def _floors(L):
    F = "Architecture/Floors"
    L.box("Floor_Hall", -HALF, HALF + WALL_T, -HALF, HALF, SLAB_BOTTOM, 0, mat="FloorChecker", folder=F, kind="Floor")
    L.box("Floor_Vestibule", VEST_X0 - WALL_T, -HALF, -VEST_HW, VEST_HW, SLAB_BOTTOM, 0, mat="FloorChecker", folder=F,
          kind="Floor")
    L.box("Floor_Porch", HALF + WALL_T, PORCH_X1, -PORCH_HW, PORCH_HW, SLAB_BOTTOM, 0, mat="FloorChecker", folder=F,
          kind="Floor")


def _galleries(L):
    G, z0, z1 = "Architecture/Galleries", Z_GALLERY - GALLERY_SLAB, Z_GALLERY
    L.box("Gallery_N", NORTH_GAL_X0, HALF, -GAL_IN, GAL_IN, z0, z1, mat="FloorChecker", folder=G, kind="GallerySlab")
    for sy, t in ((-1, "W"), (1, "E")):
        L.box("Gallery_" + t, SIDE_GAL_X0, HALF, sy * GAL_IN, sy * HALF, z0, z1, mat="FloorChecker", folder=G,
              kind="GallerySlab")
        # 45-degree landing at the inner corner where the stair arrives
        L.obox("Gallery_Landing" + t, NORTH_GAL_X0, sy * GAL_IN, (z0 + z1) / 2, LANDING, LANDING, GALLERY_SLAB,
               yaw=45.0, mat="FloorChecker", folder=G, kind="GallerySlab")
        # fascia trim on the west/east gallery front and south end
        L.kit("GalleryFascia%s_1" % t, "SM_LM_Trim_Band_01", 800, sy * GAL_IN, z1 - 48, -sy * 90.0, collision="none",
              folder="Architecture/Trim")
    for i, c in enumerate([-1000.0, -600.0, -200.0, 200.0, 600.0, 1000.0]):
        L.kit("GalleryFasciaN_%d" % (i + 1), "SM_LM_Trim_Band_01", NORTH_GAL_X0, c, Z_GALLERY - 48, 180.0,
              collision="none", folder="Architecture/Trim")
    # columns under the gallery edges
    for sy, t in ((-1, "W"), (1, "E")):
        for j, cx in enumerate((800.0, 1150.0)):
            L.kit("GalleryColumn%s_%d" % (t, j + 1), "SM_LM_Column_Plain_01", cx, sy * (GAL_IN + 60), 0, 0.0,
                  folder="Architecture/Columns", kind="Column", step_up=False)
    for j, cy in enumerate((-900.0, -450.0, 450.0, 900.0)):
        L.kit("GalleryColumnN_%d" % (j + 1), "SM_LM_Column_Ornate_01", NORTH_GAL_X0 + 60, cy, 0, 180.0,
              folder="Architecture/Columns", kind="Column", step_up=False)
    # balustrades (kit sections, 200 du) + invisible walls up to the ceiling
    R, B = "Architecture/Railings", "Collision/Blockers"
    bz = dict(mat="Invisible", collision="invisible", folder=B, kind="Blocker", shadow=False)
    xr = NORTH_GAL_X0 + RAIL_D / 2
    ends = GAL_IN - LANDING * D2                 # 1203: where the landing chamfer starts
    for i in range(12):
        L.kit("RailN_%02d" % (i + 1), "SM_LM_Balustrade_01", xr, -ends + 100 + i * 200, Z_GALLERY, 180.0, folder=R,
              kind="Balustrade")
    L.box("Blocker_RailN", NORTH_GAL_X0, NORTH_GAL_X0 + RAIL_D, -ends, ends, Z_GALLERY, Z_CEIL, **bz)
    for sy, t in ((-1, "W"), (1, "E")):
        yr = sy * (GAL_IN + RAIL_D / 2)
        for i in range(3):
            L.kit("Rail%s_%d" % (t, i + 1), "SM_LM_Balustrade_01", SIDE_GAL_X0 + 100 + i * 200, yr, Z_GALLERY,
                  -sy * 90.0, folder=R, kind="Balustrade")
        L.box("Blocker_Rail" + t, SIDE_GAL_X0, ends, sy * GAL_IN, sy * (GAL_IN + RAIL_D), Z_GALLERY, Z_CEIL, **bz)
        for i, cy in enumerate((GAL_IN + 100, GAL_IN + 250)):
            L.kit("Rail%sEnd_%d" % (t, i + 1), "SM_LM_Balustrade_01", SIDE_GAL_X0 + RAIL_D / 2, sy * cy, Z_GALLERY, 180.0,
                  folder=R, kind="Balustrade")
        L.box("Blocker_Rail%sEnd" % t, SIDE_GAL_X0, SIDE_GAL_X0 + RAIL_D, sy * GAL_IN, sy * HALF, Z_GALLERY, Z_CEIL, **bz)
        L.kit("RailPost%s_End" % t, "SM_LM_Post_01", SIDE_GAL_X0 + RAIL_D / 2, sy * (GAL_IN + RAIL_D / 2), Z_GALLERY, 0.0,
              folder=R, kind="Post")
        L.kit("RailPost%s_Landing" % t, "SM_LM_Post_01", ends, sy * (GAL_IN + RAIL_D / 2), Z_GALLERY, 0.0, folder=R,
              kind="Post")
        L.kit("RailPostN_%s" % t, "SM_LM_Post_01", xr, sy * ends, Z_GALLERY, 0.0, folder=R, kind="Post")


def _stairs(L):
    """Two 45-degree grand staircases rising from near the fountain to the NW / NE landings."""
    B = "Collision/Blockers"
    for sy, t in ((-1, "W"), (1, "E")):
        yaw = 45.0 * sy                                # ascend towards the corner: NW = -45, NE = +45
        d = (math.cos(math.radians(yaw)), math.sin(math.radians(yaw)))
        p = (-d[1], d[0])                              # left of the ascent
        mx = NORTH_GAL_X0 - LANDING / 2 * D2           # landing chamfer midpoint
        my = sy * (GAL_IN - LANDING / 2 * D2)
        bx, by = mx - STAIR_RUN * d[0], my - STAIR_RUN * d[1]
        F = "Architecture/Stairs_" + t
        L.kit("Stair%s" % t, "SM_LM_Stair_Grand_01", bx, by, 0, yaw=yaw, collision="none", folder=F, kind="Stair")
        for k in range(1, N_TREADS + 1):              # stacked step slabs (collision proxy)
            a0 = (k - 1) * TREAD
            ln = STAIR_RUN - a0
            cx, cy = bx + (a0 + ln / 2) * d[0], by + (a0 + ln / 2) * d[1]
            L.obox("Stair%s_Proxy%02d" % (t, k), cx, cy, (k - 0.5) * RISE, ln, STAIR_W, RISE, yaw=yaw, mat="Stairs",
                   folder=F + "/Proxy", kind="StairProxy", proxy=True)
        L.ramp("Stair%s_RampCollision" % t, bx - TREAD * d[0], by - TREAD * d[1], 0.0, yaw, STAIR_RUN + TREAD,
               Z_GALLERY, STAIR_W, mat="Invisible", collision="invisible", folder=F, kind="StairRamp", shadow=False)
        for side in (-1, 1):
            off = side * (STAIR_W / 2 - 10)
            L.kit("Stair%s_Balustrade%s" % (t, "L" if side > 0 else "R"), "SM_LM_StairBalustrade_01",
                  bx + off * p[0], by + off * p[1], 0, yaw=yaw, collision="none", folder=F, kind="StairBalustrade")
            cx, cy = bx + STAIR_RUN / 2 * d[0] + off * p[0], by + STAIR_RUN / 2 * d[1] + off * p[1]
            L.obox("Blocker_Stair%s%s" % (t, "L" if side > 0 else "R"), cx, cy, Z_CEIL / 2, STAIR_RUN, 20, Z_CEIL, yaw=yaw,
                   mat="Invisible", collision="invisible", folder=B, kind="Blocker", shadow=False)
            nx, ny = bx - 35 * d[0] + side * (STAIR_W / 2 - 33) * p[0], by - 35 * d[1] + side * (STAIR_W / 2 - 33) * p[1]
            L.kit("Stair%s_Newel%s" % (t, "L" if side > 0 else "R"), "SM_LM_NewelPost_01", nx, ny, 0, yaw=yaw,
                  folder=F, kind="Newel", step_up=False)


# ---------------------------------------------------------------------------
# Entrance, porch, exterior
# ---------------------------------------------------------------------------
def _porch_and_exterior(L):
    P, B = "Architecture/Porch", "Collision/Blockers"
    bz = dict(mat="Invisible", collision="invisible", folder=B, kind="Blocker", shadow=False)
    x0 = HALF + WALL_T
    for i in range(5):
        L.kit("PorchRailN_%d" % (i + 1), "SM_LM_Balustrade_01", PORCH_X1 - RAIL_D / 2, -400 + i * 200, 0, 180.0, folder=P)
    for sy, t in ((-1, "W"), (1, "E")):
        for i in range(3):
            L.kit("PorchRail%s_%d" % (t, i + 1), "SM_LM_Balustrade_01", x0 + 160 + i * 200, sy * (PORCH_HW - RAIL_D / 2), 0,
                  -sy * 90.0, folder=P)
        L.kit("PorchPost%s" % t, "SM_LM_NewelPost_01", PORCH_X1 - 33, sy * (PORCH_HW - 33), 0, 180.0, folder=P, step_up=False)
        L.kit("PorchLantern%s" % t, "SM_LM_Lantern_01", PORCH_X1 - 33, sy * (PORCH_HW - 33), 150, 180.0, collision="none",
              folder=P)
        L.box("Blocker_Porch" + t, x0, PORCH_X1 + 20, sy * PORCH_HW, sy * (PORCH_HW + 20), 0, 700, **bz)
    L.box("Blocker_PorchN", PORCH_X1, PORCH_X1 + 20, -PORCH_HW - 20, PORCH_HW + 20, 0, 700, **bz)
    E = "Exterior"
    kw = dict(collision="none", folder=E, shadow=False)
    L.box("Ext_Ground", -3000, 9500, -7000, 7000, -130, -110, mat="Ground", kind="ExtGround", **kw)
    L.kit("Ext_Fountain", "SM_LM_Fountain_01", 4700, 0, -110, 180.0, scale=(1.3, 1.3, 1.3), collision="none", folder=E)
    L.kit("Ext_Backdrop", "SM_LM_Backdrop_CastleCliff_01", 7200, -900, -110, 180.0, collision="none", folder=E)
    L.kit("Ext_Moon", "SM_LM_Moon_01", 7300, 2600, 2400, 180.0, collision="none", folder=E)
    for sy, t in ((-1, "W"), (1, "E")):
        L.box("Ext_Hedge" + t, 2750, 4200, sy * 420, sy * 520, -110, 10, mat="Foliage", kind="ExtHedge", **kw)
        for i, x in enumerate((3300, 4000, 5400)):
            L.cyl("Ext_Tree%s%d" % (t, i + 1), x, sy * 1100, 220, -110, 1000, shape="cone", mat="Foliage", kind="ExtTree", **kw)
        L.kit("Ext_Planter" + t, "SM_LM_Planter_Flowers_01", 2800, sy * 300, -110, 180.0, collision="none", folder=E)
    for n, a, b, c, d, e, f in (("N", 9500, 9600, -7100, 7100, -200, 5100), ("S", -3100, -3000, -7100, 7100, -200, 5100),
                                ("W", -3100, 9600, -7100, -7000, -200, 5100), ("E", -3100, 9600, 7000, 7100, -200, 5100),
                                ("Top", -3100, 9600, -7100, 7100, 5000, 5100)):
        L.box("Ext_Sky_" + n, a, b, c, d, e, f, mat="NightSky", kind="SkyBox", **kw)


# ---------------------------------------------------------------------------
# Hero pieces, furniture, dressing
# ---------------------------------------------------------------------------
def _centre(L):
    fx, fy = FOUNTAIN
    L.kit("Fountain", "SM_LM_Fountain_01", fx, fy, 0, 180.0, shape="cyl", folder="Props/Fountain", step_up=False)
    for sy, t in ((-1, "W"), (1, "E")):
        L.kit("Lion" + t, "SM_LM_LionStatue_01", fx, sy * 560, 0, 180.0, folder="Props/Statues")
    ring = [(15, "SM_LM_Plant_CrownPot_01"), (-15, "SM_LM_Plant_CrownPot_01"), (165, "SM_LM_Plant_Potted_01"),
            (-165, "SM_LM_Plant_Potted_01"), (125, "SM_LM_Urn_Gold_01"), (-125, "SM_LM_Urn_Gold_01")]
    for i, (ang, mesh) in enumerate(ring):
        a = math.radians(ang)
        L.kit("FountainPlanter_%d" % (i + 1), mesh, fx + 540 * math.cos(a), fy + 540 * math.sin(a), 0, ang + 180.0,
              folder="Props/Plants")
        if mesh.startswith("SM_LM_Urn"):
            L.kit("FountainFern_%d" % (i + 1), "SM_LM_Plant_Fern_01", fx + 540 * math.cos(a), fy + 540 * math.sin(a), 95,
                  ang, collision="none", folder="Props/Plants")
    # rugs + carpet runner along the N-S axis
    R = "Props/Rugs"
    L.kit("Rug_South", "SM_LM_Rug_Leaf_01", -1100, 0, 0.2, 0.0, collision="none", folder=R)
    L.kit("Rug_North", "SM_LM_Rug_Crown_01", 900, 0, 0.2, 180.0, collision="none", folder=R)
    L.kit("Rug_Vestibule", "SM_LM_Rug_Crown_01", -2200, 0, 0.2, 0.0, collision="none", folder=R)
    for i, x in enumerate((-430.0, -1800.0, 480.0, 1271.5, 1514.5, 1757.5, -2560.0)):
        L.kit("Runner_%d" % (i + 1), "SM_LM_Runner_01", x, 0, 0.5, 90.0, collision="none", folder=R)


def _lounge(L, sy):
    t = "W" if sy < 0 else "E"
    F = "Furniture/Lounge" + t
    wall = sy * HALF
    face = 90.0 if sy < 0 else -90.0   # facing into the room from this wall
    L.kit("Fireplace" + t, "SM_LM_Fireplace_01", LOUNGE_X, wall, 0, face, folder="Props/Fireplaces", step_up=False)
    L.kit("FireplaceFire" + t, "SM_LM_Fire_01", LOUNGE_X, wall - sy * 60, 12, face, scale=(1.2, 0.8, 0.9),
          collision="none", folder="Props/Fireplaces")
    cy = wall - sy * 400
    L.kit("LoungeRug" + t, "SM_LM_Rug_Lounge_01", LOUNGE_X, cy, 0.3, 0.0, collision="none", folder=F)
    L.kit("LoungeTable" + t, "SM_LM_OrnateTable_01", LOUNGE_X, cy, 0, face, folder=F)
    L.kit("LoungeCandles" + t, "SM_LM_Candelabra_Small_01", LOUNGE_X, cy, 84, face, collision="none", folder=F)
    for side, u in ((-1, "S"), (1, "N")):
        L.kit("LoungeSofa%s%s" % (t, u), "SM_LM_Sofa_01", LOUNGE_X + side * 235, cy, 0, 180.0 if side > 0 else 0.0, folder=F)
        L.kit("LoungeCushion%s%s" % (t, u), "SM_LM_Cushion_Leaf_01", LOUNGE_X + side * 240, cy, 50,
              180.0 if side > 0 else 0.0, collision="none", folder=F)
    L.kit("LoungeChair" + t, "SM_LM_Chair_01", LOUNGE_X, cy - sy * 250, 0, face + 180.0, folder=F)
    L.kit("LoungeOttoman" + t, "SM_LM_Ottoman_Purple_01", LOUNGE_X + 330, wall - sy * 120, 0, face, folder=F)
    L.kit("UpperBanner" + t, "SM_LM_Banner_Red_01", 0, wall, 1420, face, collision="none", folder="Props/Banners")


def _corners(L):
    S = "Furniture/SouthCorners"
    # south-west: globe, open treasure chest, plants
    L.kit("Globe", "SM_LM_Globe_01", -1400, -1400, 0, 45.0, folder=S)
    L.kit("TreasureChestOpen", "SM_LM_TreasureChest_Open_01", -1730, -1150, 0, 0.0, folder=S)
    L.kit("PlantSW", "SM_LM_Plant_CrownPot_01", -1600, -1600, 0, 45.0, folder="Props/Plants")
    L.kit("CandelabraSW", "SM_LM_Candelabra_Floor_01", -1250, -1720, 0, 90.0, folder="Props/Lighting")
    # south-east: chess table with chairs, chest, plants
    L.kit("ChessTable", "SM_LM_ChessTable_01", -1350, 1350, 0, 0.0, folder=S)
    L.kit("ChessChairS", "SM_LM_Chair_01", -1510, 1350, 0, 0.0, folder=S)
    L.kit("ChessChairN", "SM_LM_Chair_01", -1190, 1350, 0, 180.0, folder=S)
    L.kit("TreasureChest", "SM_LM_TreasureChest_01", -1730, 1150, 0, 0.0, folder=S)
    L.kit("PlantSE", "SM_LM_Plant_Potted_01", -1600, 1600, 0, -45.0, folder="Props/Plants")
    L.kit("CandelabraSE", "SM_LM_Candelabra_Floor_01", -1250, 1720, 0, -90.0, folder="Props/Lighting")
    # crowned dogs flanking the vestibule opening
    for sy, t in ((-1, "W"), (1, "E")):
        L.kit("DogStatue" + t, "SM_LM_DogStatue_0%d" % (1 if sy < 0 else 2), -HALF + 60, sy * 790, 0, 0.0,
              folder="Props/Statues")
        L.kit("UpperBannerS" + t, "SM_LM_Banner_Crown_01", -HALF, sy * 400, 1420, 0.0, collision="none",
              folder="Props/Banners")


def _under_galleries(L):
    U = "Furniture/UnderGalleries"
    for sy, t in ((-1, "W"), (1, "E")):
        wall, face = sy * HALF, (90.0 if sy < 0 else -90.0)
        if sy < 0:
            L.kit("Bookshelf" + t, "SM_LM_Bookshelf_01", 800, wall - sy * 41, 0, face, folder=U)
            L.kit("BookcaseCrown" + t, "SM_LM_Bookcase_Crown_01", 1600, wall - sy * 41, 0, face, folder=U)
        else:
            L.kit("GrandfatherClock", "SM_LM_GrandfatherClock_01", 800, wall, 0, face, folder=U)
            L.kit("ClockOrnate", "SM_LM_Clock_Ornate_01", 1600, wall, 0, face, folder=U)
        # gallery level: knights either side of the gallery door, busts on the north gallery
        for k, cx in enumerate((950.0, 1450.0)):
            L.kit("GalleryKnight%s%d" % (t, k + 1), "SM_LM_KnightArmor_01", cx, wall - sy * 45, Z_GALLERY, face,
                  folder="Props/Armor")
        L.kit("GalleryBust" + t, "SM_LM_Bust_0%d" % (1 if sy < 0 else 2), HALF - 50, sy * 700, Z_GALLERY, 180.0,
              folder="Props/Statues")
        # front-arch knights and banners (ground floor, under the north gallery)
        L.kit("DoorKnight" + t, "SM_LM_KnightArmor_01", HALF - 45, sy * 300, 0, 180.0, folder="Props/Armor")
        L.kit("DoorCandelabra" + t, "SM_LM_Candelabra_Floor_01", HALF - 40, sy * 560, 0, 180.0, folder="Props/Lighting")
        L.kit("NorthBanner" + t, "SM_LM_Banner_Crown_01", HALF, sy * 800, 690, 180.0, collision="none", folder="Props/Banners")
        # hanging greenery over the north rail
        for k, cy in enumerate((500.0, 1000.0)):
            L.kit("RailIvy%s%d" % (t, k), "SM_LM_Ivy_Hanging_0%d" % (k + 1), NORTH_GAL_X0, sy * cy, Z_GALLERY + 80, 180.0,
                  collision="none", folder="Props/Plants")
    L.kit("UpperBannerN", "SM_LM_Banner_Crown_01", HALF, 0, 1500, 180.0, collision="none", folder="Props/Banners")
    L.kit("VestibuleChest", "SM_LM_Crate_Crown_01", -2480, -480, 0, 45.0, folder="Furniture/Vestibule")
    L.kit("VestibulePlant", "SM_LM_Plant_Potted_01", -2480, 480, 0, -45.0, folder="Props/Plants")


def _lights_dressing(L):
    C = "Props/Chandeliers"
    for name, x, y, zc, sc in (("Fountain", 0, 0, Z_CEIL, 1.0), ("South", -1100, 0, Z_CEIL, 1.0), ("North", 1000, 0, Z_CEIL, 0.9),
                               ("Vestibule", -2200, 0, Z_UPPER, 0.6)):
        chain = 147.0 if zc == Z_CEIL else 0.0
        if chain:
            L.kit("Chain" + name, "SM_LM_Chain_01", x, y, zc, 0.0, scale=(1.5, 1.5, 1.0), collision="none", folder=C)
        L.kit("Chandelier" + name, "SM_LM_Chandelier_01", x, y, zc - chain, 0.0, scale=(sc, sc, sc), collision="none", folder=C)
    S = "Props/Sconces"
    n = 0
    for wall, (axis, face, facing, span) in WALLS.items():
        for c in _bays(span)[:-1]:
            b = c + BAY / 2                          # pilaster between two bays
            if wall == "S" and abs(b) < VEST_HW + 1:
                continue
            if wall in ("W", "E") and (abs(b - LOUNGE_X) < 350 or b > SIDE_GAL_X0 - 1):
                continue
            if wall == "N" and abs(b) < 250:
                continue
            px, py = (face, b) if axis == "y" else (b, face)
            mesh = "SM_LM_WallSconce_Bowl_01" if n % 2 else "SM_LM_WallSconce_Torch_01"
            L.kit("Sconce_%s%02d" % (wall, n), mesh, px, py, 380, facing, collision="none", folder=S)
            n += 1


# ---------------------------------------------------------------------------
# Gameplay markers, lights, test points
# ---------------------------------------------------------------------------
PLAYER_START = (-2300.0, 0.0, 0.0)
PLAYER_START_YAW = 0.0

_stair_mid = STAIR_RUN / 2
_bx = NORTH_GAL_X0 - LANDING / 2 * D2 - STAIR_RUN * D2
TEST_POINTS = [
    ("Spawn", -2300, 0, 0),
    ("VestibuleDoor", -2480, 0, 0),
    ("HallEntry", -1650, 0, 0),
    ("FountainSouth", -380, 0, 0),
    ("FountainNorth", 380, 0, 0),
    ("FountainWest", 0, -390, 0),
    ("FountainEast", 0, 390, 0),
    ("LoungeW_Hearth", LOUNGE_X, -HALF + 200, 0),
    ("LoungeE_Hearth", LOUNGE_X, HALF - 200, 0),
    ("SW_Corner", -1550, -1150, 0),
    ("SE_Chess", -1350, 1150, 0),
    ("StairW_Bottom", _bx - 60 * D2, -(_bx - 60 * D2), 0),
    ("StairW_Middle", _bx + _stair_mid * D2, -(_bx + _stair_mid * D2), Z_GALLERY / 2),
    ("StairW_Top", NORTH_GAL_X0 + 60 * D2 - LANDING / 2 * D2, -(GAL_IN + 60 * D2 - LANDING / 2 * D2), Z_GALLERY),
    ("StairE_Bottom", _bx - 60 * D2, _bx - 60 * D2, 0),
    ("StairE_Top", NORTH_GAL_X0 + 60 * D2 - LANDING / 2 * D2, GAL_IN + 60 * D2 - LANDING / 2 * D2, Z_GALLERY),
    ("GalleryW", 1200, -1600, Z_GALLERY),
    ("GalleryE", 1200, 1600, Z_GALLERY),
    ("GalleryN", 1625, 0, Z_GALLERY),
    ("GalleryW_SouthEnd", 700, -1620, Z_GALLERY),
    ("UnderGalleryW", 1200, -1620, 0),
    ("UnderGalleryE", 1200, 1620, 0),
    ("BehindStairNW", 1650, -1650, 0),
    ("FrontArch", 1830, 0, 0),
    ("Porch", 2300, 0, 0),
]

LIGHTS = [
    # label, type, (x, y, z) du, colour, intensity (cd / lux), attenuation du, rotation
    ("PL_LM_Chandelier_Fountain", "point", (0, 0, 1150), (1.0, 0.72, 0.42), 2500.0, 3500.0, None),
    ("PL_LM_Chandelier_South", "point", (-1100, 0, 1150), (1.0, 0.72, 0.42), 2000.0, 3000.0, None),
    ("PL_LM_Chandelier_North", "point", (1000, 0, 1150), (1.0, 0.72, 0.42), 1800.0, 3000.0, None),
    ("PL_LM_Chandelier_Vestibule", "point", (-2200, 0, 560), (1.0, 0.72, 0.42), 700.0, 1400.0, None),
    ("PL_LM_Fireplace_W", "point", (LOUNGE_X, -HALF + 200, 120), (1.0, 0.45, 0.15), 600.0, 1100.0, None),
    ("PL_LM_Fireplace_E", "point", (LOUNGE_X, HALF - 200, 120), (1.0, 0.45, 0.15), 600.0, 1100.0, None),
    ("PL_LM_Fountain", "point", (0, 0, 300), (0.25, 0.5, 1.0), 500.0, 1000.0, None),
    ("PL_LM_ExteriorFountain", "point", (4700, 0, 250), (0.25, 0.5, 1.0), 800.0, 1500.0, None),
    ("PL_LM_GalleryW", "point", (1200, -1600, Z_GALLERY + 300), (1.0, 0.7, 0.4), 300.0, 1200.0, None),
    ("PL_LM_GalleryE", "point", (1200, 1600, Z_GALLERY + 300), (1.0, 0.7, 0.4), 300.0, 1200.0, None),
    ("DL_LM_Moon", "directional", (2200, 0, 1800), (0.55, 0.65, 1.0), 2.5, None, (-35.0, 200.0, 0.0)),
    ("SL_LM_Sky", "sky", (0, 0, 1200), (0.45, 0.55, 1.0), 0.35, None, None),
]

NAV_BOUNDS = ((VEST_X0 - WALL_T, PORCH_X1), (-HALF - WALL_T, HALF + WALL_T), (SLAB_BOTTOM, Z_GALLERY + 300))

STAIR_SPECS = [("GrandStairs", RISE, TREAD)]

MATERIALS = {
    # blockout colours (used for cubes and collision proxies): base, roughness, metallic, emissive, strength
    "Floor": ((0.62, 0.55, 0.45), 0.35, 0.0, (0, 0, 0), 0.0),
    "FloorChecker": ((0.62, 0.55, 0.45), 0.35, 0.0, (0, 0, 0), 0.0),  # replaced by the marble checker when dressed
    "FloorDark": ((0.16, 0.14, 0.13), 0.35, 0.0, (0, 0, 0), 0.0),
    "Wall": ((0.10, 0.10, 0.12), 0.8, 0.0, (0, 0, 0), 0.0),
    "Stone": ((0.45, 0.42, 0.38), 0.7, 0.0, (0, 0, 0), 0.0),
    "Stairs": ((0.40, 0.37, 0.33), 0.6, 0.0, (0, 0, 0), 0.0),
    "Gold": ((0.85, 0.60, 0.20), 0.3, 1.0, (0, 0, 0), 0.0),
    "Wood": ((0.22, 0.11, 0.05), 0.6, 0.0, (0, 0, 0), 0.0),
    "Fabric": ((0.16, 0.05, 0.25), 0.9, 0.0, (0, 0, 0), 0.0),
    "Carpet": ((0.03, 0.05, 0.25), 0.95, 0.0, (0, 0, 0), 0.0),
    "Metal": ((0.50, 0.50, 0.55), 0.35, 1.0, (0, 0, 0), 0.0),
    "Plant": ((0.05, 0.22, 0.05), 0.8, 0.0, (0, 0, 0), 0.0),
    "NightSky": ((0.0, 0.0, 0.0), 1.0, 0.0, (0.01, 0.02, 0.06), 1.0),
    "Foliage": ((0.01, 0.04, 0.03), 0.9, 0.0, (0, 0, 0), 0.0),
    "Ground": ((0.03, 0.04, 0.05), 0.9, 0.0, (0, 0, 0), 0.0),
    "Kit": ((0.55, 0.50, 0.42), 0.6, 0.0, (0, 0, 0), 0.0),       # cube stand-in for a kit model
    "Invisible": None,
}


def build_design():
    L = _Layout()
    _floors(L)
    _walls(L)
    _galleries(L)
    _stairs(L)
    _porch_and_exterior(L)
    _centre(L)
    for sy in (-1, 1):
        _lounge(L, sy)
    _corners(L)
    _under_galleries(L)
    _lights_dressing(L)
    return L.prims


def build(scale=None):
    s = LM_SCALE if scale is None else scale
    return [p.scaled(s) for p in build_design()]


def scaled_point(p, scale=None):
    s = LM_SCALE if scale is None else scale
    return tuple(v * s for v in p)
