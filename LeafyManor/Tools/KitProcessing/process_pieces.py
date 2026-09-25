"""Turn split sheet pieces into game-ready FBX files.

usage: python process_pieces.py mapping.json out_dir [only_name ...]

mapping.json: list of entries
  name       SM_LM_... output name
  src        "<sheet>_P##" piece id (or list -> joined)
  category   Architecture | Props | Furniture
  size       [W, D, H] target cm (null = follow uniform scale)
  fit        "height" | "width" | "depth" | "exact_wh" | "exact"
  rot_z      degrees applied before fitting (so the front faces -Y)
  pivot      bottom_center | bottom_center_front | bottom_center_back | top_center | back_center
  tris       triangle budget
  collision  "none" | "box" | "hull" | [[x0,x1,y0,y1,z0,z1] ...] boxes in final cm relative to pivot
  mirror_x   optional bool
"""
import json
import math
import os
import sys


import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
mapping_path, out_dir = sys.argv[1], os.path.abspath(sys.argv[2])
only = set(sys.argv[3:])
entries = json.load(open(mapping_path))
os.makedirs(out_dir, exist_ok=True)
os.makedirs(os.path.join(out_dir, "_preview"), exist_ok=True)

_loaded = {}


def load_piece(pid):
    sheet = pid.rsplit("_P", 1)[0]
    if sheet not in _loaded:
        with bpy.data.libraries.load(os.path.join(HERE, "split", sheet + ".blend")) as (src, dst):
            dst.objects = list(src.objects)
            dst.materials = list(src.materials)
        _loaded[sheet] = {o.name: o for o in dst.objects if o is not None}
    ob = _loaded[sheet][pid].copy()
    ob.data = _loaded[sheet][pid].data.copy()
    bpy.context.scene.collection.objects.link(ob)
    return ob, sheet


def bounds(ob):
    n = len(ob.data.vertices)
    co = np.empty(n * 3, np.float32)
    ob.data.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    return co.min(0), co.max(0)


def transform(ob, m):
    ob.data.transform(m)
    ob.data.update()


def make_box(name, x0, x1, y0, y1, z0, z1):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x = x0 if v.co.x < 0 else x1
        v.co.y = y0 if v.co.y < 0 else y1
        v.co.z = z0 if v.co.z < 0 else z1
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def hull(name, src, max_pts=4000):
    n = len(src.data.vertices)
    co = np.empty(n * 3, np.float32)
    src.data.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    if len(co) > max_pts:
        co = co[np.random.default_rng(0).choice(len(co), max_pts, replace=False)]
    bm = bmesh.new()
    for p in co:
        bm.verts.new(p)
    res = bmesh.ops.convex_hull(bm, input=bm.verts)
    kill = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
    if kill:
        bmesh.ops.delete(bm, geom=kill, context="VERTS")
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


