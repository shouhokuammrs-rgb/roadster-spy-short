"""Shared greybox builders for the cliff-road set (Blender bpy, headless).
World: road runs along +Y, vertical wall at x=-4, guardrail at x=+3, sea beyond. Units: metres.
Blender axes: +Z up. Camera looks along local -Z; rotation (90°,0,0) looks along +Y.
"""
import bpy, math, os
from mathutils import Vector

FPS = 24

def reset(width=540, height=960, dur=5, flat=True):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _mats.clear()   # 材質のキャッシュは新しいシーンでは無効
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 1, int(round(FPS * dur))
    sc.render.resolution_x, sc.render.resolution_y = width, height
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'FLAT' if flat else 'STUDIO'
    sc.display.shading.color_type = 'MATERIAL'
    sc.display.shading.show_shadows = not flat   # 10/19 影で立体を読ませる。太陽は海側（+X）の低い位置＝夕方
    sc.display.light_direction = (0.62, -0.25, 0.74); sc.display.shadow_shift = 0.05; sc.display.shading.shadow_intensity = 0.45
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
           man=(0.12,0.12,0.14), skin=(0.85,0.65,0.5), gun=(0.2,0.2,0.2), vapor=(0.8,0.84,0.9), ghost=(0.9,0.9,0.85),
           route=(1.0,0.3,0.1), glass_suv=(0.05,0.05,0.06), glass_coupe=(0.17,0.18,0.2), cabin=(0.15,0.14,0.13), crack=(0.95,0.95,1.0), gunmetal=(0.55,0.56,0.6),
           headlight=(1.0,1.0,1.0), taillight=(0.85,0.05,0.04))
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

def car(name, loc, L, Wd, Hh, m, rotz=0, glass=True, nozzles=False, shape="hero"):
    """Car with a real silhouette (models.py, 10/19). Opaque parts end with _body, glass with _cab, wheels contain _wh (POV hiding uses these).
    PREVIS_BOXCARS=1 で前の箱の車に戻せる（比較用）。"""
    root = empty(name, loc, (0, 0, rotz))
    if os.environ.get("PREVIS_BOXCARS") != "1":
        import models
        gm = M({"suv": 'glass_suv', "coupe": 'glass_coupe'}.get(shape, 'glass'))
        mats = {k: M(k) for k in ("headlight", "taillight")}
        mats.update(chrome=mat("chrome", (0.85, 0.86, 0.9)), dark=mat("dark", (0.06, 0.06, 0.07)), tyre=mat("tyre", (0.05, 0.05, 0.05)),
                    rim=mat("rim", (0.45, 0.46, 0.5)), coupe_rim=mat("coupe_rim", (0.72, 0.72, 0.75)))
        models.build(name, root, shape, L, Wd, m, gm if glass else m, mats, nozzles=nozzles)
        if not glass:
            for ch in list(root.children):
                if ch.name.endswith("_cab"): bpy.data.objects.remove(ch, do_unlink=True)
        return root
    # ガラス：外から撮るカットは中を写さない（10/17）。ロードスター＝金の反射、SUV＝黒スモーク、クーペ＝暗いグレー
    gm = M({"suv": 'glass_suv', "coupe": 'glass_coupe'}.get(shape, 'glass'))
    if shape == "suv":      # 低いボンネット（1.0）＋高い車体（1.4）＋キャビン（1.9）
        box(name+"_hood_body", (0, L*0.34, 0.5), (Wd, L*0.32, 1.0), m, parent=root)
        box(name+"_rear_body", (0, -L*0.16, 0.7), (Wd, L*0.68, 1.4), m, parent=root)
        if glass: box(name+"_cab", (0, -L*0.16, 1.65), (Wd*0.9, L*0.6, 0.5), gm, parent=root)
    elif shape == "coupe":  # 長いボンネット＋後ろ寄りのキャビン
        box(name+"_hood_body", (0, L*0.25, 0.375), (Wd, L*0.5, 0.75), m, parent=root)
        box(name+"_rear_body", (0, -L*0.25, 0.475), (Wd, L*0.5, 0.95), m, parent=root)
        if glass: box(name+"_cab", (0, -L*0.12, 1.1), (Wd*0.85, L*0.38, 0.4), gm, parent=root)
        # 前後の目印（10/19 C02 v2 で向きが逆に生成された）：前に丸目 2 灯（白）、尻に小さな赤いテール 2 灯
        for sx in (-1, 1):
            box(name+f"_lamp{sx}_body", (sx*Wd*0.32, L*0.5+0.02, 0.55), (0.22, 0.05, 0.22), M('headlight'), parent=root)
            box(name+f"_tl{sx}_body", (sx*Wd*0.36, -L*0.5-0.02, 0.7), (0.16, 0.05, 0.1), M('taillight'), parent=root)
    else:                   # ウェッジ：低い鼻＋高い尻＋金ガラスのキャビン
        box(name+"_hood_body", (0, L*0.275, 0.225), (Wd, L*0.45, 0.45), m, parent=root)
        box(name+"_rear_body", (0, -L*0.225, 0.385), (Wd, L*0.55, 0.77), m, parent=root)
        if glass: box(name+"_cab", (0, -L*0.1, 0.94), (Wd*0.85, L*0.4, 0.35), gm, parent=root)
        # 前後が読めるように（10/19 本人指摘：C01 で尻から降りてきた）：鼻の白い一文字、尻の赤い一文字、二枚羽のリアウイング
        box(name+"_nose_body", (0, L*0.5+0.02, 0.12), (Wd*0.9, 0.05, 0.08), M('headlight'), parent=root)
        box(name+"_tail_body", (0, -L*0.5-0.02, 0.62), (Wd*0.9, 0.05, 0.1), M('taillight'), parent=root)
        for px in (-0.45, 0.45): box(name+f"_pylon{'L' if px < 0 else 'R'}_body", (px, -L*0.42, 0.95), (0.06, 0.12, 0.4), m, parent=root)
        box(name+"_wing_body", (0, -L*0.44, 1.17), (Wd*0.95, 0.35, 0.05), m, parent=root)
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(name+f"_wh{sx}{sy}", (sx*Wd/2, sy*L*0.33, 0.33), (0.25, 0.66, 0.66), M('gun'), parent=root)
            if nozzles:  # four corner thruster nozzles on the underside
                box(name+f"_nz{sx}{sy}", (sx*Wd*0.38, sy*L*0.42, 0.12), (0.25, 0.25, 0.2), M('gun'), parent=root)
    return root

