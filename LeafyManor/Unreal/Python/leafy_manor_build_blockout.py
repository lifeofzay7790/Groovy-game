"""
Leafy Manor - Entrance Hall: build the playable blockout inside Unreal Editor (UE 5.1+).

Run:  Tools > Execute Python Script...  ->  pick this file
      (needs the "Python Editor Script Plugin"; keep leafy_manor_layout.py next to it)

What it does (only ever touches /Game/LeafyManor/ and the level it creates):
  1. Asks you to save any unsaved work (standard save dialog) - cancel aborts.
  2. Creates the /Game/LeafyManor/* folder structure.
  3. Creates blockout meshes (copies of the engine basic shapes with simple collision),
     one grid master material + instances.
  4. Opens (or creates) /Game/LeafyManor/Maps/LVL_LM_EntranceHall_Blockout.
  5. Deletes actors it spawned on a previous run (tag "LM_Blockout") and rebuilds:
     architecture, stairs, galleries, invisible safety collision, furniture proxies,
     work lights, PlayerStart, test markers, NavMeshBoundsVolume.
  6. Saves the level and the /Game/LeafyManor assets.

It never creates or edits a character, controller, camera or GameMode: your
project's default GameMode spawns your existing player at the PlayerStart.
"""

import importlib
import os
import sys

import unreal

try:
    _HERE = os.path.dirname(os.path.abspath(__file__))
    if _HERE not in sys.path:
        sys.path.append(_HERE)
except NameError:  # executed without __file__: rely on Content/Python being on sys.path
    pass

import leafy_manor_layout as lm  # noqa: E402

importlib.reload(lm)  # pick up edits without restarting the editor

ROOT = "/Game/LeafyManor"
FOLDERS = ["Architecture", "Architecture/Blockout", "Props", "Furniture", "Materials", "Materials/Blockout",
           "Textures", "Blueprints", "Lighting", "FX", "Models", "Maps"]
MAP_PATH = ROOT + "/Maps/LVL_LM_EntranceHall_Blockout"
BLOCKOUT_TAG = "LM_Blockout"
OUTLINER_ROOT = "LeafyManor_Blockout"
REBUILD_MATERIALS = False  # True = regenerate M_LM_Blockout graph + instances

EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
ASSET_TOOLS = unreal.AssetToolsHelpers.get_asset_tools()

SHAPES = {
    # key: (engine source, asset name, simple collision to add if the copy has none)
    "box": ("/Engine/BasicShapes/Cube", "SM_LM_BO_Cube", "BOX"),
    "cyl": ("/Engine/BasicShapes/Cylinder", "SM_LM_BO_Cylinder", "NDOP10_Z"),
    "cone": ("/Engine/BasicShapes/Cone", "SM_LM_BO_Cone", "NDOP10_Z"),
    "sphere": ("/Engine/BasicShapes/Sphere", "SM_LM_BO_Sphere", "SPHERE"),
}


def _log(msg):
    unreal.log("[LeafyManor] " + msg)


# ---------------------------------------------------------------------------
# Assets
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


def _connect(a, b, pin=""):
    if not MEL.connect_material_expressions(a, "", b, pin):
        raise RuntimeError("material connection failed: %s -> %s.%s" % (a.get_name(), b.get_name(), pin))


def ensure_master_material(folder):
    """M_LM_Blockout: tinted 1 m world-space checker (reads scale at a glance) + roughness/metal/emissive params."""
    mat, created = _new_asset("M_LM_Blockout", folder, unreal.Material, unreal.MaterialFactoryNew())
    if not created:
        return mat
    V, S = unreal.MaterialExpressionVectorParameter, unreal.MaterialExpressionScalarParameter
    base = _expr(mat, V, -700, -300, parameter_name="BaseColor", default_value=unreal.LinearColor(0.5, 0.5, 0.5, 1))
    grid = _expr(mat, S, -1300, -60, parameter_name="GridSize", default_value=100.0)
    contrast = _expr(mat, S, -700, -120, parameter_name="GridContrast", default_value=0.12)
    wpos = _expr(mat, unreal.MaterialExpressionWorldPosition, -1500, 0)
    offset = _expr(mat, unreal.MaterialExpressionAdd, -1300, 0, const_b=0.37)  # avoid flicker on faces at exact metres
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
    _connect(wpos, offset, "A")
    _connect(offset, div, "A")
    _connect(grid, div, "B")
    _connect(div, flr)
    _connect(flr, dot, "A")
    _connect(ones, dot, "B")
    _connect(dot, half, "A")
    _connect(half, frac)
    _connect(frac, checker, "A")
    _connect(checker, shade, "A")
    _connect(contrast, shade, "B")
    _connect(shade, inv)
    _connect(base, color, "A")
    _connect(inv, color, "B")
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
    """M_LM_BO_Collision: translucent red preview for invisible collision (hidden in game anyway)."""
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


