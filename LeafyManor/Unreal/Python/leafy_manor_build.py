"""
Leafy Manor - Entrance Hall: build the level inside Unreal Editor (UE 5.1+).

Run:  Tools > Execute Python Script...  ->  pick this file
      Needs the "Python Editor Script Plugin" + "Editor Scripting Utilities".
      Keep leafy_manor_layout.py and leafy_manor_kit.py next to it, and the repo's LeafyManor/Models
      folder two levels up (the default when you run it from the repo clone) - or set MODELS_DIR below.

What it does (only ever touches /Game/LeafyManor/ and the level it creates):
  1. Asks you to save unsaved work (standard dialog) - Cancel aborts without changes.
  2. Imports the model kit (FBX with UCX collision) + textures from LeafyManor/Models, creates the kit,
     stair, carpet and marble-checker-floor materials.   (skipped if DRESSED = False)
  3. Opens / creates /Game/LeafyManor/Maps/LVL_LM_EntranceHall.
  4. Removes actors from a previous run (tag "LM_Blockout") and rebuilds the hall: kit models, hidden
     collision stand-ins for walls and stairs, invisible safety walls, lights, PlayerStart, test markers,
     NavMeshBoundsVolume, post-process.
  5. Saves the level and /Game/LeafyManor.

It never creates or edits a character, controller, camera or GameMode: your project's default GameMode
spawns your existing player at the PlayerStart.
"""

import glob
import importlib
import os
import sys

import unreal

try:
    _HERE = os.path.dirname(os.path.abspath(__file__))
    if _HERE not in sys.path:
        sys.path.append(_HERE)
except NameError:  # executed without __file__: rely on Content/Python being on sys.path
    _HERE = ""

import leafy_manor_kit as lmk  # noqa: E402
import leafy_manor_layout as lm  # noqa: E402

importlib.reload(lmk)
importlib.reload(lm)

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
DRESSED = True                    # False = grey blockout only (no model import)
MODELS_DIR = os.path.normpath(os.path.join(_HERE, "..", "..", "Models"))
REIMPORT_MODELS = False           # True = re-import FBX/textures even if the assets already exist
REBUILD_MATERIALS = False         # True = regenerate the generated materials
ENABLE_NANITE = True
SCONCE_LIGHTS = True              # small warm light at every wall sconce

ROOT = "/Game/LeafyManor"
FOLDERS = ["Architecture", "Architecture/Blockout", "Props", "Furniture", "Materials", "Materials/Blockout",
           "Materials/Kit", "Textures", "Blueprints", "Lighting", "FX", "Models", "Maps"]
MAP_PATH = ROOT + "/Maps/LVL_LM_EntranceHall"
BLOCKOUT_TAG = "LM_Blockout"
OUTLINER_ROOT = "LeafyManor"

EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
ASSET_TOOLS = unreal.AssetToolsHelpers.get_asset_tools()

SHAPES = {
    "box": ("/Engine/BasicShapes/Cube", "SM_LM_BO_Cube", "BOX"),
    "cyl": ("/Engine/BasicShapes/Cylinder", "SM_LM_BO_Cylinder", "NDOP10_Z"),
    "cone": ("/Engine/BasicShapes/Cone", "SM_LM_BO_Cone", "NDOP10_Z"),
    "sphere": ("/Engine/BasicShapes/Sphere", "SM_LM_BO_Sphere", "SPHERE"),
}
WHITE_TEX = "/Engine/EngineResources/WhiteSquareTexture"
NORMAL_TEX = "/Engine/EngineMaterials/DefaultNormal"


def _log(msg):
    unreal.log("[LeafyManor] " + msg)


# ---------------------------------------------------------------------------
# Blockout assets
# ---------------------------------------------------------------------------
def ensure_folders():
    for f in [""] + FOLDERS:
        path = ROOT + ("/" + f if f else "")
        if not EAL.does_directory_exist(path):
            EAL.make_directory(path)


