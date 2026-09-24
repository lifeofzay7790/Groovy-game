"""Split a merged piece further by connected components (no bbox merging).

usage: python resplit.py <sheet> <pid> [min_tris]
Adds <pid>a, <pid>b ... objects to split/<sheet>.blend, preview GLBs and json entries; removes <pid>.
Components smaller than min_tris are attached to the nearest big component.
"""
import json
import os
import sys

import bpy
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

HERE = os.path.dirname(os.path.abspath(__file__))
sheet, pid = sys.argv[1], sys.argv[2]
min_tris = int(sys.argv[3]) if len(sys.argv) > 3 else 2000
blend = os.path.join(HERE, "split", sheet + ".blend")
bpy.ops.wm.open_mainfile(filepath=blend)
ob = bpy.data.objects[pid]
me = ob.data
nv = len(me.vertices)
co = np.empty(nv * 3, np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
lv = np.empty(len(me.loops), np.int32); me.loops.foreach_get("vertex_index", lv)
tri = lv.reshape(-1, 3)
uv = np.empty(len(me.loops) * 2, np.float32); me.uv_layers[0].data.foreach_get("uv", uv); uv = uv.reshape(-1, 3, 2)
e = np.concatenate([tri[:, [0, 1]], tri[:, [1, 2]]])
n, vlab = connected_components(coo_matrix((np.ones(len(e), np.int8), (e[:, 0], e[:, 1])), shape=(nv, nv)), directed=False)
flab = vlab[tri[:, 0]]
counts = np.bincount(flab, minlength=n)
big = [c for c in np.argsort(-counts) if counts[c] >= min_tris]
cent = {c: co[vlab == c].mean(0) for c in range(n) if counts[c] > 0}
assign = {}
for c in range(n):
    if counts[c] == 0:
        continue
    assign[c] = c if c in big else min(big, key=lambda b: np.linalg.norm(cent[c] - cent[b]))
groups = {}
for c, b in assign.items():
    groups.setdefault(b, []).append(c)
order = sorted(groups, key=lambda b: float(cent[b][0]))
mat = me.materials[0]
info = json.load(open(os.path.join(HERE, "split", sheet + ".json")))
info["pieces"] = [p for p in info["pieces"] if p["id"] != pid]
for k, b in enumerate(order):
    fsel = np.where(np.isin(flab, groups[b]))[0]
    t = tri[fsel]
    vids, inv = np.unique(t, return_inverse=True)
    pm = bpy.data.meshes.new(pid + chr(97 + k))
    pm.from_pydata(co[vids].tolist(), [], inv.reshape(-1, 3).tolist())
    pm.uv_layers.new(name="UVMap")
    pm.uv_layers[0].data.foreach_set("uv", uv[fsel].reshape(-1))
    pm.materials.append(mat)
    no = bpy.data.objects.new(pid + chr(97 + k), pm)
    bpy.context.scene.collection.objects.link(no)
    c = co[vids]
    info["pieces"].append(dict(id=no.name, min=[round(float(v), 4) for v in c.min(0)],
                               max=[round(float(v), 4) for v in c.max(0)], tris=int(len(fsel))))
    cp = no.copy(); cp.data = no.data.copy(); bpy.context.scene.collection.objects.link(cp)
    if len(fsel) > 12000:
        d = cp.modifiers.new("dec", "DECIMATE"); d.ratio = 12000 / len(fsel)
    bpy.ops.object.select_all(action="DESELECT"); cp.select_set(True); bpy.context.view_layer.objects.active = cp
    bpy.ops.export_scene.gltf(filepath=os.path.join(HERE, "split", "glb", no.name + ".glb"), use_selection=True,
                              export_apply=True, export_format="GLB", export_yup=True)
    bpy.data.objects.remove(cp)
    print("NEW", no.name, len(fsel))
bpy.data.objects.remove(ob)
bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True)
json.dump(info, open(os.path.join(HERE, "split", sheet + ".json"), "w"), indent=1)
