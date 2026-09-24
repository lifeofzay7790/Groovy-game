"""Split a Tripo 'kit sheet' FBX into separate pieces.

usage: python split_sheet.py <sheet.fbx> <tex_prefix> <out_dir>
Writes <out_dir>/<name>.blend (full-res pieces), preview GLBs and pieces.json.
"""
import json
import os
import sys

import bpy
import numpy as np
from PIL import Image
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

fbx, tex_prefix, out = sys.argv[1:4]
out = os.path.abspath(out)
name = os.path.splitext(os.path.basename(fbx))[0].replace("+", "_")
TEX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tex")
os.makedirs(os.path.join(out, "glb"), exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=fbx)
src = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]
bpy.context.view_layer.objects.active = src
src.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
me = src.data

nv, nl, npoly = len(me.vertices), len(me.loops), len(me.polygons)
co = np.empty(nv * 3, np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
lv = np.empty(nl, np.int32); me.loops.foreach_get("vertex_index", lv)
lt = np.empty(npoly, np.int32); me.polygons.foreach_get("loop_total", lt)
assert (lt == 3).all(), "expected triangles"
tri = lv.reshape(-1, 3)
uv = np.empty(nl * 2, np.float32); me.uv_layers.active.data.foreach_get("uv", uv); uv = uv.reshape(-1, 3, 2)

# connected components over vertices
e = np.concatenate([tri[:, [0, 1]], tri[:, [1, 2]]])
g = coo_matrix((np.ones(len(e), np.int8), (e[:, 0], e[:, 1])), shape=(nv, nv))
ncomp, vlab = connected_components(g, directed=False)
flab = vlab[tri[:, 0]]

# component bounding boxes
bmin = np.full((ncomp, 3), np.inf); bmax = np.full((ncomp, 3), -np.inf)
np.minimum.at(bmin, vlab, co); np.maximum.at(bmax, vlab, co)
used = np.zeros(ncomp, bool); used[np.unique(flab)] = True

# cluster components whose (slightly expanded) boxes overlap
MARGIN = 0.003
parent = np.arange(ncomp)
def find(a):
    while parent[a] != a:
        parent[a] = parent[parent[a]]; a = parent[a]
    return a
ids = np.where(used)[0]
lo, hi = bmin[ids] - MARGIN, bmax[ids] + MARGIN
for k, c in enumerate(ids):
    ov = np.all((lo[k] <= hi) & (hi[k] >= lo), axis=1)
    for j in ids[ov]:
        ra, rb = find(c), find(j)
        if ra != rb:
            parent[rb] = ra
root = np.array([find(c) for c in range(ncomp)])
plab = root[flab]
pieces = np.unique(plab)

# material with 1K preview texture
prev_png = os.path.join(out, "glb", name + "_basecolor_1k.png")
if not os.path.exists(prev_png):
    Image.open(os.path.join(TEX, tex_prefix + "_basecolor.JPEG")).resize((1024, 1024), Image.LANCZOS).save(prev_png)
mat = bpy.data.materials.new(name + "_preview"); mat.use_nodes = True
bsdf = mat.node_tree.nodes["Principled BSDF"]
img = mat.node_tree.nodes.new("ShaderNodeTexImage"); img.image = bpy.data.images.load(prev_png); img.image.pack()
mat.node_tree.links.new(img.outputs["Color"], bsdf.inputs["Base Color"])
bsdf.inputs["Roughness"].default_value = 0.7

info = []
order = sorted(pieces, key=lambda p: 0)
objs = []
for p in pieces:
    fsel = np.where(plab == p)[0]
    if len(fsel) < 30:
        continue
    t = tri[fsel]
    vids, inv = np.unique(t, return_inverse=True)
    pm = bpy.data.meshes.new("piece")
    pm.from_pydata(co[vids].tolist(), [], inv.reshape(-1, 3).tolist())
    pm.uv_layers.new(name="UVMap")
    pm.uv_layers[0].data.foreach_set("uv", uv[fsel].reshape(-1))
    ob = bpy.data.objects.new("piece", pm)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(mat)
    c = co[vids]
    objs.append((ob, c.min(0), c.max(0), len(fsel)))

# stable order: by rows (top view: -Y front rows first), then x
objs.sort(key=lambda o: (round(float((o[1][1] + o[2][1]) / 2) / 0.06), float(o[1][0])))
for i, (ob, mn, mx, nt) in enumerate(objs):
    pid = "%s_P%02d" % (name, i + 1)
    ob.name = ob.data.name = pid
    info.append(dict(id=pid, min=[round(float(v), 4) for v in mn], max=[round(float(v), 4) for v in mx], tris=int(nt)))

bpy.ops.object.select_all(action="DESELECT")
bpy.data.objects.remove(src)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, name + ".blend"), compress=True)

# preview GLBs (decimated copies)
for ob, mn, mx, nt in objs:
    cp = ob.copy(); cp.data = ob.data.copy(); bpy.context.scene.collection.objects.link(cp)
    if nt > 12000:
        d = cp.modifiers.new("dec", "DECIMATE"); d.ratio = 12000 / nt
    bpy.ops.object.select_all(action="DESELECT"); cp.select_set(True); bpy.context.view_layer.objects.active = cp
    bpy.ops.export_scene.gltf(filepath=os.path.join(out, "glb", ob.name + ".glb"), use_selection=True,
                              export_apply=True, export_format="GLB", export_yup=True)
    bpy.data.objects.remove(cp)

json.dump(dict(sheet=name, tex=tex_prefix, pieces=info), open(os.path.join(out, name + ".json"), "w"), indent=1)
print("SHEET", name, "components", ncomp, "pieces", len(info))
