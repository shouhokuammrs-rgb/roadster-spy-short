"""Self-check sheet for the vehicle proxies: python3 model_sheet.py OUT.png  (side view and 3/4 view of hero / coupe / SUV)."""
import sys, os, math, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scene_lib import *
OUT = sys.argv[1]
views = [("side", (14, 0, 1.2), (90, 0, 90)), ("front34", (9, 9, 3.2), (78, 0, 135)), ("rear34", (-8, -9, 3.0), (78, 0, -40))]
tiles = []
for vn, cp, cr in views:
    sc = reset(width=900, height=420, flat=False); sc.frame_end = 1
    sc.display.shading.show_shadows = True
    box("Floor", (0, 0, -0.05), (40, 40, 0.1), M('road'))
    car("Hero", (0, -6, 0), 4.9, 2.0, 1.1, M('hero'), nozzles=True, shape="hero")
    car("Coupe", (0, 0, 0), 4.6, 1.7, 1.3, M('coupe'), shape="coupe")
    car("SUV", (0, 6, 0), 4.9, 2.0, 1.9, M('suv'), shape="suv")
    cam = camera(cp, tuple(math.radians(v) for v in cr), lens=22)
    sc.camera = cam
    sc.render.filepath = OUT + f"_{vn}.png"; bpy.ops.render.render(write_still=True); tiles.append(OUT + f"_{vn}.png")
subprocess.run(["ffmpeg", "-y", "-v", "error"] + sum([["-i", t] for t in tiles], []) + ["-filter_complex", f"vstack=inputs={len(tiles)}", OUT], check=True)
print("DONE", OUT)
