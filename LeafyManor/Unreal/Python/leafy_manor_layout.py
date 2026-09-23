"""
Leafy Manor - Entrance Hall: playable blockout layout (pure data).

This module has NO `unreal` import so the exact same data drives:
  * leafy_manor_build_blockout.py   -> spawns the blockout inside Unreal Editor
  * ../../Tools/validate_blockout.py -> offline walkability / collision checks

Conventions (Unreal):
  +X = North (towards the exterior front doors), +Y = East, +Z = Up, centimetres.
  Rotations are (pitch, yaw, roll) in degrees; +yaw turns +X towards +Y,
  +pitch tilts +X upwards.

Everything below is authored in "design units" (du) at human scale
(180 cm reference person) and multiplied by LM_SCALE, so the whole room can be
re-fitted to the player character by changing one number.
"""

import math

# ---------------------------------------------------------------------------
# Player + scale
# ---------------------------------------------------------------------------
# Measured from the character FBX (tripo_convert_*.fbx, UnitScaleFactor 100,
# imported at scale 1.0). Capsule values are ASSUMPTIONS - replace them with the
# values from your character Blueprint and re-run the validator.
PLAYER = {
    "mesh_height_cm": 97.8,
    "capsule_radius_cm": 28.0,
    "capsule_half_height_cm": 50.0,
    "max_step_height_cm": 45.0,          # CharacterMovement default
    "walkable_floor_angle_deg": 44.765,  # CharacterMovement default
}

REFERENCE_HUMAN_CM = 180.0
# >1 makes the architecture feel grander than "real life" around the player.
GRANDEUR = 1.25
LM_SCALE = round(PLAYER["mesh_height_cm"] / REFERENCE_HUMAN_CM * GRANDEUR, 2)  # 0.68

# ---------------------------------------------------------------------------
# Design dimensions (du)
# ---------------------------------------------------------------------------
BAY = 400.0             # modular wall bay width
WALL_T = 60.0           # wall thickness
SLAB_BOTTOM = -200.0    # every floor slab / wall extends down to here (no gaps)

RISE = 16.0             # stair riser
TREAD = 30.0            # grand stair tread
ENTRY_TREAD = 40.0      # entry steps tread

Z_MAIN = 0.0            # main hall floor
Z_VEST = -6 * RISE      # sunken entry vestibule (-96)
Z_GALLERY = 36 * RISE   # upper gallery floor (576)
GALLERY_SLAB = 40.0
Z_CEIL = 1600.0

HALL_X0, HALL_X1 = -1400.0, 1800.0   # 8 bays north-south
HALL_HW = 1400.0                     # half width -> 7 bays east-west
VEST_X0, VEST_HW = -2200.0, 600.0    # vestibule: 2 bays deep, 3 bays wide

GAL_D = 350.0                        # gallery depth
SIDE_GAL_X0 = 800.0                  # side galleries start here (stair top)
NORTH_GAL_X0 = HALL_X1 - GAL_D       # 1450
GAL_INNER = HALL_HW - GAL_D          # 1050 (|Y| of side gallery inner edge)

FRONT_DOOR_HW, FRONT_DOOR_H = 200.0, 520.0
SIDE_DOOR_X0, SIDE_DOOR_X1, SIDE_DOOR_H = 1100.0, 1300.0, 360.0
RAIL_H, RAIL_T = 90.0, 20.0

STAIR_STEPS = int(Z_GALLERY / RISE) - 1          # 35 boxes, last riser = gallery edge
STAIR_X0 = SIDE_GAL_X0 - STAIR_STEPS * TREAD     # -250 (first riser)

FOUNTAIN_X = -500.0
PORCH_X1, PORCH_HW = 2600.0, 500.0


# ---------------------------------------------------------------------------
# Primitive container
# ---------------------------------------------------------------------------
class Prim:
    """One blockout piece = one StaticMeshActor in Unreal.

    shape:     'box' | 'cyl' | 'cone' | 'sphere' (engine basic shapes, 100 cm, centred pivot)
    center:    (x, y, z) world centre
    size:      (sx, sy, sz) full extents before rotation
    rot:       (pitch, yaw, roll) degrees
    mat:       material key (see MATERIALS)
    collision: 'block' (BlockAll) | 'none' | 'invisible' (hidden in game, blocks pawns, ignores camera)
    kind:      element type, used later to swap proxies for final Blender meshes
    """

    __slots__ = ("label", "shape", "center", "size", "rot", "mat", "collision", "folder", "kind", "shadow", "step_up")

    def __init__(self, label, shape, center, size, rot=(0.0, 0.0, 0.0), mat="Stone",
                 collision="block", folder="Architecture", kind="", shadow=True, step_up=None):
        self.label = label
        self.shape = shape
        self.center = tuple(float(v) for v in center)
        self.size = tuple(float(v) for v in size)
        self.rot = tuple(float(v) for v in rot)
        self.mat = mat
        self.collision = collision
        self.folder = folder
        self.kind = kind or label.split("_")[0]
        self.shadow = shadow
        # Furniture/props get CanCharacterStepUpOn = No so the player never climbs onto them.
        self.step_up = (not folder.startswith(("Props", "Furniture"))) if step_up is None else step_up

    def scaled(self, s):
        return Prim(self.label, self.shape, [v * s for v in self.center], [v * s for v in self.size],
                    self.rot, self.mat, self.collision, self.folder, self.kind, self.shadow, self.step_up)


