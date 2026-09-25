"""Procedural grand staircase + balustrade for Leafy Manor (Blender 4.5 as a module).

usage: python build_stairs.py out_dir
Outputs (FBX, metres + FBX Units Scale, ascent along +X, pivot = floor at the first riser, centred on width):
  Architecture/SM_LM_Stair_Grand_01.fbx       slots: M_LM_StairMarble, M_LM_StairCarpet
  Architecture/SM_LM_StairBalustrade_01.fbx   slots: M_LM_Kit_Stairs (kit balusters), M_LM_StairMarble (handrail)
"""
import os
import sys

import bpy
import bmesh

OUT = os.path.abspath(sys.argv[1])
HERE = os.path.dirname(os.path.abspath(__file__))
N_TREADS, RISE, TREAD, WIDTH = 41, 0.1224, 0.204, 2.38
CARPET_W, TILE = 1.40, 1.36
CARPET_ASPECT = 400.0 / 347.0           # captured runner texture: height / width
RAIL_H, RAIL_W, RAIL_T = 0.61, 0.14, 0.08
L = N_TREADS * TREAD


def new_obj(name, slots):
    me = bpy.data.meshes.new(name)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    for s in slots:
        me.materials.append(bpy.data.materials.get(s) or bpy.data.materials.new(s))
    return ob


def quad(bm, uvl, pts, uvs, mat):
    f = bm.faces.new([bm.verts.new(p) for p in pts])
    f.material_index = mat
    for loop, uv in zip(f.loops, uvs):
        loop[uvl].uv = uv
    return f


def build_stair():
    ob = new_obj("SM_LM_Stair_Grand_01", ["M_LM_StairMarble", "M_LM_StairCarpet"])
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    hw, cw = WIDTH / 2, CARPET_W / 2
    for i in range(N_TREADS + 1):                      # risers (last one = gallery edge)
        x, z0, z1 = i * TREAD, i * RISE, (i + 1) * RISE
        quad(bm, uvl, [(x, hw, z0), (x, -hw, z0), (x, -hw, z1), (x, hw, z1)],
             [(hw / TILE, z0 / TILE), (-hw / TILE, z0 / TILE), (-hw / TILE, z1 / TILE), (hw / TILE, z1 / TILE)], 0)
    for i in range(N_TREADS):                          # treads
        x0, x1, z = i * TREAD, (i + 1) * TREAD, (i + 1) * RISE
        quad(bm, uvl, [(x0, -hw, z), (x1, -hw, z), (x1, hw, z), (x0, hw, z)],
             [(x0 / TILE, -hw / TILE), (x1 / TILE, -hw / TILE), (x1 / TILE, hw / TILE), (x0 / TILE, hw / TILE)], 0)
    for s in (-1, 1):                                  # solid sides, one column per step
        y = s * hw
        for i in range(N_TREADS):
            x0, x1, z = i * TREAD, (i + 1) * TREAD, (i + 1) * RISE
            pts = [(x0, y, 0), (x1, y, 0), (x1, y, z), (x0, y, z)]
            uvs = [(x0 / TILE, 0), (x1 / TILE, 0), (x1 / TILE, z / TILE), (x0 / TILE, z / TILE)]
            if s > 0:
                pts, uvs = pts[::-1], uvs[::-1]
            quad(bm, uvl, pts, uvs, 0)
    zt = (N_TREADS + 1) * RISE                         # back face
    quad(bm, uvl, [(L, -hw, 0), (L, hw, 0), (L, hw, zt), (L, -hw, zt)],
         [(0, 0), (WIDTH / TILE, 0), (WIDTH / TILE, zt / TILE), (0, zt / TILE)], 0)
    # carpet runner draped over risers and treads
    vrep = CARPET_W * CARPET_ASPECT
    s = 0.0
    for i in range(N_TREADS + 1):
        x, z0, z1 = i * TREAD - 0.006, i * RISE, (i + 1) * RISE
        quad(bm, uvl, [(x, cw, z0), (x, -cw, z0), (x, -cw, z1), (x, cw, z1)],
             [(1, s / vrep), (0, s / vrep), (0, (s + RISE) / vrep), (1, (s + RISE) / vrep)], 1)
        s += RISE
        if i < N_TREADS:
            x0, x1, z = i * TREAD - 0.006, (i + 1) * TREAD - 0.006, (i + 1) * RISE + 0.006
            quad(bm, uvl, [(x0, -cw, z), (x1, -cw, z), (x1, cw, z), (x0, cw, z)],
                 [(0, s / vrep), (0, (s + TREAD) / vrep), (1, (s + TREAD) / vrep), (1, s / vrep)], 1)
            s += TREAD
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bm.to_mesh(ob.data)
    bm.free()
    return ob


