"""Shared greybox builders for the cliff-road set (Blender bpy, headless).
World: road runs along +Y, vertical wall at x=-4, guardrail at x=+3, sea beyond. Units: metres.
Blender axes: +Z up. Camera looks along local -Z; rotation (90°,0,0) looks along +Y.
"""
import bpy, math, os
from mathutils import Vector

FPS = 24

def reset(width=540, height=960, dur=5, flat=True):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 1, FPS * dur
    sc.render.resolution_x, sc.render.resolution_y = width, height
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'FLAT' if flat else 'STUDIO'
    sc.display.shading.color_type = 'MATERIAL'
    sc.display.shading.show_shadows = False
    sc.display.shading.show_cavity = True
    sc.world = bpy.data.worlds.new("W"); sc.world.color = (0.55, 0.7, 0.9)
    return sc

_mats = {}
def mat(name, rgb):
    if name not in _mats:
        m = bpy.data.materials.new(name); m.diffuse_color = (*rgb, 1); _mats[name] = m
    return _mats[name]

PAL = dict(road=(0.25,0.25,0.27), wall=(0.78,0.72,0.6), rail=(0.9,0.9,0.9), sea=(0.1,0.35,0.55),
           suv=(0.05,0.05,0.06), coupe=(0.75,0.75,0.78), hero=(0.95,0.94,0.9), glass=(0.6,0.5,0.2),
           man=(0.12,0.12,0.14), skin=(0.85,0.65,0.5), gun=(0.2,0.2,0.2), vapor=(1,1,1), ghost=(0.9,0.9,0.85),
           route=(1.0,0.3,0.1), cabin=(0.15,0.14,0.13), crack=(0.95,0.95,1.0))
def M(k): return mat(k, PAL[k])

def box(name, loc, dim, m, rot=(0,0,0), parent=None):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=rot)
    o = bpy.context.object; o.name = name; o.scale = (dim[0]/2, dim[1]/2, dim[2]/2)
    o.data.materials.append(m)
    if parent: o.parent = parent
    return o

def empty(name, loc, rot=(0,0,0), parent=None):
    bpy.ops.object.empty_add(location=loc, rotation=rot); e = bpy.context.object; e.name = name
    if parent: e.parent = parent
    return e

def key(o, attr, frame, value):
    setattr(o, attr, value); o.keyframe_insert(data_path=attr, frame=frame)

def environment(length=100):
    box("Road", (-0.5, 20, -0.05), (7, length, 0.1), M('road'))
    box("Wall", (-4.6, 20, 20), (1.2, length, 40), M('wall'))
    box("Sea", (30, 20, -8), (60, length, 0.1), M('sea'))
    for y in range(-30, 70, 2):
        box(f"Post{y}", (3, y, 0.45), (0.1, 0.1, 0.9), M('rail'))
    box("RailBar", (3, 20, 0.85), (0.08, length, 0.1), M('rail'))

def car(name, loc, L, Wd, Hh, m, rotz=0, glass=True, nozzles=False):
    root = empty(name, loc, (0, 0, rotz))
    box(name+"_body", (0, 0, Hh*0.35), (Wd, L, Hh*0.7), m, parent=root)
    if glass: box(name+"_cab", (0, -L*0.05, Hh*0.85), (Wd*0.9, L*0.45, Hh*0.3), M('glass'), parent=root)
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(name+f"_wh{sx}{sy}", (sx*Wd/2, sy*L*0.33, 0.33), (0.25, 0.66, 0.66), M('gun'), parent=root)
            if nozzles:  # four corner thruster nozzles on the underside
                box(name+f"_nz{sx}{sy}", (sx*Wd*0.38, sy*L*0.42, 0.12), (0.25, 0.25, 0.2), M('gun'), parent=root)
    return root

def suv(name, y, rotz=math.radians(90)):
    return car(name, (-0.5, y, 0), 4.9, 2.0, 1.9, M('suv'), rotz=rotz)

def vance_gt(y=16, angle_deg=18, glass=True):
    """Vance's coupe, stopped tight to the wall, nose turned toward the wall (-X) by angle_deg."""
    return car("VanceGT", (-2.6, y, 0), 4.6, 1.7, 1.3, M('coupe'), rotz=math.radians(angle_deg), glass=glass)

def man(n, x, y, face_minus_y=False):
    """Standing figure with head pivot and rifle pivot. Returns (root, head, gun)."""
    root = empty("Man"+n, (x, y, 0), (0, 0, math.pi if face_minus_y else 0))
    box(f"Man{n}_legs", (0, 0, 0.45), (0.4, 0.3, 0.9), M('man'), parent=root)
    box(f"Man{n}_torso", (0, 0, 1.2), (0.5, 0.3, 0.6), M('man'), parent=root)
    head = empty(f"Man{n}_headpivot", (0, 0, 1.55), parent=root)
    box(f"Man{n}_head", (0, 0, 0.12), (0.22, 0.24, 0.24), M('skin'), parent=head)
    gun = empty(f"Man{n}_gunpivot", (0.15, 0.1, 1.4), parent=root)
    box(f"Man{n}_gun", (0, 0.45, 0), (0.06, 0.9, 0.08), M('gun'), parent=gun)
    return root, head, gun

def vapor(name, loc, dim):
    return box(name, loc, dim, M('vapor'))

def jet(name, parent, loc, length=3.0):
    """White vapor jet pointing -Z (downwards) from a nozzle; scale its Z to animate."""
    bpy.ops.mesh.primitive_cone_add(radius1=0.15, radius2=0.6, depth=1.0, location=loc)
    o = bpy.context.object; o.name = name; o.parent = parent
    o.rotation_euler = (math.pi, 0, 0)  # wide end down
    o.scale = (1, 1, length); o.location = (loc[0], loc[1], loc[2] - length/2)
    o.data.materials.append(M('vapor'))
    return o

def camera(loc, rot, lens=24, parent=None, name="Cam"):
    bpy.ops.object.camera_add(location=loc, rotation=rot)
    cam = bpy.context.object; cam.name = name; cam.data.lens = lens; cam.data.sensor_width = 36
    if parent: cam.parent = parent
    bpy.context.scene.camera = cam
    return cam

def finish(OUT, top_center=(-0.5, 10), top_frame=None, render=True):
    """Save .blend/.glb, render frames (optional) and a top-down map."""
    sc = bpy.context.scene
    bpy.ops.wm.save_as_mainfile(filepath=OUT + ".blend")
    bpy.ops.export_scene.gltf(filepath=OUT + ".glb", export_format='GLB', export_animations=True,
                              export_cameras=True, export_lights=False, export_apply=True)
    main_cam = sc.camera
    if render:
        os.makedirs(OUT + "_frames", exist_ok=True)
        sc.render.image_settings.file_format = 'PNG'
        sc.render.filepath = OUT + "_frames/f_"
        bpy.ops.render.render(animation=True)
    bpy.ops.object.camera_add(location=(top_center[0], top_center[1], 60), rotation=(0, 0, 0))
    top = bpy.context.object; top.name = "Top"; top.data.type = 'ORTHO'; top.data.ortho_scale = 70
    sc.camera = top; sc.frame_set(top_frame or int(3.5*FPS))
    sc.render.image_settings.file_format = 'PNG'; sc.render.filepath = OUT + "_top.png"
    bpy.ops.render.render(write_still=True)
    sc.camera = main_cam
    print("DONE", OUT)
