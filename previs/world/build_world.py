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
CREST_END = 50.0; Y0 = 8.5; V0 = 4.0; ACC = 3.0; VMAX = 20.0
T_ACC = (VMAX - V0) / ACC                       # 5.33 s
def car_y(w):                                   # on the upper road, before take-off
    t = w - CREST_END
    if t <= T_ACC: return Y0 + V0 * t + 0.5 * ACC * t * t
    return Y0 + V0 * T_ACC + 0.5 * ACC * T_ACC ** 2 + VMAX * (t - T_ACC)
W_TO = 62.8                                     # take-off (jets on)
Y_TO = car_y(W_TO)
GAP = [round(Y_TO + 5), round(Y_TO + 5) + 15]   # the fallen bridge
FLIGHT = 2.4; V_AIR = 16.0; APEX = 4.0
W_LAND = W_TO + FLIGHT; Y_LAND = Y_TO + V_AIR * FLIGHT
ROLL0, ROLL1 = W_TO + 0.2, W_LAND - 0.3         # one barrel roll, 360°
def air(w):
    u = (w - W_TO) / FLIGHT
    y = Y_TO + V_AIR * (w - W_TO); z = 40 + 4 * APEX * u * (1 - u)
    roll = 0 if w <= ROLL0 else (360 if w >= ROLL1 else 360 * (w - ROLL0) / (ROLL1 - ROLL0))
    return y, z, roll
W_UNDER = 63.4                                  # rocket passes under the car (C15)
Y_STOP, YAW_STOP, W_STOP = Y_LAND + 12, 150, W_LAND + 2.3   # drift: ends facing back toward the gap (rear glass toward the blast, C18)
# pursuer: waits on the upper road, launches when radioed, closes to ~14 m, brakes at the near edge
PURSUE = [(46.5, None), (53.0, 28.0), (54.5, 14.0), (62.4, 16.0)]   # (W, distance behind the car)
W_SUV_STOP = 65.0; Y_SUV_STOP = GAP[0] - 3
def suv_y(w):
    if w <= 46.5: return -70.0
    if w <= 53.0:  # accelerate from rest to meet the car 28 m behind
        y1 = car_y(53.0) - 28.0; u = (w - 46.5) / 6.5; return -70.0 + (y1 + 70.0) * (u * u * (3 - 2 * u))
    if w <= 62.4:
        for (wa, da), (wb, db) in zip(PURSUE[1:], PURSUE[2:]):
            if wa <= w <= wb: return car_y(w) - (da + (db - da) * (w - wa) / (wb - wa))
    ya = car_y(62.4) - 16.0; u = min(1, (w - 62.4) / (W_SUV_STOP - 62.4))
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
WORLD_DUR = round(W["C18"] + 5.5, 1)

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
add({"id": "Sho_cafe", "type": "man", "life": [0, 11.5],
     "keys": [dict(k, t=R(k["t"] + W["C03"]), p=mv(k["p"])) for k in obj("C03", "Sho")["keys"]]})
add({"id": "Chair", "type": "prop", "variant": "chair", "keys": [dict(obj("C03", "Chair")["keys"][0], p=mv(obj("C03", "Chair")["keys"][0]["p"]))]})
add({"id": "Table", "type": "prop", "variant": "table", "keys": [dict(obj("C03", "Table")["keys"][0], p=mv(obj("C03", "Table")["keys"][0]["p"]))]})
add({"id": "Sho_walk", "type": "man", "life": [11.5, 15.5], "note": "［映さない］カフェから 9m 先のロードスターへ",
     "keys": [{"t": 11.5, "p": [14.0, 7.3, -45], "r": [0, 0, 16], "pose": "stand"}, {"t": 15.3, "p": [11.9, 14.6, -45], "r": [0, 0, 16], "pose": "stand"}]})
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
    rk.append({"t": R(W_LAND + u * (W_STOP - W_LAND)), "p": [-7.5, R(Y_LAND + e * (Y_STOP - Y_LAND)), 40.0], "r": [0, 0, R(YAW_STOP * e, 1)]})
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
sp = obj("C13a", "Spark")["keys"]
add({"id": "Spark", "type": "fx", "variant": "spark", "parent": "Roadster", "keys": [dict(sp[0], t=0)] + shift(sp, W["C13a"])})
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
cuts = []
for c in OLD["cuts"]:
    cid = c["id"]; cam = cam_of(cid)
    if cid == "C03":   # the café moved with the table
        cam["keys"] = [dict(k, p=mv(k["p"])) for k in cam["keys"]]
    if cid == "C15":   # side-on tracking shot: keep level with the car (sample the car's world keys, incl. landing)
        def ry(w):
            ks = rk
            if w <= ks[0]["t"]: return ks[0]["p"][1]
            for a, b in zip(ks, ks[1:]):
                if a["t"] <= w <= b["t"]: return a["p"][1] + (b["p"][1] - a["p"][1]) * (w - a["t"]) / (b["t"] - a["t"])
            return ks[-1]["p"][1]
        cam["keys"] = [{"t": R(t), "p": [4.0, R(ry(W["C15"] + t)), 41.8], "r": [84, 0, 90]} for t in (0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5)]
    if cid == "C17":   # from the pursuer's side of the gap
        cam["keys"] = [{"t": 0, "p": [-7.5, GAP[0] - 2, 41.2], "r": [88, 0, 0]}]
    cuts.append({"id": cid, "title": c["title"], "start": R(W[cid]), "dur": c["dur"], "beats": c["beats"], "camera": cam, "view": VIEW.get(cid, {})})
cuts[[x["id"] for x in cuts].index("C15")]["editSpeed"] = 0.3   # slowed in the edit (reference stays real-time)

out = {"meta": dict(OLD["meta"], version=3, model="world",
                    note="世界（world.objects）を 1 本の時間 W で動かし、各カットは camera＋[start, start+dur] の窓で切り取る（docs/08_world_timeline.md）",
                    physics={"upperRoad": f"登りきり W{CREST_END} から {ACC} m/s² で {VMAX} m/s（{VMAX*3.6:.0f} km/h）", "takeoff": W_TO, "gap": GAP,
                             "landing": [R(W_LAND), R(Y_LAND)], "rocket": f"W{W_FIRE} 発射、{V_ROCKET:.1f} m/s、W{W_UNDER} に車の真下、W{W_BLAST:.2f} に y={Y_BLAST:.0f} で着弾"}),
       "set": dict(OLD["set"], upperRoad=dict(OLD["set"]["upperRoad"], gap=GAP), cafe={"p": [CAFE[0], CAFE[1], -45]}),
       "world": {"dur": WORLD_DUR, "objects": objs},
       "cuts": cuts, "dropped": OLD.get("dropped", [])}
json.dump(out, open(os.path.join(P, "blocking.json"), "w"), ensure_ascii=False, indent=1)
print("world dur", WORLD_DUR, "gap", GAP, "take-off y", R(Y_TO, 1), "landing", R(W_LAND, 2), R(Y_LAND, 1), "stop", R(W_STOP, 2), R(Y_STOP, 1))
print("rocket", R(V_ROCKET, 1), "m/s; blast W", R(W_BLAST, 2), "y", R(Y_BLAST, 1))
for c in cuts: print(f"  {c['id']:5} W {c['start']:6.2f}–{c['start'] + c['dur']:6.2f}")
