"""Build the single world timeline (blocking.json v3) from the per-cut blocking (blocking_v2_percut.json).

World = every person / vehicle / effect moving in ONE time axis W (seconds), including what no camera sees.
Cut   = a camera + a window [start, start+dur] of world time + per-cut view flags (hideInPOV / noCab).

This script is the migration and the record of how the unseen gaps were filled (docs/08_world_timeline.md).
After it has run once, blocking.json is edited directly (editor or by hand); re-running overwrites it.
usage: python3 world/build_world.py
"""
import json, math, copy, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # previs/ (interp.py)

H = os.path.dirname(os.path.abspath(__file__)); P = os.path.dirname(H)
OLD = json.load(open(os.path.join(P, "blocking_v2_percut.json")))
CUT = {c["id"]: c for c in OLD["cuts"]}
def obj(cid, oid): return next(o for o in CUT[cid]["objects"] if o["id"] == oid)
def shift(keys, dt, until=None, frm=None):
    out = []
    for k in keys:
        if until is not None and k["t"] > until + 1e-6: continue
        if frm is not None and k["t"] < frm - 1e-6: continue
        out.append(dict(copy.deepcopy(k), t=round(k["t"] + dt, 3)))
    return out
R = lambda v, n=3: round(v, n)

# ---------------------------------------------------------------- world start of each cut (W seconds)
W = {"C02": 0.0, "C03": 6.0, "C06": 17.0, "C06b": 22.0, "C01": 22.8, "C07": 27.5, "C09": 32.5, "C10": 36.0, "C12": 40.5}

# ---------------------------------------------------------------- upper-road chase, computed physically
# 10/18 見直し：物理は「撮りたい絵が成立する値」に寄せる（C13a の火花が見える車間、C14 の「ええ」でアクセル、短いジャンプ、追っ手と向き合って止まる）
CREST_END = 50.0; Y0 = 8.5; V0 = 4.0; ACC = 3.0; VCRUISE = 16.0
W_KICK = 61.5; ACC2 = 4.0                       # C14「ええ」→ アクセル（二人がシートに押し付けられる）
T_ACC = (VCRUISE - V0) / ACC                    # 4 s
def car_v(w):
    t = w - CREST_END
    if t <= T_ACC: return V0 + ACC * t
    if w <= W_KICK: return VCRUISE
    return VCRUISE + ACC2 * (w - W_KICK)
def car_y(w):                                   # on the upper road, before take-off
    t = w - CREST_END
    if t <= T_ACC: return Y0 + V0 * t + 0.5 * ACC * t * t
    y1 = Y0 + V0 * T_ACC + 0.5 * ACC * T_ACC ** 2
    if w <= W_KICK: return y1 + VCRUISE * (t - T_ACC)
    y2 = y1 + VCRUISE * (W_KICK - CREST_END - T_ACC); dt = w - W_KICK
    return y2 + VCRUISE * dt + 0.5 * ACC2 * dt * dt
W_TO = 62.8                                     # take-off (jets on)
Y_TO = car_y(W_TO); V_TO = car_v(W_TO)
GAP = [round(Y_TO + 5), round(Y_TO + 5) + 15]   # the fallen bridge (15 m)
FLIGHT = 2.4; APEX = 4.0
# 10/19 physics_check：踏み切りで 21 → 11 m/s に一瞬で落ちていた（着地点を「縁の 6m 先」に決め打ちしていた）。
# 空中では水平の速さは変わらない → 着地点は速さ×滞空時間（縁の約 31m 先）。噴射が効いているので山は 4m のまま（重力より浅い弧）
V_AIR = V_TO
Y_LAND = Y_TO + V_AIR * FLIGHT
W_LAND = W_TO + FLIGHT
ROLL0, ROLL1 = W_TO + 0.2, W_LAND - 0.3         # one barrel roll, 360°
def air(w):
    u = (w - W_TO) / FLIGHT
    y = Y_TO + V_AIR * (w - W_TO); z = 40 + 4 * APEX * u * (1 - u)
    roll = 0 if w <= ROLL0 else (360 if w >= ROLL1 else 360 * (w - ROLL0) / (ROLL1 - ROLL0))
    return y, z, roll
W_UNDER = 63.4                                  # rocket passes under the car (C15)
YAW_STOP, W_STOP = 180, W_LAND + 2.3
Y_STOP = Y_LAND + V_AIR * (W_STOP - W_LAND) / 2   # 一定の減速で止まる距離（v·T/2）。前は 10m で、着地の速さと合っていなかった   # drift: ends nose-back, facing the pursuers (rear glass toward the blast = C18)
# pursuer: waits on the upper road, launches when radioed, closes to 8 m for the shots (C13a), drops back, brakes at the near edge
PURSUE = [(46.5, None), (53.0, 20.0), (54.6, 8.0), (57.5, 9.0), (60.0, 13.0), (62.4, 15.0)]   # 10/19 20→8m を 1.3→1.6 秒に（2.6G で詰めていた）。C13a の 3 発（W54.5–55.3）は 8m のまま   # (W, distance behind the car)
W_SUV_STOP = 65.0; Y_SUV_STOP = GAP[0] - 3
# 10/19 physics_check：区間のつなぎ目で速さが跳んでいた（W53 で 2.8→23 m/s）。車間はなめらかな曲線（PCHIP）、
# 発進は 0 から W53 の速さまでのエルミート、ブレーキは W62.4 の速さから 0 までのエルミート
def _pchip(xs, ys):
    import interp as _ip
    ms = _ip._slopes(xs, ys)
    return lambda x: _ip._eval(xs, ys, ms, x)
_gap = _pchip([w for w, _ in PURSUE[1:]], [d for _, d in PURSUE[1:]])
def _herm(t, T, y0, y1, v0, v1):
    u = t / T; return (2*u**3 - 3*u**2 + 1) * y0 + (u**3 - 2*u**2 + u) * T * v0 + (-2*u**3 + 3*u**2) * y1 + (u**3 - u**2) * T * v1
