"""Player character -> web GLB with procedural Idle / Walk / Run / Jump clips (arms down, leg swing).

Usage (Blender Python / bpy module): python pack_char.py <player.fbx> <basecolor.jpg>
"""
import os, sys, math
import bpy
from mathutils import Vector, Quaternion

HERE = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(HERE, 'build'), exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=os.path.abspath(sys.argv[-2]))
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
mesh = next(o for o in bpy.data.objects if o.type == 'MESH')

# texture: 1K base colour
img = bpy.data.images.load(os.path.abspath(sys.argv[-1]))
img.scale(1024, 1024)
mat = bpy.data.materials.new('M_Player')
mat.use_nodes = True
bsdf = mat.node_tree.nodes['Principled BSDF']
bsdf.inputs['Roughness'].default_value = 0.8
t = mat.node_tree.nodes.new('ShaderNodeTexImage')
t.image = img
mat.node_tree.links.new(t.outputs['Color'], bsdf.inputs['Base Color'])
mesh.data.materials.clear()
mesh.data.materials.append(mat)

B = arm.data.bones
P = arm.pose.bones
up = Vector((0, 0, 1))
fwd = (B['ball_l'].head_local - B['foot_l'].head_local)
fwd = Vector((0, math.copysign(1, fwd.y), 0)) if abs(fwd.y) > abs(fwd.x) else Vector((math.copysign(1, fwd.x), 0, 0))
side = fwd.cross(up).normalized()          # lateral axis
print('forward', fwd, 'lateral', side)


def local_q(bone, world_q):
    """Armature-space rotation about the bone head -> pose-bone local quaternion."""
    R = B[bone].matrix_local.to_quaternion()
    return R.inverted() @ world_q @ R


def swing_axis(bone, sign):
    """Axis about which +angle moves the bone's tail toward `sign` * forward."""
    d = (B[bone].tail_local - B[bone].head_local).normalized()
    q = Quaternion(side, 0.2)
    return side if (q @ d).dot(fwd) * sign > d.dot(fwd) * sign else -side


def arm_down(bone, extra=0.0):
    d = (B[bone].tail_local - B[bone].head_local).normalized()
    out = Vector((d.x, d.y, 0)).normalized()
    target = (out * 0.28 + Vector((0, 0, -1))).normalized()
    q = d.rotation_difference(target)
    ax = swing_axis(bone, 1)
    return Quaternion(ax, extra) @ q


LEG_F = {b: swing_axis(b, 1) for b in ('thigh_l', 'thigh_r')}
KNEE = {b: swing_axis(b, -1) for b in ('calf_l', 'calf_r')}


def pose(frame, leg, knee_l, knee_r, armsw, bob, torso=0.0):
    for pb in P:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = Quaternion()
    P['upperarm_l'].rotation_quaternion = local_q('upperarm_l', arm_down('upperarm_l', -armsw))
    P['upperarm_r'].rotation_quaternion = local_q('upperarm_r', arm_down('upperarm_r', armsw))
    P['lowerarm_l'].rotation_quaternion = local_q('lowerarm_l', Quaternion(LEG_F['thigh_l'], 0.15))
    P['lowerarm_r'].rotation_quaternion = local_q('lowerarm_r', Quaternion(LEG_F['thigh_r'], 0.15))
    P['thigh_l'].rotation_quaternion = local_q('thigh_l', Quaternion(LEG_F['thigh_l'], leg))
    P['thigh_r'].rotation_quaternion = local_q('thigh_r', Quaternion(LEG_F['thigh_r'], -leg))
    P['calf_l'].rotation_quaternion = local_q('calf_l', Quaternion(KNEE['calf_l'], knee_l))
    P['calf_r'].rotation_quaternion = local_q('calf_r', Quaternion(KNEE['calf_r'], knee_r))
    P['spine_01'].rotation_quaternion = local_q('spine_01', Quaternion(side, torso) if torso else Quaternion())
    P['pelvis'].location = Vector((0, 0, 0))
    P['root'].location = P['root'].bone.matrix_local.to_3x3().inverted() @ Vector((0, 0, bob))
    for pb in P:
        pb.keyframe_insert('rotation_quaternion', frame=frame)
    P['root'].keyframe_insert('location', frame=frame)


def clip(name, frames):
    arm.animation_data_create()
    act = bpy.data.actions.new(name)
    arm.animation_data.action = act
    for f, args in frames:
        pose(f, *args)
    tr = arm.animation_data.nla_tracks.new()
    tr.name = name
    tr.strips.new(name, 1, act)
    arm.animation_data.action = None


s = 0.01  # armature units are metres in Blender after import
clip('Idle', [(1, (0, 0, 0, 0.04, 0)), (30, (0, 0, 0, 0.06, 0.004)), (60, (0, 0, 0, 0.04, 0))])
W, K, A = 0.45, 0.6, 0.35
clip('Walk', [(1, (W, 0.1, 0.1, A, 0)), (8, (0, 0.1, K, 0, 0.012)), (16, (-W, 0.1, 0.1, -A, 0)),
              (24, (0, K, 0.1, 0, 0.012)), (32, (W, 0.1, 0.1, A, 0))])
R, KR, AR = 0.7, 1.0, 0.6
clip('Run', [(1, (R, 0.2, 0.3, AR, 0, 0.12)), (6, (0, 0.2, KR, 0, 0.02, 0.12)), (11, (-R, 0.3, 0.2, -AR, 0, 0.12)),
             (16, (0, KR, 0.2, 0, 0.02, 0.12)), (21, (R, 0.2, 0.3, AR, 0, 0.12))])
clip('Jump', [(1, (0.35, 0.9, 0.2, -0.5, 0, 0.05)), (10, (0.35, 0.9, 0.2, -0.5, 0, 0.05))])

bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=os.path.join(HERE, 'build', 'player_raw.glb'), export_format='GLB',
                          use_selection=True, export_image_format='JPEG', export_jpeg_quality=82,
                          export_animations=True, export_animation_mode='NLA_TRACKS', export_force_sampling=True,
                          export_def_bones=False, export_extras=False)
print('dims', mesh.dimensions[:], [a.name for a in bpy.data.actions])
