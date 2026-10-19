"""10/19 ドアミラーの映り込みをはめ込む（Workbench は鏡を描かない）。

usage: python3 mirror_comp.py C13b
  1. cuts[].camera.mirrorRear（車に付いた後ろ向きのカメラ）で同じカットをもう一度レンダー（out/<cut>_rear/）
  2. 本番のコマ（out/<cut>_frames）でマゼンタの鏡面（view.mirrorKey）を探し、後ろ向きの絵を左右反転してはめ込む
  3. 動画・参照・シートを作り直す
"""
import json, os, sys, subprocess, copy
from PIL import Image
H = os.path.dirname(os.path.abspath(__file__)); os.chdir(H)
CUT = sys.argv[1]
b = json.load(open("blocking.json"))
c = next(x for x in b["cuts"] if x["id"] == CUT)
mr = c["camera"]["mirrorRear"]
rb = copy.deepcopy(b); rc = next(x for x in rb["cuts"] if x["id"] == CUT)
rc["camera"] = {"lens": mr["lens"], "parent": c["camera"]["parent"], "keys": [{"t": 0, "p": mr["p"], "r": mr["r"]}]}
rc["view"] = {k: v for k, v in c["view"].items() if k != "mirrorKey"}
os.makedirs("out/_rear", exist_ok=True)
json.dump(rb, open("out/_rear/b.json", "w"))
subprocess.run(["python3", "render_blocking.py", "--", "out/_rear/b.json", CUT, "out/_rear/"], check=True, stdout=subprocess.DEVNULL)
FR = f"out/{CUT}_frames"; RR = f"out/_rear/{CUT}_frames"
n = 0
for fn in sorted(os.listdir(FR)):
    im = Image.open(os.path.join(FR, fn)).convert("RGB"); px = im.load(); W, Hh = im.size
    mask = Image.new("L", im.size, 0); mp = mask.load(); xs, ys = [], []
    for y in range(Hh):
        for x in range(W):
            r_, g_, b_ = px[x, y]
            if r_ > 35 and b_ > 35 and g_ < 0.5 * min(r_, b_):   # マゼンタ（陰っても色相は残る）
                mp[x, y] = 255; xs.append(x); ys.append(y)
    if xs:
        x0, x1, y0, y1 = min(xs), max(xs) + 1, min(ys), max(ys) + 1
        rear = Image.open(os.path.join(RR, fn)).convert("RGB").transpose(Image.FLIP_LEFT_RIGHT)
        # 鏡の縦横比に合わせて中央を切り出す
        rw, rh = rear.size; ar = (x1 - x0) / max(1, (y1 - y0))
        cw, ch = (rw, int(rw / ar)) if rw / ar <= rh else (int(rh * ar), rh)
        rear = rear.crop(((rw - cw) // 2, (rh - ch) // 2, (rw - cw) // 2 + cw, (rh - ch) // 2 + ch)).resize((x1 - x0, y1 - y0))
        im.paste(rear, (x0, y0), mask.crop((x0, y0, x1, y1))); n += 1
    im.save(os.path.join(FR, fn))
OUT = f"out/{CUT}"
subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", "24", "-i", FR + "/f_%04d.png", "-c:v", "libx264", "-crf", "30", "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT + ".mp4"], check=True)
subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", "24", "-i", FR + "/f_%04d.png", "-vf", "scale=360:640", "-c:v", "libx264", "-crf", "34", "-preset", "veryslow", "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT + "_ref.mp4"], check=True)
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", OUT + ".mp4", "-vf", "fps=2,scale=270:-1,tile=5x2", "-frames:v", "1", OUT + "_sheet.jpg"], check=True)
print("mirror frames", n)