def _pursue(w): return car_y(w) - _gap(w)
def _vel(f, w, h=1e-3): return (f(w + h) - f(w - h)) / (2 * h)
def suv_y(w):
    if w <= 46.5: return -70.0
    if w <= 53.0: return _herm(w - 46.5, 6.5, -70.0, _pursue(53.0), 0.0, _vel(_pursue, 53.0 + 2e-3))
    if w <= 62.4: return _pursue(w)
    if w <= W_SUV_STOP: return _herm(w - 62.4, W_SUV_STOP - 62.4, _pursue(62.4), Y_SUV_STOP, _vel(_pursue, 62.4 - 2e-3), 0.0)
    return Y_SUV_STOP
W_FIRE = 62.0
ROCKET_Y0 = suv_y(W_FIRE) + 1.6
Y_UNDER = air(W_UNDER)[0]
V_ROCKET = (Y_UNDER - ROCKET_Y0) / (W_UNDER - W_FIRE)
Y_BLAST = Y_STOP + 50
W_BLAST = W_UNDER + (Y_BLAST - Y_UNDER) / V_ROCKET

# cut windows after the wall climb follow the physics
W.update({"C13a": 53.5, "C13b": 57.0, "C14": 59.0, "C14b": W_FIRE - 2.5, "C15": W_TO - 1.6, "C16": W_TO - 0.3,
          "C17": W_LAND - 1.2, "C18": W_STOP + 1.2})
DUR = {"C03": 6.5, "C18": 6.5}   # 10/19 英語の台詞の長さで出し直し   # 台詞の長さから（docs/09_shot_length.md）。他は 5 秒
WORLD_DUR = round(W["C18"] + DUR["C18"] + 0.5, 1)

# ---------------------------------------------------------------- world objects
objs = []
def add(o): objs.append(o); return o

SEAT_Z = -0.01   # 10/19 ロードスターの座席：倒した座り方（rig/poses.json）で頭のてっぺん 1.00、足 0.18（屋根 1.09・床 0.2）
GT_DX = 0.25   # クーペを壁から離した量（C02 のカメラの狙い・Vance の降り口も同じだけずらす）
# set pieces that never move
for oid in ("SUV_rear", "SUV_rear2", "SUV_front", "SUV_front2", "VanceGT"):
    o = copy.deepcopy(obj("C02", oid)); o.pop("noCab", None); o.pop("hideInPOV", None)
    if oid == "VanceGT":   # 10/19 physics_check：前の左角が壁に 12cm めり込んでいた → 25cm 道の側へ（壁との隙間 13cm）
        for k in o["keys"]: k["p"] = [R(k["p"][0] + GT_DX), k["p"][1], k["p"][2]]
    add(o)

# enemies: aiming through the siege and the smoke, lose the car and look up in C12
for m in "ABCDEFGH":
    k12 = obj("C12", m)["keys"]
    add({"id": m, "type": "man", "keys": [dict(k12[0], t=0.0)] + shift(k12, W["C12"])})

# Vance: in the coupe → crosses inside the smoke → in the Roadster
gtV = copy.deepcopy(obj("C02", "Vance")["keys"][0]); gtV["p"] = [gtV["p"][0], gtV["p"][1], 0.05]   # 10/19 倒した座り方でクーペの床（0.25）に足、屋根（1.22）の下に頭
add({"id": "Vance_gt", "type": "man", "parent": "VanceGT", "life": [0, 33.0],
     "keys": [dict(gtV, t=0.0), dict(gtV, t=5.0), dict(gtV, t=6.0, pose="sit")]})
# 拳銃：C02 でマガジンを確かめた後、残り 3 発を温存して膝の上に下ろす（銃口は足元）。10/19 C01 で「内側から撃った」と読まれたため。
# それまでは胸の高さに浮いたままだった（Vance の姿勢が sit に変わっても拳銃が残っていた）
LAP = {"r": [-65, 0, 0]}
pk = obj("C02", "Pistol")["keys"]
add({"id": "Pistol", "type": "prop", "variant": "pistol", "parent": "Vance_gt", "life": [0, 33.0],
     "keys": pk + [dict(pk[-1], t=5.0), {"t": 6.0, "p": [0.12, 0.30, 0.46], **LAP}]})
mk = obj("C02", "Mag")["keys"]
add({"id": "Mag", "type": "prop", "variant": "magazine", "parent": "Vance_gt", "life": [0, 33.0],
     "keys": mk + [{"t": 6.0, "p": [0.12, 0.26, 0.42], **LAP}]})
add({"id": "Vance_walk", "type": "man", "life": [33.0, 35.6], "note": "［映さない・煙の中］クーペの右ドアから 2m 隣のロードスターへ",
     "keys": [{"t": 33.0, "p": [R(-1.6 + GT_DX), 16.0, 0], "r": [0, 0, -90], "pose": "stand"},
              {"t": 34.6, "p": [-0.4, 16.3, 0], "r": [0, 0, -90], "pose": "stand"},
              {"t": 35.6, "p": [0.1, 16.4, 0], "r": [0, 0, -90], "pose": "stand"}]})
add({"id": "Vance", "type": "man", "parent": "Roadster", "life": [35.6, WORLD_DUR],
     "keys": [{"t": 35.6, "p": [0.35, 0.15, SEAT_Z], "r": [0, 0, 0], "pose": "sit"}]})