class _Layout:
    def __init__(self):
        self.prims = []
        self._labels = set()

    def add(self, label, shape, center, size, **kw):
        if label in self._labels:
            raise ValueError("duplicate label " + label)
        self._labels.add(label)
        self.prims.append(Prim(label, shape, center, size, **kw))

    def box(self, label, x0, x1, y0, y1, z0, z1, **kw):
        x0, x1 = sorted((x0, x1))
        y0, y1 = sorted((y0, y1))
        self.add(label, "box", ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), (x1 - x0, y1 - y0, z1 - z0), **kw)

    def cyl(self, label, cx, cy, r, z0, z1, shape="cyl", **kw):
        self.add(label, shape, (cx, cy, (z0 + z1) / 2), (2 * r, 2 * r, z1 - z0), **kw)

    def ramp(self, label, xa, za, xb, zb, y0, y1, thickness=20.0, **kw):
        """Box whose TOP face runs from (xa, za) to (xb, zb) along +X (xb > xa)."""
        y0, y1 = sorted((y0, y1))
        theta = math.atan2(zb - za, xb - xa)
        length = math.hypot(xb - xa, zb - za)
        mx, mz = (xa + xb) / 2, (za + zb) / 2
        cx = mx + thickness / 2 * math.sin(theta)
        cz = mz - thickness / 2 * math.cos(theta)
        self.add(label, "box", (cx, (y0 + y1) / 2, cz), (length, y1 - y0, thickness),
                 rot=(math.degrees(theta), 0.0, 0.0), **kw)

    def frame(self, anchor, yaw, prefix, folder, kind):
        return _Frame(self, anchor, yaw, prefix, folder, kind)


