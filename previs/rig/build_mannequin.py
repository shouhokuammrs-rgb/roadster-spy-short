"""Build the rigged previs mannequin and bake the pose library.

usage: python3 build_mannequin.py            (run from anywhere)
writes (next to this file):
  mannequin.blend     armature "MannequinRig" + skinned mesh "MannequinMesh" (rest = stand)
  mannequin.glb       same, with one animation clip per pose (for the Blocking Editor)
  poses_baked.json    per pose: bone -> local quaternion (w,x,y,z), Hips location, gun
  pose_sheet.png      every pose, front and side, for self-check

Bones use Mixamo names (Hips, Spine, Spine1, Spine2, Neck, Head, Left/Right Shoulder/Arm/ForeArm/Hand, UpLeg/Leg/Foot/ToeBase)
so clips from other tools can be retargeted later. The figure faces +Y; its left side is -X.
Mesh = capsules rigidly weighted to one bone each (an artist's mannequin: segments, no skin stretching).
"""
import bpy, bmesh, json, math, os, sys
from mathutils import Vector, Matrix, Quaternion, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = json.load(open(os.path.join(HERE, "poses.json")))["poses"]

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

# ---------------- skeleton (rest = standing, arms down) ----------------
B = {  # name: (head, tail, parent)
    "Hips": ((0, 0, 0.95), (0, 0, 1.05), None),
    "Spine": ((0, 0, 1.05), (0, 0, 1.18), "Hips"),
    "Spine1": ((0, 0, 1.18), (0, 0, 1.30), "Spine"),
    "Spine2": ((0, 0, 1.30), (0, 0, 1.43), "Spine1"),
    "Neck": ((0, 0, 1.43), (0, 0, 1.53), "Spine2"),
    "Head": ((0, 0, 1.53), (0, 0, 1.78), "Neck"),
}
for side, sx in (("Left", -1), ("Right", 1)):
    B[f"{side}Shoulder"] = ((sx*0.03, 0, 1.40), (sx*0.17, 0, 1.41), "Spine2")
    B[f"{side}Arm"] = ((sx*0.19, 0, 1.40), (sx*0.21, 0.0, 1.11), f"{side}Shoulder")
    B[f"{side}ForeArm"] = ((sx*0.21, 0.0, 1.11), (sx*0.22, 0.0, 0.85), f"{side}Arm")
    B[f"{side}Hand"] = ((sx*0.22, 0.0, 0.85), (sx*0.22, 0.0, 0.76), f"{side}ForeArm")
    B[f"{side}UpLeg"] = ((sx*0.1, 0, 0.93), (sx*0.1, 0, 0.51), "Hips")
    B[f"{side}Leg"] = ((sx*0.1, 0, 0.51), (sx*0.1, 0, 0.09), f"{side}UpLeg")
    B[f"{side}Foot"] = ((sx*0.1, 0, 0.09), (sx*0.1, 0.14, 0.03), f"{side}Leg")
    B[f"{side}ToeBase"] = ((sx*0.1, 0.14, 0.03), (sx*0.1, 0.22, 0.03), f"{side}Foot")

arm_data = bpy.data.armatures.new("MannequinRig")
rig = bpy.data.objects.new("MannequinRig", arm_data); sc.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='EDIT')
for name, (h, t, p) in B.items():
    eb = arm_data.edit_bones.new(name); eb.head = h; eb.tail = t; eb.roll = 0
    if p: eb.parent = arm_data.edit_bones[p]; eb.use_connect = False
bpy.ops.object.mode_set(mode='OBJECT')

# ---------------- mesh: capsules, each rigidly bound to one bone ----------------
parts = []
def _finish(o, bone):
    for poly in o.data.polygons: poly.use_smooth = True
    vg = o.vertex_groups.new(name=bone); vg.add(list(range(len(o.data.vertices))), 1.0, 'REPLACE'); parts.append(o)
def sphere(bone, c, r, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=c, segments=20, ring_count=10)
    o = bpy.context.object; o.scale = scale; bpy.ops.object.transform_apply(scale=True); _finish(o, bone)
def capsule(bone, a, b, r):
    a, b = Vector(a), Vector(b); d = b - a
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=d.length, location=(a + b) / 2, vertices=20)
    o = bpy.context.object; o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler(); bpy.ops.object.transform_apply(rotation=True); _finish(o, bone)
    sphere(bone, a, r); sphere(bone, b, r)

