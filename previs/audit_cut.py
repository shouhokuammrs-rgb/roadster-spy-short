"""What does a cut's camera actually frame? For each 0.5 s: screen position, height %, distance of the key objects.
usage: python3 audit_cut.py -- C15   (run from previs/, after render_blocking.py has written out/C15.blend)
"""
import bpy, sys, json, mathutils
from bpy_extras.object_utils import world_to_camera_view
cid = sys.argv[sys.argv.index("--")+1]
bpy.ops.wm.open_mainfile(filepath=f"out/{cid}.blend"); sc = bpy.context.scene; cam = sc.camera
d = json.load(open("blocking.json")); cut = next(c for c in d["cuts"] if c["id"] == cid)
targets = [n for n in ("Roadster", "SUV_chase", "Rocket", "Boom", "MirrorR", "Launcher", "Shooter", "Flash", "Spark") if n in bpy.data.objects]
def screen(o):
    pts = []
    for ob in [o] + list(o.children_recursive):
        if ob.type != 'MESH' or ob.hide_render: continue
        for c in ob.bound_box: pts.append(world_to_camera_view(sc, cam, ob.matrix_world @ mathutils.Vector(c)))
    if not pts: return None
    xs = [p.x for p in pts if p.z > 0]; ys = [p.y for p in pts if p.z > 0]
    if not xs: return "behind"
    x0, x1, y0, y1 = max(0, min(xs)), min(1, max(xs)), max(0, min(ys)), min(1, max(ys))
    if x1 <= x0 or y1 <= y0: return "off"
    dist = (o.matrix_world.translation - cam.matrix_world.translation).length
    return f"x{(x0+x1)/2:.2f} y{(y0+y1)/2:.2f} h{(y1-y0)*100:.0f}% {dist:.0f}m"
print(f"## {cid} W{cut['start']:.1f}  " + " / ".join(f"{b[0]}-{b[1]}s {b[2]}" for b in cut["beats"]))
for f in range(1, 121, 12):
    sc.frame_set(f); t = (f-1)/24
    row = []
    for n in targets:
        o = bpy.data.objects[n]
        if o.hide_render and not o.children: continue
        r = screen(o)
        if r and r not in ("off", "behind"): row.append(f"{n}[{r}]")
    car = bpy.data.objects["Roadster"].matrix_world.translation
    print(f"  t{t:3.1f} W{cut['start']+t:5.1f} car y{car.y:6.1f} z{car.z:4.1f} | " + "  ".join(row))
