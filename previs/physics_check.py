"""Physics / contact check of the world timeline (10/19 本人「オブジェクト同士の接触とか動きとか物理的に自然に」).

Samples blocking.json's world at 24 fps with the same interpolation as the renderer (interp.py) and reports:
  sink      a car's wheel or body corner inside the terrain (road, wall, cliff, quay, upper road)
  rail      a car's body crossing a guardrail below the rail's top
  float     a car that is not touching anything (all four wheels > 0.15 m clear) — fine for jumps, listed so we can judge
  overlap   two cars, or a standing man and a car, occupying the same space
  feet      a standing man whose feet are above / below the ground
  jerk      speed changing faster than a car or a person can (one-frame velocity jump)
  slide     a car on the ground moving sideways to its nose (> 25°)
usage: python3 physics_check.py [--md]   → out/physics_report.json (+ markdown table on stdout)
"""
import json, math, os, sys
import numpy as np
import interp
if os.environ.get('PHYS_LINEAR') == '1': interp.SMOOTH = False

H = os.path.dirname(os.path.abspath(__file__))
B = json.load(open(os.path.join(H, "blocking.json")))
OBJ = {o["id"]: o for o in B["world"]["objects"]}
FPS = 24
T_END = B["world"].get("dur", 75.7)
GAP = B["set"].get("upperRoad", {}).get("gap", [1e9, 1e9])

# vehicle sizes = models.py / render_blocking make_car (L, W, H) and wheels (radius, y, inset)
DIMS = {"hero": (4.9, 2.0, 1.2, 0.34, 1.60, 0.16), "coupe": (4.6, 1.7, 1.3, 0.33, 1.45, 0.12), "suv": (4.9, 2.0, 1.92, 0.40, 1.55, 0.14)}
STAND = {"stand", "aim", "lower", "lookup", "launcher_stand", "walk"}   # poses with feet on the ground


def solid(x, y, z):
    """Terrain occupancy (the set in render_blocking.py): rock under the lower road, the wall/upper road, the cliff, the quay."""
    if x < -4.0:
        if -11.0 <= x and GAP[0] <= y <= GAP[1]: return z < 20.0
        if x < -11.0: return z < 80.0
        return z < 40.0
    if x <= 5.3: return z < 0.0
    return z < -45.0


RAILS = [(3.0, 0.0, 0.9), (-4.2, 40.0, 40.9), (-10.8, 40.0, 40.9)]   # x, z bottom, z top (thin, all along y)


def rot(r):
    rx, ry, rz = [math.radians(v) for v in r]
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]]); Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]); Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def world(oid, t):
    """(position, rotation matrix) in world space, following parents."""
    o = OBJ[oid]; k = interp.sample(o["keys"], t)
    p = np.array(k.get("p", [0, 0, 0]), float); R = rot(k.get("r", [0, 0, 0]))
    if o.get("parent") in OBJ:
        pp, PR = world(o["parent"], t); return pp + PR @ p, PR @ R
    return p, R


def alive(o, t):
    life = o.get("life"); return life is None or life[0] - 1e-6 <= t <= life[1] + 1e-6


# 横から見た輪郭（models.py と同じ y,z）。車体の点＝輪郭を左右の幅に置いたもの。ガードレールは輪郭の辺が面を横切るかで見る
OUTLINE = {
    "hero": [(2.3, 0.2), (2.45, 0.30), (2.42, 0.40), (1.0, 0.64), (0.0, 1.10), (-0.75, 1.12), (-2.0, 1.20), (-2.4, 1.20), (-2.45, 0.80), (-2.45, 0.34), (-2.3, 0.2)],
    "coupe": [(2.18, 0.25), (2.3, 0.45), (2.23, 0.66), (1.8, 0.78), (0.6, 0.86), (0.05, 1.22), (-0.75, 1.30), (-1.7, 0.9), (-2.25, 0.78), (-2.3, 0.4), (-2.12, 0.25)],
    "suv": [(2.3, 0.32), (2.45, 0.5), (2.45, 1.02), (1.3, 1.14), (0.85, 1.78), (-2.33, 1.91), (-2.45, 1.18), (-2.45, 0.5), (-2.3, 0.32)],
}
def car_points(variant):
    L, W, Hh, r, wy, inset = DIMS[variant]; hw = W / 2 * 0.95
    body = [(sx * hw, y, z) for sx in (-1, 1) for y, z in OUTLINE[variant]]
    wheels = [((sx * (W / 2 - inset), sy * wy, r)) for sx in (-1, 1) for sy in (-1, 1)]
    return np.array(body, float), np.array(wheels, float), r


