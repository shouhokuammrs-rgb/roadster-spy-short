"""Render a cut of blocking.json as a greybox reference video (Blender bpy, headless).
usage: python3 render_blocking.py -- blocking.json C12 OUTDIR
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
DUR = cut["dur"]; os.makedirs(OUTDIR, exist_ok=True)
sc = reset(dur=DUR)

# ---------- set ----------
L = 400
box("Road", (-0.5, 60, -0.05), (7, L, 0.1), M('road'))
box("Wall", (-4.6, 60, 19.9), (1.2, L, 39.8), M('wall'))  # 上端は上の道の下
box("RailBar", (3, 60, 0.85), (0.08, L, 0.1), M('rail'))
for y in range(-40, 200, 2): box(f"Post{y}", (3, y, 0.45), (0.1, 0.1, 0.9), M('rail'))
box("Cliff", (5.0, 60, -22.5), (0.6, L, 45), M('wall'))
box("Quay", (17.5, 60, -45.05), (25, L, 0.1), M('road'))
box("Sea", (130, 60, -46), (200, L, 0.1), M('sea'))
gap = cut.get("gap")
if gap:
    g0, g1 = gap
    box("UpperA", (-7.5, (g0-60)/2, 39.95), (7, g0+60, 0.1), M('road'))
    box("UpperB", (-7.5, g1+(260-g1)/2, 39.95), (7, 260-g1, 0.1), M('road'))
    box("EdgeA", (-7.5, g0-0.5, 39), (7, 1, 2), mat("edge", (0.42,0.35,0.29)))
    box("EdgeB", (-7.5, g1+0.5, 39), (7, 1, 2), mat("edge", (0.42,0.35,0.29)))
else:
    box("Upper", (-7.5, 60, 39.95), (7, L, 0.1), M('road'))
box("URail1", (-4.2, 60, 40.85), (0.08, L, 0.1), M('rail'))
box("URail2", (-10.8, 60, 40.85), (0.08, L, 0.1), M('rail'))
box("Mountain", (-26, 60, 60), (30, 1.5, 40), M('wall'))

# ---------- objects ----------
built = {}
def make_car(variant):
    spec = {"hero": (4.9, 2.0, 1.1, M('hero'), True), "coupe": (4.6, 1.7, 1.3, M('coupe'), False), "suv": (4.9, 2.0, 1.9, M('suv'), False)}[variant]
    Lc, W, H, m, nz = spec
    return car("car", (0, 0, 0), Lc, W, H, m, glass=True, nozzles=nz, shape=variant)

POSES = {"aim": (0, 0, (0.15, 0.1, 1.4), 1.0), "lower": (0, -60, (0.15, 0.1, 1.05), 1.0), "lookup": (45, -60, (0.15, 0.1, 1.05), 1.0),
         "sit": (0, None, None, 0.52), "sitlookup": (60, None, None, 0.52), "launcher": (0, 10, (0.2, 0.1, 1.45), 1.0),
         "leanout": (0, 0, (0.15, 0.25, 1.35), 1.0)}
# 腕：肩と肘の前方回転（度）。(shL, elL, shR, elR)。+ が前へ振る
ARMS = {"aim": (75, 25, 70, 30), "lower": (30, 60, 25, 65), "lookup": (30, 60, 25, 65), "sit": (55, 50, 55, 50), "sitlookup": (55, 50, 55, 50),
        "launcher": (80, 40, 100, 30), "leanout": (80, 20, 75, 25), "relax": (5, 5, 5, 5)}

for o in cut["objects"]:
    typ = o["type"]
    if typ == "car":
        root = make_car(o["variant"]); root.name = o["id"]
        if o.get("hideInPOV") or o.get("noCab"):  # POV car / open-door cut: drop the cab box
            for ch in list(root.children):
                if ch.name.endswith("_cab"): bpy.data.objects.remove(ch, do_unlink=True)
    elif typ == "man":
        root, head, gun = man(o["id"], 0, 0); root.name = o["id"]; root["head"] = head.name; root["gun"] = gun.name
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
        if o.get("variant") == "mirror":  # ドアミラー
            box("Mirror_housing", (0, 0, 0), (0.22, 0.10, 0.14), mat("cabin_dk", (0.16, 0.15, 0.14)), parent=root)
            box("Mirror_glass", (0, -0.06, 0), (0.18, 0.02, 0.10), mat("mirror", (0.62, 0.7, 0.78)), parent=root)
        elif o.get("variant") == "cabin":  # ロードスターのコクピット（左ハンドル）
            dk, lt = mat("cabin_dk", (0.16, 0.15, 0.14)), mat("cabin_lt", (0.42, 0.38, 0.35))
            box("Cab_dash", (0, 0.95, 0.75), (1.8, 0.5, 0.26), dk, parent=root)
            for sx in (-1, 1):
                box(f"Cab_pillar{sx}", (sx*0.88, 1.15, 0.95), (0.08, 0.12, 0.5), lt, parent=root)
                box(f"Cab_door{sx}", (sx*0.95, 0.1, 0.55), (0.05, 1.7, 0.4), dk, parent=root)
                box(f"Cab_seat{sx}", (sx*0.35, -0.1, 0.33), (0.5, 0.5, 0.1), lt, parent=root)
                box(f"Cab_back{sx}", (sx*0.35, -0.38, 0.6), (0.5, 0.12, 0.55), lt, parent=root)
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
    for k in ("p", "r", "s", "a"):
        if k in a and k in b:
            out[k] = [lerp(x, y, u) for x, y in zip(a[k], b[k])] if isinstance(a[k], list) else lerp(a[k], b[k], u)
        elif k in a: out[k] = a[k]
    out["pose"] = a.get("pose"); out["pose2"] = b.get("pose"); out["u"] = u; return out

# bake every frame (linear) — simplest and exactly matches the editor
for f in range(1, FPS*DUR + 1):
    t = (f - 1) / FPS
    for oid, (root, o) in built.items():
        k = sample(o["keys"], t); typ = o["type"]
        if "p" in k and typ not in ("jets", "door"): root.location = k["p"]; root.keyframe_insert("location", frame=f)
        if "r" in k and typ not in ("jets", "door"): root.rotation_euler = [math.radians(v) for v in k["r"]]; root.keyframe_insert("rotation_euler", frame=f)
        if typ == "vapor" and "s" in k: root.scale = [v/2 for v in k["s"]]; root.keyframe_insert("scale", frame=f)
        if typ == "fx" and "s" in k: s = max(0.001, k["s"]); root.scale = (s, s, s); root.keyframe_insert("scale", frame=f); root.hide_render = k["s"] <= 0.001; root.keyframe_insert("hide_render", frame=f)
        if typ == "jets":
            s = k.get("s", 0)
            for jn in root["jets"]:
                j = bpy.data.objects[jn]; j.scale = (1, 1, max(0.01, s)); j.location.z = 0.1 - max(0.01, s)/2; j.keyframe_insert("scale", frame=f); j.keyframe_insert("location", frame=f)
                j.hide_render = s < 0.05; j.keyframe_insert("hide_render", frame=f)
        if typ == "door": root.rotation_euler = (0, math.radians(-(k.get("a", 0))), 0); root.keyframe_insert("rotation_euler", frame=f)
        if typ == "man":
            P = POSES.get(k.get("pose") or "aim", POSES["aim"]); P2 = POSES.get(k.get("pose2") or k.get("pose") or "aim", P); u = k.get("u", 0)
            # 姿勢はキー間で補間する（頭・銃の角度と位置）。銃の有無が変わる区間は手前の姿勢に従う
            headA = P[0] + (P2[0] - P[0]) * u
            head = bpy.data.objects[root["head"]]; gun = bpy.data.objects[root["gun"]]
            head.rotation_euler = (math.radians(headA), 0, 0); head.keyframe_insert("rotation_euler", frame=f)
            A = ARMS.get(k.get("pose") or "aim", ARMS["aim"]); A2 = ARMS.get(k.get("pose2") or k.get("pose") or "aim", A)
            for nm, i in (("shL", 0), ("elL", 1), ("shR", 2), ("elR", 3)):
                piv = bpy.data.objects[f"Man{o['id']}_{nm}"]; piv.rotation_euler = (math.radians(A[i] + (A2[i] - A[i]) * u), 0, 0); piv.keyframe_insert("rotation_euler", frame=f)
            if P[1] is None: gun.hide_render = True
            else:
                gA = P[1] + ((P2[1] - P[1]) * u if P2[1] is not None else 0); gP = [a + ((b - a) * u if P2[2] else 0) for a, b in zip(P[2], P2[2] or P[2])]
                gun.hide_render = False; gun.rotation_euler = (math.radians(gA), 0, 0); gun.location = gP; gun.keyframe_insert("rotation_euler", frame=f); gun.keyframe_insert("location", frame=f)
            gun.keyframe_insert("hide_render", frame=f)
            for gm in gun.children: gm.hide_render = gun.hide_render; gm.keyframe_insert("hide_render", frame=f)  # hide_render は子に継承されない
            root.scale = (1, 1, P[3]); root.keyframe_insert("scale", frame=f)

# camera = the object of type camera
cam_obj = next(root for root, o in built.values() if o["type"] == "camera")
sc.camera = cam_obj
# POV: hide the body of the car the camera rides in (and of anything flagged hideInPOV); a POV man keeps only his gun
for root, o in built.values():
    if o.get("hideInPOV"):
        if o["type"] == "car":
            for ch in root.children:
                if ch.name.endswith(("_body", "_cab")) or "_wh" in ch.name: ch.hide_render = True
        elif o["type"] == "man":
            for ch in root.children_recursive:
                if ch.name.startswith("Man" + o["id"]) and ch.name.endswith(("_legs", "_torso", "_head")): ch.hide_render = True

OUT = os.path.join(OUTDIR, CUT_ID)
bpy.ops.wm.save_as_mainfile(filepath=OUT + ".blend")
os.makedirs(OUT + "_frames", exist_ok=True)
sc.render.image_settings.file_format = 'PNG'; sc.render.filepath = OUT + "_frames/f_"
bpy.ops.render.render(animation=True)
subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", "24", "-i", OUT + "_frames/f_%04d.png", "-c:v", "libx264", "-crf", "30", "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT + ".mp4"], check=True)
subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", "24", "-i", OUT + "_frames/f_%04d.png", "-vf", "scale=360:640", "-c:v", "libx264", "-crf", "34", "-preset", "veryslow", "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT + "_ref.mp4"], check=True)
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", OUT + ".mp4", "-vf", "fps=2,scale=270:-1,tile=5x2", "-frames:v", "1", OUT + "_sheet.jpg"], check=True)
print("DONE", OUT)