def ensure_blockout_meshes():
    sme = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    meshes = {}
    for key, (src, name, collision) in SHAPES.items():
        dst = "%s/Architecture/Blockout/%s" % (ROOT, name)
        if not EAL.does_asset_exist(dst):
            if not EAL.duplicate_asset(src, dst):
                raise RuntimeError("Could not duplicate %s -> %s" % (src, dst))
        mesh = EAL.load_asset(dst)
        if sme.get_simple_collision_count(mesh) == 0:
            sme.add_simple_collisions(mesh, getattr(unreal.ScriptCollisionShapeType, collision))
            EAL.save_loaded_asset(mesh)
        meshes[key] = mesh
    return meshes


def _new_asset(name, folder, cls, factory):
    path = "%s/%s" % (folder, name)
    if EAL.does_asset_exist(path):
        if not REBUILD_MATERIALS:
            return EAL.load_asset(path), False
        EAL.delete_asset(path)
    return ASSET_TOOLS.create_asset(name, folder, cls, factory), True


def _expr(mat, cls, x, y, **props):
    e = MEL.create_material_expression(mat, cls, x, y)
    for k, v in props.items():
        e.set_editor_property(k, v)
    return e


def _connect(a, b, pin="", out=""):
    if not MEL.connect_material_expressions(a, out, b, pin):
        raise RuntimeError("material connection failed: %s.%s -> %s.%s" % (a.get_name(), out, b.get_name(), pin))


