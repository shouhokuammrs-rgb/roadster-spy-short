"""Render a cut of blocking.json as a greybox reference video (Blender bpy, headless).
usage: python3 render_blocking.py -- blocking.json C12 OUTDIR
World model (v3): world.objects move in world time W; the cut is camera + window [start, start+dur] + view flags.
Writes OUTDIR/C12.mp4 (540x960), OUTDIR/C12_ref.mp4 (360x640, small, for Seedance), OUTDIR/C12_sheet.jpg, OUTDIR/C12.blend
Same conventions as the editor: Blender axes, degrees, Euler XYZ, +Y = forward/nose.
"""
import sys, json, math, os, subprocess
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from scene_lib import *

args = sys.argv[sys.argv.index("--")+1:]
JSON_PATH, CUT_ID, OUTDIR = args[0], args[1], args[2]
DATA = json.load(open(JSON_PATH))
cut = next(c for c in DATA["cuts"] if c["id"] == CUT_ID)
START = cut["start"]; VIEW = cut.get("view", {})
HIDE_POV, NO_CAB = set(VIEW.get("hideInPOV", [])), set(VIEW.get("noCab", []))
CAM = dict(cut["camera"], id="Cam", type="camera")
OBJECTS = DATA["world"]["objects"] + [CAM]
DUR = cut["dur"]; os.makedirs(OUTDIR, exist_ok=True)
sc = reset(dur=DUR, flat=False)  # STUDIO: マネキンの立体が読める

# ---------- set ----------
Y0, Y1 = -150, 450; L = Y1 - Y0; YC = (Y0 + Y1) / 2
box("Road", (-0.5, YC, -0.05), (7, L, 0.1), M('road'))
box("Wall", (-4.6, YC, 19.9), (1.2, L, 39.8), M('wall'))  # 上端は上の道の下
box("RailBar", (3, YC, 0.85), (0.08, L, 0.1), M('rail'))
for y in range(-60, 120, 2): box(f"Post{y}", (3, y, 0.45), (0.1, 0.1, 0.9), M('rail'))
box("Cliff", (4.15, YC, -22.55), (2.3, L, 45), M('wall'))  # 10/19 ガードレール(x3.0)から崖の外面(x5.3)まで岩で埋める。前は x3.0–4.7 が空いていて、C06b の生成が「谷」と読んだ
box("Quay", (17.5, YC, -45.05), (25, L, 0.1), M('road'))
box("Sea", (130, YC, -46), (200, L, 0.1), M('sea'))
gap = DATA["set"].get("upperRoad", {}).get("gap")
if gap:
    g0, g1 = gap
    box("UpperA", (-7.5, (Y0 + g0) / 2, 39.95), (7, g0 - Y0, 0.1), M('road'))
    box("UpperB", (-7.5, (g1 + Y1) / 2, 39.95), (7, Y1 - g1, 0.1), M('road'))
    box("EdgeA", (-7.5, g0-0.5, 39), (7, 1, 2), mat("edge", (0.42,0.35,0.29)))
    box("EdgeB", (-7.5, g1+0.5, 39), (7, 1, 2), mat("edge", (0.42,0.35,0.29)))
    box("GapFloor", (-7.5, (g0 + g1) / 2, 20), (7, g1 - g0, 0.1), mat("edge", (0.42,0.35,0.29)))  # 落ちた橋の下（深い）
else:
    box("Upper", (-7.5, YC, 39.95), (7, L, 0.1), M('road'))
box("URail1", (-4.2, YC, 40.85), (0.08, L, 0.1), M('rail'))
box("URail2", (-10.8, YC, 40.85), (0.08, L, 0.1), M('rail'))
box("Mountain", (-26, YC, 60), (30, L, 40), M('wall'))

# ---------- objects ----------
built = {}
def make_car(variant, name):
    spec = {"hero": (4.9, 2.0, 1.1, M('hero'), True), "coupe": (4.6, 1.7, 1.3, M('coupe'), False), "suv": (4.9, 2.0, 1.9, M('suv'), False)}[variant]
    Lc, W, H, m, nz = spec
    return car(name, (0, 0, 0), Lc, W, H, m, glass=True, nozzles=nz, shape=variant)  # 部品名は「車の id_部品」（重複でリネームされない）

# ---------- mannequin (rig/build_mannequin.py) ----------
RIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rig")
BAKED = json.load(open(os.path.join(RIG_DIR, "poses_baked.json")))["poses"]
with bpy.data.libraries.load(os.path.join(RIG_DIR, "mannequin.blend"), link=False) as (src, dst):
    dst.objects = ["MannequinRig", "MannequinMesh"]
SRC_RIG, SRC_MESH = dst.objects
HERO_IDS = {"Sho", "Vance"}  # light-grey mannequins; everyone else is the dark-clothed enemy