# Sho: café → walks to the parked car → drives
CAFE = (14.0, 7.0); dx, dy = CAFE[0] - 10.0, CAFE[1] - (-20.0)      # café moved next to the car (was y=-20)
def mv(p): return [R(p[0] + dx), R(p[1] + dy), p[2]]
C03_SHO = [(0, "chair"), (2.5, "chair"), (3.0, "chairlookup"), (4.8, "chairlookup"), (5.2, "chair")]   # 10/19 英語の台詞：「The upper road」で見上げ、「Up there.」(4.0) の後に戻り、「On it.」(5.3)   # 10/18 コードネームを 007 に（「ダブルオーセブンから」で台詞が 0.6 秒延び、以降を 0.6 秒後ろへ）   # 10/18 台詞に合わせて組み直し：「上の道」で見上げ、「上。」の後で戻り、「了解。」
sk0 = obj("C03", "Sho")["keys"][0]
add({"id": "Sho_cafe", "type": "man", "life": [0, 12.5],
     "keys": [dict(sk0, t=R(t_ + W["C03"]), p=mv(sk0["p"]), pose=po) for t_, po in C03_SHO]})
add({"id": "Chair", "type": "prop", "variant": "chair", "keys": [dict(obj("C03", "Chair")["keys"][0], p=mv(obj("C03", "Chair")["keys"][0]["p"]))]})
add({"id": "Table", "type": "prop", "variant": "table", "keys": [dict(obj("C03", "Table")["keys"][0], p=mv(obj("C03", "Table")["keys"][0]["p"]))]})
add({"id": "Sho_walk", "type": "man", "life": [12.5, 15.5], "note": "［映さない］カフェから 9m 先のロードスターへ（小走り）",
     "keys": [{"t": 12.5, "p": [14.0, 7.3, -45], "r": [0, 0, 16], "pose": "stand"}, {"t": 15.3, "p": [11.9, 14.6, -45], "r": [0, 0, 16], "pose": "stand"}]})
sho_in = {"p": [-0.35, 0.15, SEAT_Z], "r": [0, 0, 0]}
c07 = W["C07"]
add({"id": "Sho", "type": "man", "parent": "Roadster", "life": [15.5, WORLD_DUR],
     "keys": [dict(sho_in, t=15.5, pose="drive"), dict(sho_in, t=c07 + 2.2, pose="drive"), dict(sho_in, t=c07 + 3.0, pose="turnright"),
              dict(sho_in, t=W["C09"] + 0.2, pose="turnright"), dict(sho_in, t=W["C09"] + 0.8, pose="drive")]})

# ---------------------------------------------------------------- 10/19 接触の物理（physics_check.py が見つけたもの）
# ロードスターの輪郭（models.py と同じ、横から見た y,z）。ヨー 90°（鼻が -X）で壁に向かうとき、ピッチ θ での各点の x,z を出す
HERO_PTS = [(2.45, 0.30), (2.42, 0.40), (1.0, 0.64), (0.0, 1.10), (-0.75, 1.12), (-2.45, 0.80), (-2.45, 0.34), (2.3, 0.2), (-2.3, 0.2),
            (-2.4, 1.20), (-2.0, 1.20), (1.6, 0.0), (-1.6, 0.0)]    # 最後の 2 つ＝前後のタイヤの接地点
def _rel(theta):
    """local (y, z) → world offset (dx, dz) for r=[theta, 0, 90] (nose toward -X, pitched nose-up by theta)."""
    c, s_ = math.cos(math.radians(theta)), math.sin(math.radians(theta))
    return [(-(y * c - z * s_), y * s_ + z * c) for y, z in HERO_PTS]
def tipup(theta, wall_x, ground):
    """車をピッチ θ にしたとき、どの点も壁（x < wall_x）にも地面（z < ground）にも入らない、いちばん壁寄り・低い位置（＝壁と地面に触れる）"""
    rel = _rel(theta); return [R(wall_x + max(-dx for dx, _ in rel) + 0.01), R(ground + max(-dz for _, dz in rel))]
def ease(u): return u * u * (3 - 2 * u)
def wall_climb_start(t0, t1, wall_x, ground, y, approach_from=None):
    """崖・壁の根元で前が持ち上がって壁に乗る（t0 で水平・壁に鼻先が触れる → t1 で垂直・壁に密着）。前は鼻先が 0.8m 壁にめり込んでいた"""
    ks = []
    for i in range(9):
        u = i / 8; th = 90 * ease(u); x, z = tipup(th, wall_x, ground)
        ks.append({"t": R(t0 + (t1 - t0) * u), "p": [x, y, z], "r": [R(th, 1), 0, 90]})
    return ks
# Roadster
rk = []
rk.append({"t": 0.0, "p": [12.0, 16.5, -45], "r": [0, 0, 90]})                       # parked on the quay, facing the cliff
rk += shift(obj("C06", "Roadster")["keys"], W["C06"], until=2.8)                      # launch, mount the cliff
rk += shift(OLD["tracks"]["arrival_roadster"]["keys"], W["C06b"])                     # climb out, hover, land by the coupe
c10 = obj("C10", "Roadster")["keys"]
# 10/19 physics_check：壁の手前で横滑り（鼻と進む向きが 30〜90° ずれ、壁と平行に動きながら前が持ち上がっていた）→ 道なりの経路を速度の物理で走る：
# 直進で 0.7g 加速 → 0.9g で 5 m/s まで減速 → 半径 2.6m で左の壁へ向き直る（横 G ≈ 1.0、限界）→ 0.9g で止まりながら壁に鼻先 → W38.5 で前が上がる
def c10_path():
    A_ACC, A_BRK, V_ARC, RAD = 7.0, 9.0, 5.0, 2.6
    x0, y0 = 1.2, 16.5; yA = 4.0 + RAD; S1 = y0 - yA; CEN = (x0 - RAD, yA); S2 = S1 + RAD * math.pi / 2
    x_tip = tipup(0, -4.0, 0.0)[0]; L = S2 + (CEN[0] - x_tip)
    def at(sv):
        if sv <= S1: return (x0, y0 - sv), 180.0
        if sv <= S2:
            ph = (sv - S1) / RAD; return (CEN[0] + RAD * math.cos(ph), CEN[1] - RAD * math.sin(ph)), math.degrees(math.atan2(math.sin(ph), -math.cos(ph)))
        return (CEN[0] - (sv - S2), 4.0), 90.0
    def vcap(sv):
        v = math.sqrt(max(0, 2 * A_BRK * (L - sv)))
        if sv < S1: v = min(v, math.sqrt(V_ARC ** 2 + 2 * A_BRK * (S1 - sv)))
        elif sv <= S2: v = min(v, V_ARC)
        return v
    dt = 1 / 240; sv, v, tt, track = 0.0, 0.0, 0.0, [(0.0, 0.0)]
    while sv < L - 1e-3 and tt < 6:
        v = min(v + A_ACC * dt, vcap(sv)); 
        if v < 1e-3 and sv > L / 2: break
        sv += v * dt; tt += dt; track.append((tt, sv))
    T = tt; t_start = W["C10"] + 2.5 - T
    ks = []
    n = int(T / 0.1)
    for i in range(n + 1):
        ti = min(T, i * 0.1); svi = min(L, next(sv_ for tt_, sv_ in track if tt_ >= ti - 1e-9))
        (px, py), yaw = at(svi)
        ks.append({"t": R(t_start + ti), "p": [R(px), R(py), 0], "r": [0, 0, R(yaw, 1)]})
    return ks, t_start
