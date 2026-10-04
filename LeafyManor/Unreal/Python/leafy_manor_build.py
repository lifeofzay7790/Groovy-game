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
     With MOOD on: the night / candlelight grade, volumetric haze, candle lights, glowing flames and
     fountain water, navy rugs and banners, darker walls and a polished marble floor.
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
MOOD = True                       # night / candlelight look from the master sheet (see MOOD_* below)

# Mood (MOOD = True). Values are applied on every run, so tweak them here and re-run.
MOOD_EXPOSURE_EV = (1.5, 5.0)     # auto-exposure range (EV100); a higher minimum keeps the hall darker
MOOD_EXPOSURE_BIAS = -1.0         # negative = moodier
MOOD_BLOOM = 1.0
MOOD_VIGNETTE = 0.6
MOOD_FOG_DENSITY = 0.05           # volumetric haze that makes candles and the fountain glow
MOOD_WALL_TINT = (0.62, 0.58, 0.56)   # darkens the cream wall / column / cornice kit
MOOD_STAIR_TINT = (0.8, 0.77, 0.74)   # balustrades and stair marble
# Glow and navy recolour per model, as parameters of M_LM_KitFX. These are set when the material
# instance is first created; after changing them, delete Materials/Kit/FX (or set REBUILD_MATERIALS).
FX_MATERIALS = {
    "SM_LM_Rug_Leaf_01": dict(RecolorAmount=1.0, RecolorSatMin=0.15),
    "SM_LM_Rug_Crown_01": dict(RecolorAmount=1.0, RecolorSatMin=0.15),
    "SM_LM_Rug_Lounge_01": dict(RecolorAmount=1.0, RecolorSatMin=0.15),
    "SM_LM_Banner_Red_01": dict(RecolorAmount=1.0),
    "SM_LM_Banner_Crown_01": dict(RecolorAmount=1.0),
    "SM_LM_Candelabra_Floor_01": dict(GlowStrength=12.0, GlowThreshold=0.25, FlickerAmount=0.08),
    "SM_LM_Candelabra_Small_01": dict(GlowStrength=12.0, GlowThreshold=0.25, FlickerAmount=0.08),
    "SM_LM_Lantern_01": dict(GlowStrength=10.0, GlowThreshold=0.25, FlickerAmount=0.08),
    "SM_LM_LampPost_01": dict(GlowStrength=10.0, GlowThreshold=0.3, FlickerAmount=0.08),
    "SM_LM_WallSconce_Torch_01": dict(GlowStrength=12.0, GlowThreshold=0.25, FlickerAmount=0.1),
    "SM_LM_WallSconce_Bowl_01": dict(GlowStrength=12.0, GlowThreshold=0.25, FlickerAmount=0.1),
    "SM_LM_Chandelier_01": dict(GlowStrength=8.0, GlowThreshold=0.3),
    "SM_LM_Chandelier_Grand_01": dict(GlowStrength=8.0, GlowThreshold=0.35, FlickerAmount=0.05),
    "SM_LM_Candelabra_Grand_01": dict(GlowStrength=12.0, GlowThreshold=0.35, FlickerAmount=0.08),
    "SM_LM_Candle_Cluster_01": dict(GlowStrength=10.0, GlowThreshold=0.35, FlickerAmount=0.1),
    "SM_LM_Fire_01": dict(GlowStrength=30.0, GlowThreshold=0.0, FlickerAmount=0.25),
    "SM_LM_Fountain_01": dict(WaterGlow=15.0),
}

ROOT = "/Game/LeafyManor"
FOLDERS = ["Architecture", "Architecture/Blockout", "Props", "Furniture", "Materials", "Materials/Blockout",
           "Materials/Kit", "Materials/Kit/FX", "Textures", "Blueprints", "Lighting", "FX", "Models", "Maps"]
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


def ensure_kit_master(folder, name="M_LM_KitMaster", fx=False):
    """M_LM_KitMaster: BaseColor / Normal / ORM (R=AO, G=Roughness, B=Metallic) + constant fallbacks.
    fx=True (M_LM_KitFX) adds the navy recolour and the flame / water glow, see _kit_fx."""
    mat, created = _new_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
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
    MEL.connect_material_property(_kit_fx(mat, col) if fx else col, "", unreal.MaterialProperty.MP_BASE_COLOR)
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