def mannequin(oid):
    """Man root (empty, feet at origin, faces +Y) → rig → skinned mesh, plus a gun pivot driven by the pose."""
    root = empty(oid, (0, 0, 0))
    rig = SRC_RIG.copy(); rig.name = f"Man{oid}_rig"; sc.collection.objects.link(rig); rig.parent = root
    for pb in rig.pose.bones: pb.rotation_mode = 'QUATERNION'
    m = SRC_MESH.copy(); m.name = f"Man{oid}_mannequin"; sc.collection.objects.link(m); m.parent = rig
    m.modifiers["Armature"].object = rig
    m.material_slots[0].link = 'OBJECT'
    hero = oid.split("_")[0] in HERO_IDS  # 主役 2 人は青灰色（スーツの色。銀のクーペ・白い車・黒い敵と区別）。Sho_cafe / Vance_gt なども主役
    # 10/19 肌色だと寄りで裸に見え、参照動画が NSFW 判定された（C02）→ 服の色に
    m.material_slots[0].material = mat("mann_hero", (0.30, 0.34, 0.42)) if hero else mat("mann_enemy", (0.13, 0.13, 0.15))
    gun = empty(f"Man{oid}_gunpivot", (0, 0, 0), parent=root)
    box(f"Man{oid}_gun", (0, 0.45, 0), (0.06, 0.9, 0.08), M('gunmetal'), parent=gun)
    root["rig"] = rig.name; root["gun"] = gun.name
    return root

def qslerp(a, b, u):
    from mathutils import Quaternion
    return Quaternion(a).slerp(Quaternion(b), u)

for o in OBJECTS:
    typ = o["type"]
    if typ == "car":
        root = make_car(o["variant"], o["id"]); root.name = o["id"]
        if o["id"] in HIDE_POV or o["id"] in NO_CAB:  # POV car / open-door cut: drop the cab box
            for ch in list(root.children):
                if ch.name.endswith("_cab"): bpy.data.objects.remove(ch, do_unlink=True)
    elif typ == "man":
        root = mannequin(o["id"])
    elif typ == "vapor":
        root = vapor(o["id"], (0, 0, 0), (1, 1, 1))
    elif typ == "camera":
        root = camera((0, 0, 0), (math.radians(90), 0, 0), lens=o.get("lens", 24), name=o["id"])
    elif typ == "fx":
        if o.get("variant") == "fire":
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5); root = bpy.context.object; root.data.materials.append(mat("fire", (1.0, 0.42, 0.1)))
        elif o.get("variant") == "missile":
            bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=1.2, rotation=(math.radians(90), 0, 0)); root = bpy.context.object; root.data.materials.append(M('gun'))
        else:
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.3); root = bpy.context.object; root.data.materials.append(mat("spark", (1.0, 0.88, 0.5)))
        root.name = o["id"]
    elif typ == "prop":
        root = empty(o["id"], (0, 0, 0))
        if o.get("variant") == "pistol":  # 拳銃（スライドが +Y）。グリップは下、マガジンは別の prop
            box("Pistol_slide", (0, 0.02, 0.0), (0.035, 0.19, 0.04), M('gunmetal'), parent=root)
            box("Pistol_grip", (0, -0.05, -0.05), (0.03, 0.045, 0.1), M('gun'), parent=root)
        elif o.get("variant") == "magazine":  # マガジン＋上に真鍮の弾 3 発
            box("Mag_body", (0, 0, 0), (0.026, 0.035, 0.1), M('gun'), parent=root)
            for i in range(3): box(f"Mag_round{i}", (0, -0.01 + 0.012*i, 0.056 + 0.006*i), (0.02, 0.03, 0.01), mat("brass", (0.85, 0.62, 0.2)), parent=root)
        elif o.get("variant") == "chair":  # カフェの椅子（座面 0.45）
            cm = mat("chair", (0.4, 0.3, 0.22))
            box("Chair_seat", (0, 0, 0.43), (0.45, 0.45, 0.04), cm, parent=root); box("Chair_back", (0, -0.21, 0.7), (0.42, 0.04, 0.5), cm, parent=root)
            for sx in (-1, 1):
                for sy in (-1, 1): box(f"Chair_leg{sx}{sy}", (sx*0.19, sy*0.19, 0.21), (0.04, 0.04, 0.42), cm, parent=root)
        elif o.get("variant") == "mirror":  # ドアミラー
            box("Mirror_housing", (0, 0, 0), (0.22, 0.10, 0.14), mat("cabin_dk", (0.16, 0.15, 0.14)), parent=root)
            box("Mirror_glass", (0, -0.06, 0), (0.18, 0.02, 0.10), mat("mirror", (0.62, 0.7, 0.78)), parent=root)
        elif o.get("variant") == "cabin":  # ロードスターのコクピット（左ハンドル）
            dk, lt = mat("cabin_dk", (0.16, 0.15, 0.14)), mat("cabin_lt", (0.42, 0.38, 0.35))
            box("Cab_dash", (0, 0.95, 0.75), (1.8, 0.5, 0.26), dk, parent=root)
            for sx in (-1, 1):
                box(f"Cab_pillar{sx}", (sx*0.88, 1.15, 0.95), (0.08, 0.12, 0.5), lt, parent=root)
                box(f"Cab_door{sx}", (sx*0.95, 0.1, 0.55), (0.05, 1.7, 0.4), dk, parent=root)
                box(f"Cab_seat{sx}", (sx*0.35, -0.12, 0.2), (0.5, 0.55, 0.1), lt, parent=root)
                box(f"Cab_back{sx}", (sx*0.35, -0.45, 0.5), (0.5, 0.12, 0.6), lt, parent=root)
            bpy.ops.mesh.primitive_torus_add(location=(-0.35, 0.62, 0.78), rotation=(math.pi/2 - 0.35, 0, 0), major_radius=0.18, minor_radius=0.025)
            w = bpy.context.object; w.name = "Cab_wheel"; w.data.materials.append(dk); w.parent = root
            box("Cab_console", (0, 0.2, 0.38), (0.3, 0.4, 0.18), dk, parent=root)
            box("Cab_roof", (0, -0.2, 1.2), (1.9, 1.6, 0.04), dk, parent=root)
        else:
            box(o["id"]+"_top", (0, 0, 0.75), (0.9, 0.9, 0.05), mat("table", (0.55, 0.42, 0.29)), parent=root)
    elif typ == "jets":
        root = empty(o["id"], (0, 0, 0)); root["jets"] = [jet(f"{o['id']}_{sx}{sy}", root, (sx*0.76, sy*2.05, 0.1), length=1.0).name for sx in (-1, 1) for sy in (-1, 1)]
    elif typ == "door":
        root = empty(o["id"], (0, 0.2, 1.1)); box(o["id"]+"_panel", (0.97, 0, -0.5), (0.06, 1.6, 1.0), M('hero'), parent=root)
    else:
        root = empty(o["id"], (0, 0, 0))
    root.rotation_mode = 'XYZ'
    built[o["id"]] = (root, o)

