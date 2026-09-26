"""Pack the kit models used by the layout into one web GLB (decimated, shared textures).

Usage (Blender Python / bpy module): python pack_kit.py <kit_out_dir>
<kit_out_dir> is the folder given to KitProcessing/process_pieces.py; its _preview/*.glb are read.
"""
import os, sys, json
import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
PREVIEW_DIR = os.path.join(os.path.abspath(sys.argv[-1]), '_preview')
os.makedirs(os.path.join(HERE, 'build'), exist_ok=True)
sys.path.insert(0, REPO + '/Unreal/Python')
import leafy_manor_layout as lm

used = sorted({p.mesh for p in lm.build() if p.mesh})
TEX_SRC = REPO + '/Models/Textures'
TEX_SIZE = {'door_set': 2048, 'Architecture': 2048}
TARGET = {'SM_LM_Fountain_01': 16000, 'SM_LM_StairBalustrade_01': 14000, 'SM_LM_Stair_Grand_01': 999999,
          'SM_LM_Runner_01': 999999, 'SM_LM_LionStatue_01': 9000, 'SM_LM_Backdrop_CastleCliff_01': 7000}
for w in ('Plain', 'Window', 'Arch', 'DoorSingle', 'DoorDouble'):
    TARGET['SM_LM_Wall_%s_01' % w] = 4500
TARGET.update({'SM_LM_Cornice_01': 1800, 'SM_LM_Balustrade_01': 2500})

bpy.ops.wm.read_factory_settings(use_empty=True)
shared_img, shared_mat = {}, {}


def image_for(name):
    """Map a preview image name to a shared, resized image."""
    if name in shared_img:
        return shared_img[name]
    if name.endswith('_basecolor_1k'):
        sheet = name[:-len('_basecolor_1k')]
        src = '%s/T_LM_Kit_%s_BaseColor.jpg' % (TEX_SRC, sheet)
        size = TEX_SIZE.get(sheet, 1024)
    else:
        src, size = '%s/%s.png' % (TEX_SRC, name), 512
    img = bpy.data.images.load(src)
    img.scale(size, size)
    img.name = 'T_' + name
    img.file_format = 'JPEG'
    shared_img[name] = img
    return img


def material_for(src_mat):
    img = None
    for n in src_mat.node_tree.nodes:
        if n.type == 'TEX_IMAGE' and n.image:
            img = n.image.name.rsplit('.', 1)[0] if n.image.name[-4:-3] == '.' and n.image.name[-3:].isdigit() else n.image.name
    key = img or 'none'
    if key in shared_mat:
        return shared_mat[key]
    m = bpy.data.materials.new('M_' + key)
    m.use_nodes = True
    bsdf = m.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Roughness'].default_value = 0.55
    if img:
        t = m.node_tree.nodes.new('ShaderNodeTexImage')
        t.image = image_for(img)
        m.node_tree.links.new(t.outputs['Color'], bsdf.inputs['Base Color'])
    shared_mat[key] = m
    return m


report = []
for name in used:
    path = os.path.join(PREVIEW_DIR, name + '.glb')
    if not os.path.exists(path):
        report.append((name, 'MISSING'))
        continue
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == 'MESH']
    bpy.ops.object.select_all(action='DESELECT')
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for o in new:
        if o != ob and o.name in bpy.data.objects:
            bpy.data.objects.remove(o, do_unlink=True)
    ob.name = ob.data.name = name
    for i, s in enumerate(ob.material_slots):
        s.material = material_for(s.material)
    tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    tgt = TARGET.get(name, min(6000, max(1500, int(tris * 0.2))))
    if tris > tgt:
        mod = ob.modifiers.new('dec', 'DECIMATE')
        mod.ratio = tgt / tris
        bpy.ops.object.modifier_apply(modifier='dec')
    after = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    report.append((name, tris, after))

# drop the preview images/materials that came with the imports
for m in list(bpy.data.materials):
    if m not in shared_mat.values():
        bpy.data.materials.remove(m)
for im in list(bpy.data.images):
    if im not in shared_img.values():
        bpy.data.images.remove(im)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=os.path.join(HERE, 'build', 'kit_raw.glb'), export_format='GLB',
                          use_selection=True, export_image_format='JPEG', export_jpeg_quality=80,
                          export_apply=True, export_animations=False, export_extras=False)
tot = 0
for r in report:
    print(r)
    tot += r[2] if len(r) == 3 else 0
print('TOTAL tris', tot, 'meshes', len(report))
