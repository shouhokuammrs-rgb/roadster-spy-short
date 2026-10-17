"""C12 greybox previs — Blender (bpy) headless.
Scene coordinates (meters): road runs along +Y. Wall = plane x=-4. Guardrail x=+3. Sea beyond.
Camera sits behind the rear enemy SUV, looking +Y; tilts up from 2.5 s.
"""
import bpy, math, sys
from mathutils import Vector

OUT = sys.argv[sys.argv.index("--")+1] if "--" in sys.argv else "/tmp/c12"
FPS, DUR = 24, 5
W, H = 540, 960

# ---------- reset ----------
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
sc = bpy.context.scene
sc.render.fps = FPS
sc.frame_start, sc.frame_end = 1, FPS*DUR
sc.render.resolution_x, sc.render.resolution_y = W, H
sc.render.engine = 'BLENDER_WORKBENCH'
sc.display.shading.light = 'FLAT'
sc.display.shading.color_type = 'MATERIAL'
sc.display.shading.show_shadows = False
sc.display.shading.show_cavity = True
sc.render.film_transparent = False
sc.world = bpy.data.worlds.new("W"); sc.world.color = (0.55, 0.7, 0.9)

def mat(name, rgb):
    m = bpy.data.materials.new(name); m.diffuse_color = (*rgb, 1); return m

M = dict(road=mat("road",(0.25,0.25,0.27)), wall=mat("wall",(0.78,0.72,0.6)), rail=mat("rail",(0.9,0.9,0.9)),
         sea=mat("sea",(0.1,0.35,0.55)), suv=mat("suv",(0.05,0.05,0.06)), coupe=mat("coupe",(0.75,0.75,0.78)),
         hero=mat("hero",(0.95,0.94,0.9)), glass=mat("glass",(0.6,0.5,0.2)), man=mat("man",(0.12,0.12,0.14)),
         skin=mat("skin",(0.85,0.65,0.5)), gun=mat("gun",(0.2,0.2,0.2)), vapor=mat("vapor",(1,1,1)))

def box(name, loc, dim, m, rot=(0,0,0), parent=None):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=rot)
    o = bpy.context.object; o.name = name; o.scale = (dim[0]/2, dim[1]/2, dim[2]/2)
    o.data.materials.append(m)
    if parent: o.parent = parent
    return o

def empty(name, loc, rot=(0,0,0)):
    bpy.ops.object.empty_add(location=loc, rotation=rot); e = bpy.context.object; e.name = name; return e

def key(o, attr, frame, value):
    setattr(o, attr, value); o.keyframe_insert(data_path=attr, frame=frame)

# ---------- environment ----------
box("Road", (-0.5, 20, -0.05), (7, 80, 0.1), M['road'])
box("Wall", (-4.6, 20, 20), (1.2, 80, 40), M['wall'])          # vertical limestone wall at x≈-4
box("Sea", (30, 20, -8), (60, 80, 0.1), M['sea'])
for y in range(-20, 60, 2):                                      # guardrail posts
    box(f"Post{y}", (3, y, 0.45), (0.1, 0.1, 0.9), M['rail'])
box("RailBar", (3, 20, 0.85), (0.08, 80, 0.1), M['rail'])

# ---------- cars (boxes) ----------
def car(name, loc, L, Wd, Hh, m, rotz=0, glass=True):
    root = empty(name, loc, (0, 0, rotz))
    box(name+"_body", (0, 0, Hh*0.35), (Wd, L, Hh*0.7), m, parent=root)
    if glass: box(name+"_cab", (0, -L*0.05, Hh*0.85), (Wd*0.9, L*0.45, Hh*0.3), M['glass'], parent=root)
    for sx in (-1, 1):
        for sy in (-1, 1):
            w = box(name+f"_wh{sx}{sy}", (sx*Wd/2, sy*L*0.33, 0.33), (0.25, 0.66, 0.66), M['gun'], parent=root)
    return root

# Enemy SUV blocking the road BEHIND (nearest camera), parked across the road
suv_rear = car("SUV_rear", (-0.5, -5, 0), 4.9, 2.0, 1.9, M['suv'], rotz=math.radians(90))
# Enemy SUV blocking the road AHEAD
suv_front = car("SUV_front", (-0.5, 32, 0), 4.9, 2.0, 1.9, M['suv'], rotz=math.radians(90))
# Vance's abandoned silver coupe, tight against the wall, nose +Y
coupe = car("VanceGT", (-2.8, 10, 0), 4.6, 1.7, 1.3, M['coupe'])
# Hero car on the wall: underside toward -X (wall), nose up (+Z). Starts hidden in vapor at z≈1, climbs.
hero = empty("Hero_root", (-3.95, 11.5, 1.0))
hero_body = car("Hero", (0, 0, 0), 4.9, 2.0, 1.1, M['hero'], glass=True)
hero_body.parent = hero
# rotate car so its length runs along +Z and its underside faces -X: first pitch nose up 90° about X, then roll
hero_body.rotation_euler = (math.radians(90), 0, 0)         # length along Z, roof toward -Y
hero_body.rotation_euler = (math.radians(90), math.radians(90), 0)  # roof toward +X (away from wall) -> underside on wall
# keyframes: hidden (z=1) until 2.5 s, then 5 m -> 25 m by 5 s, linear
key(hero, "location", 1, Vector((-3.95, 11.5, 1.0)))
key(hero, "location", int(2.5*FPS), Vector((-3.95, 11.5, 5.0)))
key(hero, "location", FPS*DUR, Vector((-3.95, 11.5, 25.0)))

