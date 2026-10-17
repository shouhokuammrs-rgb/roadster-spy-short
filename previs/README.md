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

## 3D で確認する（インタラクティブ）

- `viewer.html`：Three.js ビューア（GLB を base64 で埋め込み済み）。ドラッグで回転、スライダーで時間、「カメラ視点」で本番の 9:16 画角、「真上」で配置図。アーティファクトとして公開済み（更新は同じファイルを再公開）
- `c12_v1.blend`：Blender で開ける本体。オブジェクト名＝ドキュメントの名前（ManA〜D, SUV_rear, VanceGT, Hero_root, Cam）
- `c12_v1.glb`：glTF 書き出し（他ツール用）

スクリプトを直したら `PREVIS_RENDER=0` で再実行 → glb/blend が更新される → viewer.html の base64 を差し替えて再公開。

## ブロッキングエディタ（本人が動かす用）

- `editor_src.html` ＋ `blocking.json` → `editor.html`（JSON を埋め込んで公開）。全 18 カットの配置・動き・カメラを 3D でドラッグ編集し、「JSON を書き出す」で受け渡す
- 受け取った JSON は `render_blocking.py -- blocking.json C12 out/` で同じ配置をレンダー → `C12_ref.mp4` を Seedance の参照に、`C12_sheet.jpg` で確認
- 規約：Blender 座標（x 右、y 進行、z 上）、度、Euler XYZ、+Y が車の鼻。人は関節つき（肩・肘のピボット `Man{id}_shL/_elL/_shR/_elR`）。`pose`（aim / lower / lookup / sit / sitlookup / launcher / leanout）で頭・腕・銃の角度が決まり、キー間で補間される。車は hero＝ウェッジ、coupe＝長いボンネット、suv＝低いボンネット＋高いキャビン（部品名：`_body` 不透明、`_cab` ガラス、`_wh` 車輪）。`prop` の `cabin` はロードスターのコクピット（車内カットで Roadster の子に置く）。`hideInPOV` は車でも人でも使える（人は銃だけ残る）
- 削除したカットは `dropped` に移す（エディタには出ない）。C11 がそこにある
- 編集はブラウザに自動保存（その端末のみ）。「このカットを初期に戻す」で blocking.json の値に戻る