capsule("Hips", (-0.09, 0, 0.97), (0.09, 0, 0.97), 0.12)
capsule("Spine", (0, 0, 1.04), (0, 0, 1.16), 0.115)
capsule("Spine1", (0, 0, 1.18), (0, 0, 1.27), 0.125)
capsule("Spine2", (-0.08, 0, 1.34), (0.08, 0, 1.34), 0.13)
capsule("Neck", (0, 0, 1.44), (0, 0, 1.53), 0.048)
sphere("Head", (0, 0.01, 1.645), 0.105, (1, 1.05, 1.18))
sphere("Head", (0, 0.105, 1.64), 0.03, (1, 1, 1.2))          # nose bump = which way the face points
for side, sx in (("Left", -1), ("Right", 1)):
    sphere(f"{side}Arm", (sx*0.19, 0, 1.40), 0.062)            # shoulder ball
    capsule(f"{side}Arm", (sx*0.19, 0, 1.38), (sx*0.21, 0, 1.13), 0.05)
    capsule(f"{side}ForeArm", (sx*0.21, 0, 1.10), (sx*0.22, 0, 0.87), 0.041)
    sphere(f"{side}Hand", (sx*0.22, 0.01, 0.8), 0.045, (0.7, 1.0, 1.35))
    capsule(f"{side}UpLeg", (sx*0.1, 0, 0.9), (sx*0.1, 0, 0.53), 0.072)
    capsule(f"{side}Leg", (sx*0.1, 0, 0.5), (sx*0.1, 0, 0.11), 0.055)
    capsule(f"{side}Foot", (sx*0.1, 0.0, 0.05), (sx*0.1, 0.17, 0.035), 0.04)
for o in parts: o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
mesh = bpy.context.object; mesh.name = "MannequinMesh"; mesh.data.name = "MannequinMesh"
m = bpy.data.materials.new("Mannequin"); m.diffuse_color = (0.75, 0.75, 0.77, 1); mesh.data.materials.append(m)
mesh.parent = rig
mod = mesh.modifiers.new("Armature", 'ARMATURE'); mod.object = rig

# ---------------- IK for authoring (hands) ----------------
def empty(name, loc=(0, 0, 0)):
    e = bpy.data.objects.new(name, None); e.location = loc; sc.collection.objects.link(e); return e
tgt = {s: empty(f"IK_{s}") for s in ("L", "R")}
pole = {s: empty(f"Pole_{s}") for s in ("L", "R")}
for s, side in (("L", "Left"), ("R", "Right")):
    pb = rig.pose.bones[f"{side}ForeArm"]
    c = pb.constraints.new('IK'); c.target = tgt[s]; c.pole_target = pole[s]; c.pole_angle = math.radians(-90); c.chain_count = 2
for pb in rig.pose.bones: pb.rotation_mode = 'QUATERNION'

def set_pose(P):
    for pb in rig.pose.bones: pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
    hips = Vector(P["hips"])
    # Hips bone: local Y = world +Z (bone points up), local Z = world -Y, local X = world X  → convert world offset to bone space
    rig.pose.bones["Hips"].location = (hips.x, hips.z, -hips.y)
    for bn, deg in P["rot"].items():  # 数値 = X（前後）だけ、[x, y, z] = ボーンローカルの Euler XYZ（背骨は y でひねり、z で横傾き）
        e = deg if isinstance(deg, list) else [deg, 0, 0]
        rig.pose.bones[bn].rotation_quaternion = Euler([math.radians(v) for v in e], 'XYZ').to_quaternion()
    for s in ("L", "R"):
        tgt[s].location = P["hands"][s]; pole[s].location = P["elbows"][s]
    bpy.context.view_layer.update()

def bake():
    """Visual pose (with IK) → local quaternions per bone."""
    out = {}
    for pb in rig.pose.bones:  # parents come before children in this list
        M = rig.convert_space(pose_bone=pb, matrix=pb.matrix, from_space='POSE', to_space='LOCAL')
        out[pb.name] = M
    return out

baked = {}
for name, P in SPEC.items():
    set_pose(P)
    mats = bake()
    q = {bn: list(M.to_quaternion().normalized()) for bn, M in mats.items()}
    baked[name] = {"q": q, "hipsLoc": list(mats["Hips"].to_translation()), "gun": P.get("gun")}

# drop the IK, keep a pure FK rig
for s, side in (("L", "Left"), ("R", "Right")):
    pb = rig.pose.bones[f"{side}ForeArm"]; pb.constraints.remove(pb.constraints[0])