c10_keys, C10_GO = c10_path()
rk = [k for k in rk if not (C10_GO - 1e-6 <= k["t"] < W["C10"] + 2.5 - 1e-6)] + c10_keys[:-1]   # 最後の点は壁に乗る最初のキー（tipup）
rk += shift([k for k in c10 if k["t"] >= 2.5], W["C10"], until=3.3)                   # ladder-lean onto the wall
rk += shift(obj("C12", "Roadster")["keys"], W["C12"])                                 # climbing (C12)
v = 6.0; zc = 28.0; w_top = W["C12"] + 5 + (37.6 - zc) / v
rk.append({"t": R(w_top), "p": [-3.34, 4.0, 37.6], "r": [90, 0, 90]})                # nose reaches the top
for dt, p_, r_ in ((0.4, [-3.9, 4.0, 39.3], [55, 0, 90]), (0.8, [-5.0, 4.0, 40.0], [15, 0, 90]), (1.2, [-6.0, 4.2, 40.0], [0, 0, 90]),
                   (2.2, [-7.5, 6.0, 40.0], [0, 0, 18])):
    rk.append({"t": R(w_top + dt), "p": p_, "r": r_})
w = CREST_END
while w < W_TO - 1e-6:
    rk.append({"t": R(w), "p": [-7.5, R(car_y(w)), 40.0], "r": [0, 0, 0]}); w += 0.5
w = W_TO
while w <= W_LAND + 1e-6:
    y, z, roll = air(w); rk.append({"t": R(w), "p": [-7.5, R(y), R(z)], "r": [0, R(roll, 1), 0]}); w += 0.2
for u in (0.25, 0.5, 0.75, 1.0):                                                        # drift to a stop, ending nose-back
    e = 1 - (1 - u) ** 2
    rk.append({"t": R(W_LAND + u * (W_STOP - W_LAND)), "p": [-7.5, R(Y_LAND + e * (Y_STOP - Y_LAND)), 40.0], "r": [0, 360, R(YAW_STOP * e, 1)]})   # ロールは 360 のまま（0 に戻すと、補間で着地後にもう一回転する）
rk.sort(key=lambda k: k["t"])

# (a) 崖（外面 x=5.3、岸壁 z=-45）：W19.0 で鼻先が崖に触れ、W19.8 に垂直
rk = [k for k in rk if not (19.0 - 1e-6 <= k["t"] <= 19.8 + 1e-6)] + wall_climb_start(19.0, 19.8, 5.3, -45.0, 16.5)
# (b) 道の岩壁（面 x=-4.0、道 z=0）：W38.5 で鼻先が壁に触れ、W39.3 に垂直
rk = [k for k in rk if not (W["C10"] + 2.5 - 1e-6 <= k["t"] <= W["C10"] + 3.3 + 1e-6)] + wall_climb_start(W["C10"] + 2.5, W["C10"] + 3.3, -4.0, 0.0, 4.0)
# (c) 壁を登っている間は面にタイヤが触れている（前は崖で 36cm、道の岩壁で 66cm 浮いていた）
for k in rk:
    if abs(k["r"][0] - 90) < 1e-6 and k["r"][2] == 90 and k["r"][1] == 0:
        if k["p"][0] > 4.0: k["p"][0] = 5.31
        elif -4.5 < k["p"][0] < -2.0 and k["p"][2] < 39.0: k["p"][0] = -3.99
# (d) 上の道に上がるところ：ガードレール（x=-4.2、高さ 0.9）を車体が突き抜けていた → 噴射で小さく跳んで越える
w_top = [k["t"] for k in rk if abs(k["p"][2] - 37.6) < 1e-6][0]
rk = [k for k in rk if not (w_top + 1e-6 < k["t"] < w_top + 2.2 - 1e-6)]
for dt, p_, r_ in ((0.35, [-3.99, 4.0, 39.7], [90, 0, 90]), (0.75, [-4.7, 4.0, 42.0], [50, 0, 90]), (1.15, [-5.9, 4.1, 42.3], [12, 0, 85]),
                   (1.6, [-7.2, 4.7, 40.0], [0, 0, 45])):
    rk.append({"t": R(w_top + dt), "p": p_, "r": r_})
# (e) クーペの横に降りるとき、車の角が海側のガードレール（x=3.0）をかすめていた → 少し道の内側へ
for k in rk:
    if abs(k["t"] - 26.6) < 1e-6: k["p"][0] = 1.25; k["p"][2] = 0.5
rk.sort(key=lambda k: k["t"])
add({"id": "Roadster", "type": "car", "variant": "hero", "keys": rk})
add({"id": "Cabin", "type": "prop", "variant": "cabin", "parent": "Roadster", "keys": [{"t": 0, "p": [0, 0, 0], "r": [0, 0, 0]}]})
add({"id": "MirrorR", "type": "prop", "variant": "mirror", "parent": "Roadster", "keys": obj("C13b", "MirrorR")["keys"]})
add({"id": "DoorR", "type": "door", "parent": "Roadster",
     "keys": [{"t": 0, "a": 0}, {"t": c07 + 1.0, "a": 0}, {"t": c07 + 2.2, "a": 75}, {"t": 35.0, "a": 75}, {"t": 35.8, "a": 0}]})
