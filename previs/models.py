"""Vehicle proxies with real silhouettes (10/19 本人「もっと立体的な図形作れるじゃん？」).

Each body is a side profile (y forward, z up) extruded across the width with a taper (narrower at the top and toward
the ends) and rounded with a bevel modifier. Wheels are tyres + rims. Glass is its own solid so POV / open-door cuts can
drop it. Part names keep the old contract: opaque parts end with _body, glass with _cab, wheels contain _wh.
Car root: origin on the ground at the car's centre, +Y = nose.
"""
import bpy, bmesh, math
from mathutils import Vector


def _link(o, parent):
    bpy.context.scene.collection.objects.link(o)
    if parent: o.parent = parent
    return o


def loft(name, profile, hw_bottom, hw_top, m, parent=None, plan=None, bevel=0.05, segs=3):
    """Extrude a closed side profile [(y, z), ...] across X. Half-width goes hw_bottom→hw_top with height,
    times plan(y) (1 = full width) so noses and tails round off in plan view."""
    zs = [z for _, z in profile]; z0, z1 = min(zs), max(zs)
    bm = bmesh.new(); L, R = [], []
    for y, z in profile:
        t = (z - z0) / max(1e-6, z1 - z0); hw = (hw_bottom + (hw_top - hw_bottom) * t) * (plan(y) if plan else 1.0)
        L.append(bm.verts.new((-hw, y, z))); R.append(bm.verts.new((hw, y, z)))
    n = len(profile)
    bm.faces.new(list(reversed(L))); bm.faces.new(R)
    for i in range(n):
        j = (i + 1) % n; bm.faces.new((L[i], L[j], R[j], R[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(m)
    if bevel:
        b = o.modifiers.new("Bevel", 'BEVEL'); b.width = bevel; b.segments = segs; b.limit_method = 'ANGLE'; b.angle_limit = math.radians(25)
    for p in me.polygons: p.use_smooth = True
    try: me.set_sharp_from_angle(angle=math.radians(40))
    except Exception: pass
    return _link(o, parent)


def cyl(name, loc, r, depth, m, axis="X", parent=None, verts=24):
    rot = {"X": (0, math.pi / 2, 0), "Y": (math.pi / 2, 0, 0), "Z": (0, 0, 0)}[axis]
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, rotation=rot, vertices=verts)
    o = bpy.context.object; o.name = name; o.data.materials.append(m)
    for p in o.data.polygons: p.use_smooth = True
    if parent: o.parent = parent
    return o


def wheel(name, x, y, r, width, tyre, rim, parent):
    """タイヤ＋ホイール＋スポーク。軸（空のオブジェクト name）を中心に X まわりで回す（render_blocking が走った距離から回転を出す）"""
    piv = bpy.data.objects.new(name, None); bpy.context.scene.collection.objects.link(piv)
    piv.parent = parent; piv.location = (x, y, r); piv["wheel_r"] = r
    cyl(name + "_tyre", (0, 0, 0), r, width, tyre, parent=piv)
    s = 1 if x > 0 else -1
    cyl(name + "_rim", (s * width * 0.06, 0, 0), r * 0.62, width * 0.92, rim, parent=piv)
    cyl(name + "_hub", (s * width * 0.48, 0, 0), r * 0.18, 0.04, tyre, parent=piv, verts=12)
    for a_ in (0, 60, 120):   # スポーク 3 本（6 方向）：回っているのが見える
        bpy.ops.mesh.primitive_cube_add(location=(s * width * 0.47, 0, 0), rotation=(math.radians(a_), 0, 0))
        o = bpy.context.object; o.name = name + f"_spoke{a_}"; o.scale = (0.012, r * 0.58, 0.022); o.data.materials.append(tyre); o.parent = piv
    return piv


def roadster(name, root, L, W, body, glass, mats):
    """Hero: low white wedge, gold canopy set forward, gull-wing roof, rear wing on two pylons, four corner nozzles."""
    h = L / 2
    plan = lambda y: 0.86 + 0.14 * math.cos(min(1.0, abs(y) / h) * math.pi / 2) ** 0.5
    loft(name + "_shell_body", [(h - 0.12, 0.20), (h, 0.30), (h - 0.03, 0.40), (1.0, 0.64), (0.80, 0.68), (-1.0, 0.80),
                                (-2.0, 0.83), (-h, 0.80), (-h, 0.34), (-h + 0.15, 0.20)], W / 2, W / 2 * 0.92, body, root, plan)
    loft(name + "_canopy_cab", [(0.95, 0.60), (0.0, 1.08), (-0.75, 1.12), (-1.40, 0.82), (-1.40, 0.60)], W / 2 * 0.80, W / 2 * 0.58, glass, root, bevel=0.06)
    # 前後の目印（10/19）：鼻の白い一文字、尻の赤い一文字、二枚羽のリアウイング
    loft(name + "_nose_body", [(h + 0.015, 0.27), (h + 0.035, 0.30), (h + 0.015, 0.33), (h - 0.05, 0.30)], W / 2 * 0.80, W / 2 * 0.80, mats["headlight"], root, bevel=0)
    loft(name + "_tail_body", [(-h - 0.02, 0.58), (-h - 0.02, 0.70), (-h + 0.04, 0.70), (-h + 0.04, 0.58)], W / 2 * 0.88, W / 2 * 0.88, mats["taillight"], root, bevel=0)
    for px in (-0.45, 0.45):
        loft(name + f"_pylon{'L' if px < 0 else 'R'}_body", [(-1.95, 0.80), (-2.10, 1.17), (-2.20, 1.17), (-2.15, 0.80)], 0.03, 0.03, body, root, bevel=0.01)
        bpy.data.objects[name + f"_pylon{'L' if px < 0 else 'R'}_body"].location.x = px
    loft(name + "_wing_body", [(-1.95, 1.16), (-2.05, 1.20), (-2.40, 1.19), (-2.40, 1.15)], W / 2 * 0.95, W / 2 * 0.95, body, root, bevel=0.015)


def coupe(name, root, L, W, body, glass, mats):
    """Vance: 60s British GT. Long bonnet, fastback, round lamps, chrome bumpers, wire-look wheels."""
    h = L / 2
    plan = lambda y: 0.84 + 0.16 * math.cos(min(1.0, abs(y) / h) * math.pi / 2) ** 0.6
    loft(name + "_shell_body", [(h - 0.12, 0.25), (h, 0.45), (h - 0.07, 0.66), (1.8, 0.78), (0.6, 0.86), (-1.7, 0.90),
                                (-h + 0.05, 0.78), (-h, 0.40), (-h + 0.18, 0.25)], W / 2, W / 2 * 0.90, body, root, plan)
    loft(name + "_house_cab", [(0.55, 0.84), (0.05, 1.22), (-0.75, 1.26), (-1.70, 0.92), (-1.70, 0.84)], W / 2 * 0.86, W / 2 * 0.64, glass, root, bevel=0.06)
    loft(name + "_roof_body", [(0.06, 1.21), (0.04, 1.25), (-0.75, 1.30), (-1.05, 1.21)], W / 2 * 0.67, W / 2 * 0.67, body, root, bevel=0.03)
    chrome = mats["chrome"]
    for sy in (-1, 1):
        loft(name + f"_bumper{sy}_body", [(sy * (h + 0.04), 0.33), (sy * (h + 0.04), 0.41), (sy * (h - 0.04), 0.41), (sy * (h - 0.04), 0.33)], W / 2 * 0.86, W / 2 * 0.86, chrome, root, bevel=0.02)
    # 前後の目印（10/19 C02 v2）：前に丸目 2 灯（白）、尻に赤いテール 2 灯
    for sx in (-1, 1):
        cyl(name + f"_lamp{sx}_body", (sx * W * 0.32, h - 0.02, 0.60), 0.11, 0.08, mats["headlight"], axis="Y", parent=root)
        loft(name + f"_tl{sx}_body", [(-h + 0.01, 0.58), (-h + 0.01, 0.68), (-h + 0.06, 0.68), (-h + 0.06, 0.58)], 0.09, 0.09, mats["taillight"], root, bevel=0)
        bpy.data.objects[name + f"_tl{sx}_body"].location.x = sx * W * 0.34
    loft(name + "_grille_body", [(h + 0.005, 0.40), (h + 0.005, 0.56), (h - 0.03, 0.56), (h - 0.03, 0.40)], 0.22, 0.24, mats["dark"], root, bevel=0.01)


def suv_body(name, root, L, W, body, glass, mats):
    """Black SUV: upright nose, flat bonnet, tall smoked greenhouse, roof cap."""
    h = L / 2
    plan = lambda y: 0.93 + 0.07 * math.cos(min(1.0, abs(y) / h) * math.pi / 2) ** 0.4
    loft(name + "_shell_body", [(h - 0.15, 0.32), (h, 0.50), (h, 1.02), (1.30, 1.14), (-h + 0.05, 1.18), (-h, 0.50), (-h + 0.15, 0.32)],
         W / 2, W / 2 * 0.97, body, root, plan, bevel=0.07)
    loft(name + "_house_cab", [(1.30, 1.10), (0.85, 1.78), (-h + 0.12, 1.84), (-h + 0.05, 1.12)], W / 2 * 0.95, W / 2 * 0.86, glass, root, bevel=0.05)
    loft(name + "_roof_body", [(0.86, 1.77), (0.82, 1.85), (-h + 0.10, 1.91), (-h + 0.12, 1.83)], W / 2 * 0.88, W / 2 * 0.88, body, root, bevel=0.03)
    loft(name + "_grille_body", [(h + 0.01, 0.62), (h + 0.01, 0.98), (h - 0.03, 0.98), (h - 0.03, 0.62)], W / 2 * 0.62, W / 2 * 0.62, mats["dark"], root, bevel=0.01)
    for sx in (-1, 1):  # 細いヘッドライト（前後が分かる）
        loft(name + f"_lamp{sx}_body", [(h + 0.015, 0.88), (h + 0.015, 0.96), (h - 0.02, 0.96), (h - 0.02, 0.88)], 0.16, 0.16, mats["headlight"], root, bevel=0)
        bpy.data.objects[name + f"_lamp{sx}_body"].location.x = sx * W * 0.38


SPEC = {  # variant: (builder, wheel radius, wheel y, wheel width, track inset)
    "hero": (roadster, 0.34, 1.60, 0.30, 0.16),
    "coupe": (coupe, 0.33, 1.45, 0.22, 0.12),
    "suv": (suv_body, 0.40, 1.55, 0.30, 0.14),
}


def build(name, root, variant, L, W, body, glass, mats, nozzles=False):
    fn, r, wy, ww, inset = SPEC[variant]
    fn(name, root, L, W, body, glass, mats)
    for sx in (-1, 1):
        for sy in (-1, 1):
            wheel(name + f"_wh{sx}{sy}", sx * (W / 2 - inset), sy * wy, r, ww, mats["tyre"], mats["coupe_rim" if variant == "coupe" else "rim"], root)
            if nozzles:  # 四隅の噴射口（下面）
                cyl(name + f"_nz{sx}{sy}_body", (sx * W * 0.38, sy * L * 0.42, 0.14), 0.12, 0.12, mats["dark"], axis="Z", parent=root, verts=16)
