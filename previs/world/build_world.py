"""Build the single world timeline (blocking.json v3) from the per-cut blocking (blocking_v2_percut.json).

World = every person / vehicle / effect moving in ONE time axis W (seconds), including what no camera sees.
Cut   = a camera + a window [start, start+dur] of world time + per-cut view flags (hideInPOV / noCab).

This script is the migration and the record of how the unseen gaps were filled (docs/08_world_timeline.md).
After it has run once, blocking.json is edited directly (editor or by hand); re-running overwrites it.
usage: python3 world/build_world.py
"""
import json, math, copy, os

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
Y_LAND = GAP[1] + 6                             # 着地は正確：向こうの縁の 6m 先
V_AIR = (Y_LAND - Y_TO) / FLIGHT
W_LAND = W_TO + FLIGHT
ROLL0, ROLL1 = W_TO + 0.2, W_LAND - 0.3         # one barrel roll, 360°
def air(w):
    u = (w - W_TO) / FLIGHT
    y = Y_TO + V_AIR * (w - W_TO); z = 40 + 4 * APEX * u * (1 - u)
    roll = 0 if w <= ROLL0 else (360 if w >= ROLL1 else 360 * (w - ROLL0) / (ROLL1 - ROLL0))
    return y, z, roll
W_UNDER = 63.4                                  # rocket passes under the car (C15)
Y_STOP, YAW_STOP, W_STOP = Y_LAND + 10, 180, W_LAND + 2.3   # drift: ends nose-back, facing the pursuers (rear glass toward the blast = C18)
# pursuer: waits on the upper road, launches when radioed, closes to 8 m for the shots (C13a), drops back, brakes at the near edge
PURSUE = [(46.5, None), (53.0, 20.0), (54.3, 8.0), (57.5, 9.0), (60.0, 13.0), (62.4, 15.0)]   # (W, distance behind the car)
W_SUV_STOP = 65.0; Y_SUV_STOP = GAP[0] - 3
def suv_y(w):
    if w <= 46.5: return -70.0
    if w <= 53.0:  # accelerate from rest to meet the car 20 m behind
        y1 = car_y(53.0) - 20.0; u = (w - 46.5) / 6.5; return -70.0 + (y1 + 70.0) * (u * u * (3 - 2 * u))
    if w <= 62.4:
        for (wa, da), (wb, db) in zip(PURSUE[1:], PURSUE[2:]):
            if wa <= w <= wb: return car_y(w) - (da + (db - da) * (w - wa) / (wb - wa))
    ya = car_y(62.4) - 15.0; u = min(1, (w - 62.4) / (W_SUV_STOP - 62.4))
    return ya + (Y_SUV_STOP - ya) * (1 - (1 - u) ** 2)
W_FIRE = 62.0
ROCKET_Y0 = suv_y(W_FIRE) + 1.6
Y_UNDER = air(W_UNDER)[0]
V_ROCKET = (Y_UNDER - ROCKET_Y0) / (W_UNDER - W_FIRE)
Y_BLAST = Y_STOP + 50
W_BLAST = W_UNDER + (Y_BLAST - Y_UNDER) / V_ROCKET

# cut windows after the wall climb follow the physics
W.update({"C13a": 53.5, "C13b": 57.0, "C14": 59.0, "C14b": W_FIRE - 2.5, "C15": W_TO - 1.6, "C16": W_TO - 0.3,
          "C17": W_LAND - 1.2, "C18": W_STOP + 1.2})
DUR = {"C03": 7.0, "C18": 8.0}   # 台詞の長さから（docs/09_shot_length.md）。他は 5 秒
WORLD_DUR = round(W["C18"] + DUR["C18"] + 0.5, 1)

# ---------------------------------------------------------------- world objects
objs = []
def add(o): objs.append(o); return o

# set pieces that never move
for oid in ("SUV_rear", "SUV_rear2", "SUV_front", "SUV_front2", "VanceGT"):
    o = copy.deepcopy(obj("C02", oid)); o.pop("noCab", None); o.pop("hideInPOV", None); add(o)

# enemies: aiming through the siege and the smoke, lose the car and look up in C12
for m in "ABCDEFGH":
    k12 = obj("C12", m)["keys"]
    add({"id": m, "type": "man", "keys": [dict(k12[0], t=0.0)] + shift(k12, W["C12"])})

# Vance: in the coupe → crosses inside the smoke → in the Roadster
gtV = obj("C02", "Vance")["keys"][0]
add({"id": "Vance_gt", "type": "man", "parent": "VanceGT", "life": [0, 33.0],
     "keys": [dict(gtV, t=0.0), dict(gtV, t=5.0), dict(gtV, t=6.0, pose="sit")]})