def _op(mat, cls, x, y, in_a=None, in_b=None, **props):
    """Material node fed by in_a -> A and in_b -> B (in_a alone goes to the only input of one-input nodes)."""
    e = _expr(mat, cls, x, y, **props)
    for src, pin in ((in_a, "A" if in_b is not None or "const_b" in props else ""), (in_b, "B")):
        if src is not None:
            _connect(src, e, pin)
    return e


def _kit_fx(mat, col):
    """Adds to the kit master (M_LM_KitFX):
    * recolour: purple / pink / red fabric -> RecolorColor (navy), keeping gold and orange. Hue test that
      works in linear colour: 8*(B-G)/max + 10*(0.12 - G/max), gated by saturation so greys stay grey.
    * glow: warm bright texels (flames, candle tips) * GlowStrength, blue texels (fountain water) * WaterGlow,
      with an optional flicker whose phase depends on where the actor stands.
    Every effect is off by default (amounts 0), so an instance only does what FX_MATERIALS asks for."""
    S, V, C = unreal.MaterialExpressionScalarParameter, unreal.MaterialExpressionVectorParameter, \
        unreal.MaterialExpressionComponentMask
    Mul, Add, Sub, Div = unreal.MaterialExpressionMultiply, unreal.MaterialExpressionAdd, \
        unreal.MaterialExpressionSubtract, unreal.MaterialExpressionDivide
    Mx, Mn, Sat = unreal.MaterialExpressionMax, unreal.MaterialExpressionMin, unreal.MaterialExpressionSaturate

    def p(name, x, y, value):
        return _expr(mat, S, x, y, parameter_name=name, default_value=value)

    X, Y = -2400, 900
    r = _op(mat, C, X, Y, col, r=True, g=False, b=False, a=False)
    g = _op(mat, C, X, Y + 120, col, r=False, g=True, b=False, a=False)
    b = _op(mat, C, X, Y + 240, col, r=False, g=False, b=True, a=False)
    mx = _op(mat, Mx, X + 200, Y, _op(mat, Mx, X + 150, Y + 60, r, g), b)
    mn = _op(mat, Mn, X + 200, Y + 200, _op(mat, Mn, X + 150, Y + 260, r, g), b)
    mxs = _op(mat, Mx, X + 350, Y, mx, const_b=0.0001)
    # recolour mask
    t1 = _op(mat, Mul, X + 650, Y, _op(mat, Div, X + 500, Y, _op(mat, Sub, X + 350, Y + 100, b, g), mxs),
             p("RecolorBlueK", X + 500, Y + 100, 8.0))
    t2 = _op(mat, Mul, X + 650, Y + 200,
             _op(mat, Sub, X + 500, Y + 200, p("RecolorGreenCut", X + 350, Y + 200, 0.12),
                 _op(mat, Div, X + 350, Y + 300, g, mxs)),
             p("RecolorGreenK", X + 500, Y + 300, 10.0))
    hue = _op(mat, Sat, X + 800, Y, _op(mat, Add, X + 750, Y + 100, t1, t2))
    sat = _op(mat, Div, X + 500, Y + 400, _op(mat, Sub, X + 350, Y + 400, mx, mn), mxs)
    satm = _op(mat, Sat, X + 800, Y + 400, _op(mat, Mul, X + 750, Y + 400,
                                                  _op(mat, Sub, X + 650, Y + 400, sat, p("RecolorSatMin", X + 500, Y + 500, 0.35)),
                                                  const_b=4.0))
    mask = _op(mat, Mul, X + 1050, Y, _op(mat, Mul, X + 950, Y + 100, hue, satm),
               p("RecolorAmount", X + 950, Y + 200, 0.0))
    lum = _op(mat, unreal.MaterialExpressionDotProduct, X + 350, Y + 600, col,
              _expr(mat, unreal.MaterialExpressionConstant3Vector, X + 200, Y + 650,
                    constant=unreal.LinearColor(0.2126, 0.7152, 0.0722, 0.0)))
    navy = _expr(mat, V, X + 800, Y + 600, parameter_name="RecolorColor", default_value=unreal.LinearColor(0.02, 0.035, 0.22, 1))
    gain = _op(mat, Mn, X + 800, Y + 750, _op(mat, Mul, X + 650, Y + 750, lum, p("RecolorGain", X + 500, Y + 800, 25.0)),
               const_b=3.0)
    out = _expr(mat, unreal.MaterialExpressionLinearInterpolate, X + 1250, Y)
    _connect(col, out, "A")
    _connect(_op(mat, Mul, X + 1050, Y + 600, navy, gain), out, "B")
    _connect(mask, out, "Alpha")
    # glow
    thr = p("GlowThreshold", X + 350, Y + 950, 0.25)
    den = _op(mat, Mx, X + 650, Y + 1000, _op(mat, unreal.MaterialExpressionOneMinus, X + 500, Y + 1000, thr), const_b=0.01)
    lm_ = _op(mat, unreal.MaterialExpressionSquareRoot, X + 950, Y + 950,
              _op(mat, Sat, X + 850, Y + 950, _op(mat, Div, X + 750, Y + 950, _op(mat, Sub, X + 500, Y + 900, lum, thr), den)))
    warm = _op(mat, Sat, X + 950, Y + 1100, _op(mat, Add, X + 850, Y + 1100,
                                                  _op(mat, Mul, X + 750, Y + 1100, _op(mat, Sub, X + 650, Y + 1100, r, b),
                                                      const_b=4.0), const_b=0.5))
    flame = _op(mat, Mul, X + 1250, Y + 1000, _op(mat, Mul, X + 1100, Y + 1000, lm_, warm),
                p("GlowStrength", X + 1100, Y + 1150, 0.0))
    water = _op(mat, Mul, X + 1250, Y + 1300,
                _op(mat, Sat, X + 1100, Y + 1300, _op(mat, Mul, X + 950, Y + 1300,
                                                       _op(mat, Sub, X + 800, Y + 1300, b, _op(mat, Mx, X + 650, Y + 1350, r, g)),
                                                       p("WaterK", X + 800, Y + 1400, 4.0))),
                p("WaterGlow", X + 1100, Y + 1450, 0.0))
    # flicker: 1 + amount * (sin(t*speed + phase) + 0.5 sin(t*speed*2.3 + phase))
    phase = _op(mat, unreal.MaterialExpressionDotProduct, X + 500, Y + 1650,
                _expr(mat, unreal.MaterialExpressionObjectPositionWS, X + 350, Y + 1600),
                _expr(mat, unreal.MaterialExpressionConstant3Vector, X + 350, Y + 1700,
                      constant=unreal.LinearColor(0.013, 0.017, 0.011, 0.0)))
    tt = _op(mat, Add, X + 800, Y + 1600, _op(mat, Mul, X + 650, Y + 1550,
                                               _expr(mat, unreal.MaterialExpressionTime, X + 500, Y + 1500),
                                               p("FlickerSpeed", X + 500, Y + 1550, 9.0)), phase)
    s1 = _op(mat, unreal.MaterialExpressionSine, X + 950, Y + 1600, tt, period=6.2832)
    s2 = _op(mat, Mul, X + 1100, Y + 1700, _op(mat, unreal.MaterialExpressionSine, X + 950, Y + 1700,
                                                _op(mat, Mul, X + 800, Y + 1700, tt, const_b=2.3), period=6.2832),
             const_b=0.5)
    flick = _op(mat, Add, X + 1400, Y + 1600, _op(mat, Mul, X + 1300, Y + 1600, _op(mat, Add, X + 1200, Y + 1600, s1, s2),
                                                  p("FlickerAmount", X + 1200, Y + 1700, 0.0)), const_b=1.0)
    emis = _op(mat, Mul, X + 1600, Y + 1000, col,
               _op(mat, Mul, X + 1500, Y + 1100, _op(mat, Add, X + 1400, Y + 1100, flame, water), flick))
    MEL.connect_material_property(emis, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    return out


def ensure_floor_checker(folder, name="M_LM_FloorChecker", polished=False):
    """M_LM_FloorChecker: cream / black marble tiles (136 cm) in world space - no UVs needed.
    polished=True (M_LM_FloorMarble, the mood floor): darker tint parameters and a near-mirror finish."""
    mat, created = _new_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
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
    if polished:
        V = unreal.MaterialExpressionVectorParameter
        for tex, pin, pname, value, y in ((cream, "A", "CreamTint", (0.62, 0.58, 0.52), -250),
                                          (black, "B", "BlackTint", (0.8, 0.8, 0.86), 50)):
            tinted = _expr(mat, unreal.MaterialExpressionMultiply, -500, y)
            _connect(tex, tinted, "A", "RGB")
            _connect(_expr(mat, V, -650, y + 150, parameter_name=pname, default_value=unreal.LinearColor(*value, 1)),
                     tinted, "B")
            _connect(tinted, lerp, pin)
    else:
        _connect(cream, lerp, "A", "RGB")
        _connect(black, lerp, "B", "RGB")
    _connect(chk, lerp, "Alpha")
    MEL.connect_material_property(lerp, "", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = _expr(mat, S, -250, 200, parameter_name="Roughness", default_value=0.1 if polished else 0.22)
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(mat)
    EAL.save_loaded_asset(mat)
    return mat


def _kit_instance(name, folder, parent, spec, scalars=None):
    b, n, o, use, rough, metal = spec
    mi, created = _new_asset(name, folder, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    if created:
        MEL.set_material_instance_parent(mi, parent)
        MEL.set_material_instance_texture_parameter_value(mi, "BaseColorTex", _tex(b, WHITE_TEX))
        MEL.set_material_instance_texture_parameter_value(mi, "NormalTex", _tex(n, NORMAL_TEX))
        if o:
            MEL.set_material_instance_texture_parameter_value(mi, "ORMTex", _tex(o, WHITE_TEX))
        for k, v in dict(UseORM=use, Roughness=rough, Metallic=metal, **(scalars or {})).items():
            MEL.set_material_instance_scalar_parameter_value(mi, k, v)
        MEL.update_material_instance(mi)
        EAL.save_loaded_asset(mi)
    return mi


def ensure_water_material(folder):
    """M_LM_Water: unlit, translucent, two-sided glowing water for SM_LM_FountainWater_01. Bands move along the
    mesh's V (outward on the pools, downward on the curtain) and wobble along U."""
    mat, created = _new_asset("M_LM_Water", folder, unreal.Material, unreal.MaterialFactoryNew())
    if not created:
        return mat
    for prop, value in (("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT),
                        ("shading_model", unreal.MaterialShadingModel.MSM_UNLIT), ("two_sided", True)):
        mat.set_editor_property(prop, value)
    S, C = unreal.MaterialExpressionScalarParameter, unreal.MaterialExpressionComponentMask
    Mul, Add, Sine = unreal.MaterialExpressionMultiply, unreal.MaterialExpressionAdd, unreal.MaterialExpressionSine
    uv = _expr(mat, unreal.MaterialExpressionTextureCoordinate, -1400, 0)
    u = _op(mat, C, -1250, -60, uv, r=True, g=False, b=False, a=False)
    v = _op(mat, C, -1250, 60, uv, r=False, g=True, b=False, a=False)
    wob = _op(mat, Mul, -900, -60, _op(mat, Sine, -1000, -60, _op(mat, Mul, -1100, -60, u, const_b=18.0), period=6.2832),
              const_b=1.5)
    t = _op(mat, Mul, -1100, 200, _expr(mat, unreal.MaterialExpressionTime, -1250, 200),
            _expr(mat, S, -1250, 300, parameter_name="FlowSpeed", default_value=5.0))
    phase = _op(mat, Add, -800, 100, _op(mat, Add, -900, 100, _op(mat, Mul, -1000, 60, v,
                                                                  _expr(mat, S, -1100, 120, parameter_name="Bands", default_value=40.0)),
                                         wob), t)
    band = _op(mat, Add, -500, 100, _op(mat, Mul, -600, 100, _op(mat, Sine, -700, 100, phase, period=6.2832), const_b=0.5),
               const_b=0.5)
    col = _expr(mat, unreal.MaterialExpressionVectorParameter, -500, -150, parameter_name="WaterColor",
                default_value=unreal.LinearColor(0.15, 0.45, 1.0, 1.0))
    glow = _op(mat, Mul, -300, -50, _op(mat, Add, -350, 100, _op(mat, Mul, -420, 100, band, const_b=0.45), const_b=0.55),
               _expr(mat, S, -500, 250, parameter_name="Glow", default_value=8.0))
    MEL.connect_material_property(_op(mat, Mul, -150, -100, col, glow), "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    op = _op(mat, Mul, -150, 200, _op(mat, Add, -300, 200, _op(mat, Mul, -400, 250, band, const_b=0.3), const_b=0.7),
             _expr(mat, S, -300, 350, parameter_name="Opacity", default_value=0.5))
    MEL.connect_material_property(op, "", unreal.MaterialProperty.MP_OPACITY)
    MEL.recompile_material(mat)
    EAL.save_loaded_asset(mat)
    return mat


def _set_tint(mi, rgb):
    want = unreal.LinearColor(rgb[0], rgb[1], rgb[2], 1.0)
    have = MEL.get_material_instance_vector_parameter_value(mi, "Tint")
    if all(abs(getattr(have, c) - getattr(want, c)) < 1e-4 for c in "rgb"):
        return
    MEL.set_material_instance_vector_parameter_value(mi, "Tint", want)
    MEL.update_material_instance(mi)
    EAL.save_loaded_asset(mi)


def ensure_kit_materials():
    """Returns (slot materials, per-model FX materials {mesh: {slot: MI}})."""
    folder = ROOT + "/Materials/Kit"
    master = ensure_kit_master(folder)
    mats = {"FloorChecker": ensure_floor_checker(folder, "M_LM_FloorMarble", polished=True) if MOOD
            else ensure_floor_checker(folder),
            "M_LM_Water": ensure_water_material(folder)}
    specs = {}
    for f in glob.glob(os.path.join(MODELS_DIR, "Textures", "T_LM_Kit_*_BaseColor.*")):
        sheet = os.path.basename(f)[len("T_LM_Kit_"):].rsplit("_BaseColor", 1)[0]
        specs["M_LM_Kit_" + sheet] = ("T_LM_Kit_%s_BaseColor" % sheet, "T_LM_Kit_%s_Normal" % sheet,
                                     "T_LM_Kit_%s_ORM" % sheet, 1.0, 0.5, 0.0)
    specs["M_LM_StairMarble"] = ("T_LM_Marble_Cream_BaseColor", None, None, 0.0, 0.25, 0.0)
    specs["M_LM_StairCarpet"] = ("T_LM_StairCarpet_BaseColor", None, None, 0.0, 0.95, 0.0)
    for slot, spec in specs.items():
        mats[slot] = _kit_instance("MI" + slot[1:], folder, master, spec)
    # mood: darker walls and stairs (applied every run, white when MOOD is off)
    for slot, tint in (("M_LM_Kit_door_set", MOOD_WALL_TINT), ("M_LM_Kit_Stairs", MOOD_STAIR_TINT),
                       ("M_LM_StairMarble", MOOD_STAIR_TINT)):
        if slot in mats:
            _set_tint(mats[slot], tint if MOOD else (1.0, 1.0, 1.0))
    fx = {}
    if MOOD:
        fx_master = ensure_kit_master(folder, "M_LM_KitFX", fx=True)
        for mesh, params in FX_MATERIALS.items():
            slot = lmk.KIT.get(mesh, {}).get("material")
            if slot in specs:
                fx[mesh] = {slot: _kit_instance("MI_LM_FX_" + mesh[len("SM_LM_"):], folder + "/FX", fx_master,
                                                specs[slot], params)}
    return mats, fx


def assign_kit_materials(meshes, kit_mats, fx_mats):
    sme = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    for name, mesh in meshes.items():
        changed = False
        for i, sm in enumerate(mesh.get_editor_property("static_materials")):
            slot = str(sm.get_editor_property("material_slot_name"))
            key = next((k for k in kit_mats if slot == k or slot.startswith(k + "_") or slot.startswith(k + ".")), None)
            want = fx_mats.get(name, {}).get(key) or kit_mats.get(key)
            if key and sm.get_editor_property("material_interface") != want:
                mesh.set_material(i, want)
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


# mood light changes: label prefix -> (intensity multiplier, radius multiplier, volumetric scattering)
MOOD_LIGHTS = {
    "PL_LM_Chandelier": (1.2, 1.0, 1.0),
    "PL_LM_Fireplace": (2.5, 1.3, 1.5),
    "PL_LM_Fountain": (3.0, 1.5, 3.0),
    "PL_LM_ExteriorFountain": (2.0, 1.2, 2.0),
    "PL_LM_Sconce": (2.0, 1.3, 1.0),
    "PL_LM_Candle": (1.0, 1.0, 1.0),
    "DL_LM_Moon": (0.4, 1.0, 1.0),
    "SL_LM_Sky": (0.35, 1.0, 1.0),
}
# warm light at the flames of floor / table candelabras and lanterns: mesh -> flame height (cm), candelas
CANDLE_LIGHTS = {"SM_LM_Candelabra_Floor_01": (125.0, 260.0), "SM_LM_Candelabra_Small_01": (52.0, 120.0),
                 "SM_LM_Lantern_01": (28.0, 90.0), "SM_LM_LampPost_01": (135.0, 300.0),
                 "SM_LM_Candelabra_Grand_01": (195.0, 320.0), "SM_LM_Candle_Cluster_01": (52.0, 160.0)}


def _try_set(obj, prop, value):
    """Calls the component's set_<prop> when it has one, else sets the editor property; warns instead of
    failing the build when this engine version names it differently."""
    try:
        setter = getattr(obj, "set_" + prop, None)
        if callable(setter):
            setter(value)
        else:
            obj.set_editor_property(prop, value)
        return True
    except Exception as exc:
        unreal.log_warning("[LeafyManor] %s.%s not set: %s" % (obj.get_class().get_name(), prop, exc))
        return False


def ensure_flicker_function(folder):
    """M_LM_LF_Flicker: light-function material that makes the fireplace lights flicker."""
    mat, created = _new_asset("M_LM_LF_Flicker", folder, unreal.Material, unreal.MaterialFactoryNew())
    if not created:
        return mat
    mat.set_editor_property("material_domain", unreal.MaterialDomain.MD_LIGHT_FUNCTION)
    Mul, Add, Sine = unreal.MaterialExpressionMultiply, unreal.MaterialExpressionAdd, unreal.MaterialExpressionSine
    t = _expr(mat, unreal.MaterialExpressionTime, -900, 0)
    total = None
    for i, (speed, amp) in enumerate(((7.0, 0.12), (17.3, 0.07), (31.1, 0.04))):
        w = _op(mat, Mul, -600, i * 150, _op(mat, Sine, -700, i * 150, _op(mat, Mul, -800, i * 150, t, const_b=speed),
                                              period=6.2832), const_b=amp)
        total = w if total is None else _op(mat, Add, -450, i * 150, total, w)
    MEL.connect_material_property(_op(mat, Add, -300, 0, total, const_b=0.88), "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.recompile_material(mat)
    EAL.save_loaded_asset(mat)
    return mat


def spawn_lights(eas, s, prims, dressed):
    import math
    lights = list(lm.LIGHTS)
    if dressed and SCONCE_LIGHTS:
        for p in prims:
            if p.mesh and "WallSconce" in p.mesh:
                yaw = math.radians(p.rot[1] + 90.0)
                x, y, z = p.pivot
                lights.append(("PL_LM_" + p.label, "point",
                               ((x + 40 * math.cos(yaw)) / s, (y + 40 * math.sin(yaw)) / s, z / s + 70),
                               (1.0, 0.62, 0.3), 120.0, 700.0, None))
    if dressed and MOOD:
        for p in prims:
            if p.mesh in CANDLE_LIGHTS:
                h, cd = CANDLE_LIGHTS[p.mesh]
                x, y, z = p.pivot
                lights.append(("PL_LM_Candle_" + p.label, "point", (x / s, y / s, (z + h * p.mesh_scale[2]) / s),
                               (1.0, 0.6, 0.28), cd, 650.0, None))
    flicker = ensure_flicker_function(ROOT + "/Lighting") if MOOD else None
    for label, kind, pos, color, intensity, atten, rot in lights:
        mult, rmult, scatter = next((v for k, v in MOOD_LIGHTS.items() if label.startswith(k)), (1.0, 1.0, 1.0)) \
            if MOOD else (1.0, 1.0, 1.0)
        cls = {"point": unreal.PointLight, "directional": unreal.DirectionalLight, "sky": unreal.SkyLight}[kind]
        r = unreal.Rotator(roll=rot[2], pitch=rot[0], yaw=rot[1]) if rot else unreal.Rotator()
        actor = eas.spawn_actor_from_class(cls, unreal.Vector(*(v * s for v in pos)), r)
        comp = actor.get_editor_property("light_component")
        comp.set_mobility(unreal.ComponentMobility.MOVABLE)
        if kind == "point":
            comp.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
            comp.set_intensity(intensity * s * s * mult)
            comp.set_attenuation_radius(atten * s * rmult)
            if label.startswith(("PL_LM_Sconce", "PL_LM_Candle")):
                comp.set_cast_shadows(False)
            if MOOD:
                _try_set(comp, "source_radius", 4.0)
                _try_set(comp, "volumetric_scattering_intensity", scatter)
                if label.startswith("PL_LM_Fireplace") and flicker:
                    _try_set(comp, "light_function_material", flicker)
        else:
            comp.set_intensity(intensity * mult)
        comp.set_light_color(unreal.LinearColor(color[0], color[1], color[2], 1.0))
        _finish(actor, label, "Lighting", "Light")


def _pp(pp, prop, value):
    try:
        pp.set_editor_property("override_" + prop, True)
        pp.set_editor_property(prop, value)
    except Exception as exc:
        unreal.log_warning("[LeafyManor] post-process %s not set: %s" % (prop, exc))


def spawn_mood(eas, pp):
    """Night / candlelight grade from the master sheet: dark exposure, bloom, vignette, navy shadows and warm
    highlights, Lumen GI + reflections (the polished floor mirrors the candles), and volumetric haze."""
    V4 = unreal.Vector4
    for prop, value in (("auto_exposure_min_brightness", MOOD_EXPOSURE_EV[0]),
                        ("auto_exposure_max_brightness", MOOD_EXPOSURE_EV[1]),
                        ("auto_exposure_bias", MOOD_EXPOSURE_BIAS),
                        ("bloom_intensity", MOOD_BLOOM),
                        ("vignette_intensity", MOOD_VIGNETTE),
                        ("color_contrast", V4(1.08, 1.08, 1.08, 1.0)),
                        ("color_saturation", V4(1.06, 1.03, 1.0, 1.0)),
                        ("color_gain_shadows", V4(0.88, 0.94, 1.18, 1.0)),
                        ("color_gain_highlights", V4(1.08, 1.0, 0.88, 1.0)),
                        ("screen_space_reflection_quality", 100.0)):
        _pp(pp, prop, value)
    for prop, enum, value in (("dynamic_global_illumination_method", "DynamicGlobalIlluminationMethod", "LUMEN"),
                              ("reflection_method", "ReflectionMethod", "LUMEN")):
        if hasattr(unreal, enum) and hasattr(getattr(unreal, enum), value):
            _pp(pp, prop, getattr(getattr(unreal, enum), value))
    fog = eas.spawn_actor_from_class(unreal.ExponentialHeightFog, unreal.Vector(0, 0, 0))
    fc = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    if fc:
        for prop, value in (("fog_density", MOOD_FOG_DENSITY), ("fog_height_falloff", 0.05),
                            ("fog_max_opacity", 0.7), ("start_distance", 0.0),
                            ("volumetric_fog", True), ("volumetric_fog_scattering_distribution", 0.5),
                            ("volumetric_fog_extinction_scale", 1.5), ("volumetric_fog_distance", 4000.0)):
            _try_set(fc, prop, value)
        dusk = unreal.LinearColor(0.006, 0.008, 0.02, 1.0)
        if not _try_set(fc, "fog_inscattering_luminance", dusk):   # UE 5.0 name
            _try_set(fc, "fog_inscattering_color", dusk)
    _finish(fog, "Fog_LM_Haze", "Lighting", "Fog")


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
    if MOOD:
        spawn_mood(eas, pp)
    else:
        for prop, value in (("auto_exposure_min_brightness", 0.0), ("auto_exposure_max_brightness", 8.0),
                            ("auto_exposure_bias", 0.5)):
            _pp(pp, prop, value)
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
        kit_mats, fx_mats = ensure_kit_materials()
        assign_kit_materials(kit_meshes, kit_mats, fx_mats)
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