def suv(name, y, rotz=math.radians(90)):
    return car(name, (-0.5, y, 0), 4.9, 2.0, 1.9, M('suv'), rotz=rotz, shape="suv")

def vance_gt(y=16, angle_deg=18, glass=True):
    """Vance's coupe, stopped tight to the wall, nose turned toward the wall (-X) by angle_deg."""
    return car("VanceGT", (-2.6, y, 0), 4.6, 1.7, 1.3, M('coupe'), rotz=math.radians(angle_deg), glass=glass, shape="coupe")

def man(n, x, y, face_minus_y=False):
    """Articulated figure: two legs, torso, head pivot, two arms (shoulder/elbow pivots), rifle pivot. Returns (root, head, gun).
    Arm pivots are named Man{n}_shL / _shR (shoulder) and Man{n}_elL / _elR (elbow); +X rotation swings the arm forward."""
    root = empty("Man"+n, (x, y, 0), (0, 0, math.pi if face_minus_y else 0))
    for sx, side in ((-1, "L"), (1, "R")):
        box(f"Man{n}_leg{side}_legs", (sx*0.11, 0, 0.45), (0.18, 0.26, 0.9), M('man'), parent=root)
    box(f"Man{n}_torso", (0, 0, 1.2), (0.44, 0.26, 0.6), M('man'), parent=root)
    head = empty(f"Man{n}_headpivot", (0, 0, 1.52), parent=root)
    box(f"Man{n}_head", (0, 0, 0.13), (0.2, 0.22, 0.24), M('skin'), parent=head)
    box(f"Man{n}_nose_head", (0, 0.12, 0.12), (0.06, 0.05, 0.05), M('gun'), parent=head)
    for sx, side in ((-1, "L"), (1, "R")):
        sh = empty(f"Man{n}_sh{side}", (sx*0.27, 0, 1.45), parent=root)
        box(f"Man{n}_uarm{side}_torso", (0, 0, -0.15), (0.1, 0.1, 0.3), M('man'), parent=sh)
        el = empty(f"Man{n}_el{side}", (0, 0, -0.3), parent=sh)
        box(f"Man{n}_farm{side}_torso", (0, 0, -0.14), (0.09, 0.09, 0.28), M('man'), parent=el)
        box(f"Man{n}_hand{side}_head", (0, 0, -0.31), (0.08, 0.08, 0.08), M('skin'), parent=el)
    gun = empty(f"Man{n}_gunpivot", (0.15, 0.1, 1.4), parent=root)
    box(f"Man{n}_gun", (0, 0.45, 0), (0.06, 0.9, 0.08), M('gunmetal'), parent=gun)
    return root, head, gun