def rail_hits(bw, n):
    """輪郭の辺（左右それぞれ n 点のループ）が x=rx の面を、レールの高さの範囲で横切るか"""
    out = []
    for side in (0, 1):
        loop = bw[side * n:(side + 1) * n]
        for i in range(n):
            a, b = loop[i], loop[(i + 1) % n]
            for rx, z0, z1 in RAILS:
                if (a[0] - rx) * (b[0] - rx) < 0:
                    u = (rx - a[0]) / (b[0] - a[0]); zc = a[2] + (b[2] - a[2]) * u
                    if z0 <= zc <= z1: out.append((rx, zc, z1))
    return out


def inside_box(pts, c, R, half):
    loc = (pts - c) @ R
    return np.all(np.abs(loc) <= half, axis=1)


cars = [oid for oid, o in OBJ.items() if o["type"] == "car"]
men = [oid for oid, o in OBJ.items() if o["type"] == "man"]
issues = []
def add(kind, oid, t, note): issues.append({"kind": kind, "id": oid, "t": round(t, 3), "note": note})

frames = [i / FPS for i in range(int(T_END * FPS) + 1)]
prev = {}
for t in frames:
    state = {}
    for oid in cars:
        o = OBJ[oid]
        if not alive(o, t): continue
        p, R = world(oid, t); body, wheels, r = car_points(o["variant"]); state[oid] = (p, R)
        bw = p + body @ R.T; ww = p + wheels @ R.T
        down = R @ np.array([0, 0, -1.0])
        contact = ww + down * r
        sunk = [i for i, q in enumerate(contact) if solid(*(q - down * 0.06))]   # contact point more than 6 cm inside the ground
        if sunk: add("sink", oid, t, f"wheel {sunk} in the ground")
        bs = [q for q in bw if solid(q[0], q[1], q[2] + 0.02)]   # 2cm 以内は「触れている」
        if bs: add("sink", oid, t, f"body corner in the ground at {np.round(bs[0], 2).tolist()}")
        hits = rail_hits(bw, len(OUTLINE[o["variant"]]))
        if hits: add("rail", oid, t, f"body crosses the rail at x={hits[0][0]} at z {hits[0][1]:.2f} (rail top {hits[0][2]})")
        # touching anything? step along each wheel's down axis
        clear = []
        for q in contact:
            d = 0.0
            while d < 0.6 and not solid(*(q + down * d)): d += 0.03
            clear.append(d)
        if min(clear) >= 0.15: add("float", oid, t, f"all wheels clear ≥ {min(clear):.2f} m")
        state[oid] = (p, R, min(clear) < 0.15)
    # car vs car
    for i, a in enumerate(cars):
        for b in cars[i + 1:]:
            if a in state and b in state:
                (pa, Ra, _), (pb, Rb, _) = state[a], state[b]
                if np.linalg.norm(pa - pb) > 7: continue
                body_a, _, _ = car_points(OBJ[a]["variant"]); L, W, Hh = DIMS[OBJ[b]["variant"]][:3]
                ins = inside_box(pa + body_a @ Ra.T, pb + Rb @ np.array([0, 0, Hh / 2]), Rb, np.array([W / 2, L / 2, Hh / 2]))
                if ins.any(): add("overlap", f"{a}+{b}", t, "car bodies overlap")
    # men
    for oid in men:
        o = OBJ[oid]
        if not alive(o, t): continue
        k = interp.sample(o["keys"], t); p, R = world(oid, t)
        if o.get("parent") is None and (k.get("pose") in STAND):
            # ground height under the feet
            g = p[2]
            while solid(p[0], p[1], g - 0.01) and g > p[2] - 1: g -= 0.02
            if not solid(p[0], p[1], p[2] - 0.03): add("feet", oid, t, f"feet {p[2]:.2f} m, nothing under them")
            elif solid(p[0], p[1], p[2] + 0.05): add("feet", oid, t, "feet below the ground")
            for c in [c for c in cars if c in state]:
                pc, Rc, _ = state[c]; L, W, Hh = DIMS[OBJ[c]["variant"]][:3]
                ring = np.array([[p[0] + 0.22 * math.cos(a), p[1] + 0.22 * math.sin(a), p[2] + z] for a in np.linspace(0, 2 * math.pi, 8, endpoint=False) for z in (0.3, 1.0)])
                if inside_box(ring, pc + Rc @ np.array([0, 0, Hh / 2]), Rc, np.array([W / 2, L / 2, Hh / 2])).any():
                    add("overlap", f"{oid}+{c}", t, "man inside a car body")
        state[oid] = (p, R, True)
    # motion (world velocity of roots)
    for oid in list(state):
        p = state[oid][0]
        if oid in prev:
            pp, pv = prev[oid]
            v = (p - pp) * FPS
            if pv is not None:
                a = np.linalg.norm(v - pv) * FPS
                carried = OBJ[oid].get("parent") in OBJ and OBJ[OBJ[oid]["parent"]]["type"] == "car"   # 乗っている人は車と同じ加速度を受ける
                limit = 25.0 if (oid in cars or carried) else 15.0
                if a > limit and np.linalg.norm(v) + np.linalg.norm(pv) > 0.5:
                    add("jerk", oid, t, f"accel {a:.0f} m/s² (speed {np.linalg.norm(pv):.1f}→{np.linalg.norm(v):.1f} m/s)")
            if oid in cars and len(state[oid]) == 3 and state[oid][2]:
                vh = np.array([v[0], v[1]]); sp = np.linalg.norm(vh)
                if sp > 2.0:
                    fwd = state[oid][1] @ np.array([0, 1.0, 0]); fh = np.array([fwd[0], fwd[1]])
                    if np.linalg.norm(fh) > 0.5:
                        ang = math.degrees(math.acos(max(-1, min(1, abs(fh @ vh) / (np.linalg.norm(fh) * sp)))))
                        if ang > 25: add("slide", oid, t, f"moving {ang:.0f}° off its nose at {sp:.1f} m/s")
            prev[oid] = (p, v)
        else:
            prev[oid] = (p, None)
    for oid in list(prev):
        if oid not in state: del prev[oid]

