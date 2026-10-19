"""World vs generation, side by side every 0.5 s at the same cut-local time (CLAUDE.md: 採用した生成は世界と同じ時刻で並べて照合).
usage: python3 gen/compare.py C03 v1   → gen/C03_world_vs_v1.jpg
World frames: previs/out/<cut>_frames/f_NNNN.png (24 fps, frame 1 = t0). Generation: gen/<cut>_<v>.mp4.
"""
import os, subprocess, sys, glob, tempfile
from PIL import Image, ImageDraw
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(H)
cut, ver = sys.argv[1], sys.argv[2]
step = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5
wdir = os.path.join(R, "previs", "out", f"{cut}_frames"); n = len(glob.glob(os.path.join(wdir, "f_*.png")))
vid = os.path.join(H, f"{cut}_{ver}.mp4")
dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", vid]))
tmp = tempfile.mkdtemp()
W, Hh = 180, 320; times = [round(i * step, 2) for i in range(int(min(dur, n / 24) / step) + 1)]
sheet = Image.new("RGB", (len(times) * W, 2 * Hh + 20), "black"); d = ImageDraw.Draw(sheet)
for k, t in enumerate(times):
    f = min(n, int(round(t * 24)) + 1)
    sheet.paste(Image.open(os.path.join(wdir, f"f_{f:04d}.png")).convert("RGB").resize((W, Hh)), (k * W, 20))
    g = os.path.join(tmp, f"g{k}.png")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(min(t, dur - 0.05)), "-i", vid, "-frames:v", "1", g], check=True)
    sheet.paste(Image.open(g).convert("RGB").resize((W, Hh)), (k * W, 20 + Hh))
    d.text((k * W + 4, 4), f"t{t:.1f}", fill="white")
out = os.path.join(H, f"{cut}_world_vs_{ver}.jpg"); sheet.save(out, quality=85); print(out)
