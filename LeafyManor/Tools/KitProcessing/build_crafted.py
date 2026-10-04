"""Procedural Leafy Manor models on the 'Crafted' texture sheet (Blender 4.5 as a module).

usage: python build_crafted.py <out_dir>
Run crafted_textures.py first. Writes FBX files (metres + FBX Units Scale, front = -Y, no collision) into
LeafyManor/Models/<category>/ and preview GLBs into <out_dir>/_preview/ (for Tools/WebWalkthrough/add_web_models.sh):
  SM_LM_Banner_GoodPlants_01, SM_LM_Banner_HigherTogether_01   text banners, pivot top centre back
  SM_LM_Rug_NavyLeaf_01, SM_LM_Rug_NavyCrown_01                 navy / gold rugs, pivot bottom centre
  SM_LM_FountainWater_01                                        glowing water layers for SM_LM_Fountain_01, in the
                                                                fountain's own frame (same pivot), slot M_LM_Water
"""
import math
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from crafted_textures import BANNER_SIDE, REGIONS, SIZE  # noqa: E402

MODELS = os.path.join(HERE, "..", "..", "Models")
OUT = os.path.abspath(sys.argv[1])
SHEET = "Crafted"
os.makedirs(os.path.join(OUT, "_preview"), exist_ok=True)


def uv_of(region, fu, fv):
    """Fractions (0..1 across, 0..1 down) of an atlas region -> Blender UV (v up)."""
    x0, y0, x1, y1 = REGIONS[region]
    return (x0 + (x1 - x0) * fu) / SIZE, 1.0 - (y0 + (y1 - y0) * fv) / SIZE