jk = [{"t": 0, "s": 0}] + shift(obj("C06", "Jets")["keys"], W["C06"], until=2.8) + shift(OLD["tracks"]["arrival_jets"]["keys"], W["C06b"])
jk += [{"t": 29.0, "s": 0}, {"t": 32.5, "s": 0}, {"t": 32.7, "s": 3}, {"t": 35.0, "s": 3}, {"t": 35.6, "s": 0},   # smoke screen
       {"t": R(W_TO - 0.2), "s": 0}, {"t": W_TO, "s": 3}, {"t": R(W_LAND), "s": 1.5}, {"t": R(W_LAND + 0.4), "s": 0},
       {"t": R(w_top + 0.2), "s": 0}, {"t": R(w_top + 0.45), "s": 2.5}, {"t": R(w_top + 1.2), "s": 1}, {"t": R(w_top + 1.5), "s": 0}]   # 上の道へ跳ぶ噴射
jk.sort(key=lambda k: k["t"])
add({"id": "Jets", "type": "jets", "parent": "Roadster", "keys": jk})
vk = [k for k in shift(OLD["tracks"]["arrival_vapor"]["keys"], W["C06b"]) if k["t"] < 27.5] + [{"t": 27.8, "p": [0.6, 16.5, 1.2], "s": [5, 11, 3.6]}]  # 窓の外で止める（カメラが煙の箱の中に入ると白くならない）
vk += [{"t": 28.4, "p": [0.8, 16.5, 0.6], "s": [6, 9, 1.2]}, {"t": 29.5, "p": [0, 16, 0.25], "s": [6, 9, 0.5]},   # 着地のガスは C07 の頭で薄れ、車の側面が見えてくる
        {"t": 32.5, "p": [0.5, 16.5, 0.3], "s": [6, 9, 0.6]},
       # 煙幕は車（y=16.5）を中心に前後へ広がる：後ろの 4 人（y≈-7〜-12）も前の 4 人（y≈34〜39）も見えなくなる
       {"t": 33.5, "p": [0.0, 16.5, 1.0], "s": [7, 22, 2.5]}, {"t": 35.0, "p": [-0.3, 16.5, 1.4], "s": [8, 46, 3.0]}, {"t": 37.5, "p": [-0.5, 16.5, 1.6], "s": [9, 66, 3.6]},
       {"t": 40.5, "p": [-0.5, 16.5, 1.2], "s": [9, 60, 2.6]}, {"t": 43.0, "p": [-0.8, 16.5, 0.5], "s": [7, 40, 1.0]}, {"t": 45.5, "p": [-0.8, 16.5, 0.2], "s": [5, 26, 0.15]},
       {"t": 47.0, "p": [-0.8, 16.5, 0.05], "s": [0.1, 0.1, 0.1]}]
vk.sort(key=lambda k: k["t"])
add({"id": "Vapor", "type": "vapor", "life": [22.0, 47.0], "keys": vk})

# pursuer (third team, waiting on the upper road) and its two shooters
sk = []; w = 0.0
for w in [0.0, 46.5] + [R(46.5 + i * 0.5) for i in range(1, int((W_SUV_STOP + 2 - 46.5) / 0.5) + 1)]:
    sk.append({"t": R(w), "p": [-7.5, R(suv_y(w)), 40.0], "r": [0, 0, 0]})
add({"id": "SUV_chase", "type": "car", "variant": "suv", "keys": sk,
     "note": "上の道で待機していた別チーム（運転手・助手席の射手・後席のランチャー）。無線で呼ばれて W46.5 に発進"})
_sk = copy.deepcopy(obj("C13a", "Shooter")["keys"][0]); _sk["p"][0] = R(_sk["p"][0] - 0.17)   # 10/19 腰が車体の外（x1.09、車幅 1.0）で太ももがドアを突き抜けていた → 窓枠に腰掛け、上半身だけ乗り出す
add({"id": "Shooter", "type": "man", "parent": "SUV_chase", "life": [52.0, 60.0], "keys": [dict(_sk, t=52.0)]})
_lk = copy.deepcopy(obj("C14b", "Shooter")["keys"][0]); _lk["p"][0] = R(_lk["p"][0] - 0.1)   # 10/19 腰が車体の縁（x1.01）→ 窓枠の内側に腰掛ける
add({"id": "Launcher", "type": "man", "parent": "SUV_chase", "life": [58.0, 64.5], "keys": [dict(_lk, t=58.0)]})
add({"id": "Flash", "type": "fx", "variant": "fire", "parent": "SUV_chase",
     "keys": [{"t": 0, "p": [1.1, 0.6, 1.9], "s": 0}, {"t": W_FIRE, "p": [1.1, 0.6, 1.9], "s": 0}, {"t": R(W_FIRE + 0.2), "p": [1.1, 0.6, 1.9], "s": 3}, {"t": R(W_FIRE + 0.6), "p": [1.1, 0.6, 1.9], "s": 0}]})
SHOTS = (1.0, 1.4, 1.8)   # C13a の 3 発。10/18 間隔 1.3 → 0.4 秒（拳銃の連射。カットが 2 秒で収まる）
spk = [{"t": 0, "p": [0, -2.4, 1.0], "s": 0}]
for s_, x_ in zip(SHOTS, (0, 0.3, -0.2)):
    w_ = W["C13a"] + s_; spk += [{"t": R(w_ - 0.05), "p": [x_, -2.4, 1.0], "s": 0}, {"t": R(w_), "p": [x_, -2.4, 1.0], "s": 0.5}, {"t": R(w_ + 0.15), "p": [x_, -2.4, 1.0], "s": 0}]