for e in list(tgt.values()) + list(pole.values()): bpy.data.objects.remove(e)

def apply_baked(name):
    d = baked[name]
    for pb in rig.pose.bones:
        pb.rotation_quaternion = d["q"][pb.name]; pb.location = (0, 0, 0)
    rig.pose.bones["Hips"].location = d["hipsLoc"]
    bpy.context.view_layer.update()

json.dump({"bones": list(B.keys()), "poses": baked}, open(os.path.join(HERE, "poses_baked.json"), "w"), indent=1)

# ---------------- pose sheet (self-check) ----------------
sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'MATERIAL'
sc.display.shading.show_cavity = True
sc.render.resolution_x, sc.render.resolution_y = 300, 420
sc.world = bpy.data.worlds.new("W"); sc.world.color = (0.55, 0.62, 0.7)
gm = bpy.data.materials.new("gun"); gm.diffuse_color = (0.15, 0.15, 0.17, 1)
bpy.ops.mesh.primitive_cube_add(); gun = bpy.context.object; gun.name = "SheetGun"; gun.data.materials.append(gm)
bpy.ops.mesh.primitive_plane_add(size=6); fl = bpy.context.object; fm = bpy.data.materials.new("floor"); fm.diffuse_color = (0.3, 0.3, 0.32, 1); fl.data.materials.append(fm)
cam_d = bpy.data.cameras.new("C"); cam_d.type = 'ORTHO'; cam_d.ortho_scale = 2.3
cam = bpy.data.objects.new("C", cam_d); sc.collection.objects.link(cam); sc.camera = cam
tiles = []
for name in SPEC:
    apply_baked(name)
    g = baked[name]["gun"]
    gun.hide_render = g is None
    if g:
        Lg = 1.4 if g["long"] else 0.9; W = 0.12 if g["long"] else 0.06
        gun.scale = (W/2, Lg/2, W/2); gun.rotation_euler = (math.radians(g["rotX"]), 0, 0)
        gun.location = Vector(g["pos"]) + Matrix.Rotation(math.radians(g["rotX"]), 3, 'X') @ Vector((0, Lg/2, 0))
    for view, loc, rot in (("front", (0, 4, 0.95), (math.radians(90), 0, math.radians(180))), ("side", (4, 0.2, 0.95), (math.radians(90), 0, math.radians(90)))):
        cam.location = loc; cam.rotation_euler = rot
        path = os.path.join(HERE, f"_sheet_{name}_{view}.png"); sc.render.filepath = path
        bpy.ops.render.render(write_still=True); tiles.append((name, view, path))
gun.hide_render = True
apply_baked("stand")
bpy.data.objects.remove(gun); bpy.data.objects.remove(fl); bpy.data.objects.remove(cam)

# ---------------- actions for glTF (one clip per pose) ----------------
rig.animation_data_create()
for name in SPEC:
    act = bpy.data.actions.new(name); act.use_fake_user = True
    rig.animation_data.action = act
    apply_baked(name)
    for f in (1, 2):  # two identical keys so the exporter keeps the channel
        for pb in rig.pose.bones:
            pb.keyframe_insert("rotation_quaternion", frame=f)
            pb.keyframe_insert("location", frame=f)
rig.animation_data.action = None
apply_baked("stand")
for pb in rig.pose.bones: pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "mannequin.blend"))
bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True); mesh.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.join(HERE, "mannequin.glb"), export_format='GLB', use_selection=True,
                          export_animations=True, export_animation_mode='ACTIONS', export_optimize_animation_size=False,
                          export_force_sampling=True, export_def_bones=False, export_apply=False, export_skins=True)

# contact sheet
from PIL import Image, ImageDraw
names = list(SPEC)
W, H = 300, 420
sheet = Image.new("RGB", (W*2*min(4, len(names)), H*((len(names)+3)//4)), "white")
for i, name in enumerate(names):
    for j, view in enumerate(("front", "side")):
        im = Image.open(os.path.join(HERE, f"_sheet_{name}_{view}.png")).convert("RGB")
        ImageDraw.Draw(im).text((8, 8), f"{name} {view}", fill=(0, 0, 0))
        sheet.paste(im, (((i % 4)*2 + j)*W, (i//4)*H))
        os.remove(os.path.join(HERE, f"_sheet_{name}_{view}.png"))
sheet.save(os.path.join(HERE, "pose_sheet.png"))
print("BUILT", len(names), "poses")
