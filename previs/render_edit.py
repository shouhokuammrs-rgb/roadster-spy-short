"""Assemble the whole film from the rendered greybox cuts, following the edit (blocking.json → edit.order, cuts[].edit, cuts[].lines).
usage: python3 render_edit.py            (needs out/<CUT>_frames from render_blocking.py for every cut)
writes out/edit_preview.mp4 (540x960, 24 fps) and out/edit_strip.jpg (one frame per cut)
Each frame shows: the cut id, screen time, a silence marker, and the lines (English subtitle + Japanese) at their times.
The temp voice (voice/temp_voice.py → out/voice/<id>.wav) is mixed in at each line's screen time, so the timing can be heard.
"""
import json, os, subprocess, shutil, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont

H = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(H, "out")
D = json.load(open(os.path.join(H, "blocking.json")))
CUTS = {c["id"]: c for c in D["cuts"]}; FPS = 24
FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
if not os.path.exists(FONT): FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
f_sub, f_lab, f_ja = ImageFont.truetype(FONT, 24), ImageFont.truetype(FONT, 18), ImageFont.truetype(FONT, 17)
SR = 48000; voice = []   # (screen time, wav path)
def shown(l): return max(l[2] + 0.3, 0.83) if len(l) > 2 else 1.8   # 字幕の表示時間：声＋0.3 秒、最短 5/6 秒

def wrap(text, font, width, draw):
    lines, cur = [], ""
    for ch in text:
        if draw.textlength(cur + ch, font=font) > width: lines.append(cur); cur = ch
        else: cur += ch
    return lines + [cur] if cur else lines

tmp = os.path.join(OUT, "_edit_frames"); shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
n = 0; screen = 0.0; strip = []
silences = D["edit"].get("silences", [])
for cid in D["edit"]["order"]:
    c = CUTS[cid]; e = c["edit"]; src = os.path.join(OUT, f"{cid}_frames")
    if c.get("take"):   # 採用した生成があれば、それを 24fps・540x960 のコマにして使う
        src = os.path.join(OUT, f"_take_{cid}"); shutil.rmtree(src, ignore_errors=True); os.makedirs(src)
        subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(os.path.dirname(H), c["take"]), "-vf", "fps=24,scale=540:960", os.path.join(src, "f_%04d.png")], check=True)
    frames = sorted(os.listdir(src)); count = round((e["out"] - e["in"]) / e["speed"] * FPS)
    for l in c.get("lines", []):
        if len(l) > 3 and l[3] and e["in"] - 0.01 <= l[0] < e["out"]: voice.append((screen + (l[0] - e["in"]) / e["speed"], os.path.join(OUT, "voice", l[3] + ".wav")))
    for k in range(count):
        t = e["in"] + k / FPS * e["speed"]                       # time inside the cut
        im = Image.open(os.path.join(src, frames[min(len(frames) - 1, int(round(t * FPS)))])).convert("RGB")
        dr = ImageDraw.Draw(im); W_, H_ = im.size; st = screen + k / FPS
        lab = f"{cid}{' 生成' if c.get('take') else ''}  {st:4.1f}s" + ("  ×%.2f" % e["speed"] if e["speed"] != 1 else "")
        if any(a <= st < b for a, b in silences): lab += "  無音"
        dr.rectangle([0, 0, W_, 30], fill=(0, 0, 0)); dr.text((10, 4), lab, font=f_lab, fill=(242, 183, 5))
        cur = [l for l in c.get("lines", []) if l[0] <= t < l[0] + shown(l) and len(l) > 4 and l[4]]   # 字幕は英語の台詞だけ（「（頂点で無音）」などの演出メモは出さない）
        if cur:
            l = cur[-1]; en = l[4] if len(l) > 4 and l[4] else None
            rows = wrap(en, f_sub, W_ - 40, dr); y = H_ - 70 - 32 * len(rows)
            for r in rows:
                w = dr.textlength(r, font=f_sub); x = (W_ - w) / 2
                dr.text((x, y), r, font=f_sub, fill=(255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0)); y += 32
        im.save(os.path.join(tmp, f"f_{n:05d}.png")); n += 1
        if k == count // 2: strip.append(im.resize((W_ // 3, H_ // 3)))
    screen += count / FPS
for k in range(round(D["edit"].get("endBlack", 0) * FPS)):     # 黒で終わる
    Image.new("RGB", (540, 960), (0, 0, 0)).save(os.path.join(tmp, f"f_{n:05d}.png")); n += 1
mix = np.zeros(int(n / FPS * SR) + SR, np.float32)            # 仮の声のトラック
for st, path in voice:
    with wave.open(path) as w: a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32)
    i = int(st * SR); mix[i:i + len(a)] += a[:len(mix) - i]
wav = os.path.join(tmp, "voice.wav")
with wave.open(wav, "wb") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(np.clip(mix, -32767, 32767).astype(np.int16).tobytes())
mp4 = os.path.join(OUT, "edit_preview.mp4")
subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", str(FPS), "-i", os.path.join(tmp, "f_%05d.png"), "-i", wav,
                "-c:v", "libx264", "-crf", "26", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-shortest", "-movflags", "+faststart", mp4], check=True)
cols = 9; w, h = strip[0].size; sheet = Image.new("RGB", (w * cols, h * ((len(strip) + cols - 1) // cols)), "white")
for i, im in enumerate(strip): sheet.paste(im, ((i % cols) * w, (i // cols) * h))
sheet.save(os.path.join(OUT, "edit_strip.jpg"), quality=85)
shutil.rmtree(tmp)
print("DONE", mp4, f"{n / FPS:.1f}s")
