"""Layout -> Web/scene.json for the browser walkthrough (three.js space, metres) + walkability grid.

Run after split_gltf.py (it records the model file sizes for the loading bar).
"""
import base64, gzip, json, math, os, struct, sys
from array import array

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, REPO + '/Unreal/Python')
sys.path.insert(0, REPO + '/Tools')
import leafy_manor_layout as lm
import validate_blockout as vb

WEB = os.path.join(REPO, 'Web')
S = lm.LM_SCALE
prims = lm.build(S)
R = lambda v: round(v, 3)


def T(p):  # UE cm -> three.js metres
    return [R(p[1] / 100), R(p[2] / 100), R(-p[0] / 100)]


def box_matrix(p):
    """Column-major 4x4 for a unit primitive scaled/rotated like the UE actor."""
    pt, yw = math.radians(p.rot[0]), math.radians(p.rot[1])
    ex = (math.cos(pt) * math.cos(yw), math.cos(pt) * math.sin(yw), math.sin(pt))
    ey = (-math.sin(yw), math.cos(yw), 0.0)
    ez = (-math.sin(pt) * math.cos(yw), -math.sin(pt) * math.sin(yw), math.cos(pt))
    # three.js basis: X <- UE Y axis column, Y <- UE Z, Z <- -UE X (same mapping as T)
    bx = [v * 100 for v in T([e * p.size[0] for e in ex])]
    by = [v * 100 for v in T([e * p.size[2] for e in ez])]
    bz = [v * 100 for v in T([e * p.size[1] for e in ey])]
    c = T(p.center)
    return [R(bx[0] / 100), R(bx[1] / 100), R(bx[2] / 100), 0, R(by[0] / 100), R(by[1] / 100), R(by[2] / 100), 0,
            R(bz[0] / 100), R(bz[1] / 100), R(bz[2] / 100), 0, c[0], c[1], c[2], 1]


kit, boxes, cam = {}, [], []
flames = []  # [x,y,z (three), size, kind]
for p in prims:
    visible = not p.proxy and p.collision != 'invisible' and p.mat != 'Invisible'
    if p.mesh and visible:
        kit.setdefault(p.mesh, []).append(T(p.pivot) + [R(math.radians(90 - p.rot[1]))] +
                                          [p.mesh_scale[0], p.mesh_scale[2], p.mesh_scale[1]])
        yaw = math.radians(p.rot[1] + 90.0)
        x, y, z = p.pivot
        if 'WallSconce' in p.mesh:
            flames.append(T((x + 22 * math.cos(yaw), y + 22 * math.sin(yaw), z + 48)) + [0.5, 's'])
        elif 'Candelabra_Floor' in p.mesh:
            flames.append(T((x, y, z + 132)) + [0.7, 'c'])
        elif 'Candelabra_Small' in p.mesh:
            flames.append(T((x, y, z + 56)) + [0.35, 'c'])
        elif 'Fire_01' in p.mesh:
            flames.append(T((x, y, z + 35)) + [1.6, 'f'])
        elif 'Lantern' in p.mesh:
            flames.append(T((x, y, z + 30)) + [0.5, 's'])
    elif visible and not p.mesh:
        boxes.append(dict(m=p.mat, s=p.shape, x=box_matrix(p), l=p.label))
    if p.collision not in ('none', 'invisible') and max(p.size) >= 40:
        cam.append(box_matrix(p))

lights = []
for label, kind, pos, col, inten, att, rot in lm.LIGHTS:
    if kind == 'point':
        lights.append(dict(l=label, p=T([v * S for v in pos]), c=col, i=inten, d=R(att * S / 100)))

# ---- walkability grid (reachable standing heights per 10 cm cell) ----------------
P = lm.PLAYER
cell = 10.0
nb = lm.NAV_BOUNDS
bounds = ((nb[0][0] * S - 50, nb[0][1] * S + 50), (nb[1][0] * S - 50, nb[1][1] * S + 50))
g, valid, node_near, neighbours = vb.analyse(prims, P['capsule_radius_cm'], P['capsule_half_height_cm'],
                                             P['max_step_height_cm'], cell, bounds, z_top=lm.Z_CEIL * S - 1.0)
start = node_near(*lm.scaled_point(lm.PLAYER_START, S))
reach, falls = vb.flood(start, neighbours)
levels = {}
for i, j, t in reach:
    levels.setdefault((i, j), []).append(t)
L = max(len(v) for v in levels.values())
EMPTY = -32768
data = array('h', [EMPTY]) * (g.nx * g.ny * L)
for (i, j), ts in levels.items():
    for n, t in enumerate(sorted(ts)):
        data[(n * g.nx + i) * g.ny + j] = int(round(t * 4))
blob = gzip.compress(data.tobytes(), 9, mtime=0)
# solid spans per cell (lo, hi), clipped to the playable height, for obstacle / landing tests
ZMAX = lm.Z_CEIL * S + 50
K = max(len([sp for sp in (g.spans[k] or ()) if sp[0] < ZMAX]) for k in range(g.nx * g.ny))
sd = array('h', [EMPTY]) * (g.nx * g.ny * K * 2)
for k in range(g.nx * g.ny):
    for n, (lo, hi, _) in enumerate([sp for sp in (g.spans[k] or ()) if sp[0] < ZMAX]):
        sd[(n * g.nx * g.ny + k) * 2] = int(round(max(lo, -2000) * 4))
        sd[(n * g.nx * g.ny + k) * 2 + 1] = int(round(min(hi, ZMAX) * 4))
sblob = gzip.compress(sd.tobytes(), 9, mtime=0)
grid = dict(x0=g.x0, y0=g.y0, cell=cell, nx=g.nx, ny=g.ny, L=L, K=K, q=4, b64=base64.b64encode(blob).decode(),
            spans=base64.b64encode(sblob).decode())

sx, sy, sz = lm.scaled_point(lm.PLAYER_START, S)
out = dict(kit=kit, boxes=boxes, cam=cam, lights=lights, flames=flames,
           mats={k: v for k, v in lm.MATERIALS.items() if v},
           start=dict(ue=[sx, sy, start[2]], yaw=lm.PLAYER_START_YAW),
           player=dict(radius=P['capsule_radius_cm'], half=P['capsule_half_height_cm'], step=P['max_step_height_cm']),
           dims=dict(z_gallery=lm.Z_GALLERY * S, half=lm.HALF * S, vest_x0=lm.VEST_X0 * S, porch_x1=lm.PORCH_X1 * S,
                     lounge_x=lm.LOUNGE_X * S, gal_in=lm.GAL_IN * S, north_gal_x0=lm.NORTH_GAL_X0 * S,
                     side_gal_x0=lm.SIDE_GAL_X0 * S, fountain=[v * S for v in lm.FOUNTAIN]),
           grid=grid)
out['bytes'] = {k: os.path.getsize(os.path.join(WEB, k)) for k in ('kit.json', 'player.json')}
json.dump(out, open(os.path.join(WEB, 'scene.json'), 'w'), separators=(',', ':'))
print('kit meshes', len(kit), 'instances', sum(len(v) for v in kit.values()), 'boxes', len(boxes), 'cam', len(cam),
      'flames', len(flames), 'grid', g.nx, g.ny, 'L', L, 'reach', len(reach), 'gz', len(blob), 'K', K, 'spans gz', len(sblob),
      'json', os.path.getsize(os.path.join(WEB, 'scene.json')))