class Builder:
    def __init__(self):
        self.v, self.f, self.uv = [], [], []

    def quad_grid(self, pos, uv, nu, nv, flip=False):
        """pos(i, j) / uv(i, j) for i in 0..nu, j in 0..nv -> quads."""
        base = len(self.v)
        grid_uv = {}
        for j in range(nv + 1):
            for i in range(nu + 1):
                self.v.append(pos(i, j))
                grid_uv[(i, j)] = uv(i, j)
        for j in range(nv):
            for i in range(nu):
                a, b = base + j * (nu + 1) + i, base + j * (nu + 1) + i + 1
                c, d = b + nu + 1, a + nu + 1
                face = [a, d, c, b] if flip else [a, b, c, d]
                self.f.append(face)
                self.uv.append([grid_uv[((k - base) % (nu + 1), (k - base) // (nu + 1))] for k in face])

    def sphere(self, c, r, region, seg=16, rings=8):
        self.quad_grid(lambda i, j: (c[0] + r * math.sin(math.pi * j / rings) * math.cos(2 * math.pi * i / seg),
                                     c[1] + r * math.sin(math.pi * j / rings) * math.sin(2 * math.pi * i / seg),
                                     c[2] + r * math.cos(math.pi * j / rings)),
                       lambda i, j: uv_of(region, i / seg, j / rings), seg, rings, flip=True)

    def obj(self, name, slot):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        uvl = me.uv_layers.new(name="UVMap")
        k = 0
        for poly, uvs in zip(me.polygons, self.uv):
            for li, uv in zip(poly.loop_indices, uvs):
                uvl.data[li].uv = uv
            k += 1
        me.validate()
        for p in me.polygons:
            p.use_smooth = True
        me.materials.append(bpy.data.materials.get(slot) or bpy.data.materials.new(slot))
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        return ob


def banner(name, region):
    """2.0 m cloth on a gold rod, V-shaped bottom with gold fringe. Pivot = top of the rod, at the wall (y = 0)."""
    b = Builder()
    W, z_t, z_s, z_p = 2.0, -0.10, -0.10 - 3.0, -0.10 - 3.7
    assert abs((z_t - z_s) / (z_t - z_p) - BANNER_SIDE) < 1e-6
    nu, nv = 32, 60

    def xyz(i, j):
        x = -W / 2 + W * i / nu
        bottom = z_s - (1 - abs(x) / (W / 2)) * (z_s - z_p)
        t = j / nv
        z = z_t + (bottom - z_t) * t
        y = -0.08 - 0.02 * math.sin(x * math.pi * 2.5 + 0.3) * (0.25 + 0.75 * t)
        return x, y, z

    b.quad_grid(xyz, lambda i, j: uv_of(region, i / nu, (z_t - xyz(i, j)[2]) / (z_t - z_p)), nu, nv, flip=True)
    # fringe hanging from the V edge
    b.quad_grid(lambda i, j: (xyz(i, nv)[0], xyz(i, nv)[1] - 0.004, xyz(i, nv)[2] - 0.14 * j),
                lambda i, j: uv_of("fringe", i / nu, j), nu, 1, flip=True)
    # rod + finials
    seg, r = 20, 0.035
    b.quad_grid(lambda i, j: (-1.15 + 2.3 * j, -0.08 + r * math.cos(2 * math.pi * i / seg), -0.06 + r * math.sin(2 * math.pi * i / seg)),
                lambda i, j: uv_of("gold", j, i / seg), seg, 1)
    for sx in (-1, 1):
        b.sphere((sx * 1.2, -0.08, -0.06), 0.065, "gold")
        b.sphere((sx * 1.29, -0.08, -0.06), 0.03, "gold")
    return b.obj(name, "M_LM_Kit_" + SHEET)


def rug(name, region, W, D, T=0.012):
    b = Builder()
    b.quad_grid(lambda i, j: (-W / 2 + W * i, -D / 2 + D * j, T), lambda i, j: uv_of(region, i, j), 1, 1)
    edge = lambda i, j: uv_of(region, 0.5, 0.003)        # navy sliver for the sides
    for (ax, ay, bx, by) in ((-W / 2, -D / 2, W / 2, -D / 2), (W / 2, -D / 2, W / 2, D / 2),
                             (W / 2, D / 2, -W / 2, D / 2), (-W / 2, D / 2, -W / 2, -D / 2)):
        b.quad_grid(lambda i, j: (ax + (bx - ax) * i, ay + (by - ay) * i, T * (1 - j)), edge, 1, 1, flip=True)
    return b.obj(name, "M_LM_Kit_" + SHEET)


def water(name):
    """Pool surface (r 1.62 m at 1.40 m), upper-bowl surface (r 1.12 m at 2.36 m) and the falling curtain between,
    measured from SM_LM_Fountain_01. UVs: u around, v outward / downward (the water material animates along v)."""
    b = Builder()
    seg = 64
    for R, z, rings in ((1.62, 1.40, 6), (1.12, 2.36, 5)):
        b.quad_grid(lambda i, j: (R * j / rings * math.cos(2 * math.pi * i / seg), R * j / rings * math.sin(2 * math.pi * i / seg), z),
                    lambda i, j: (4 * i / seg, j / rings), seg, rings, flip=True)
    r0, z0, r1, z1, rows = 1.17, 2.33, 1.45, 1.40, 8
    b.quad_grid(lambda i, j: ((r0 + (r1 - r0) * j / rows) * math.cos(2 * math.pi * i / seg),
                              (r0 + (r1 - r0) * j / rows) * math.sin(2 * math.pi * i / seg), z0 + (z1 - z0) * j / rows),
                lambda i, j: (8 * i / seg, j / rows), seg, rows, flip=True)
    return b.obj(name, "M_LM_Water")


def export(ob, category):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    path = os.path.join(MODELS, category, ob.name + ".fbx")
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, apply_scale_options="FBX_SCALE_UNITS",
                             object_types={"MESH"}, mesh_smooth_type="FACE", add_leaf_bones=False, path_mode="STRIP",
                             use_mesh_modifiers=True, bake_anim=False)
    # preview GLB with the sheet's 1k texture (also on the water, so its UVs survive packing; the page swaps
    # in its own animated water material)
    slot = ob.data.materials[0]
    if True:
        pm = bpy.data.materials.new(ob.name + "_prev")
        pm.use_nodes = True
        node = pm.node_tree.nodes.new("ShaderNodeTexImage")
        node.image = PREVIEW_IMG
        pm.node_tree.links.new(node.outputs["Color"], pm.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
        ob.data.materials[0] = pm
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "_preview", ob.name + ".glb"), use_selection=True,
                              export_format="GLB", export_yup=True)
    ob.data.materials[0] = slot
    xs = [v.co for v in ob.data.vertices]
    size = [round((max(c[k] for c in xs) - min(c[k] for c in xs)) * 100, 1) for k in range(3)]
    print("DONE", ob.name, size, len(ob.data.polygons), "faces ->", os.path.relpath(path, MODELS))


bpy.ops.wm.read_factory_settings(use_empty=True)
_prev_png = os.path.join(OUT, "_preview", SHEET + "_basecolor_1k.png")   # pack_kit.py maps this name to the 4K sheet
_img = bpy.data.images.load(os.path.join(MODELS, "Textures", "T_LM_Kit_%s_BaseColor.jpg" % SHEET))
_img.scale(1024, 1024)
_img.save(filepath=_prev_png, quality=90)
PREVIEW_IMG = bpy.data.images.load(_prev_png)
for ob, cat in ((banner("SM_LM_Banner_GoodPlants_01", "banner_plants"), "Props"),
                (banner("SM_LM_Banner_HigherTogether_01", "banner_higher"), "Props"),
                (rug("SM_LM_Rug_NavyLeaf_01", "rug_leaf", 7.40, 6.80), "Props"),
                (rug("SM_LM_Rug_NavyCrown_01", "rug_crown", 3.40, 3.40), "Props"),
                (water("SM_LM_FountainWater_01"), "Props")):
    export(ob, cat)
