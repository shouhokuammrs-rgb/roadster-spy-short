"""Derive every cut's used range (IN/OUT) from rules, instead of by feel (docs/09_shot_length.md).

  IN  = (first essential event or line) - LEAD     LEAD = time to read the frame before the event matters
  OUT = max(last essential event + TAIL, last line end + PAD)
  screen length = (OUT - IN) / speed

LEAD / TAIL (screen seconds; the evidence is in docs/09_shot_length.md):
  new  0.6  new place or new viewpoint: a category decision on a picture takes ~0.6 s (Potter 2012)
  known 0.4 viewpoint/space already seen
  cont 0.25 continues the previous shot's action: one fixation (~0.25 s)
  payoff 0.5  the shot's point must be registered: ~0.5 s of uninterrupted processing (Potter 2012)
  flow   0.1  the next shot continues the motion (cut on action), so no hold
  PAD    0.15 after the last syllable (never clip a line)
Line lengths come from voice/lines.json (temp voice; re-run with the real voices).
Event times are cut-local seconds measured in the greybox (out/events.json, contact sheets) or set by the staging below.
usage: python3 shot_length.py   → world/edit_derived.json + prints the table
"""
import json, os
H = os.path.dirname(os.path.abspath(__file__))
VOICE = json.load(open(os.path.join(H, "voice", "lines.json")))["lines"]
LEAD = {"new": 0.6, "known": 0.4, "cont": 0.25}; TAIL = {"payoff": 0.5, "flow": 0.1}; PAD = 0.15

# cut: lead class, essential span [start, end] (cut-local), what must be seen, tail class, lines [(voice id, start)], speed, note
SPEC = {
 "C01": ("cont", [0.6, 4.7], "外からの着弾で大きなひび(0.6)→ひるむ→顔が右へ→白い車が鼻先から降りてくる→白が窓を埋めきる(生成 v4 で実測)", "flow", [], 1,
         "冒頭は掴み。前方の銃火は C02 で見せ直すので 1 注視ぶんだけ。白で切る＝次への転換"),
 "C02": ("new", [1.2, 4.5], "8人と4台の包囲(寄り始め 1.2 までに読む)→手元の真鍮の弾(生成 v3 で 4.4 から)", "payoff", [("C02", 0.4)], 1,
         "台詞の「あと3発」を弾が見えている間に終える"),
 "C03": ("new", [0.8, 6.0], "無線→「The upper road」で見上げる→「Up there.」→戻る→「On it.」→カップを置く", "flow", [("C03a", 0.8), ("C03b", 4.0), ("C03c", 5.3)], 1,
         "台詞が主役のカット。見上げは「上の道」で起きる（台詞に合わせて組み直した）"),
 "C06": ("known", [1.0, 3.25], "発進→壁に乗って垂直(3.25)", "flow", [], 1, "車は C03 の画面にも停まっているので known"),
 "C06b": ("new", [1.0, 3.2], "鼻先が手すりの上に出る→頂点で一拍(2.0–3.2)", "flow", [], 1, "降りる動きは C01 で見せ済み"),
 "C07": ("cont", [1.0, 3.25], "ガルウイングが開く→Sho が振り向く→顔に寄る", "flow", [("C07", 3.1)], 1, "C01 と同じ場所の Vance 主観なので cont"),
 "C09": ("new", [0.6, 2.75], "白が道をこちらへ流れ、視界を埋め、盲撃ち", "payoff", [], 1, "白で埋まる＝このカットの要点"),
 "C10": ("new", [0.8, 4.5], "一言→間（1秒・台本）→壁に乗って地平線が回る→Vance の目", "flow", [("C10", 0.8)], 1, "車内ツーショットの初出"),
 "C12": ("known", [1.5, 3.5], "銃を下ろす→A が見上げる→B が続く", "payoff", [], 1, "見上げが「順に」連なるのが要点。2人目で伝わる"),
 "C13a": ("new", [1.4, 2.0], "3発→尻で火花、ガラスは無傷(生成 v1 で実測：1 発目が 1.4)", "payoff", [], 1, "上の道の初出。撃つ間隔を 1.3→0.4 秒に詰めた（拳銃の連射）"),
 "C13b": ("new", [0.8, 2.5], "ミラーの SUV（「しつこいな」）→前を向く→橋がない", "payoff", [("C13b", 0.8)], 1, "ミラーの中は小さく込み入る＝読むのに要る"),
 "C14": ("known", [1.0, 2.9], "「...The bridge is out.」「Yes.」→アクセル、シートに押し付けられる", "flow", [("C14a", 1.0), ("C14b", 2.25)], 1, "C10 と同じ車内"),
 "C14b": ("new", [2.4, 3.2], "筒の口がこちら→静止→発射の炎(生成 v1 で実測：発射 2.9、炎 3.0–3.2)", "flow", [], 1, "炎で切る"),
 "C15": ("new", [1.75, 2.45], "左に SUV・中央に浮いた車・右に裂け目、ロケットが真下を抜ける", "flow", [], 0.35, "スロー。ロールの続きは C16 がそのまま受ける（巻き戻さない）"),
 "C16": ("cont", [1.2, 2.4], "空と海が回る（C15 の続きから 360° まで）", "flow", [], 1, "C15 の終わり W63.7 から続ける"),
 "C17": ("new", [1.2, 2.9], "着地→ドリフト→奥で火球が上がる", "payoff", [], 1, ""),
 "C18": ("known", [0.5, 5.8], "「Mine had an ejector seat.」→間（1秒・台本）→「This one ejects the whole car.」→口の端", "payoff", [("C18a", 0.5), ("C18b", 3.55)], 1, "口の端が上がって黒"),
}

