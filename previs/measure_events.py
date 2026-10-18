"""Measure what each cut actually shows, every 0.125 s, so shot lengths can be argued from data (docs/09_shot_length.md).
usage: python3 measure_events.py            (needs out/<CUT>.blend from render_blocking.py)
writes out/events.json: {cut: [{t, Roadster:[x,y,h%] or null, ..., white: fraction of frame covered by vapor}]}
"""
import bpy, json, mathutils, os
from bpy_extras.object_utils import world_to_camera_view
D = json.load(open("blocking.json")); res = {}
NAMES = ("Roadster", "SUV_chase", "Rocket", "Boom", "Vapor")
def box(sc, cam, o):
    pts = []
    for ob in [o] + list(o.children_recursive):
        if ob.type != 'MESH' or ob.hide_render or ob.hide_get(): continue
        for c in ob.bound_box: pts.append(world_to_camera_view(sc, cam, ob.matrix_world @ mathutils.Vector(c)))
    pts = [p for p in pts if p.z > 0]
    if not pts: return None
    x0, x1 = max(0, min(p.x for p in pts)), min(1, max(p.x for p in pts))
    y0, y1 = max(0, min(p.y for p in pts)), min(1, max(p.y for p in pts))
    if x1 <= x0 or y1 <= y0: return None
    return [round((x0 + x1) / 2, 2), round((y0 + y1) / 2, 2), round((y1 - y0) * 100), round((x1 - x0) * (y1 - y0), 3)]
for c in D["cuts"]:
    cid = c["id"]; f = f"out/{cid}.blend"
    if not os.path.exists(f): continue
    bpy.ops.wm.open_mainfile(filepath=f); sc = bpy.context.scene; cam = sc.camera; rows = []
    for fr in range(1, 121, 3):
        sc.frame_set(fr); row = {"t": round((fr - 1) / 24, 3)}
        for n in NAMES:
            o = bpy.data.objects.get(n)
            row[n] = box(sc, cam, o) if o else None
        rows.append(row)
    res[cid] = rows
json.dump(res, open("out/events.json", "w"))
print("DONE", len(res))