def vapor(name, loc, dim):
    """White vapor block. Has an inner skin facing inward, so a camera INSIDE the smoke sees white (not a dark box)."""
    import bmesh
    o = box(name, loc, dim, soft_vapor())
    bm = bmesh.new(); bm.from_mesh(o.data)
    dup = bmesh.ops.duplicate(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:])["geom"]
    bmesh.ops.scale(bm, vec=(0.98, 0.98, 0.98), verts=[g for g in dup if isinstance(g, bmesh.types.BMVert)])
    bmesh.ops.reverse_faces(bm, faces=[g for g in dup if isinstance(g, bmesh.types.BMFace)])
    bm.to_mesh(o.data); bm.free()
    puffy(o)
    return o

def soft_vapor():
    """10/19 蒸気は半透明（固い箱・円錐に読まれないように。C06b v1）。煙の中に入ったときの白い板は M('vapor')（不透明）のまま"""
    m = mat("vapor_soft", (1.0, 1.0, 1.0)); m.diffuse_color = (1.0, 1.0, 1.0, 0.82)   # 暗い地面の上で灰色（石）に見えたので白く濃く
    try: m.surface_render_method = 'BLENDED'
    except Exception: m.blend_method = 'BLEND'
    return m

def puffy(o, disp=0.12):
    """角を丸めて、表面をもこもこに（蒸気・煙の塊）。細分化で縮むぶん頂点を 1.3 倍に広げて、見た目の大きさを元の箱に合わせる"""
    for v in o.data.vertices: v.co *= 1.3
    sub = o.modifiers.new("Sub", 'SUBSURF'); sub.levels = sub.render_levels = 3
    if disp:
        t = bpy.data.textures.new(o.name + "_puff", 'CLOUDS'); t.noise_scale = 0.25
        d = o.modifiers.new("Puff", 'DISPLACE'); d.texture = t; d.strength = disp; d.texture_coords = 'LOCAL'
    for p in o.data.polygons: p.use_smooth = True

def rockface(name, x, y0, y1, z0, z1, facing, m, amp=0.6, step=1.0):
    """岩肌：x の面に貼る、ノイズで凹凸をつけた板（facing=+1 は +X 向き）。10/19 凹凸は面より奥（壁の中）だけ：いちばん出っ張った所が元の面 x。
    道・路肩・車が触れる面は動かない（physics_check の地形と同じ）"""
    import bmesh
    ny, nz = max(2, int((y1 - y0) / step)), max(2, int((z1 - z0) / step))
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=ny, y_segments=nz, size=0.5)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    o.scale = (y1 - y0, z1 - z0, 1)
    o.rotation_euler = (math.pi / 2, 0, math.pi / 2 if facing > 0 else -math.pi / 2)
    o.location = (x - facing * amp * 0.5, (y0 + y1) / 2, (z0 + z1) / 2)
    me.materials.append(m)
    t = bpy.data.textures.new(name + "_n", 'CLOUDS'); t.noise_scale = 2.5; t.noise_depth = 4   # 世界座標で 2.5m の凹凸
    d = o.modifiers.new("Rock", 'DISPLACE'); d.texture = t; d.strength = amp; d.texture_coords = 'GLOBAL'; d.direction = 'Z'
    return o

def jet(name, parent, loc, length=3.0):
    """White vapor jet pointing -Z (downwards) from a nozzle; scale its Z to animate."""
    bpy.ops.mesh.primitive_cone_add(radius1=0.15, radius2=0.6, depth=1.0, location=loc)
    o = bpy.context.object; o.name = name; o.parent = parent
    o.rotation_euler = (math.pi, 0, 0)  # wide end down
    o.scale = (1, 1, length); o.location = (loc[0], loc[1], loc[2] - length/2)
    o.data.materials.append(soft_vapor()); puffy(o, 0)
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