add({"id": "Spark", "type": "fx", "variant": "spark", "parent": "Roadster", "keys": spk})
# 着弾（10/19 C01 で生成に先に入れてしまったものを世界へ戻す）：前の SUV からの弾が Vance の目の前、フロントガラスの外側に当たる。
# 世界の時刻 W23.4（C01 の 0.6 秒）。Vance はひるむ（C01 のカメラ＝Vance の目が小さく跳ねて引く）
W_HIT_GT = 23.4
add({"id": "HitGT", "type": "fx", "variant": "spark", "parent": "VanceGT", "note": "フロントガラス外側への着弾（ひびが広がる。ガラスは持つ）",
     "keys": [{"t": 0, "p": [0.42, 0.75, 1.12], "s": 0}, {"t": R(W_HIT_GT - 0.02), "p": [0.42, 0.75, 1.12], "s": 0},
              {"t": W_HIT_GT, "p": [0.42, 0.75, 1.12], "s": 0.35}, {"t": R(W_HIT_GT + 0.25), "p": [0.42, 0.75, 1.12], "s": 0}]})
add({"id": "Rocket", "type": "fx", "variant": "missile", "life": [W_FIRE, R(W_BLAST + 0.1)],
     "keys": [{"t": W_FIRE, "p": [-6.8, R(ROCKET_Y0), 41.9], "s": 1}, {"t": W_UNDER, "p": [-7.5, R(Y_UNDER), 40.9], "s": 1},
              {"t": R(W_BLAST), "p": [-7.5, R(Y_BLAST), 40.3], "s": 1}]})
add({"id": "Boom", "type": "fx", "variant": "fire", "life": [R(W_BLAST), WORLD_DUR],
     "keys": [{"t": R(W_BLAST), "p": [-7.5, R(Y_BLAST), 40.5], "s": 0}, {"t": R(W_BLAST + 0.4), "p": [-7.5, R(Y_BLAST), 42], "s": 5},
              {"t": R(W_BLAST + 2.5), "p": [-7.5, R(Y_BLAST), 45], "s": 7}, {"t": WORLD_DUR, "p": [-7.5, R(Y_BLAST), 48], "s": 5}]})

# ---------------------------------------------------------------- cuts = camera + window + view flags
def cam_of(cid):
    c = next(o for o in CUT[cid]["objects"] if o["type"] == "camera")
    return {"lens": c.get("lens", 24), "parent": c.get("parent"), "keys": c["keys"]}
VIEW = {"C01": {"hideInPOV": ["VanceGT", "Vance_gt"]}, "C02": {"noCab": ["VanceGT"]}, "C07": {"hideInPOV": ["VanceGT", "Vance_gt"], "noCab": ["Roadster"]},
        "C09": {"hideInPOV": ["B"]}, "C10": {"hideInPOV": ["Roadster"]}, "C13b": {"hideInPOV": ["Roadster"]}, "C14": {"hideInPOV": ["Roadster"]},
        "C16": {"hideInPOV": ["Roadster"]}, "C18": {"hideInPOV": ["Roadster"]}}
def tl(w, cid): return R(w - W[cid], 1)   # world time → cut time
# 編集（本編でどこを使うか）：shot_length.py が規則から出す（world/edit_derived.json）。in/out はカット内の秒、speed は再生速度
DER = json.load(open(os.path.join(H, "edit_derived.json")))
VOICE = json.load(open(os.path.join(P, "voice", "lines.json")))["lines"]
EDIT = {k: tuple(v) for k, v in DER["edit"].items()}
END_BLACK = 1.5
# 採用した生成（あれば通しの動画でグレーボックスの代わりに使う。要点の時刻は生成で測り直して shot_length.py に入れる）
TAKES = {"C01": "gen/C01_v4.mp4", "C02": "gen/C02_v3.mp4", "C03": "gen/C03_v2.mp4", "C06": "gen/C06_v1.mp4", "C06b": "gen/C06b_v2.mp4"}
# 台詞（声＝voice/lines.json の仮の声の長さ）と効果音のメモ。[t, 表示, 長さ, 声 id, 英語字幕]
SFX = {"C01": [[0.6, "（ガシャッ）"], [2.2, "（プシュゥッ）"]], "C06b": [[2.0, "（頂点で無音）"]], "C09": [[0.0, "（音が消える）"]],
       "C14b": [[2.5, "（ボシュッ）"]], "C16": [[1.2, "（息だけ）"]], "C17": [[1.2, "（ドン）"], [1.6, "（キーッ）"], [2.7, "（遠くでバァン）"]]}
LINES = {}
for cid in EDIT:
    ls = [[t_, txt, 1.2, None, None] for t_, txt in SFX.get(cid, [])]
    for lid, t_ in DER["lines"].get(cid, []):
        v = VOICE[lid]; ls.append([t_, f"{v['speaker']}「{v['ja']}」", v["dur"], lid, v["en"]])
    LINES[cid] = sorted(ls, key=lambda l: l[0])