for oid, (root, o) in built.items():
    if o.get("parent") and o["parent"] in built: root.parent = built[o["parent"]][0]

def lerp(a, b, u): return a + (b - a) * u
def sample(keys, t):
    if t <= keys[0]["t"]: return keys[0]
    if t >= keys[-1]["t"]: return keys[-1]
    i = 0
    while keys[i+1]["t"] <= t: i += 1
    a, b = keys[i], keys[i+1]; u = (t - a["t"]) / max(1e-6, b["t"] - a["t"]); out = {}
    for k in ("p", "r", "s", "a", "lens"):
        if k in a and k in b:
            out[k] = [lerp(x, y, u) for x, y in zip(a[k], b[k])] if isinstance(a[k], list) else lerp(a[k], b[k], u)
        elif k in a: out[k] = a[k]
    out["pose"] = a.get("pose"); out["pose2"] = b.get("pose"); out["u"] = u; return out

# bake every frame (linear) — simplest and exactly matches the editor
def set_hidden(root, hidden, f):
    for ob in [root] + list(root.children_recursive):
        if ob.get("_off_base") is None: ob["_off_base"] = int(ob.hide_render)
        ob.hide_render = hidden or bool(ob["_off_base"]); ob.keyframe_insert("hide_render", frame=f)
for f in range(1, int(round(FPS*DUR)) + 1):
    t = (f - 1) / FPS; Wt = START + t
    for oid, (root, o) in built.items():
        tt = t if o["type"] == "camera" else Wt
        life = o.get("life")
        if life is not None:
            alive = life[0] - 1e-6 <= tt <= life[1] + 1e-6
            if not alive or root.get("_was_dead") is not None:
                set_hidden(root, not alive, f); root["_was_dead"] = 1
            if not alive: continue
        k = sample(o["keys"], tt); typ = o["type"]
        if "p" in k and typ not in ("jets", "door"): root.location = k["p"]; root.keyframe_insert("location", frame=f)
        if "r" in k and typ not in ("jets", "door"): root.rotation_euler = [math.radians(v) for v in k["r"]]; root.keyframe_insert("rotation_euler", frame=f)
        if typ == "vapor" and "s" in k: root.scale = [v/2 for v in k["s"]]; root.keyframe_insert("scale", frame=f)
        if typ == "fx" and "s" in k: s = max(0.001, k["s"]); root.scale = (s, s, s); root.keyframe_insert("scale", frame=f); root.hide_render = k["s"] <= 0.001; root.keyframe_insert("hide_render", frame=f)
        if typ == "jets":
            s = k.get("s", 0)
            for jn in root["jets"]:
                j = bpy.data.objects[jn]; j.scale = (1, 1, max(0.01, s)); j.location.z = 0.1 - max(0.01, s)/2; j.keyframe_insert("scale", frame=f); j.keyframe_insert("location", frame=f)
                j.hide_render = s < 0.05; j.keyframe_insert("hide_render", frame=f)
        if typ == "camera":  # レンズもキーで動く（ズーム）。キーに無ければカメラ全体の lens
            root.data.lens = k.get("lens", o.get("lens", 24)); root.data.keyframe_insert("lens", frame=f)
        if typ == "door": root.rotation_euler = (0, math.radians(-(k.get("a", 0))), 0); root.keyframe_insert("rotation_euler", frame=f)
        if typ == "man":
            pa = BAKED.get(k.get("pose") or "stand", BAKED["stand"]); pb_ = BAKED.get(k.get("pose2") or k.get("pose") or "stand", pa); u = k.get("u", 0)
            rig = bpy.data.objects[root["rig"]]
            for bone in rig.pose.bones:
                bone.rotation_quaternion = qslerp(pa["q"][bone.name], pb_["q"][bone.name], u); bone.keyframe_insert("rotation_quaternion", frame=f)
            hb = rig.pose.bones["Hips"]; hb.location = [x + (y - x) * u for x, y in zip(pa["hipsLoc"], pb_["hipsLoc"])]; hb.keyframe_insert("location", frame=f)
            gun = bpy.data.objects[root["gun"]]; ga, gb = pa["gun"], pb_["gun"] or pa["gun"]
            gun.hide_render = ga is None
            if ga:
                gun.location = [x + (y - x) * u for x, y in zip(ga["pos"], gb["pos"])]
                gun.rotation_euler = (math.radians(ga["rotX"] + (gb["rotX"] - ga["rotX"]) * u), 0, 0)
                L = 1.6 if ga["long"] else 1.0; gun.scale = (2.0 if ga["long"] else 1.0, L, 2.0 if ga["long"] else 1.0)
                gun.keyframe_insert("location", frame=f); gun.keyframe_insert("rotation_euler", frame=f); gun.keyframe_insert("scale", frame=f)
            gun.keyframe_insert("hide_render", frame=f)
            for gm in gun.children: gm.hide_render = gun.hide_render; gm.keyframe_insert("hide_render", frame=f)