# group consecutive frames into spans
spans = []
for kind in ("sink", "rail", "overlap", "feet", "jerk", "slide", "float"):
    byid = {}
    for it in issues:
        if it["kind"] == kind: byid.setdefault(it["id"], []).append(it)
    for oid, its in byid.items():
        cur = [its[0]]
        for it in its[1:]:
            if it["t"] - cur[-1]["t"] <= 1.5 / FPS: cur.append(it)
            else: spans.append((kind, oid, cur[0]["t"], cur[-1]["t"], cur[0]["note"])); cur = [it]
        spans.append((kind, oid, cur[0]["t"], cur[-1]["t"], cur[0]["note"]))

def cuts_at(t0, t1):
    return [c["id"] for c in B["cuts"] if c["start"] <= t1 and t0 <= c["start"] + c["dur"]]

# 意図したもの（判断済み）：ジャンプ・ホバー・壁に乗る瞬間の尻すり（float）、着地後のドリフト（slide）、煙の中で乗り移る（overlap）
INTENDED = [("float", "Roadster", None), ("slide", "Roadster", (65.0, 67.6)), ("overlap", "Vance_walk+VanceGT", None), ("overlap", "Vance_walk+Roadster", None),
            # 速さの変わり方が大きいが物理として正しいもの：壁の根元で前が持ち上がる（支点が後輪→尻→前輪へ移る）、噴射での踏み切り・着地の衝撃、上の道へ跳ぶ噴射、壁を登りきる手前の減速（重力＋ブレーキ）
            ("jerk", "Roadster", (19.0, 20.4)), ("jerk", "Roadster", (38.4, 39.5)), ("jerk", "Roadster", (62.7, 63.2)), ("jerk", "Roadster", (64.9, 65.4)),
            ("jerk", "Roadster", (47.3, 48.9)), ("jerk", "Roadster", (21.7, 22.1)),
            ("jerk", "Sho", (19.0, 20.6)), ("jerk", "Sho", (38.4, 39.5)), ("jerk", "Sho", (62.7, 63.2)), ("jerk", "Sho", (64.9, 65.4)), ("jerk", "Sho", (47.3, 48.9)), ("jerk", "Sho", (21.5, 22.1)),
            ("jerk", "Vance", (38.4, 39.5)), ("jerk", "Vance", (62.7, 63.2)), ("jerk", "Vance", (64.9, 65.4)), ("jerk", "Vance", (47.3, 48.9)),
            ("jerk", "Sho_walk", None), ("jerk", "Launcher", (64.4, 64.6))]   # 歩いて止まる・寿命の終わり（映さない）
def intended(k, i, a, b):
    for kk, ii, win in INTENDED:
        if kk == k and ii == i and (win is None or (win[0] <= a and b <= win[1])): return True
    return False
rep = [{"kind": k, "id": i, "t0": a, "t1": b, "note": n, "cuts": cuts_at(a, b), "intended": intended(k, i, a, b)} for k, i, a, b, n in spans]
json.dump({"smooth": interp.SMOOTH, "spans": rep}, open(os.path.join(H, "out", "physics_report.json"), "w"), ensure_ascii=False, indent=1)
for r in rep:
    print(f"{'ok ' if r['intended'] else '!! '}{r['kind']:7} {r['id']:22} W{r['t0']:6.2f}–{r['t1']:6.2f}  {','.join(r['cuts']) or '-':12} {r['note']}")
print("TOTAL", len(rep), "spans,", sum(not r["intended"] for r in rep), "to fix (smooth=%s)" % interp.SMOOTH)