BEATS = {   # 上の道のカットは世界の物理から時刻を出す（数字を手で書かない）
  "C03": [[0, 0.8, "Sho の後ろ姿、カップ。無線が光る"], [0.8, 3.7, "Chief「Double-O-Seven. The upper road. Use the car.」"], [2.5, 3.0, "「The upper road」で Sho の頭が大きく上を向く（首と頭で約 60°、上体も少し反る）。頭が上がりきってから、カメラが 3.0→3.9 秒でティルトアップ。崖の縁と空"],
          [4.0, 4.7, "Sho「Up there.」"], [4.8, 5.2, "頭が戻る。カメラは 5.0→5.7 秒で戻る"], [5.3, 5.9, "「On it.」"], [5.6, 6.5, "手が止まってからカップを置く"]],
  "C13a": [[0, 1.0, "上の道。SUV の右（助手席）窓から男が上半身を出し、前の白い車へ構える"], [1.0, 2.0, "3 発（0.4 秒間隔）。白い車の尻で火花、ガラスは無傷"], [2.0, 5, "構えたまま追う"]],
  "C13b": [[0, 1.5, "右のサイドミラーに SUV。「しつこいな」"], [1.5, 2.5, "前を向く"], [2.5, 5, "橋が落ちている"]],
  "C18": [[0, 0.5, "リアガラスの向こうに遠い火球。前を向いたまま"], [0.5, 2.5, "Vance「Mine had an ejector seat.」"], [2.5, 3.55, "間（1秒）"],
          [3.55, 5.2, "Sho、横目で「This one ejects the whole car.」"], [5.3, 5.8, "Vance の口の端が 0.5mm 上がる"], [5.8, 6.5, "黒へ"]],
  "C14": [[0, tl(W_KICK, "C14"), "裂け目が迫る。Vance の手がドアハンドルへ。「……橋がないが」「ええ」"], [tl(W_KICK, "C14"), 5, "アクセル。二人がシートに押し付けられる。リアガラスの向こうで追っ手がランチャーを構える"]],
  "C15": [[0, tl(W_FIRE, "C15"), "裂け目の横から。左に追っ手 SUV、中央に白い車、右に裂け目の縁"], [tl(W_FIRE, "C15"), tl(W_TO, "C15"), f"SUV からロケット（{V_ROCKET:.0f} m/s）"],
          [tl(W_TO, "C15"), tl(W_UNDER, "C15"), "四隅が噴いて浮く"], [tl(W_UNDER, "C15"), R(tl(W_UNDER, "C15") + 0.4, 1), "ロケットが車の真下を抜ける（ここだけさらにスロー）"],
          [R(tl(W_UNDER, "C15") + 0.4, 1), 5, "裂け目の上を飛び、一回転して向こう岸へ"]],
  "C16": [[0, tl(ROLL0, "C16"), "車内。前に裂け目、浮き上がる"], [tl(ROLL0, "C16"), tl(ROLL1, "C16"), "空と海が 360°。Vance は口を閉じたまま手の甲。Sho はハンドルを小さく切る"],
          [tl(ROLL1, "C16"), 5, "着地、ドリフト"]],
  "C17": [[0, tl(W_LAND, "C17"), "追っ手の屋根越し。空中の白い車が向こう岸へ"], [tl(W_LAND, "C17"), tl(W_STOP, "C17"), "着地、ドリフトで 180° 回り、こちらに鼻先を向けて止まる"],
          [tl(W_BLAST, "C17"), 5, "その奥の地面にロケットが着弾、小さめの火球"]],
}
cuts = []
for c in OLD["cuts"]:
    cid = c["id"]; cam = cam_of(cid)
    if cid == "C03":   # the café moved with the table; the tilt follows Sho's new head timing (0.2 s late)
        k0 = cam["keys"][0]; up = cam["keys"][2]["r"]
        cam["keys"] = [dict(k0, t=t_, p=mv(k0["p"]), r=r_) for t_, r_ in ((0, k0["r"]), (3.0, k0["r"]), (3.9, up), (5.0, up), (5.7, k0["r"]))]   # 10/19 C03 v1：頭とカメラが同時に動き、見上げが読めなかった → 頭が上がりきってからカメラ
    if cid == "C06":   # 10/19 0–1.5 秒で車が画面の右端で切れていた（IN 0.6 で白い車が読めない）→ 右へ 20° 振って始め（0.9 まで止める）、発進に付いて 1.8 で元の向きへ
        ks = cam["keys"]; k0 = ks[0]
        pan = [k0["r"][0], k0["r"][1], k0["r"][2] - 20]; cam["keys"] = [dict(k0, t=0, r=pan), dict(k0, t=0.9, r=pan), dict(k0, t=1.8)] + [k for k in ks if k["t"] > 1.8]
    def ry(w):   # 10/19 レンダーと同じ補間（interp.py）
        import interp as _ip
        return _ip.sample(rk, w)["p"]
    def look(frm, to):
        dx, dy, dz = to[0] - frm[0], to[1] - frm[1], to[2] - frm[2]; h = math.hypot(dx, dy)
        return [R(90 + math.degrees(math.atan2(dz, h)), 1), 0, R(math.degrees(math.atan2(-dx, dy)), 1)]
    if cid == "C15":   # 真横：裂け目の手前の縁の横に固定、車を追ってパン（SUV・車・裂け目・真下を抜けるロケットが同じ画に入る）
        cp = [13.0, GAP[0] - 2.0, 41.6]
        cam = {"lens": 22, "parent": None, "keys": [{"t": R(t), "p": cp, "r": look(cp, [-7.5, ry(W["C15"] + t)[1] - 3.0, 40.8])} for t in (0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5)]}
    if cid == "C02":   # 10/19 寄る途中（2.1→3.0）で壁を向いて画面が壁だけになっていた → 途中は運転席の窓を狙い続ける
        ks = cam["keys"]; a_ = next(k for k in ks if abs(k["t"] - 2.1) < 1e-6); b_ = next(k for k in ks if abs(k["t"] - 3.0) < 1e-6)
        WIN = [R(-1.75 + GT_DX), 16.3, 1.15]   # クーペ運転席の窓（世界座標）
        mid = [{"t": t_, "p": p_, "r": look(p_, WIN)} for t_, p_ in ((2.4, [1.7, 8.5, 3.8]), (2.7, [1.5, 13.8, 2.5]))]   # 海側を回り込みながら窓へ
        # 引き（0–1.2）：手前の 4 人（y≈-6.6, -12.1）がカメラの真下に隠れていた → 少し後ろ・上から、より見下ろす
        WIDE = {"p": [3.2, -21.0, 10.5], "r": [56, 0, 2]}
        ks = [dict(k, **WIDE) if k["t"] <= 1.2 else k for k in ks]
        # 窓越しの後半は手元へ寄る（10/19 v2 でマガジンの 3 発が読めなかった）。拳銃は世界で (-2.22, 16.24, 0.94) あたり
        HANDS = [R(-2.22 + GT_DX), 16.24, 0.94]; HEAD_HANDS = [R(-2.2 + GT_DX), 16.15, 1.15]
        ks = [k for k in ks if k["t"] <= 3.0] + [
            {"t": 3.6, "p": [R(-0.8 + GT_DX), 16.7, 1.35], "r": look([R(-0.8 + GT_DX), 16.7, 1.35], HEAD_HANDS)},
            {"t": 4.4, "p": [R(-1.0 + GT_DX), 16.5, 1.2], "r": look([R(-1.0 + GT_DX), 16.5, 1.2], HANDS)},
            {"t": 5.0, "p": [R(-1.05 + GT_DX), 16.45, 1.2], "r": look([R(-1.05 + GT_DX), 16.45, 1.2], HEAD_HANDS)}]
        cam["keys"] = sorted(ks + mid, key=lambda k: k["t"])
    if cid == "C01":   # 着弾でひるむ：目が小さく跳ねて後ろへ引き、戻る（W_HIT_GT）
        k0 = cam["keys"][0]; th = R(W_HIT_GT - W["C01"], 2); rb = list(k0["r"]); pb = list(k0["p"])
        jolt = [dict(k0, t=R(th - 0.02, 2)), dict(k0, t=R(th + 0.08, 2), p=[pb[0], R(pb[1] - 0.06), R(pb[2] + 0.02)], r=[rb[0] + 4, rb[1], rb[2] + 1.5]),
                dict(k0, t=R(th + 0.45, 2))]
        cam["keys"] = [k for k in cam["keys"] if k["t"] < th - 0.05 or k["t"] > th + 0.5] + jolt
        cam["keys"].sort(key=lambda k: k["t"])
    if cid == "C17":   # 追っ手側から：追っ手 SUV の屋根の後ろに載せたカメラ。SUV と一緒に縁で止まり、向こう岸の着地・ドリフト・奥の爆発
        cam = {"lens": 60, "parent": "SUV_chase", "keys": [{"t": 0, "p": [-0.7, -2.6, 3.3], "r": [84, 0, 0]}]}   # 10/19 着地が縁の 31m 先（速さを保つ）になって遠い → 望遠 35→60mm
    beats = BEATS.get(cid, c["beats"])
    e = EDIT[cid]
    cuts.append({"id": cid, "title": c["title"], "start": R(W[cid]), "dur": DUR.get(cid, c["dur"]), "beats": beats, "camera": cam, "view": VIEW.get(cid, {}),
                 "edit": {"in": e[0], "out": e[1], "speed": e[2]}, "lines": LINES.get(cid, []), **({"take": TAKES[cid]} if cid in TAKES else {})})