rows, edit = [], {}
for cid, (lead, (e0, e1), what, tail, lines, spd, note) in SPEC.items():
    first = min([e0] + [s for _, s in lines]); line_end = max([0] + [s + VOICE[l]["dur"] for l, s in lines])
    i = max(0.0, first - LEAD[lead] * spd)
    o = max(e1 + TAIL[tail] * spd, line_end + PAD)
    bound = "台詞" if lines and line_end + PAD >= e1 - 0.6 else "動き"   # 要点が台詞で終わる（動きを台詞に合わせて組んだ）なら台詞
    edit[cid] = [round(i, 2), round(o, 2), spd]
    rows.append((cid, lead, e0, e1, tail, sum(VOICE[l]["dur"] for l, _ in lines), round(i, 2), round(o, 2), round((o - i) / spd, 2), what, note, bound))
json.dump({"rule": {"lead": LEAD, "tail": TAIL, "pad": PAD}, "edit": edit,
           "lines": {cid: [[l, s] for l, s in SPEC[cid][4]] for cid in SPEC}}, open(os.path.join(H, "world", "edit_derived.json"), "w"), ensure_ascii=False, indent=1)
import sys
if "--md" in sys.argv:   # docs/09 の表
    print("| カット | 要点（これが見えれば終わり） | 読む時間 | 要点の区間（秒） | 後ろ | 声 | IN–OUT | 長さ | 決めているもの | メモ |\n|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r[0]} | {r[9]} | {r[1]} {LEAD[r[1]]} | {r[2]}–{r[3]} | {r[4]} {TAIL[r[4]]} | {r[5]:.2f} | {r[6]}–{r[7]}{' ×'+str(SPEC[r[0]][5]) if SPEC[r[0]][5] != 1 else ''} | **{r[8]:.2f}** | {r[11]} | {r[10]} |")
tot = 0
for r in rows:
    tot += r[8]; print(f"{r[0]:5} lead {r[1]:5} ev {r[2]:4}-{r[3]:4} tail {r[4]:6} voice {r[5]:4.2f}s → IN {r[6]:4} OUT {r[7]:4} = {r[8]:4.2f}s  ({r[11]})")
print(f"total {tot:.2f}s (+ black)")