def ensure_materials():
    folder = ROOT + "/Materials/Blockout"
    master = ensure_master_material(folder)
    collision = ensure_collision_material(folder)
    mats = {"Invisible": collision}
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
            if estr > 0 or key in ("Carpet", "Rug", "Banner"):
                MEL.set_material_instance_scalar_parameter_value(mi, "GridContrast", 0.0)
            MEL.update_material_instance(mi)
            EAL.save_loaded_asset(mi)
        mats[key] = mi
    return mats


# ---------------------------------------------------------------------------
# Level + actors
# ---------------------------------------------------------------------------
def open_level():
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if EAL.does_asset_exist(MAP_PATH):
        ok = les.load_level(MAP_PATH)
    else:
        ok = les.new_level(MAP_PATH)
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


def spawn_prim(eas, p, meshes, mats):
    rot = unreal.Rotator(roll=p.rot[2], pitch=p.rot[0], yaw=p.rot[1])
    actor = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*p.center), rot)
    actor.set_actor_scale3d(unreal.Vector(*(v / 100.0 for v in p.size)))
    smc = actor.get_editor_property("static_mesh_component")
    smc.set_static_mesh(meshes[p.shape])
    smc.set_material(0, mats[p.mat])
    if p.collision == "none":
        smc.set_collision_profile_name("NoCollision")
    elif p.collision == "invisible":
        # Blocks the player, ignored by the camera boom and visibility traces, never rendered in game.
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
    return _finish(actor, "LM_BO_" + p.label, p.folder, p.kind)


def spawn_lights(eas, s):
    for label, kind, pos, color, intensity, atten, rot in lm.LIGHTS:
        cls = {"point": unreal.PointLight, "directional": unreal.DirectionalLight, "sky": unreal.SkyLight}[kind]
        r = unreal.Rotator(roll=rot[2], pitch=rot[0], yaw=rot[1]) if rot else unreal.Rotator()
        actor = eas.spawn_actor_from_class(cls, unreal.Vector(*(v * s for v in pos)), r)
        comp = actor.get_editor_property("light_component")
        comp.set_mobility(unreal.ComponentMobility.MOVABLE)  # no lighting build needed (Lumen)
        if kind == "point":
            comp.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
            comp.set_intensity(intensity * s * s)  # keep illuminance constant when the room is rescaled
            comp.set_attenuation_radius(atten * s)
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
    # default volume brush is 200 uu per side
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
    _finish(ppv, "PPV_LM_Blockout", "Lighting", "PostProcess")


def main():
    if not unreal.EditorLoadingAndSavingUtils.save_dirty_packages_with_dialog(True, True):
        unreal.log_warning("[LeafyManor] cancelled - nothing was changed")
        return
    ensure_folders()
    meshes = ensure_blockout_meshes()
    mats = ensure_materials()
    les = open_level()
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    clear_previous(eas)

    s = lm.LM_SCALE
    prims = lm.build(s)
    with unreal.ScopedSlowTask(len(prims) + 3, "Building Leafy Manor blockout") as task:
        task.make_dialog(True)
        for p in prims:
            if task.should_cancel():
                unreal.log_warning("[LeafyManor] build cancelled - level NOT saved")
                return
            task.enter_progress_frame(1, p.label)
            spawn_prim(eas, p, meshes, mats)
        task.enter_progress_frame(1, "Lights")
        spawn_lights(eas, s)
        task.enter_progress_frame(1, "PlayerStart, test points, nav bounds")
        spawn_gameplay(eas, s)
        task.enter_progress_frame(1, "Saving")
        les.save_current_level()
        EAL.save_directory(ROOT, only_if_is_dirty=True, recursive=True)
    _log("done: %d blockout pieces at LM_SCALE %.2f -> %s" % (len(prims), s, MAP_PATH))
    _log("press Play (Selected Viewport) to test with your character; press P in the viewport to see the NavMesh")


if __name__ == "__main__":
    main()