report = []
for e in entries:
    if only and e["name"] not in only:
        continue
    srcs = e["src"] if isinstance(e["src"], list) else [e["src"]]
    parts = [load_piece(s) for s in srcs]
    ob, sheet = parts[0]
    if len(parts) > 1:
        bpy.ops.object.select_all(action="DESELECT")
        for p, _ in parts:
            p.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.join()
    ob.name = ob.data.name = e["name"]
    tris0 = sum(len(p.vertices) - 2 for p in ob.data.polygons)

    # keep only part of a piece (two items fused on the sheet): face-centroid x fraction range
    for key, axis in (("keep_x", 0), ("keep_z", 2)):
        if not e.get(key):
            continue
        import bmesh as _bm
        bm = _bm.new(); bm.from_mesh(ob.data)
        xs = [v.co[axis] for v in bm.verts]; x0, x1 = min(xs), max(xs)
        lo, hi = e[key]
        kill = [f for f in bm.faces if not (lo <= (f.calc_center_median()[axis] - x0) / (x1 - x0) <= hi)]
        _bm.ops.delete(bm, geom=kill, context="FACES")
        loose = [v for v in bm.verts if not v.link_faces]
        _bm.ops.delete(bm, geom=loose, context="VERTS")
        bm.to_mesh(ob.data); bm.free(); ob.data.update()
    # drop small loose fragments near the floor (e.g. extra heads lying in front of a statue)
    if e.get("drop_low_small"):
        from scipy.sparse import coo_matrix
        from scipy.sparse.csgraph import connected_components
        min_tris, zf = e["drop_low_small"]
        me = ob.data
        nv = len(me.vertices)
        co = np.empty(nv * 3, np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
        lv = np.empty(len(me.loops), np.int32); me.loops.foreach_get("vertex_index", lv); tri = lv.reshape(-1, 3)
        ed = np.concatenate([tri[:, [0, 1]], tri[:, [1, 2]]])
        _, lab = connected_components(coo_matrix((np.ones(len(ed), np.int8), (ed[:, 0], ed[:, 1])), shape=(nv, nv)), directed=False)
        flab = lab[tri[:, 0]]
        cnt = np.bincount(flab)
        zc = np.bincount(flab, weights=co[tri[:, 0], 2]) / np.maximum(cnt, 1)
        zmin, zmax = co[:, 2].min(), co[:, 2].max()
        bad = set(np.where((cnt < min_tris) & (zc < zmin + zf * (zmax - zmin)))[0].tolist())
        import bmesh as _bm
        bm = _bm.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
        kill = [bm.faces[i] for i in range(len(bm.faces)) if flab[i] in bad]
        _bm.ops.delete(bm, geom=kill, context="FACES")
        _bm.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
        bm.to_mesh(me); bm.free(); me.update()
        print("dropped", len(kill), "fragment faces")
    # lay flat panels (rugs, tiles): front (-Y) turns to face up
    if e.get("rot_x"):
        transform(ob, Matrix.Rotation(math.radians(e["rot_x"]), 4, "X"))
    # auto-align: long horizontal axis -> X, and the taller half (seat backs) to +Y so the front faces -Y
    if e.get("align") == "pca":
        n = len(ob.data.vertices)
        co = np.empty(n * 3, np.float32); ob.data.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
        xy = co[:, :2] - co[:, :2].mean(0)
        w, v = np.linalg.eigh(np.cov(xy.T))
        ax = v[:, np.argmax(w)]
        ang = -math.atan2(ax[1], ax[0])
        transform(ob, Matrix.Rotation(ang, 4, "Z"))
        co = np.empty(n * 3, np.float32); ob.data.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
        yc = (co[:, 1].min() + co[:, 1].max()) / 2
        top = co[:, 2] > np.percentile(co[:, 2], 70)
        if (co[top, 1] < yc).mean() > 0.5:
            transform(ob, Matrix.Rotation(math.pi, 4, "Z"))
    # flat items (rugs) -> thinnest axis up; wall-hung panels (banners) -> thinnest axis to -Y
    if e.get("align") in ("flat", "vertical"):
        n = len(ob.data.vertices)
        co = np.empty(n * 3, np.float32); ob.data.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
        w, v = np.linalg.eigh(np.cov((co - co.mean(0)).T))
        nrm = v[:, np.argmin(w)]
        if e["align"] == "flat":
            if (nrm[2] < 0 if abs(nrm[2]) > 0.5 else nrm[1] > 0):
                nrm = -nrm
            target = Vector((0, 0, 1))
        else:
            if nrm[1] > 0:
                nrm = -nrm
            target = Vector((0, -1, 0))
        q = Vector(nrm.tolist()).rotation_difference(target)
        transform(ob, q.to_matrix().to_4x4())
        if e["align"] == "flat":  # then long axis -> X
            co = np.empty(n * 3, np.float32); ob.data.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
            xy = co[:, :2] - co[:, :2].mean(0)
            w2, v2 = np.linalg.eigh(np.cov(xy.T)); ax = v2[:, np.argmax(w2)]
            transform(ob, Matrix.Rotation(-math.atan2(ax[1], ax[0]), 4, "Z"))
    if e.get("flip_front"):
        transform(ob, Matrix.Rotation(math.pi, 4, "Z"))
    # orientation
    if e.get("rot_z"):
        transform(ob, Matrix.Rotation(math.radians(e["rot_z"]), 4, "Z"))
    if e.get("mirror_x"):
        transform(ob, Matrix.Scale(-1, 4, (1, 0, 0)))
        ob.data.flip_normals()

    # scale (work in metres: FBX Units Scale export -> 1 m = 100 cm in Unreal)
    mn, mx = bounds(ob)
    dims = mx - mn
    W, D, H = [None if v is None else v / 100.0 for v in e["size"]]
    fit = e.get("fit", "height")
    if fit == "height":
        s = [H / dims[2]] * 3
    elif fit == "width":
        s = [W / dims[0]] * 3
    elif fit == "depth":
        s = [D / dims[1]] * 3
    elif fit == "exact_wh":
        sx, sz = W / dims[0], H / dims[2]
        s = [sx, (D / dims[1]) if D else (sx + sz) / 2, sz]
    else:  # exact
        s = [W / dims[0], D / dims[1], H / dims[2]]
    transform(ob, Matrix.Diagonal((s[0], s[1], s[2], 1.0)))

    # pivot
    mn, mx = bounds(ob)
    cx, cy = (mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2
    piv = e.get("pivot", "bottom_center")
    px, py, pz = cx, cy, mn[2]
    if piv == "bottom_center_front":
        py = mn[1]
    elif piv in ("bottom_center_back",):
        py = mx[1]
    elif piv == "top_center":
        pz = mx[2]
    elif piv == "top_center_back":
        py, pz = mx[1], mx[2]
    elif piv == "back_center":
        py, pz = mx[1], (mn[2] + mx[2]) / 2
    transform(ob, Matrix.Translation((-px, -py, -pz)))

    # decimate
    budget = e.get("tris", 30000)
    if tris0 > budget:
        m = ob.modifiers.new("dec", "DECIMATE")
        m.ratio = budget / tris0
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        bpy.ops.object.modifier_apply(modifier="dec")
    for poly in ob.data.polygons:
        poly.use_smooth = True
    tris1 = len(ob.data.polygons)

    # material slot named per sheet (all pieces of a sheet share one texture set)
    mat_name = "M_LM_Kit_" + sheet
    mat = bpy.data.materials.get(mat_name) or bpy.data.materials.new(mat_name)
    ob.data.materials.clear()
    ob.data.materials.append(mat)

    # collision
    cols = []
    col = e.get("collision", "box")
    mn, mx = bounds(ob)
    if col == "box":
        cols.append(make_box("UCX_%s_01" % e["name"], mn[0], mx[0], mn[1], mx[1], mn[2], mx[2]))
    elif col == "hull":
        cols.append(hull("UCX_%s_01" % e["name"], ob))
    elif isinstance(col, list):
        for i, b in enumerate(col):
            cols.append(make_box("UCX_%s_%02d" % (e["name"], i + 1), *[v / 100.0 for v in b]))

    # export FBX (same convention as the character: metres + FBX Units Scale)
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    for c in cols:
        c.select_set(True)
    cat_dir = os.path.join(out_dir, e["category"])
    os.makedirs(cat_dir, exist_ok=True)
    bpy.ops.export_scene.fbx(filepath=os.path.join(cat_dir, e["name"] + ".fbx"), use_selection=True,
                             apply_scale_options="FBX_SCALE_UNITS", object_types={"MESH"},
                             mesh_smooth_type="FACE", add_leaf_bones=False, path_mode="STRIP",
                             use_mesh_modifiers=True, bake_anim=False)

    # preview GLB (with the sheet's 1k preview texture)
    pm = bpy.data.materials.new(e["name"] + "_prev")
    pm.use_nodes = True
    tex = os.path.join(HERE, "split", "glb", sheet + "_basecolor_1k.png")
    node = pm.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = bpy.data.images.load(tex, check_existing=True)
    pm.node_tree.links.new(node.outputs["Color"], pm.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
    ob.data.materials[0] = pm
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(out_dir, "_preview", e["name"] + ".glb"), use_selection=True,
                              export_format="GLB", export_yup=True)
    ob.data.materials[0] = mat

    mn, mx = bounds(ob)
    size_cm = [round(float(v) * 100, 1) for v in (mx - mn)]
    report.append(dict(name=e["name"], src=srcs, size_cm=size_cm, tris=tris1, collision=len(cols), sheet=sheet))
    print("DONE", e["name"], size_cm, tris1, "tris", len(cols), "UCX")
    for c in cols:
        bpy.data.objects.remove(c)
    bpy.data.objects.remove(ob)

rp = os.path.join(out_dir, "_preview", "report.json")
old = json.load(open(rp)) if os.path.exists(rp) else []
keep = {r["name"]: r for r in old}
keep.update({r["name"]: r for r in report})
json.dump(list(keep.values()), open(rp, "w"), indent=1)
