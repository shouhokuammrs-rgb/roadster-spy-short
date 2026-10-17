# previs — Blender グレーボックス

`pip install bpy` した Python から直接レンダーする（Blender 本体不要。この環境では Blender 5.2 LTS）。

```
python3 -c "import sys; sys.argv=['x','--','OUT']; exec(open('c12_previs.py').read())"
ffmpeg -framerate 24 -i OUT_frames/f_%04d.png -c:v libx264 -pix_fmt yuv420p OUT.mp4
```

- 座標系：道路 +Y、岩壁 x=−4、ガードレール x=+3、海はその先。単位 m
- Workbench レンダー、540×960、24fps、5 秒 ≈ 1 分
- `OUT_top.png` に上から見た配置が出る（`c12_v1_map.png` はラベル付き）
- 直すのは数値だけ：`men_pos`、`look_up_t`、カメラ位置／ティルト、車の keyframe

C12 の配置（v1）：
- 後ろの SUV y=−5（道を横断）＝盾。男 A〜D はその手前（カメラ側）y≈−6.7
- Vance のクーペ (−2.8, 10)、空いた路面 (0.2, 10)
- ロードスター：壁 x=−4, y=11.5、z=5→25 m（2.5→5 秒）
- カメラ (0.8, −16, 2.0)、24mm、2.5 秒から +28° までティルト