def ensure_blockout_material(folder):
    """M_LM_Blockout: tinted 1 m world-space checker + roughness/metal/emissive params."""
    mat, created = _new_asset("M_LM_Blockout", folder, unreal.Material, unreal.MaterialFactoryNew())
    if not created:
        return mat
    V, S = unreal.MaterialExpressionVectorParameter, unreal.MaterialExpressionScalarParameter
    base = _expr(mat, V, -700, -300, parameter_name="BaseColor", default_value=unreal.LinearColor(0.5, 0.5, 0.5, 1))
    grid = _expr(mat, S, -1300, -60, parameter_name="GridSize", default_value=100.0)
    contrast = _expr(mat, S, -700, -120, parameter_name="GridContrast", default_value=0.12)
    wpos = _expr(mat, unreal.MaterialExpressionWorldPosition, -1500, 0)
    offset = _expr(mat, unreal.MaterialExpressionAdd, -1300, 0, const_b=0.37)
    div = _expr(mat, unreal.MaterialExpressionDivide, -1150, 0)
    flr = _expr(mat, unreal.MaterialExpressionFloor, -1000, 0)
    ones = _expr(mat, unreal.MaterialExpressionConstant3Vector, -1000, 100, constant=unreal.LinearColor(1, 1, 1, 1))
    dot = _expr(mat, unreal.MaterialExpressionDotProduct, -850, 0)
    half = _expr(mat, unreal.MaterialExpressionMultiply, -700, 0, const_b=0.5)
    frac = _expr(mat, unreal.MaterialExpressionFrac, -550, 0)
    checker = _expr(mat, unreal.MaterialExpressionMultiply, -400, 0, const_b=2.0)
    shade = _expr(mat, unreal.MaterialExpressionMultiply, -300, -80)
    inv = _expr(mat, unreal.MaterialExpressionOneMinus, -200, -80)
    color = _expr(mat, unreal.MaterialExpressionMultiply, -100, -250)
    for a, b, pin in ((wpos, offset, "A"), (offset, div, "A"), (grid, div, "B"), (div, flr, ""), (flr, dot, "A"),
                      (ones, dot, "B"), (dot, half, "A"), (half, frac, ""), (frac, checker, "A"), (checker, shade, "A"),
                      (contrast, shade, "B"), (shade, inv, ""), (base, color, "A"), (inv, color, "B")):
        _connect(a, b, pin)
    MEL.connect_material_property(color, "", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = _expr(mat, S, -300, 150, parameter_name="Roughness", default_value=0.6)
    metal = _expr(mat, S, -300, 250, parameter_name="Metallic", default_value=0.0)
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(metal, "", unreal.MaterialProperty.MP_METALLIC)
    ecol = _expr(mat, V, -500, 400, parameter_name="EmissiveColor", default_value=unreal.LinearColor(0, 0, 0, 1))
    estr = _expr(mat, S, -500, 550, parameter_name="EmissiveStrength", default_value=0.0)
    emis = _expr(mat, unreal.MaterialExpressionMultiply, -300, 450)
    _connect(ecol, emis, "A")
    _connect(estr, emis, "B")
    MEL.connect_material_property(emis, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.recompile_material(mat)
    EAL.save_loaded_asset(mat)
    return mat


def ensure_collision_material(folder):
    mat, created = _new_asset("M_LM_BO_Collision", folder, unreal.Material, unreal.MaterialFactoryNew())
    if not created:
        return mat
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("two_sided", True)
    col = _expr(mat, unreal.MaterialExpressionVectorParameter, -400, 0, parameter_name="Color",
                default_value=unreal.LinearColor(1.0, 0.1, 0.1, 1))
    opa = _expr(mat, unreal.MaterialExpressionScalarParameter, -400, 200, parameter_name="Opacity", default_value=0.2)
    MEL.connect_material_property(col, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.connect_material_property(opa, "", unreal.MaterialProperty.MP_OPACITY)
    MEL.recompile_material(mat)
    EAL.save_loaded_asset(mat)
    return mat


def ensure_blockout_materials():
    folder = ROOT + "/Materials/Blockout"
    master = ensure_blockout_material(folder)
    mats = {"Invisible": ensure_collision_material(folder)}
    for key, spec in lm.MATERIALS.items():
        if spec is None:
            continue
        mi, created = _new_asset("MI_LM_BO_" + key, folder, unreal.MaterialInstanceConstant,
                                 unreal.MaterialInstanceConstantFactoryNew())
        if created:
            base, rough, metal, emis, estr = spec
            MEL.set_material_instance_parent(mi, master)
            MEL.set_material_instance_vector_parameter_value(mi, "BaseColor", unreal.LinearColor(*base, 1.0))
            MEL.set_material_instance_scalar_parameter_value(mi, "Roughness", rough)
            MEL.set_material_instance_scalar_parameter_value(mi, "Metallic", metal)
            MEL.set_material_instance_vector_parameter_value(mi, "EmissiveColor", unreal.LinearColor(*emis, 1.0))
            MEL.set_material_instance_scalar_parameter_value(mi, "EmissiveStrength", estr)
            if estr > 0:
                MEL.set_material_instance_scalar_parameter_value(mi, "GridContrast", 0.0)
            MEL.update_material_instance(mi)
            EAL.save_loaded_asset(mi)
        mats[key] = mi
    return mats


# ---------------------------------------------------------------------------
# Model kit import + materials
# ---------------------------------------------------------------------------
def _fbx_task(path, dest):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", path)
    task.set_editor_property("destination_path", dest)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)
    ui = unreal.FbxImportUI()
    ui.set_editor_property("import_mesh", True)
    ui.set_editor_property("import_as_skeletal", False)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("import_animations", False)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
    smd = ui.get_editor_property("static_mesh_import_data")
    smd.set_editor_property("combine_meshes", True)
    smd.set_editor_property("auto_generate_collision", False)
    smd.set_editor_property("generate_lightmap_u_vs", False)
    ui.set_editor_property("static_mesh_import_data", smd)
    task.set_editor_property("options", ui)
    return task


def _file_task(path, dest):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", path)
    task.set_editor_property("destination_path", dest)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)
    return task


def import_kit():
    if not os.path.isdir(MODELS_DIR):
        raise RuntimeError("Model kit not found at %s - set MODELS_DIR at the top of this script" % MODELS_DIR)
    tasks = []
    for f in sorted(glob.glob(os.path.join(MODELS_DIR, "Textures", "*.*"))):
        name = os.path.splitext(os.path.basename(f))[0]
        if REIMPORT_MODELS or not EAL.does_asset_exist("%s/Textures/%s" % (ROOT, name)):
            tasks.append(_file_task(f, ROOT + "/Textures"))
    for cat in ("Architecture", "Props", "Furniture"):
        for f in sorted(glob.glob(os.path.join(MODELS_DIR, cat, "*.fbx"))):
            name = os.path.splitext(os.path.basename(f))[0]
            if REIMPORT_MODELS or not EAL.does_asset_exist("%s/%s/%s" % (ROOT, cat, name)):
                tasks.append(_fbx_task(f, "%s/%s" % (ROOT, cat)))
    if tasks:
        _log("importing %d files from %s (first run takes a few minutes)" % (len(tasks), MODELS_DIR))
        ASSET_TOOLS.import_asset_tasks(tasks)
    # texture settings
    for f in glob.glob(os.path.join(MODELS_DIR, "Textures", "*.*")):
        name = os.path.splitext(os.path.basename(f))[0]
        tex = EAL.load_asset("%s/Textures/%s" % (ROOT, name))
        if tex is None:
            continue
        if name.endswith("_Normal"):
            tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
            tex.set_editor_property("srgb", False)
        elif name.endswith("_ORM"):
            tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
            tex.set_editor_property("srgb", False)
        EAL.save_loaded_asset(tex)
    meshes = {}
    for name, info in lmk.KIT.items():
        mesh = EAL.load_asset("%s/%s/%s" % (ROOT, info["category"], name))
        if mesh is None:
            unreal.log_warning("[LeafyManor] missing kit mesh %s (import failed?)" % name)
            continue
        meshes[name] = mesh
    return meshes


def _tex(name, fallback):
    t = EAL.load_asset("%s/Textures/%s" % (ROOT, name)) if name else None
    return t or EAL.load_asset(fallback)


def ensure_kit_master(folder):
    """M_LM_KitMaster: BaseColor / Normal / ORM (R=AO, G=Roughness, B=Metallic) + constant fallbacks."""
    mat, created = _new_asset("M_LM_KitMaster", folder, unreal.Material, unreal.MaterialFactoryNew())
    if not created:
        return mat
    T, S, V = unreal.MaterialExpressionTextureSampleParameter2D, unreal.MaterialExpressionScalarParameter, \
        unreal.MaterialExpressionVectorParameter
    bc = _expr(mat, T, -800, -300, parameter_name="BaseColorTex", texture=EAL.load_asset(WHITE_TEX))
    nm = _expr(mat, T, -800, 0, parameter_name="NormalTex", texture=EAL.load_asset(NORMAL_TEX),
               sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    # default ORM must be a Masks texture to match the sampler type: use any imported kit ORM map
    orm_default = next((EAL.load_asset("%s/Textures/%s" % (ROOT, os.path.splitext(os.path.basename(f))[0]))
                        for f in sorted(glob.glob(os.path.join(MODELS_DIR, "Textures", "*_ORM.*")))), None)
    orm = _expr(mat, T, -800, 300, parameter_name="ORMTex", texture=orm_default,
                sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    tint = _expr(mat, V, -500, -420, parameter_name="Tint", default_value=unreal.LinearColor(1, 1, 1, 1))
    use = _expr(mat, S, -500, 500, parameter_name="UseORM", default_value=1.0)
    rc = _expr(mat, S, -500, 380, parameter_name="Roughness", default_value=0.5)
    mc = _expr(mat, S, -500, 620, parameter_name="Metallic", default_value=0.0)
    col = _expr(mat, unreal.MaterialExpressionMultiply, -300, -300)
    _connect(bc, col, "A", "RGB")
    _connect(tint, col, "B")
    MEL.connect_material_property(col, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(nm, "RGB", unreal.MaterialProperty.MP_NORMAL)
    lr = _expr(mat, unreal.MaterialExpressionLinearInterpolate, -300, 300)
    _connect(rc, lr, "A")
    _connect(orm, lr, "B", "G")
    _connect(use, lr, "Alpha")
    lm_ = _expr(mat, unreal.MaterialExpressionLinearInterpolate, -300, 520)
    _connect(mc, lm_, "A")
    _connect(orm, lm_, "B", "B")
    _connect(use, lm_, "Alpha")
    ao = _expr(mat, unreal.MaterialExpressionLinearInterpolate, -300, 700, const_a=1.0)
    _connect(orm, ao, "B", "R")
    _connect(use, ao, "Alpha")
    MEL.connect_material_property(lr, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(lm_, "", unreal.MaterialProperty.MP_METALLIC)
    MEL.connect_material_property(ao, "", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    MEL.recompile_material(mat)
    EAL.save_loaded_asset(mat)
    return mat


def ensure_floor_checker(folder):
    """M_LM_FloorChecker: cream / black marble tiles (136 cm) in world space - no UVs needed."""
    mat, created = _new_asset("M_LM_FloorChecker", folder, unreal.Material, unreal.MaterialFactoryNew())
    if not created:
        return mat
    S = unreal.MaterialExpressionScalarParameter
    wpos = _expr(mat, unreal.MaterialExpressionWorldPosition, -1400, 0)
    mask = _expr(mat, unreal.MaterialExpressionComponentMask, -1250, 0, r=True, g=True, b=False, a=False)
    size = _expr(mat, S, -1250, 150, parameter_name="TileSize", default_value=136.0)
    uv = _expr(mat, unreal.MaterialExpressionDivide, -1100, 0)
    _connect(wpos, mask)
    _connect(mask, uv, "A")
    _connect(size, uv, "B")
    cream = _expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, -800, -250, parameter_name="CreamTex",
                  texture=_tex("T_LM_FloorTile_Cream_BaseColor", WHITE_TEX))
    black = _expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, -800, 50, parameter_name="BlackTex",
                  texture=_tex("T_LM_FloorTile_Black_BaseColor", WHITE_TEX))
    _connect(uv, cream, "UVs")
    _connect(uv, black, "UVs")
    flr = _expr(mat, unreal.MaterialExpressionFloor, -950, 300)
    ones = _expr(mat, unreal.MaterialExpressionConstant2Vector, -950, 420, r=1.0, g=1.0)
    dot = _expr(mat, unreal.MaterialExpressionDotProduct, -800, 320)
    half = _expr(mat, unreal.MaterialExpressionMultiply, -650, 320, const_b=0.5)
    frac = _expr(mat, unreal.MaterialExpressionFrac, -520, 320)
    chk = _expr(mat, unreal.MaterialExpressionMultiply, -400, 320, const_b=2.0)
    _connect(uv, flr)
    _connect(flr, dot, "A")
    _connect(ones, dot, "B")
    _connect(dot, half, "A")
    _connect(half, frac)
    _connect(frac, chk, "A")
    lerp = _expr(mat, unreal.MaterialExpressionLinearInterpolate, -250, -50)
    _connect(cream, lerp, "A", "RGB")
    _connect(black, lerp, "B", "RGB")
    _connect(chk, lerp, "Alpha")
    MEL.connect_material_property(lerp, "", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = _expr(mat, S, -250, 200, parameter_name="Roughness", default_value=0.22)
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(mat)
    EAL.save_loaded_asset(mat)
    return mat


def ensure_kit_materials():
    folder = ROOT + "/Materials/Kit"
    master = ensure_kit_master(folder)
    mats = {"FloorChecker": ensure_floor_checker(folder)}
    specs = {}
    for f in glob.glob(os.path.join(MODELS_DIR, "Textures", "T_LM_Kit_*_BaseColor.*")):
        sheet = os.path.basename(f)[len("T_LM_Kit_"):].rsplit("_BaseColor", 1)[0]
        specs["M_LM_Kit_" + sheet] = ("T_LM_Kit_%s_BaseColor" % sheet, "T_LM_Kit_%s_Normal" % sheet,
                                     "T_LM_Kit_%s_ORM" % sheet, 1.0, 0.5, 0.0)
    specs["M_LM_StairMarble"] = ("T_LM_Marble_Cream_BaseColor", None, None, 0.0, 0.25, 0.0)
    specs["M_LM_StairCarpet"] = ("T_LM_StairCarpet_BaseColor", None, None, 0.0, 0.95, 0.0)
    for slot, (b, n, o, use, rough, metal) in specs.items():
        mi, created = _new_asset("MI" + slot[1:], folder, unreal.MaterialInstanceConstant,
                                 unreal.MaterialInstanceConstantFactoryNew())
        if created:
            MEL.set_material_instance_parent(mi, master)
            MEL.set_material_instance_texture_parameter_value(mi, "BaseColorTex", _tex(b, WHITE_TEX))
            MEL.set_material_instance_texture_parameter_value(mi, "NormalTex", _tex(n, NORMAL_TEX))
            if o:
                MEL.set_material_instance_texture_parameter_value(mi, "ORMTex", _tex(o, WHITE_TEX))
            MEL.set_material_instance_scalar_parameter_value(mi, "UseORM", use)
            MEL.set_material_instance_scalar_parameter_value(mi, "Roughness", rough)
            MEL.set_material_instance_scalar_parameter_value(mi, "Metallic", metal)
            MEL.update_material_instance(mi)
            EAL.save_loaded_asset(mi)
        mats[slot] = mi
    return mats


def assign_kit_materials(meshes, kit_mats):
    sme = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    for name, mesh in meshes.items():
        changed = False
        for i, sm in enumerate(mesh.get_editor_property("static_materials")):
            slot = str(sm.get_editor_property("material_slot_name"))
            key = next((k for k in kit_mats if slot == k or slot.startswith(k + "_") or slot.startswith(k + ".")), None)
            if key and sm.get_editor_property("material_interface") != kit_mats[key]:
                mesh.set_material(i, kit_mats[key])
                changed = True
        if ENABLE_NANITE:
            try:
                ns = mesh.get_editor_property("nanite_settings")
                if not ns.get_editor_property("enabled"):
                    ns.set_editor_property("enabled", True)
                    if hasattr(sme, "set_nanite_settings"):
                        sme.set_nanite_settings(mesh, ns, apply_changes=True)
                    else:
                        mesh.set_editor_property("nanite_settings", ns)
                    changed = True
            except Exception as exc:  # older engine versions
                unreal.log_warning("[LeafyManor] Nanite not set on %s: %s" % (name, exc))
        if changed:
            EAL.save_loaded_asset(mesh)


# ---------------------------------------------------------------------------
# Level + actors
# ---------------------------------------------------------------------------
def open_level():
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    ok = les.load_level(MAP_PATH) if EAL.does_asset_exist(MAP_PATH) else les.new_level(MAP_PATH)
    if not ok:
        raise RuntimeError("Could not open/create " + MAP_PATH)
    return les


def clear_previous(eas):
    old = [a for a in eas.get_all_level_actors()
           if BLOCKOUT_TAG in [str(t) for t in a.get_editor_property("tags")]]
    if old:
        eas.destroy_actors(old)
    _log("removed %d actors from a previous run" % len(old))


def _finish(actor, label, folder, kind):
    actor.set_actor_label(label)
    actor.set_folder_path("%s/%s" % (OUTLINER_ROOT, folder))
    actor.set_editor_property("tags", [unreal.Name(BLOCKOUT_TAG), unreal.Name("LM_Kind_" + kind)])
    return actor


def _collision(actor, smc, p):
    if p.collision == "none":
        smc.set_collision_profile_name("NoCollision")
    elif p.collision == "invisible":
        smc.set_collision_profile_name("InvisibleWall")
        smc.set_collision_response_to_channel(unreal.CollisionChannel.ECC_CAMERA, unreal.CollisionResponseType.ECR_IGNORE)
        actor.set_actor_hidden_in_game(True)
        smc.set_editor_property("affect_distance_field_lighting", False)
        smc.set_editor_property("affect_dynamic_indirect_lighting", False)
    else:
        smc.set_collision_profile_name("BlockAll")
    if not p.step_up:
        smc.set_editor_property("can_character_step_up_on", unreal.CanBeCharacterBase.ECB_NO)
    if not p.shadow:
        smc.set_cast_shadow(False)


def spawn_prim(eas, p, meshes, mats, kit_meshes, kit_mats, dressed):
    kit = dressed and p.mesh in kit_meshes
    if kit:
        actor = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*p.pivot),
                                           unreal.Rotator(roll=0.0, pitch=0.0, yaw=p.rot[1]))
        actor.set_actor_scale3d(unreal.Vector(*p.mesh_scale))
        smc = actor.get_editor_property("static_mesh_component")
        smc.set_static_mesh(kit_meshes[p.mesh])
    else:
        rot = unreal.Rotator(roll=p.rot[2], pitch=p.rot[0], yaw=p.rot[1])
        actor = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*p.center), rot)
        actor.set_actor_scale3d(unreal.Vector(*(v / 100.0 for v in p.size)))
        smc = actor.get_editor_property("static_mesh_component")
        smc.set_static_mesh(meshes["cyl" if p.shape == "cyl" else p.shape if p.shape in meshes else "box"])
        mat = kit_mats.get(p.mat) if dressed else None
        smc.set_material(0, mat or mats.get(p.mat) or mats["Stone"])
        if dressed and p.proxy:
            smc.set_editor_property("visible", False)  # collision-only stand-in
            smc.set_cast_shadow(False)
    _collision(actor, smc, p)
    return _finish(actor, "LM_" + p.label, p.folder, p.kind)


def spawn_lights(eas, s, prims, dressed):
    lights = list(lm.LIGHTS)
    if dressed and SCONCE_LIGHTS:
        import math
        for p in prims:
            if p.mesh and "WallSconce" in p.mesh:
                yaw = math.radians(p.rot[1] + 90.0)
                x, y, z = p.pivot
                lights.append(("PL_LM_" + p.label, "point",
                               ((x + 40 * math.cos(yaw)) / s, (y + 40 * math.sin(yaw)) / s, z / s + 70),
                               (1.0, 0.62, 0.3), 120.0, 700.0, None))
    for label, kind, pos, color, intensity, atten, rot in lights:
        cls = {"point": unreal.PointLight, "directional": unreal.DirectionalLight, "sky": unreal.SkyLight}[kind]
        r = unreal.Rotator(roll=rot[2], pitch=rot[0], yaw=rot[1]) if rot else unreal.Rotator()
        actor = eas.spawn_actor_from_class(cls, unreal.Vector(*(v * s for v in pos)), r)
        comp = actor.get_editor_property("light_component")
        comp.set_mobility(unreal.ComponentMobility.MOVABLE)
        if kind == "point":
            comp.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
            comp.set_intensity(intensity * s * s)
            comp.set_attenuation_radius(atten * s)
            if label.startswith("PL_LM_Sconce"):
                comp.set_cast_shadows(False)
        else:
            comp.set_intensity(intensity)
        comp.set_light_color(unreal.LinearColor(color[0], color[1], color[2], 1.0))
        _finish(actor, label, "Lighting", "Light")


def spawn_gameplay(eas, s):
    ps = lm.scaled_point(lm.PLAYER_START, s)
    z = ps[2] + lm.PLAYER["capsule_half_height_cm"] + 10.0
    start = eas.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(ps[0], ps[1], z),
                                       unreal.Rotator(roll=0.0, pitch=0.0, yaw=lm.PLAYER_START_YAW))
    _finish(start, "PlayerStart_LM_Vestibule", "Gameplay", "PlayerStart")
    for name, x, y, fz in lm.TEST_POINTS:
        tp = eas.spawn_actor_from_class(unreal.TargetPoint, unreal.Vector(x * s, y * s, fz * s + 5.0))
        _finish(tp, "TP_LM_Test_" + name, "Gameplay/TestPoints", "TestPoint")
    (x0, x1), (y0, y1), (z0, z1) = lm.NAV_BOUNDS
    nav = eas.spawn_actor_from_class(unreal.NavMeshBoundsVolume,
                                     unreal.Vector((x0 + x1) / 2 * s, (y0 + y1) / 2 * s, (z0 + z1) / 2 * s))
    nav.set_actor_scale3d(unreal.Vector((x1 - x0) * s / 200.0, (y1 - y0) * s / 200.0, (z1 - z0) * s / 200.0))
    _finish(nav, "NavMeshBounds_LM_EntranceHall", "Gameplay", "NavBounds")
    ppv = eas.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0, 0, 300))
    ppv.set_editor_property("unbound", True)
    pp = ppv.get_editor_property("settings")
    for prop, value in (("auto_exposure_min_brightness", 0.0), ("auto_exposure_max_brightness", 8.0),
                        ("auto_exposure_bias", 0.5)):
        pp.set_editor_property("override_" + prop, True)
        pp.set_editor_property(prop, value)
    ppv.set_editor_property("settings", pp)
    _finish(ppv, "PPV_LM_EntranceHall", "Lighting", "PostProcess")