add({"id": "Pistol", "type": "prop", "variant": "pistol", "parent": "Vance_gt", "life": [0, 33.0], "keys": obj("C02", "Pistol")["keys"]})
add({"id": "Mag", "type": "prop", "variant": "magazine", "parent": "Vance_gt", "life": [0, 33.0], "keys": obj("C02", "Mag")["keys"]})
add({"id": "Vance_walk", "type": "man", "life": [33.0, 35.6], "note": "［映さない・煙の中］クーペの右ドアから 2m 隣のロードスターへ",
     "keys": [{"t": 33.0, "p": [-1.6, 16.0, 0], "r": [0, 0, -90], "pose": "stand"},
              {"t": 34.6, "p": [-0.4, 16.3, 0], "r": [0, 0, -90], "pose": "stand"},
              {"t": 35.6, "p": [0.1, 16.4, 0], "r": [0, 0, -90], "pose": "stand"}]})
add({"id": "Vance", "type": "man", "parent": "Roadster", "life": [35.6, WORLD_DUR],
     "keys": [{"t": 35.6, "p": [0.35, 0.15, -0.08], "r": [0, 0, 0], "pose": "sit"}]})

# Sho: café → walks to the parked car → drives
CAFE = (14.0, 7.0); dx, dy = CAFE[0] - 10.0, CAFE[1] - (-20.0)      # café moved next to the car (was y=-20)
def mv(p): return [R(p[0] + dx), R(p[1] + dy), p[2]]
C03_SHO = [(0, "chair"), (2.5, "chair"), (3.0, "chairlookup"), (5.3, "chairlookup"), (5.7, "chair")]   # 10/18 コードネームを 007 に（「ダブルオーセブンから」で台詞が 0.6 秒延び、以降を 0.6 秒後ろへ）   # 10/18 台詞に合わせて組み直し：「上の道」で見上げ、「上。」の後で戻り、「了解。」
sk0 = obj("C03", "Sho")["keys"][0]
add({"id": "Sho_cafe", "type": "man", "life": [0, 13.0],
     "keys": [dict(sk0, t=R(t_ + W["C03"]), p=mv(sk0["p"]), pose=po) for t_, po in C03_SHO]})
add({"id": "Chair", "type": "prop", "variant": "chair", "keys": [dict(obj("C03", "Chair")["keys"][0], p=mv(obj("C03", "Chair")["keys"][0]["p"]))]})
add({"id": "Table", "type": "prop", "variant": "table", "keys": [dict(obj("C03", "Table")["keys"][0], p=mv(obj("C03", "Table")["keys"][0]["p"]))]})
add({"id": "Sho_walk", "type": "man", "life": [13.0, 15.5], "note": "［映さない］カフェから 9m 先のロードスターへ（小走り）",
     "keys": [{"t": 13.0, "p": [14.0, 7.3, -45], "r": [0, 0, 16], "pose": "stand"}, {"t": 15.3, "p": [11.9, 14.6, -45], "r": [0, 0, 16], "pose": "stand"}]})
sho_in = {"p": [-0.35, 0.15, -0.08], "r": [0, 0, 0]}
c07 = W["C07"]
add({"id": "Sho", "type": "man", "parent": "Roadster", "life": [15.5, WORLD_DUR],
     "keys": [dict(sho_in, t=15.5, pose="drive"), dict(sho_in, t=c07 + 2.2, pose="drive"), dict(sho_in, t=c07 + 3.0, pose="turnright"),
              dict(sho_in, t=W["C09"] + 0.2, pose="turnright"), dict(sho_in, t=W["C09"] + 0.8, pose="drive")]})

# Roadster
rk = []
rk.append({"t": 0.0, "p": [12.0, 16.5, -45], "r": [0, 0, 90]})                       # parked on the quay, facing the cliff
rk += shift(obj("C06", "Roadster")["keys"], W["C06"], until=2.8)                      # launch, mount the cliff
rk += shift(OLD["tracks"]["arrival_roadster"]["keys"], W["C06b"])                     # climb out, hover, land by the coupe
c10 = obj("C10", "Roadster")["keys"]
rk.append({"t": W["C10"], "p": [1.2, 16.5, 0], "r": [0, 0, 180]})                    # parked until Vance is in
for t_, p_, r_ in ((0.8, [0.9, 13.5, 0], 180), (1.6, [-0.2, 8.5, 0], 160), (2.2, [-1.5, 5.0, 0], 110)):
    rk.append({"t": R(W["C10"] + t_), "p": p_, "r": [0, 0, r_]})
