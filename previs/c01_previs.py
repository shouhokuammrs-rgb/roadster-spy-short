"""C01 greybox — Vance POV cold open (0–3 s in the film, built as a 5 s clip).
Vance sits in the RIGHT-hand driver seat of VanceGT, stopped against the wall, nose turned 18° toward the wall.
0.0–1.5 s  look forward through the cracked windshield: SUV_front blocks the road, muzzle flashes.
1.0 s      a bullet hits the windshield (new crack = a small plate appears).
1.5–2.3 s  head turns right and tilts up toward the side window.
2.3–4.0 s  the Roadster descends into the gap between the coupe and the guardrail, four white jets downward.
4.0–5.0 s  vapor floods the window -> frame goes white.
"""
import sys, math
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from scene_lib import *

OUT = sys.argv[sys.argv.index("--")+1] if "--" in sys.argv else "/tmp/c01"
DUR = 5
sc = reset(dur=DUR)
environment()

# ---------- cars ----------
suv("SUV_rear", -5)
suv("SUV_front", 32)
gt = vance_gt(y=16, angle_deg=18, glass=False)  # no solid cab: the camera sits inside
# cockpit pieces so the POV reads as "inside a car" (parented to the coupe)
box("GT_dash", (0, 1.1, 0.82), (1.6, 0.5, 0.18), M('cabin'), parent=gt)
box("GT_pillarL", (-0.8, 0.9, 1.25), (0.08, 0.1, 0.7), M('cabin'), parent=gt)
box("GT_pillarR", (0.8, 0.9, 1.25), (0.08, 0.1, 0.7), M('cabin'), parent=gt)
box("GT_roof", (0, 0.2, 1.62), (1.7, 1.6, 0.06), M('cabin'), parent=gt)
box("GT_doorR", (0.85, -0.1, 0.55), (0.06, 1.4, 0.9), M('cabin'), parent=gt)
box("GT_sillR", (0.85, -0.1, 1.05), (0.06, 1.4, 0.05), M('cabin'), parent=gt)   # window sill, glass above is open air
box("GT_bpillarR", (0.85, -0.85, 1.3), (0.06, 0.1, 0.6), M('cabin'), parent=gt)
# windshield crack: a thin pale plate that pops in at 1.0 s (impact)
crack = box("GT_crack", (0.35, 1.35, 1.25), (0.5, 0.02, 0.4), M('crack'), parent=gt)
key(crack, "scale", 1, Vector((0.0, 0.0, 0.0)))
key(crack, "scale", int(1.0*FPS)-1, Vector((0.0, 0.0, 0.0)))
key(crack, "scale", int(1.0*FPS), Vector((0.25, 0.01, 0.2)))
# muzzle flashes at the front SUV (two small boxes blinking)
for i, x in enumerate((-1.3, 0.6)):
    f = box(f"Flash{i}", (x, 29.5, 1.3), (0.4, 0.4, 0.4), M('crack'))
    for t in range(0, DUR*FPS, 6):
        on = ((t//6 + i) % 2 == 0)
        key(f, "scale", t+1, Vector((0.2, 0.2, 0.2)) if on else Vector((0.0, 0.0, 0.0)))

# ---------- men: 4 behind each SUV ----------
for n, (x, y) in {"A": (-2.6, -6.6), "B": (-1.3, -6.9), "C": (0.4, -6.9), "D": (1.7, -6.6)}.items():
    man(n, x, y)
for n, (x, y) in {"E": (-2.6, 33.8), "F": (-1.3, 34.1), "G": (0.4, 34.1), "H": (1.7, 33.8)}.items():
    man(n, x, y, face_minus_y=True)

# ---------- hero car descending into the gap (reversed: nose -Y), underside toward camera ----------
hero = empty("Hero_root", (1.2, 16.5, 10.0), (0, 0, math.pi))
hero_body = car("Hero", (0, 0, 0), 4.9, 2.0, 1.1, M('hero'), nozzles=True)
hero_body.parent = hero
jets = [jet(f"Jet{sx}{sy}", hero, (sx*0.76, sy*2.05, 0.1), length=3.0) for sx in (-1, 1) for sy in (-1, 1)]
key(hero, "location", 1, Vector((1.2, 16.5, 10.0)))
key(hero, "location", int(2.3*FPS), Vector((1.2, 16.5, 10.0)))
key(hero, "location", int(4.0*FPS), Vector((1.2, 16.5, 0.0)))
key(hero, "location", DUR*FPS, Vector((1.2, 16.5, 0.0)))
for j in jets:   # jets long while descending, shrink after touchdown
    key(j, "scale", int(2.3*FPS), Vector((1, 1, 3.0)))
    key(j, "scale", int(4.0*FPS), Vector((1, 1, 3.0)))
    key(j, "scale", int(4.6*FPS), Vector((1, 1, 0.3)))

# ---------- vapor filling the gap and the window ----------
vap = vapor("Vapor", (1.2, 16.5, 0.6), (4.0, 7.0, 1.2))
key(vap, "scale", int(3.2*FPS), Vector((0.1, 0.1, 0.1)))
key(vap, "scale", int(4.0*FPS), Vector((2.0, 3.5, 1.2)))
key(vap, "scale", DUR*FPS, Vector((3.0, 5.0, 2.2)))

# ---------- camera = Vance's eyes (RHD driver seat), parented to the coupe ----------
# local coupe frame: +Y nose, +X right. Eye at right seat.
cam = camera((0.42, -0.1, 1.2), (math.radians(88), 0, 0), lens=20, parent=gt)
key(cam, "rotation_euler", 1, Vector((math.radians(88), 0, 0)))                      # forward
key(cam, "rotation_euler", int(1.5*FPS), Vector((math.radians(88), 0, 0)))
key(cam, "rotation_euler", int(2.3*FPS), Vector((math.radians(88+35), 0, math.radians(-85))))  # right & up
key(cam, "rotation_euler", int(4.0*FPS), Vector((math.radians(88+10), 0, math.radians(-88))))  # follow the car down
key(cam, "rotation_euler", DUR*FPS, Vector((math.radians(88+5), 0, math.radians(-88))))

finish(OUT, top_center=(-0.5, 14), top_frame=int(3.5*FPS), render=(os.environ.get("PREVIS_RENDER","1")=="1"))