# camera = the object of type camera
cam_obj = next(root for root, o in built.values() if o["type"] == "camera")
sc.camera = cam_obj
# fog card: when the camera is INSIDE the vapor, a white card 1.5 m in front of the lens (nearer things — a rifle, faces in the car — stay visible)
vap = [root for root, o in built.values() if o["type"] == "vapor"]
if vap:
    bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, -1.5)); fog = bpy.context.object; fog.name = "FogCard"
    fog.data.materials.append(M('vapor')); fog.parent = cam_obj
    for f in range(1, int(round(FPS*DUR)) + 1):
        sc.frame_set(f); cp = cam_obj.matrix_world.translation; inside = False
        for v in vap:
            if v.hide_render: continue
            c, h = v.matrix_world.translation, [abs(x) for x in v.scale]   # cube half-size = scale
            if all(c[i] - h[i] <= cp[i] <= c[i] + h[i] for i in range(3)): inside = True
        fog.hide_render = not inside; fog.keyframe_insert("hide_render", frame=f)
# POV: hide the body of the car the camera rides in (and of anything flagged hideInPOV); a POV man keeps only his gun
for root, o in built.values():
    if o["id"] in HIDE_POV:
        if o["type"] == "car":
            for ch in root.children:
                if ch.name.endswith(("_body", "_cab")) or "_wh" in ch.name: ch.hide_render = True
        elif o["type"] == "man":
            bpy.data.objects[f"Man{o['id']}_mannequin"].hide_render = True  # the gun stays

OUT = os.path.join(OUTDIR, CUT_ID)
bpy.ops.wm.save_as_mainfile(filepath=OUT + ".blend")
os.makedirs(OUT + "_frames", exist_ok=True)
sc.render.image_settings.file_format = 'PNG'; sc.render.filepath = OUT + "_frames/f_"
bpy.ops.render.render(animation=True)
subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", "24", "-i", OUT + "_frames/f_%04d.png", "-c:v", "libx264", "-crf", "30", "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT + ".mp4"], check=True)
subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", "24", "-i", OUT + "_frames/f_%04d.png", "-vf", "scale=360:640", "-c:v", "libx264", "-crf", "34", "-preset", "veryslow", "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT + "_ref.mp4"], check=True)
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", OUT + ".mp4", "-vf", "fps=2,scale=270:-1,tile=5x2", "-frames:v", "1", OUT + "_sheet.jpg"], check=True)
print("DONE", OUT)