class _Frame:
    """Element-local placement: local +X = the direction the element faces."""

    def __init__(self, lay, anchor, yaw, prefix, folder, kind):
        self.lay, self.anchor, self.yaw = lay, anchor, yaw
        self.prefix, self.folder, self.kind = prefix, folder, kind
        self._c, self._s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))

    def world(self, lx, ly, lz=0.0):
        ax, ay, az = self.anchor
        return (ax + lx * self._c - ly * self._s, ay + lx * self._s + ly * self._c, az + lz)

    def box(self, label, x0, x1, y0, y1, z0, z1, **kw):
        kw.setdefault("folder", self.folder)
        kw.setdefault("kind", self.kind)
        cx, cy, cz = self.world((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
        self.lay.add(self.prefix + label, "box", (cx, cy, cz), (x1 - x0, y1 - y0, z1 - z0),
                     rot=(0.0, self.yaw, 0.0), **kw)

    def cyl(self, label, lx, ly, r, z0, z1, shape="cyl", **kw):
        kw.setdefault("folder", self.folder)
        kw.setdefault("kind", self.kind)
        cx, cy, cz = self.world(lx, ly, (z0 + z1) / 2)
        self.lay.add(self.prefix + label, shape, (cx, cy, cz), (2 * r, 2 * r, z1 - z0), **kw)


# ---------------------------------------------------------------------------
# Architecture
# ---------------------------------------------------------------------------
def _subtract(ranges, lo, hi):
    out = []
    for a, b in ranges:
        if hi <= a or lo >= b:
            out.append((a, b))
            continue
        if lo > a:
            out.append((a, lo))
        if hi < b:
            out.append((hi, b))
    return out


def _wall_run(L, name, axis, face, outward, a0, a1, openings=(), z0=SLAB_BOTTOM, z1=Z_CEIL):
    """Wall split into BAY-wide modules. `face` = room-side face coordinate on the other axis,
    `outward` = +1/-1 direction the thickness grows. openings = [(a_lo, a_hi, z_lo, z_hi), ...]."""
    t0, t1 = sorted((face, face + outward * WALL_T))
    n_bays = int(round((a1 - a0) / BAY))
    for b in range(n_bays):
        b0, b1 = a0 + b * BAY, min(a0 + (b + 1) * BAY, a1)
        ops = [o for o in openings if o[0] < b1 and o[1] > b0]
        cuts = sorted({b0, b1} | {min(max(v, b0), b1) for o in ops for v in o[:2]})
        piece = 0
        for s0, s1 in zip(cuts, cuts[1:]):
            spans = [(z0, z1)]
            for o in ops:
                if o[0] <= s0 and o[1] >= s1:
                    spans = _subtract(spans, o[2], o[3])
            for za, zb in spans:
                label = "Wall_%s_%02d%s" % (name, b + 1, "" if len(cuts) == 2 and len(spans) == 1 else chr(97 + piece))
                piece += 1
                if axis == "x":
                    L.box(label, s0, s1, t0, t1, za, zb, mat="Wall", folder="Architecture/Walls", kind="WallBay")
                else:
                    L.box(label, t0, t1, s0, s1, za, zb, mat="Wall", folder="Architecture/Walls", kind="WallBay")


def _architecture(L):
    F = "Architecture/Floors"
    # Floors (slabs run down to SLAB_BOTTOM so nothing is hollow).
    L.box("Floor_MainHall", HALL_X0, HALL_X1 + WALL_T, -HALL_HW - WALL_T, HALL_HW + WALL_T, SLAB_BOTTOM, Z_MAIN,
          mat="Floor", folder=F, kind="Floor")
    L.box("Floor_Vestibule", VEST_X0, HALL_X0, -VEST_HW, VEST_HW, SLAB_BOTTOM, Z_VEST, mat="Floor", folder=F, kind="Floor")
    L.box("Floor_VestibuleDoorSill", VEST_X0 - WALL_T, VEST_X0, -FRONT_DOOR_HW, FRONT_DOOR_HW, SLAB_BOTTOM, Z_VEST,
          mat="Floor", folder=F, kind="Floor")
    L.box("Floor_Porch", HALL_X1 + WALL_T, PORCH_X1, -PORCH_HW, PORCH_HW, SLAB_BOTTOM, Z_MAIN, mat="Floor", folder=F, kind="Floor")

    # Walls (8 x 7 bay hall + vestibule), corners as separate modules.
    W = "Architecture/Walls"
    for side, tag in ((-1, "W"), (1, "E")):
        _wall_run(L, tag, "x", side * HALL_HW, side, HALL_X0, HALL_X1, openings=[
            (SIDE_DOOR_X0, SIDE_DOOR_X1, Z_MAIN, SIDE_DOOR_H),  # ground-floor side door
            (SIDE_DOOR_X0, SIDE_DOOR_X1, Z_GALLERY, Z_GALLERY + SIDE_DOOR_H),  # gallery door (same model)
        ])
    _wall_run(L, "N", "y", HALL_X1, 1, -HALL_HW, HALL_HW, openings=[(-FRONT_DOOR_HW, FRONT_DOOR_HW, Z_MAIN, FRONT_DOOR_H)])
    _wall_run(L, "SW", "y", HALL_X0, -1, -HALL_HW, -VEST_HW)
    _wall_run(L, "SE", "y", HALL_X0, -1, VEST_HW, HALL_HW)
    _wall_run(L, "VestW", "x", -VEST_HW, -1, VEST_X0, HALL_X0)
    _wall_run(L, "VestE", "x", VEST_HW, 1, VEST_X0, HALL_X0)
    _wall_run(L, "VestS", "y", VEST_X0, -1, -VEST_HW, VEST_HW,
              openings=[(-FRONT_DOOR_HW, FRONT_DOOR_HW, Z_VEST, Z_VEST + FRONT_DOOR_H)])  # same doors as the front
    for label, x0, y0 in (("NW", HALL_X1, -HALL_HW - WALL_T), ("NE", HALL_X1, HALL_HW),
                          ("SW", HALL_X0 - WALL_T, -HALL_HW - WALL_T), ("SE", HALL_X0 - WALL_T, HALL_HW),
                          ("VestSW", VEST_X0 - WALL_T, -VEST_HW - WALL_T), ("VestSE", VEST_X0 - WALL_T, VEST_HW)):
        L.box("WallCorner_" + label, x0, x0 + WALL_T, y0, y0 + WALL_T, SLAB_BOTTOM, Z_CEIL, mat="Wall", folder=W, kind="WallCorner")

    # Ceiling
    C = "Architecture/Ceiling"
    L.box("Ceiling_MainHall", HALL_X0 - WALL_T, HALL_X1 + WALL_T, -HALL_HW - WALL_T, HALL_HW + WALL_T, Z_CEIL, Z_CEIL + 40,
          mat="Wall", folder=C, kind="Ceiling")
    L.box("Ceiling_Vestibule", VEST_X0 - WALL_T, HALL_X0 - WALL_T, -VEST_HW - WALL_T, VEST_HW + WALL_T, Z_CEIL, Z_CEIL + 40,
          mat="Wall", folder=C, kind="Ceiling")

    # Galleries (U-shape: west, north, east) at Z_GALLERY.
    G = "Architecture/Galleries"
    for side, tag in ((-1, "W"), (1, "E")):
        L.box("Gallery_" + tag, SIDE_GAL_X0, HALL_X1, side * GAL_INNER, side * HALL_HW, Z_GALLERY - GALLERY_SLAB, Z_GALLERY,
              mat="Floor", folder=G, kind="GallerySlab")
    L.box("Gallery_N", NORTH_GAL_X0, HALL_X1, -GAL_INNER, GAL_INNER, Z_GALLERY - GALLERY_SLAB, Z_GALLERY,
          mat="Floor", folder=G, kind="GallerySlab")

    # Gallery balustrades (visible, BlockAll) + invisible walls up to the ceiling (no jumping off).
    R = "Architecture/Railings"
    B = "Collision/Blockers"
    for side, tag in ((-1, "W"), (1, "E")):
        y0, y1 = side * GAL_INNER, side * (GAL_INNER + RAIL_T)
        L.box("Rail_Gallery" + tag, SIDE_GAL_X0, NORTH_GAL_X0 + RAIL_T, y0, y1, Z_GALLERY, Z_GALLERY + RAIL_H,
              mat="Stone", folder=R, kind="Balustrade")
        L.box("Blocker_Gallery" + tag, SIDE_GAL_X0, NORTH_GAL_X0 + RAIL_T, y0, y1, Z_GALLERY + RAIL_H, Z_CEIL,
              mat="Invisible", collision="invisible", folder=B, kind="Blocker", shadow=False)
    L.box("Rail_GalleryN", NORTH_GAL_X0, NORTH_GAL_X0 + RAIL_T, -GAL_INNER - RAIL_T, GAL_INNER + RAIL_T, Z_GALLERY,
          Z_GALLERY + RAIL_H, mat="Stone", folder=R, kind="Balustrade")
    L.box("Blocker_GalleryN", NORTH_GAL_X0, NORTH_GAL_X0 + RAIL_T, -GAL_INNER - RAIL_T, GAL_INNER + RAIL_T,
          Z_GALLERY + RAIL_H, Z_CEIL, mat="Invisible", collision="invisible", folder=B, kind="Blocker", shadow=False)

    # Columns supporting the gallery edge.
    for side, tag in ((-1, "W"), (1, "E")):
        for i, (cx, cy) in enumerate(((1100.0, GAL_INNER + 30), (NORTH_GAL_X0 + 30, GAL_INNER + 30), (NORTH_GAL_X0 + 30, 450.0))):
            L.box("Column_%s%d" % (tag, i + 1), cx - 30, cx + 30, side * (cy - 30), side * (cy + 30), Z_MAIN,
                  Z_GALLERY - GALLERY_SLAB, mat="Stone", folder="Architecture/Columns", kind="Column")


def _grand_stairs(L):
    """Straight grand staircases along the west and east walls rising north to the side galleries."""
    for side, tag in ((-1, "W"), (1, "E")):
        folder = "Architecture/Stairs_" + tag
        yi, yo = side * GAL_INNER, side * HALL_HW
        for i in range(1, STAIR_STEPS + 1):
            L.box("Stair%s_Step%02d" % (tag, i), STAIR_X0 + TREAD * (i - 1), SIDE_GAL_X0, yi, yo,
                  RISE * (i - 1), RISE * i, mat="Stairs", folder=folder, kind="StairStep")
        # Smooth invisible ramp over the step nosings (camera/character glide instead of stepping).
        L.ramp("Stair%s_RampCollision" % tag, STAIR_X0 - TREAD, Z_MAIN, SIDE_GAL_X0, Z_GALLERY, yi, yo,
               mat="Invisible", collision="invisible", folder=folder, kind="StairRamp", shadow=False)
        # Sloped handrail (visual) + newel post + invisible side wall.
        yr0, yr1 = yi, yi + side * RAIL_T
        L.ramp("Stair%s_Handrail" % tag, STAIR_X0, RISE + 70, SIDE_GAL_X0, Z_GALLERY + 70, yr0, yr1, thickness=70,
               mat="Stone", collision="none", folder=folder, kind="StairBalustrade")
        L.box("Stair%s_Newel" % tag, STAIR_X0 - 5, STAIR_X0 + 35, yi - side * 10, yi + side * 30, Z_MAIN, 130,
              mat="Stone", folder=folder, kind="Newel")
        L.box("Blocker_Stair" + tag, STAIR_X0, SIDE_GAL_X0, yr0, yr1, Z_MAIN, Z_CEIL,
              mat="Invisible", collision="invisible", folder="Collision/Blockers", kind="Blocker", shadow=False)


def _entry(L):
    """Sunken vestibule: 6 wide steps up to the main hall, balustrade + crowned dog statues."""
    folder = "Architecture/EntrySteps"
    for k in range(1, 6):
        L.box("EntrySteps_Step%d" % k, HALL_X0 - ENTRY_TREAD * (6 - k), HALL_X0, -300, 300,
              Z_VEST + RISE * (k - 1), Z_VEST + RISE * k, mat="Stairs", folder=folder, kind="StairStep")
    L.ramp("EntrySteps_RampCollision", HALL_X0 - ENTRY_TREAD * 6, Z_VEST, HALL_X0, Z_MAIN, -300, 300,
           mat="Invisible", collision="invisible", folder=folder, kind="StairRamp", shadow=False)
    for side, tag in ((-1, "W"), (1, "E")):
        # Solid stone cheek walls so nobody walks off the side of the steps.
        L.box("EntrySteps_Cheek" + tag, HALL_X0 - ENTRY_TREAD * 5, HALL_X0, side * 300, side * 330, Z_VEST, Z_MAIN + RAIL_H,
              mat="Stone", folder=folder, kind="StairCheekWall")
        L.box("EntryRail_" + tag, HALL_X0, HALL_X0 + RAIL_T, side * 360, side * VEST_HW, Z_MAIN, Z_MAIN + RAIL_H,
              mat="Stone", folder="Architecture/Railings", kind="Balustrade")
        L.box("EntryPillar_" + tag, HALL_X0, HALL_X0 + 60, side * 300, side * 360, Z_MAIN, 150,
              mat="Stone", folder="Architecture/Railings", kind="Pedestal")
        L.box("DogStatue_" + tag, HALL_X0 + 5, HALL_X0 + 55, side * 310, side * 350, 150, 225,
              mat="Stone", folder="Props/Statues", kind="DogStatue")
    # Inner doors to the rest of the manor (closed) - same grand double door as the front entrance.
    for side, tag in ((-1, "W"), (1, "E")):
        L.box("Door_Vestibule" + tag, VEST_X0 - 40, VEST_X0 - 26, 0, side * FRONT_DOOR_HW, Z_VEST, Z_VEST + FRONT_DOOR_H,
              mat="Wood", folder="Architecture/Doors", kind="DoorGrandLeaf")


def _front_doors_and_porch(L):
    D = "Architecture/Doors"
    # Front double doors, swung open outwards (hinged on the exterior face).
    for side, tag in ((-1, "W"), (1, "E")):
        L.box("Door_Front" + tag, HALL_X1 + WALL_T, HALL_X1 + WALL_T + FRONT_DOOR_HW, side * FRONT_DOOR_HW,
              side * (FRONT_DOOR_HW + 14), Z_MAIN, FRONT_DOOR_H, mat="Wood", folder=D, kind="DoorGrandLeaf")
    P = "Architecture/Porch"
    x0 = HALL_X1 + WALL_T
    L.box("PorchRail_N", PORCH_X1 - RAIL_T, PORCH_X1, -PORCH_HW, PORCH_HW, Z_MAIN, RAIL_H, mat="Stone", folder=P, kind="Balustrade")
    for side, tag in ((-1, "W"), (1, "E")):
        L.box("PorchRail_" + tag, x0, PORCH_X1, side * (PORCH_HW - RAIL_T), side * PORCH_HW, Z_MAIN, RAIL_H,
              mat="Stone", folder=P, kind="Balustrade")
        L.box("Blocker_Porch" + tag, x0, PORCH_X1 + 20, side * PORCH_HW, side * (PORCH_HW + 20), Z_MAIN, 700,
              mat="Invisible", collision="invisible", folder="Collision/Blockers", kind="Blocker", shadow=False)
    L.box("Blocker_PorchN", PORCH_X1, PORCH_X1 + 20, -PORCH_HW - 20, PORCH_HW + 20, Z_MAIN, 700,
          mat="Invisible", collision="invisible", folder="Collision/Blockers", kind="Blocker", shadow=False)


def _exterior(L):
    """Night garden seen through the front doors. Visual only (unreachable, no collision)."""
    E = "Exterior"
    kw = dict(collision="none", folder=E, shadow=False)
    L.box("Ext_Ground", -3000, 7600, -7000, 7000, -130, -110, mat="Ground", kind="ExtGround", **kw)
    L.box("Ext_Path", PORCH_X1, 4300, -150, 150, -110, -108, mat="Floor", kind="ExtPath", **kw)
    for side, tag in ((-1, "W"), (1, "E")):
        L.box("Ext_Hedge" + tag, 2750, 4200, side * 420, side * 520, -110, 10, mat="Foliage", kind="ExtHedge", **kw)
        for i, x in enumerate((3300, 4000, 5400, 6100)):
            L.cyl("Ext_Tree%s%d" % (tag, i + 1), x, side * 1000, 220, -110, 1000, shape="cone", mat="Foliage", kind="ExtTree", **kw)
    L.cyl("Ext_Fountain_Basin", 4700, 0, 300, -110, -40, mat="Stone", kind="ExtFountain", **kw)
    L.cyl("Ext_Fountain_Water", 4700, 0, 280, -50, -46, mat="Water", kind="ExtFountain", **kw)
    L.cyl("Ext_Fountain_Column", 4700, 0, 45, -40, 150, mat="Stone", kind="ExtFountain", **kw)
    L.cyl("Ext_Fountain_Top", 4700, 0, 110, 120, 145, mat="Water", kind="ExtFountain", **kw)
    # Night-sky box (emissive), open at the bottom.
    L.box("Ext_Sky_N", 7600, 7700, -7100, 7100, -200, 5100, mat="NightSky", kind="SkyBox", **kw)
    L.box("Ext_Sky_S", -3100, -3000, -7100, 7100, -200, 5100, mat="NightSky", kind="SkyBox", **kw)
    L.box("Ext_Sky_W", -3100, 7700, -7100, -7000, -200, 5100, mat="NightSky", kind="SkyBox", **kw)
    L.box("Ext_Sky_E", -3100, 7700, 7000, 7100, -200, 5100, mat="NightSky", kind="SkyBox", **kw)
    L.box("Ext_Sky_Top", -3100, 7700, -7100, 7100, 5000, 5100, mat="NightSky", kind="SkyBox", **kw)
    L.cyl("Ext_Moon", 7400, -1800, 350, 2650, 3350, shape="sphere", mat="Moon", kind="Moon", **kw)


# ---------------------------------------------------------------------------
# Hero pieces + furniture proxies
# ---------------------------------------------------------------------------
def _fountain(L):
    f = L.frame((FOUNTAIN_X, 0.0, Z_MAIN), 0.0, "Fountain_", "Props/Fountain", "Fountain")
    f.cyl("Plinth", 0, 0, 380, 0, RISE, mat="FloorDark", step_up=True)
    f.cyl("Basin", 0, 0, 260, RISE, 86, mat="Stone")
    f.cyl("Water", 0, 0, 240, 70, 76, mat="Water", collision="none", shadow=False)
    f.cyl("NoJumpCollision", 0, 0, 262, 86, 420, mat="Invisible", collision="invisible", shadow=False, folder="Collision/Blockers")
    f.cyl("Column", 0, 0, 55, 86, 260, mat="Stone", collision="none")
    f.cyl("UpperBowl", 0, 0, 130, 180, 205, mat="Stone", collision="none")
    f.cyl("UpperWater", 0, 0, 118, 200, 206, mat="Water", collision="none", shadow=False)
    f.cyl("Crown", 0, 0, 62, 260, 320, mat="Gold", collision="none")
    # Lions on pedestals (east/west of the fountain), facing south towards the entry.
    for side, tag in ((-1, "W"), (1, "E")):
        p = L.frame((FOUNTAIN_X, side * 520.0, Z_MAIN), 180.0, "Lion%s_" % tag, "Props/Statues", "LionStatue")
        p.box("Pedestal", -55, 55, -55, 55, 0, 100, mat="Stone", kind="Pedestal")
        p.box("Statue", -45, 45, -30, 30, 100, 210, mat="Stone")
    # Planters on the diagonals.
    for i, (sx, sy) in enumerate(((1, 1), (1, -1), (-1, 1), (-1, -1))):
        p = L.frame((FOUNTAIN_X + sx * 330, sy * 330, Z_MAIN), 0.0, "FountainPlanter%d_" % (i + 1), "Props/Plants", "Planter")
        p.box("Pot", -40, 40, -40, 40, 0, 60, mat="Stone")
        p.cyl("Plant", 0, 0, 55, 60, 190, mat="Plant", collision="none")


def _fireplace_and_lounge(L, side):
    tag = "W" if side < 0 else "E"
    yaw = -90.0 * side  # faces into the room
    f = L.frame((-800.0, side * HALL_HW, Z_MAIN), yaw, "Fireplace%s_" % tag, "Props/Fireplaces", "Fireplace")
    f.box("ChimneyBreast", 0, 80, -250, 250, 0, Z_CEIL, mat="Stone")
    f.box("Hearth", 80, 160, -200, 200, 0, 12, mat="FloorDark", step_up=True)
    f.box("FireGlow", 80, 82, -120, 120, 14, 190, mat="Fire", collision="none", shadow=False)
    f.box("JambL", 80, 96, -160, -120, 12, 230, mat="Stone")
    f.box("JambR", 80, 96, 120, 160, 12, 230, mat="Stone")
    f.box("Lintel", 80, 96, -160, 160, 190, 230, mat="Stone")
    f.box("Mantel", 80, 112, -280, 280, 240, 262, mat="Stone")
    f.box("PortraitFrame", 80, 84, -115, 115, 320, 600, mat="Gold", collision="none", kind="Portrait")
    f.box("PortraitCanvas", 84, 85, -100, 100, 335, 585, mat="Painting", collision="none", kind="Portrait", shadow=False)

    lg = L.frame((-800.0, side * HALL_HW, Z_MAIN), yaw, "Lounge%s_" % tag, "Furniture/Lounge" + tag, "Lounge")
    lg.box("Rug", 150, 560, -380, 380, 0, 1.5, mat="Rug", collision="none", kind="Rug", shadow=False)
    if side < 0:
        lg.box("CoffeeTable", 295, 365, -65, 65, 0, 45, mat="Wood", kind="CoffeeTable")
    else:
        lg.box("ChessTable", 290, 370, -40, 40, 0, 70, mat="Wood", kind="ChessTable")
    lg.box("SofaSeat", 425, 520, -115, 115, 0, 45, mat="Fabric", kind="Sofa")
    lg.box("SofaBack", 500, 520, -115, 115, 45, 85, mat="Fabric", kind="Sofa")
    for s, t in ((-1, "L"), (1, "R")):
        lg.box("Armchair%sSeat" % t, 255, 345, s * 285, s * 375, 0, 45, mat="Fabric", kind="Armchair")
        lg.box("Armchair%sBack" % t, 255, 345, s * 355, s * 375, 45, 85, mat="Fabric", kind="Armchair")


def _side_rooms(L, side):
    """Under-gallery ground floor + gallery level dressing on one side."""
    tag = "W" if side < 0 else "E"
    wall = side * HALL_HW
    F = "Furniture/UnderGallery" + tag

    def strip(d0, d1):  # distance range from the side wall -> y range
        return wall - side * d0, wall - side * d1

    L.box("BookshelfA_" + tag, 830, 1070, *strip(0, 50), Z_MAIN, 320, mat="Wood", folder=F, kind="Bookshelf")
    if side < 0:
        L.box("BookshelfB_" + tag, 1500, 1770, *strip(0, 50), Z_MAIN, 320, mat="Wood", folder=F, kind="Bookshelf")
    else:
        L.box("GrandfatherClock_" + tag, 1640, 1700, *strip(0, 55), Z_MAIN, 230, mat="Wood", folder=F, kind="GrandfatherClock")
        L.box("Desk_" + tag, 1440, 1560, *strip(0, 80), Z_MAIN, 78, mat="Wood", folder=F, kind="Desk")
        L.cyl("DeskOrb_" + tag, 1500, wall - side * 40, 16, 78, 110, shape="sphere", mat="Water", collision="none",
              folder=F, kind="Orb", shadow=False)
    D = "Architecture/Doors"
    for lvl, z in (("Ground", Z_MAIN), ("Gallery", Z_GALLERY)):
        L.box("Door_Side%s_%s" % (tag, lvl), SIDE_DOOR_X0, SIDE_DOOR_X1, *strip(-35, -25), z, z + SIDE_DOOR_H,
              mat="Wood", folder=D, kind="DoorSide")
    # Knight armour flanking the gallery door.
    for i, cx in enumerate((1030.0, 1370.0)):
        L.box("KnightGallery%s%d" % (tag, i + 1), cx - 30, cx + 30, *strip(0, 70), Z_GALLERY, Z_GALLERY + 190,
              mat="Metal", folder="Props/Armor", kind="KnightArmor")
    # Busts on the north gallery.
    L.box("BustPedestal_" + tag, 1725, 1775, side * 875, side * 925, Z_GALLERY, Z_GALLERY + 110, mat="Stone",
          folder="Props/Statues", kind="Pedestal")
    L.box("Bust_" + tag, 1730, 1770, side * 880, side * 920, Z_GALLERY + 110, Z_GALLERY + 160, mat="Stone",
          folder="Props/Statues", kind="Bust")
    # Knight armour flanking the front doors (ground floor, under the north gallery).
    L.box("KnightFrontDoor_" + tag, 1710, 1770, side * 295, side * 365, Z_MAIN, 190, mat="Metal",
          folder="Props/Armor", kind="KnightArmor")


def _dressing(L):
    none = dict(collision="none", shadow=False)
    R = "Props/Rugs"
    L.box("Rug_Grand", -60, 1040, -500, 500, 0, 1.5, mat="Carpet", folder=R, kind="RugGrand", **none)
    L.box("Rug_RunnerNorth", 1040, HALL_X1 + WALL_T, -150, 150, 0, 1.2, mat="Carpet", folder=R, kind="Runner", **none)
    L.box("Rug_RunnerSouth", HALL_X0, FOUNTAIN_X - 380, -150, 150, 0, 1.2, mat="Carpet", folder=R, kind="Runner", **none)
    L.box("Rug_RunnerPorch", HALL_X1 + WALL_T, PORCH_X1 - RAIL_T, -150, 150, 0, 1.2, mat="Carpet", folder=R, kind="Runner", **none)
    L.box("Rug_RunnerVestibule", VEST_X0, HALL_X0 - ENTRY_TREAD * 5, -150, 150, Z_VEST, Z_VEST + 1.2, mat="Carpet",
          folder=R, kind="Runner", **none)
    L.box("Rug_SameSpot", -1990, -1660, -260, 260, Z_VEST, Z_VEST + 1.5, mat="Rug", folder=R, kind="RugSameSpot", **none)

    B = "Props/Banners"
    L.box("Banner_NorthCenter", HALL_X1 - 15, HALL_X1, -260, 260, 760, 1460, mat="Banner", folder=B, kind="BannerLarge", **none)
    for side, tag in ((-1, "W"), (1, "E")):
        L.box("Banner_North" + tag, HALL_X1 - 15, HALL_X1, side * 700, side * 900, 800, 1380, mat="Banner", folder=B, kind="Banner", **none)
        L.box("Banner_DoorSide" + tag, HALL_X1 - 15, HALL_X1, side * 560, side * 700, 140, 500, mat="Banner", folder=B, kind="Banner", **none)
        L.box("Banner_SideWall" + tag, -130, 130, side * HALL_HW, side * (HALL_HW - 15), 720, 1320, mat="Banner", folder=B,
              kind="BannerLarge", **none)
        L.box("Banner_Vestibule" + tag, -1900, -1700, side * VEST_HW, side * (VEST_HW - 15), 200, 650, mat="Banner", folder=B,
              kind="Banner", **none)

    Wn = "Architecture/Windows"
    for side, tag in ((-1, "W"), (1, "E")):
        for i, cx in enumerate((-1200.0, -400.0, 400.0)):
            L.box("Window_%s%d" % (tag, i + 1), cx - 100, cx + 100, side * HALL_HW, side * (HALL_HW - 2), 760, 1360,
                  mat="Window", folder=Wn, kind="Window", **none)
        L.box("Window_North" + tag, HALL_X1 - 2, HALL_X1, side * 1100, side * 1300, 760, 1360, mat="Window", folder=Wn,
              kind="Window", **none)

    C = "Props/Chandeliers"
    for name, (cx, cy), r in (("Fountain", (FOUNTAIN_X, 0.0), 160.0), ("Rug", (450.0, 0.0), 160.0), ("Vestibule", (-1900.0, 0.0), 100.0)):
        k = dict(collision="none", folder=C, kind="Chandelier")
        L.cyl("Chandelier%s_Lower" % name, cx, cy, r * 0.55, 900, 950, mat="Gold", **k)
        L.cyl("Chandelier%s_Ring" % name, cx, cy, r, 950, 1010, mat="Gold", **k)
        L.cyl("Chandelier%s_Candles" % name, cx, cy, r * 0.95, 1010, 1030, mat="Candle", shadow=False, **k)
        L.cyl("Chandelier%s_Top" % name, cx, cy, r * 0.4, 1030, 1100, mat="Gold", **k)
        L.box("Chandelier%s_Chain" % name, cx - 5, cx + 5, cy - 5, cy + 5, 1100, Z_CEIL, mat="Gold", shadow=False, **dict(k))


# ---------------------------------------------------------------------------
# Gameplay markers, lights, test points
# ---------------------------------------------------------------------------
PLAYER_START = (-2000.0, 0.0, Z_VEST)   # floor point; builder adds capsule half height
PLAYER_START_YAW = 0.0                  # facing north: stairs -> fountain -> rug -> open front doors

# (name, x, y, floor z) - the validator requires every one to be reachable on foot.
TEST_POINTS = [
    ("Spawn", -2000, 0, Z_VEST),
    ("VestibuleInnerDoor", -2120, 0, Z_VEST),
    ("VestibuleCornerW", -2120, -500, Z_VEST),
    ("EntryStepsTop", -1350, 0, Z_MAIN),
    ("FountainSouth", FOUNTAIN_X - 320, 0, RISE),
    ("FountainNorth", FOUNTAIN_X + 320, 0, RISE),
    ("FountainWest", FOUNTAIN_X, -320, RISE),
    ("FountainEast", FOUNTAIN_X, 320, RISE),
    ("RugCenter", 450, 0, Z_MAIN),
    ("LoungeW_Hearth", -800, -1175, Z_MAIN),
    ("LoungeE_Hearth", -800, 1175, Z_MAIN),
    ("LoungeW_BehindSofa", -800, -780, Z_MAIN),
    ("StairW_Bottom", -330, -1225, Z_MAIN),
    ("StairW_Middle", 275, -1225, 288),
    ("StairW_Top", 785, -1225, 560),
    ("StairE_Bottom", -330, 1225, Z_MAIN),
    ("StairE_Middle", 275, 1225, 288),
    ("StairE_Top", 785, 1225, 560),
    ("GalleryW", 1200, -1200, Z_GALLERY),
    ("GalleryE", 1200, 1200, Z_GALLERY),
    ("GalleryN_Center", 1625, 0, Z_GALLERY),
    ("GalleryN_CornerW", 1625, -1225, Z_GALLERY),
    ("GalleryN_CornerE", 1625, 1225, Z_GALLERY),
    ("UnderGalleryW", 1300, -1230, Z_MAIN),
    ("UnderGalleryE", 1300, 1230, Z_MAIN),
    ("FrontDoorInside", 1650, 0, Z_MAIN),
    ("FrontDoorThreshold", 1830, 0, Z_MAIN),
    ("Porch", 2300, 0, Z_MAIN),
    ("PorchCornerE", 2450, 380, Z_MAIN),
]

# (label, type, (x, y, z), color, intensity, attenuation du, rotation (pitch, yaw, roll))
# Intensities: point = candela (scaled by LM_SCALE^2 in the builder), directional = lux.
LIGHTS = [
    ("PL_LM_Chandelier_Fountain", "point", (FOUNTAIN_X, 0, 930), (1.0, 0.72, 0.42), 2000.0, 3000.0, None),
    ("PL_LM_Chandelier_Rug", "point", (450, 0, 930), (1.0, 0.72, 0.42), 2000.0, 3000.0, None),
    ("PL_LM_Chandelier_Vestibule", "point", (-1900, 0, 930), (1.0, 0.72, 0.42), 900.0, 1600.0, None),
    ("PL_LM_Fireplace_W", "point", (-800, -HALL_HW + 150, 90), (1.0, 0.45, 0.15), 500.0, 900.0, None),
    ("PL_LM_Fireplace_E", "point", (-800, HALL_HW - 150, 90), (1.0, 0.45, 0.15), 500.0, 900.0, None),
    ("PL_LM_Fountain", "point", (FOUNTAIN_X, 0, 130), (0.25, 0.5, 1.0), 400.0, 800.0, None),
    ("PL_LM_ExteriorFountain", "point", (4700, 0, 150), (0.25, 0.5, 1.0), 800.0, 1500.0, None),
    ("DL_LM_Moon", "directional", (2200, 0, 1800), (0.55, 0.65, 1.0), 2.5, None, (-35.0, 200.0, 0.0)),
    ("SL_LM_Sky", "sky", (0, 0, 1200), (0.45, 0.55, 1.0), 0.35, None, None),
]

NAV_BOUNDS = ((VEST_X0 - WALL_T, PORCH_X1), (-HALL_HW - WALL_T, HALL_HW + WALL_T), (SLAB_BOTTOM, Z_GALLERY + 300))

STAIR_SPECS = [  # for static checks: (name, riser du, tread du)
    ("GrandStairs", RISE, TREAD),
    ("EntrySteps", RISE, ENTRY_TREAD),
]

MATERIALS = {
    # key: (base colour, roughness, metallic, emissive colour, emissive strength)
    "Floor": ((0.62, 0.55, 0.45), 0.35, 0.0, (0, 0, 0), 0.0),
    "FloorDark": ((0.16, 0.14, 0.13), 0.35, 0.0, (0, 0, 0), 0.0),
    "Wall": ((0.10, 0.10, 0.12), 0.8, 0.0, (0, 0, 0), 0.0),
    "Stone": ((0.45, 0.42, 0.38), 0.7, 0.0, (0, 0, 0), 0.0),
    "Stairs": ((0.40, 0.37, 0.33), 0.6, 0.0, (0, 0, 0), 0.0),
    "Gold": ((0.85, 0.60, 0.20), 0.3, 1.0, (0, 0, 0), 0.0),
    "Wood": ((0.22, 0.11, 0.05), 0.6, 0.0, (0, 0, 0), 0.0),
    "Fabric": ((0.16, 0.05, 0.25), 0.9, 0.0, (0, 0, 0), 0.0),
    "Carpet": ((0.03, 0.05, 0.25), 0.95, 0.0, (0, 0, 0), 0.0),
    "Rug": ((0.10, 0.04, 0.20), 0.95, 0.0, (0, 0, 0), 0.0),
    "Banner": ((0.02, 0.03, 0.18), 0.9, 0.0, (0, 0, 0), 0.0),
    "Metal": ((0.50, 0.50, 0.55), 0.35, 1.0, (0, 0, 0), 0.0),
    "Plant": ((0.05, 0.22, 0.05), 0.8, 0.0, (0, 0, 0), 0.0),
    "Painting": ((0.08, 0.06, 0.05), 0.8, 0.0, (0, 0, 0), 0.0),
    "Water": ((0.02, 0.10, 0.30), 0.1, 0.0, (0.10, 0.45, 1.0), 4.0),
    "Fire": ((0.0, 0.0, 0.0), 1.0, 0.0, (1.0, 0.45, 0.10), 12.0),
    "Candle": ((0.3, 0.2, 0.1), 1.0, 0.0, (1.0, 0.65, 0.30), 6.0),
    "Window": ((0.0, 0.0, 0.0), 1.0, 0.0, (0.05, 0.10, 0.30), 2.0),
    "NightSky": ((0.0, 0.0, 0.0), 1.0, 0.0, (0.01, 0.02, 0.06), 1.0),
    "Moon": ((0.0, 0.0, 0.0), 1.0, 0.0, (0.80, 0.85, 1.0), 20.0),
    "Foliage": ((0.01, 0.04, 0.03), 0.9, 0.0, (0, 0, 0), 0.0),
    "Ground": ((0.03, 0.04, 0.05), 0.9, 0.0, (0, 0, 0), 0.0),
    "Invisible": None,  # translucent collision-preview material (hidden in game)
}


def build_design():
    """All blockout primitives in design units (human scale)."""
    L = _Layout()
    _architecture(L)
    _grand_stairs(L)
    _entry(L)
    _front_doors_and_porch(L)
    _exterior(L)
    _fountain(L)
    for side in (-1, 1):
        _fireplace_and_lounge(L, side)
        _side_rooms(L, side)
    _dressing(L)
    return L.prims


def build(scale=None):
    """All blockout primitives in final centimetres."""
    s = LM_SCALE if scale is None else scale
    return [p.scaled(s) for p in build_design()]


def scaled_point(p, scale=None):
    s = LM_SCALE if scale is None else scale
    return tuple(v * s for v in p)