def main():
    if not unreal.EditorLoadingAndSavingUtils.save_dirty_packages_with_dialog(True, True):
        unreal.log_warning("[LeafyManor] cancelled - nothing was changed")
        return
    ensure_folders()
    meshes = ensure_blockout_meshes()
    mats = ensure_blockout_materials()
    kit_meshes, kit_mats, dressed = {}, {}, False
    if DRESSED:
        kit_meshes = import_kit()
        kit_mats = ensure_kit_materials()
        assign_kit_materials(kit_meshes, kit_mats)
        dressed = bool(kit_meshes)
    les = open_level()
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    clear_previous(eas)

    s = lm.LM_SCALE
    prims = lm.build(s)
    with unreal.ScopedSlowTask(len(prims) + 3, "Building Leafy Manor entrance hall") as task:
        task.make_dialog(True)
        for p in prims:
            if task.should_cancel():
                unreal.log_warning("[LeafyManor] build cancelled - level NOT saved")
                return
            task.enter_progress_frame(1, p.label)
            spawn_prim(eas, p, meshes, mats, kit_meshes, kit_mats, dressed)
        task.enter_progress_frame(1, "Lights")
        spawn_lights(eas, s, prims, dressed)
        task.enter_progress_frame(1, "PlayerStart, test points, nav bounds")
        spawn_gameplay(eas, s)
        task.enter_progress_frame(1, "Saving")
        les.save_current_level()
        EAL.save_directory(ROOT, only_if_is_dirty=True, recursive=True)
    missing = sorted({p.mesh for p in prims if p.mesh and p.mesh not in kit_meshes}) if dressed else []
    if missing:
        unreal.log_warning("[LeafyManor] placed cubes for missing models: " + ", ".join(missing))
    _log("done: %d actors (%s) at LM_SCALE %.2f -> %s" % (len(prims), "dressed" if dressed else "blockout", s, MAP_PATH))
    _log("press Play to test with your character; press P in the viewport to see the NavMesh")


if __name__ == "__main__":
    main()