rk += shift([k for k in c10 if k["t"] >= 2.5], W["C10"], until=3.3)                   # ladder-lean onto the wall
rk += shift(obj("C12", "Roadster")["keys"], W["C12"])                                 # climbing (C12)
v = 6.0; zc = 28.0; w_top = W["C12"] + 5 + (37.6 - zc) / v
rk.append({"t": R(w_top), "p": [-3.34, 4.0, 37.6], "r": [90, 0, 90]})                # nose reaches the top
for dt, p_, r_ in ((0.4, [-3.9, 4.0, 39.3], [55, 0, 90]), (0.8, [-5.0, 4.0, 40.0], [15, 0, 90]), (1.2, [-6.0, 4.2, 40.0], [0, 0, 90]),
                   (2.2, [-7.5, 6.0, 40.0], [0, 0, 30])):
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
add({"id": "Roadster", "type": "car", "variant": "hero", "keys": rk})
add({"id": "Cabin", "type": "prop", "variant": "cabin", "parent": "Roadster", "keys": [{"t": 0, "p": [0, 0, 0], "r": [0, 0, 0]}]})
add({"id": "MirrorR", "type": "prop", "variant": "mirror", "parent": "Roadster", "keys": obj("C13b", "MirrorR")["keys"]})
add({"id": "DoorR", "type": "door", "parent": "Roadster",
     "keys": [{"t": 0, "a": 0}, {"t": c07 + 1.0, "a": 0}, {"t": c07 + 2.2, "a": 75}, {"t": 35.0, "a": 75}, {"t": 35.8, "a": 0}]})
jk = [{"t": 0, "s": 0}] + shift(obj("C06", "Jets")["keys"], W["C06"], until=2.8) + shift(OLD["tracks"]["arrival_jets"]["keys"], W["C06b"])
jk += [{"t": 29.0, "s": 0}, {"t": 32.5, "s": 0}, {"t": 32.7, "s": 3}, {"t": 35.0, "s": 3}, {"t": 35.6, "s": 0},   # smoke screen
       {"t": R(W_TO - 0.2), "s": 0}, {"t": W_TO, "s": 3}, {"t": R(W_LAND), "s": 1.5}, {"t": R(W_LAND + 0.4), "s": 0}]
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
add({"id": "Shooter", "type": "man", "parent": "SUV_chase", "life": [52.0, 60.0], "keys": [dict(obj("C13a", "Shooter")["keys"][0], t=52.0)]})
add({"id": "Launcher", "type": "man", "parent": "SUV_chase", "life": [58.0, 64.5], "keys": [dict(obj("C14b", "Shooter")["keys"][0], t=58.0)]})
add({"id": "Flash", "type": "fx", "variant": "fire", "parent": "SUV_chase",
     "keys": [{"t": 0, "p": [1.1, 0.6, 1.9], "s": 0}, {"t": W_FIRE, "p": [1.1, 0.6, 1.9], "s": 0}, {"t": R(W_FIRE + 0.2), "p": [1.1, 0.6, 1.9], "s": 3}, {"t": R(W_FIRE + 0.6), "p": [1.1, 0.6, 1.9], "s": 0}]})
SHOTS = (1.0, 1.4, 1.8)   # C13a の 3 発。10/18 間隔 1.3 → 0.4 秒（拳銃の連射。カットが 2 秒で収まる）
spk = [{"t": 0, "p": [0, -2.4, 1.0], "s": 0}]
for s_, x_ in zip(SHOTS, (0, 0.3, -0.2)):
    w_ = W["C13a"] + s_; spk += [{"t": R(w_ - 0.05), "p": [x_, -2.4, 1.0], "s": 0}, {"t": R(w_), "p": [x_, -2.4, 1.0], "s": 0.5}, {"t": R(w_ + 0.15), "p": [x_, -2.4, 1.0], "s": 0}]
add({"id": "Spark", "type": "fx", "variant": "spark", "parent": "Roadster", "keys": spk})
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
# 台詞（声＝voice/lines.json の仮の声の長さ）と効果音のメモ。[t, 表示, 長さ, 声 id, 英語字幕]
SFX = {"C01": [[2.0, "（キン）"], [3.4, "（プシュゥッ）"]], "C02": [[0.3, "数分前"]], "C06b": [[2.0, "（頂点で無音）"]], "C09": [[0.0, "（音が消える）"]],
       "C14b": [[2.5, "（ボシュッ）"]], "C16": [[1.2, "（息だけ）"]], "C17": [[1.2, "（ドン）"], [1.6, "（キーッ）"], [2.7, "（遠くでバァン）"]]}
LINES = {}
for cid in EDIT:
    ls = [[t_, txt, 1.2, None, None] for t_, txt in SFX.get(cid, [])]
    for lid, t_ in DER["lines"].get(cid, []):
        v = VOICE[lid]; ls.append([t_, f"{v['speaker']}「{v['ja']}」", v["dur"], lid, v["en"]])
    LINES[cid] = sorted(ls, key=lambda l: l[0])