# ---------- vapor: knee-high white cloud over the road, thinning ----------
vap = box("Vapor", (-0.8, 10, 0.6), (6.5, 14, 1.2), M['vapor'])
key(vap, "scale", 1, Vector((3.25, 7, 0.6)))
key(vap, "scale", int(2.5*FPS), Vector((3.0, 6.5, 0.25)))
key(vap, "scale", FPS*DUR, Vector((2.5, 6.0, 0.08)))

# ---------- men: behind the rear SUV, using it as cover ----------
# A = nearest camera, left (behind SUV rear-left corner); B behind hood; C behind driver door; D far right behind rear corner
men_pos = {"A": (-2.6, -6.6), "B": (-1.3, -6.9), "C": (0.4, -6.9), "D": (1.7, -6.6)}
look_up_t = {"A": 2.5, "B": 3.0, "C": 3.3, "D": 3.6}
for n, (x, y) in men_pos.items():
    root = empty("Man"+n, (x, y, 0))
    box(f"Man{n}_legs", (0, 0, 0.45), (0.4, 0.3, 0.9), M['man'], parent=root)
    torso = box(f"Man{n}_torso", (0, 0, 1.2), (0.5, 0.3, 0.6), M['man'], parent=root)
    head = empty(f"Man{n}_headpivot", (x, y, 1.55)); head.parent = root; head.location = (0, 0, 1.55)
    box(f"Man{n}_head", (0, 0, 0.12), (0.22, 0.24, 0.24), M['skin'], parent=head)
    # rifle pivot at the shoulder; rifle points +Y (forward) when aiming
    gun = empty(f"Man{n}_gunpivot", (0, 0, 0)); gun.parent = root; gun.location = (0.15, 0.1, 1.4)
    box(f"Man{n}_gun", (0, 0.45, 0), (0.06, 0.9, 0.08), M['gun'], parent=gun)
    # 0–1.5 s aiming forward; 1.5–2.5 s lower rifle to waist (pitch down 60°) and drop pivot
    key(gun, "rotation_euler", int(1.5*FPS), Vector((0, 0, 0)))
    key(gun, "rotation_euler", int(2.5*FPS), Vector((math.radians(-60), 0, 0)))
    key(gun, "location", int(1.5*FPS), Vector((0.15, 0.1, 1.4)))
    key(gun, "location", int(2.5*FPS), Vector((0.15, 0.1, 1.05)))
    # 1.5–2.5 s head turns left then right searching
    key(head, "rotation_euler", int(1.5*FPS), Vector((0, 0, 0)))
    key(head, "rotation_euler", int(1.9*FPS), Vector((0, 0, math.radians(35))))
    key(head, "rotation_euler", int(2.3*FPS), Vector((0, 0, math.radians(-35))))
    t = look_up_t[n]
    key(head, "rotation_euler", int(t*FPS), Vector((0, 0, math.radians(-10))))
    # look up at the wall (tilt back ~60°, turned toward -X i.e. the wall on the left)
    key(head, "rotation_euler", int((t+0.4)*FPS), Vector((math.radians(35), math.radians(-50), math.radians(40))))
    key(head, "rotation_euler", FPS*DUR, Vector((math.radians(45), math.radians(-55), math.radians(40))))

# ---------- camera ----------
bpy.ops.object.camera_add(location=(0.8, -16, 2.0), rotation=(math.radians(90), 0, 0))
cam = bpy.context.object; cam.name = "Cam"; cam.data.lens = 24; cam.data.sensor_width = 36
sc.camera = cam
key(cam, "rotation_euler", int(2.5*FPS), Vector((math.radians(90), 0, 0)))
# tilt up so the hero car stays in the upper third: at 5 s car at z=25, dy≈23 → car angle≈45°; aim ≈ 32°
key(cam, "rotation_euler", int(3.2*FPS), Vector((math.radians(90+10), 0, 0)))
key(cam, "rotation_euler", FPS*DUR, Vector((math.radians(90+28), 0, 0)))

# ---------- light ----------
bpy.ops.object.light_add(type='SUN', location=(10, 0, 20), rotation=(math.radians(60), 0, math.radians(-110)))
bpy.context.object.data.energy = 3

# ---------- render ----------
import os
# --- export for the interactive viewer and for Blender ---
bpy.ops.wm.save_as_mainfile(filepath=OUT + ".blend")
bpy.ops.export_scene.gltf(filepath=OUT + ".glb", export_format='GLB', export_animations=True, export_cameras=True, export_lights=False, export_apply=True)
if os.environ.get("PREVIS_RENDER", "1") == "1":
    os.makedirs(OUT + "_frames", exist_ok=True)
    sc.render.image_settings.file_format = 'PNG'
    sc.render.filepath = OUT + "_frames/f_"
    bpy.ops.render.render(animation=True)

# top-down map still
bpy.ops.object.camera_add(location=(-0.5, 10, 60), rotation=(0, 0, 0))
top = bpy.context.object; top.name = "Top"; top.data.type = 'ORTHO'; top.data.ortho_scale = 70
sc.camera = top; sc.frame_set(int(3.5*FPS))
sc.render.image_settings.file_format = 'PNG'; sc.render.filepath = OUT + "_top.png"
bpy.ops.render.render(write_still=True)
print("DONE", OUT)