# 無音はカットに結びつける（煙幕 C09、ランチャー〜回転 C14b–C16）。画面の秒は編集から計算
def screen_at(cid, edge):
    st = 0.0
    for c_ in [c["id"] for c in OLD["cuts"]]:
        i_, o_, sp_ = EDIT[c_]; d_ = (o_ - i_) / sp_
        if c_ == cid: return R(st + (d_ if edge == "end" else 0), 2)
        st += d_
SILENCES = [[screen_at("C09", "start"), screen_at("C09", "end")], [screen_at("C14b", "start"), screen_at("C16", "end")]]

# 10/19 最後のキーの後ろに同じ値のキー（止まっている）を置く：補間（interp.py）が最後のキーで速さ 0 に収める
for o in objs:
    ks = o.get("keys") or []
    if ks and ks[-1]["t"] < WORLD_DUR - 1e-6 and o["type"] in ("car", "man", "prop"):
        ks.append(dict(copy.deepcopy(ks[-1]), t=WORLD_DUR))
out = {"meta": dict(OLD["meta"], version=3, model="world",
                    note="世界（world.objects）を 1 本の時間 W で動かし、各カットは camera＋[start, start+dur] の窓で切り取る（docs/08_world_timeline.md）",
                    physics={"upperRoad": f"登りきり W{CREST_END} から {ACC} m/s² で {VCRUISE} m/s（{VCRUISE*3.6:.0f} km/h）巡航、W{W_KICK}（C14「ええ」）から {ACC2} m/s² で加速、踏み切り {V_TO:.1f} m/s（{V_TO*3.6:.0f} km/h）", "takeoff": W_TO, "gap": GAP,
                             "landing": [R(W_LAND), R(Y_LAND)], "rocket": f"W{W_FIRE} 発射、{V_ROCKET:.1f} m/s、W{W_UNDER} に車の真下、W{W_BLAST:.2f} に y={Y_BLAST:.0f} で着弾"}),
       "set": dict(OLD["set"], upperRoad=dict(OLD["set"]["upperRoad"], gap=GAP), cafe={"p": [CAFE[0], CAFE[1], -45]}),
       "world": {"dur": WORLD_DUR, "objects": objs},
       "edit": {"order": [c["id"] for c in OLD["cuts"]], "endBlack": END_BLACK, "silences": SILENCES, "silenceCuts": [["C09", "C09"], ["C14b", "C16"]],
                "note": "本編の並び（画面順）。各カットは edit.in〜out を speed で再生。silences は音楽の無音区間（画面の秒。silenceCuts のカットから計算）"},
       "cuts": cuts, "dropped": OLD.get("dropped", [])}
json.dump(out, open(os.path.join(P, "blocking.json"), "w"), ensure_ascii=False, indent=1)
print("world dur", WORLD_DUR, "gap", GAP, "take-off y", R(Y_TO, 1), "landing", R(W_LAND, 2), R(Y_LAND, 1), "stop", R(W_STOP, 2), R(Y_STOP, 1))
print("rocket", R(V_ROCKET, 1), "m/s; blast W", R(W_BLAST, 2), "y", R(Y_BLAST, 1))
for c in cuts: print(f"  {c['id']:5} W {c['start']:6.2f}–{c['start'] + c['dur']:6.2f}")