def build_balustrade():
    # import processed kit baluster (drop its collision) and array it along the flight
    bpy.ops.import_scene.fbx(filepath=os.path.join(OUT, "Architecture", "SM_LM_Baluster_01.fbx"))
    bal = None
    for o in list(bpy.context.selected_objects):
        if o.name.startswith("UCX_"):
            bpy.data.objects.remove(o)
        else:
            bal = o
    bpy.context.view_layer.objects.active = bal
    bpy.ops.object.select_all(action="DESELECT")
    bal.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    d = bal.modifiers.new("dec", "DECIMATE")
    d.ratio = 1500 / max(1, len(bal.data.polygons))
    bpy.ops.object.modifier_apply(modifier="dec")
    bz = [v.co.z for v in bal.data.vertices]
    bh = max(bz) - min(bz)
    bal.data.materials.clear()
    bal.data.materials.append(bpy.data.materials.get("M_LM_Kit_Stairs") or bpy.data.materials.new("M_LM_Kit_Stairs"))
    bal.data.materials.append(bpy.data.materials.get("M_LM_StairMarble") or bpy.data.materials.new("M_LM_StairMarble"))
    target_h = 0.5 * RISE + RAIL_H - RAIL_T                 # tread top -> rail underside (constant)
    parts = []
    for i in range(N_TREADS):
        c = bal.copy()
        c.data = bal.data.copy()
        bpy.context.scene.collection.objects.link(c)
        c.scale = (1, 1, target_h / bh)
        c.location = ((i + 0.5) * TREAD, 0, (i + 1) * RISE - min(bz) * target_h / bh)
        parts.append(c)
    bpy.data.objects.remove(bal)
    # sloped handrail (slot 1 = marble)
    rail = new_obj("rail", ["M_LM_Kit_Stairs", "M_LM_StairMarble"])
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    k = RISE / TREAD
    x0, x1 = -0.05, L + 0.05
    def zt(x):
        return RISE + x * k + RAIL_H
    hw = RAIL_W / 2
    top = [(x0, -hw, zt(x0)), (x1, -hw, zt(x1)), (x1, hw, zt(x1)), (x0, hw, zt(x0))]
    bot = [(x, y, z - RAIL_T) for x, y, z in top]
    faces = [top, bot[::-1], [bot[0], bot[1], top[1], top[0]], [top[3], top[2], bot[2], bot[3]],
             [bot[1], bot[2], top[2], top[1]], [top[0], top[3], bot[3], bot[0]]]
    for f in faces:
        quad(bm, uvl, f, [(p[0] / TILE, (p[1] + p[2]) / TILE) for p in f], 1)
    bm.to_mesh(rail.data)
    bm.free()
    parts.append(rail)
    bpy.ops.object.select_all(action="DESELECT")
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = rail
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.join()
    rail.name = rail.data.name = "SM_LM_StairBalustrade_01"
    return rail


def export(ob, sub):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    for p in ob.data.polygons:
        p.use_smooth = False
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, sub, ob.name + ".fbx"), use_selection=True,
                             apply_scale_options="FBX_SCALE_UNITS", object_types={"MESH"}, mesh_smooth_type="FACE",
                             add_leaf_bones=False, path_mode="STRIP", bake_anim=False)


def preview(ob, textures):
    mats = []
    for slot, tex in zip(ob.data.materials, textures):
        m = bpy.data.materials.new(slot.name + "_prev")
        m.use_nodes = True
        n = m.node_tree.nodes.new("ShaderNodeTexImage")
        n.image = bpy.data.images.load(tex, check_existing=True)
        m.node_tree.links.new(n.outputs["Color"], m.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
        mats.append(m)
    orig = list(ob.data.materials)
    for i, m in enumerate(mats):
        ob.data.materials[i] = m
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "_preview", ob.name + ".glb"), use_selection=True,
                              export_format="GLB", export_yup=True)
    for i, m in enumerate(orig):
        ob.data.materials[i] = m


def build_runner():
    """Floor runner tile: one texture repeat (165 x 143 cm), pivot centre on the floor, length along +X."""
    ob = new_obj("SM_LM_Runner_01", ["M_LM_StairCarpet"])
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    ln, hw = CARPET_W * CARPET_ASPECT, CARPET_W / 2
    quad(bm, uvl, [(-ln / 2, -hw, 0), (ln / 2, -hw, 0), (ln / 2, hw, 0), (-ln / 2, hw, 0)], [(0, 0), (0, 1), (1, 1), (1, 0)], 0)
    bm.to_mesh(ob.data)
    bm.free()
    return ob


bpy.ops.wm.read_factory_settings(use_empty=True)
marble = os.path.join(OUT, "Textures", "T_LM_Marble_Cream_BaseColor.png")
carpet = os.path.join(OUT, "Textures", "T_LM_StairCarpet_BaseColor.png")
st = build_stair()
export(st, "Architecture")
preview(st, [marble, carpet])
bl = build_balustrade()
export(bl, "Architecture")
preview(bl, [os.path.join(HERE, "split", "glb", "Stairs_basecolor_1k.png"), marble])
rn = build_runner()
export(rn, "Architecture")
preview(rn, [carpet])
print("STAIRS", len(st.data.polygons), "BALUSTRADE", len(bl.data.polygons))