BEATS = {   # 上の道のカットは世界の物理から時刻を出す（数字を手で書かない）
  "C03": [[0, 0.8, "Sho の後ろ姿、カップ。無線が光る"], [0.8, 4.7, "Chief「ダブルオーセブンから。上の道。あれを使いなさい。」"], [2.5, 3.0, "「上の道」で Sho の頭が上を向く。カメラは 0.2 秒遅れて 2.7→3.7 秒でティルトアップ。崖のはるか上に銃火"],
          [4.9, 5.2, "Sho「上。」"], [5.3, 5.7, "頭が戻る。カメラは 5.5→6.2 秒で戻る"], [5.8, 6.4, "「了解。」"], [6.2, 7.0, "手が止まってからカップを置く"]],
  "C13a": [[0, 1.0, "上の道。SUV の右（助手席）窓から男が上半身を出し、前の白い車へ構える"], [1.0, 2.0, "3 発（0.4 秒間隔）。白い車の尻で火花、ガラスは無傷"], [2.0, 5, "構えたまま追う"]],
  "C13b": [[0, 1.5, "右のサイドミラーに SUV。「しつこいな」"], [1.5, 2.5, "前を向く"], [2.5, 5, "橋が落ちている"]],
  "C18": [[0, 0.5, "リアガラスの向こうに遠い火球。前を向いたまま"], [0.5, 3.4, "Vance「私のには、射出座席がついていた」"], [3.4, 4.45, "間（1秒）"],
          [4.45, 6.6, "Sho、横目で「これは、車ごと飛びますよ」"], [6.6, 7.1, "Vance の口の端が 0.5mm 上がる"], [7.1, 8, "黒へ"]],
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
        cam["keys"] = [dict(k0, t=t_, p=mv(k0["p"]), r=r_) for t_, r_ in ((0, k0["r"]), (2.7, k0["r"]), (3.7, up), (5.5, up), (6.2, k0["r"]))]
    def ry(w):
        ks = rk
        if w <= ks[0]["t"]: return ks[0]["p"]
        for a_, b_ in zip(ks, ks[1:]):
            if a_["t"] <= w <= b_["t"]: u = (w - a_["t"]) / (b_["t"] - a_["t"]); return [x + (y - x) * u for x, y in zip(a_["p"], b_["p"])]
        return ks[-1]["p"]
    def look(frm, to):
        dx, dy, dz = to[0] - frm[0], to[1] - frm[1], to[2] - frm[2]; h = math.hypot(dx, dy)
        return [R(90 + math.degrees(math.atan2(dz, h)), 1), 0, R(math.degrees(math.atan2(-dx, dy)), 1)]
    if cid == "C15":   # 真横：裂け目の手前の縁の横に固定、車を追ってパン（SUV・車・裂け目・真下を抜けるロケットが同じ画に入る）
        cp = [13.0, GAP[0] - 2.0, 41.6]
        cam = {"lens": 22, "parent": None, "keys": [{"t": R(t), "p": cp, "r": look(cp, [-7.5, ry(W["C15"] + t)[1] - 3.0, 40.8])} for t in (0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5)]}
    if cid == "C17":   # 追っ手側から：追っ手 SUV の屋根の後ろに載せたカメラ。SUV と一緒に縁で止まり、向こう岸の着地・ドリフト・奥の爆発
        cam = {"lens": 35, "parent": "SUV_chase", "keys": [{"t": 0, "p": [-0.7, -2.6, 3.3], "r": [83, 0, 0]}]}
    beats = BEATS.get(cid, c["beats"])
    e = EDIT[cid]
    cuts.append({"id": cid, "title": c["title"], "start": R(W[cid]), "dur": DUR.get(cid, c["dur"]), "beats": beats, "camera": cam, "view": VIEW.get(cid, {}),
                 "edit": {"in": e[0], "out": e[1], "speed": e[2]}, "lines": LINES.get(cid, [])})
# 無音はカットに結びつける（煙幕 C09、ランチャー〜回転 C14b–C16）。画面の秒は編集から計算
def screen_at(cid, edge):
    st = 0.0
    for c_ in [c["id"] for c in OLD["cuts"]]:
        i_, o_, sp_ = EDIT[c_]; d_ = (o_ - i_) / sp_
        if c_ == cid: return R(st + (d_ if edge == "end" else 0), 2)
        st += d_
SILENCES = [[screen_at("C09", "start"), screen_at("C09", "end")], [screen_at("C14b", "start"), screen_at("C16", "end")]]

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
