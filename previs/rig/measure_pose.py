"""姿勢ごとの頭のてっぺん・いちばん下（root からの z）：python3 rig/measure_pose.py [pose …] → rig/pose_extents.json（引数なしで全部）"""
import bpy, json, os, sys
H = os.path.dirname(os.path.abspath(__file__))
B = json.load(open(os.path.join(H, "poses_baked.json")))["poses"]
bpy.ops.wm.open_mainfile(filepath=os.path.join(H, "mannequin.blend"))
rig = bpy.data.objects["MannequinRig"]; mesh = bpy.data.objects["MannequinMesh"]
for pb in rig.pose.bones: pb.rotation_mode = 'QUATERNION'
names = (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]) or list(B)
ext = {}
for name in names:
    P = B[name]
    for pb in rig.pose.bones: pb.rotation_quaternion = P["q"][pb.name]
    rig.pose.bones["Hips"].location = P["hipsLoc"]
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get(); me = mesh.evaluated_get(dg).to_mesh()
    vs = [mesh.matrix_world @ v.co for v in me.vertices]
    top = max(vs, key=lambda v: v.z); low = min(vs, key=lambda v: v.z); fwd = max(vs, key=lambda v: v.y)
    ext[name] = {"top": round(top.z, 3), "low": round(low.z, 3)}
    print(f"POSE {name:10} head top z={top.z:.3f} (y {top.y:+.2f})  lowest z={low.z:.3f} (y {low.y:+.2f})  front y={fwd.y:.2f} (z {fwd.z:.2f})")
json.dump(ext, open(os.path.join(H, "pose_extents.json"), "w"), indent=1)   # physics_check が使う（乗っている人が屋根・床に収まるか）
