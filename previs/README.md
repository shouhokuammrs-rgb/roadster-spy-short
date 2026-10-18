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

- `editor_src.html` ＋ `blocking.json` → `editor.html`（`build_editor.py`）。下の帯が世界の時間で、各カットの窓が並ぶ。帯をクリックでカットを切替。世界の物体のキーは世界の時刻で入り、そのカットを映す全カットに反映される
- 受け取った JSON は `render_blocking.py -- blocking.json C12 out/` で同じ配置をレンダー → `C12_ref.mp4` を Seedance の参照に、`C12_sheet.jpg` で確認
- 規約：Blender 座標（x 右、y 進行、z 上）、度、Euler XYZ、+Y が車の鼻。人は関節つき（肩・肘のピボット `Man{id}_shL/_elL/_shR/_elR`）。`pose`（aim / lower / lookup / sit / sitlookup / launcher / leanout）で頭・腕・銃の角度が決まり、キー間で補間される。車は hero＝ウェッジ、coupe＝長いボンネット、suv＝低いボンネット＋高いキャビン（部品名：`_body` 不透明、`_cab` ガラス、`_wh` 車輪）。`prop` の `cabin` はロードスターのコクピット（車内カットで Roadster の子に置く）。`hideInPOV` は車でも人でも使える（人は銃だけ残る）
- 削除したカットは `dropped` に移す（エディタには出ない）。C11 がそこにある
- 編集はブラウザに自動保存（その端末のみ）。「このカットを初期に戻す」で blocking.json の値に戻る

## 人物マネキン（rig/）

- `rig/poses.json`：姿勢ライブラリ（stand / aim / lower / lookup / sit / drive / sitlookup / chair / chairlookup / launcher / leanout）。骨盤の移動、背骨・脚の角度、**手首の目標位置と肘の向き（IK）**、銃の位置と角度で書く
- `python3 rig/build_mannequin.py`：骨格（Mixamo 互換のボーン名）とカプセルの体を作り、IK で解いた姿勢を焼き込む → `mannequin.blend`（レンダラ用）、`mannequin.glb`（エディタ用、1 姿勢 1 クリップ）、`poses_baked.json`、`pose_sheet.png`（全姿勢の正面・横。**姿勢を足したら必ず目で確認**）
- 体格：身長 1.78m、座った頭頂 1.14m（車内は人の足元を車の床 −0.08 に置く）、椅子に座った頭頂 1.32m
- レンダラは姿勢をキー間で球面補間、エディタはクリップの重みで混ぜる（同じ値になる）。Sho・Vance は明るいグレー、敵は黒
- エディタの再生成：`python3 build_editor.py`（blocking.json・姿勢・GLB を editor_src.html に埋め込む）

## カメラの操作（エディタ）

「カメラ視点」にすると、画面の上にカメラ操作の帯が出て、9:16 の枠に三分割の線が入る。

| 操作 | 動き |
|---|---|
| ホイール | ズーム（レンズの mm が変わる） |
| Shift＋ホイール／「寄る」「引く」 | カメラごと前後に動く（ドリー。「寄る」「引く」は 0.5m ずつ） |
| ドラッグ | 向き（パン・ティルト） |
| 右ドラッグ／Option＋ドラッグ | 平行移動（1px＝1cm） |
| 16/24/35/50/85 | レンズのプリセット |
| 向ける | 選んだ物（人は胸の高さ）にカメラを向ける |

- 「自動キー」が入っていれば、手を離した時点でその時刻のキーが入る（位置・向き・**レンズ**）。時刻を変えて別のキーを打てば、ズームイン／寄りが動きになる
- レンズはキーごとに持てる（`keys[].lens`）。レンダラも同じ値でズームする

## 世界モデル（blocking.json v3）

- `world.objects`：全員・全物体。キーは **世界の時刻 W**。`life: [W0, W1]` はその間だけ存在（Sho_cafe → Sho_walk → Sho、Vance_gt → Vance_walk → Vance）。`note` は映していない動きの説明
- `cuts[]`：`start`（W）、`dur`、`camera`（lens・parent・keys。キーは **カット内の時刻**）、`view`（`hideInPOV`＝主観で消す物、`noCab`＝ガラスを外して中を見せる車）、`beats`、C15 は `editSpeed`
- レンダー：`render_blocking.py -- blocking.json C12 out/` は、世界を W=start..start+dur で動かし、カット n のカメラで撮る
- 作り直し：`python3 world/build_world.py`（カットごとの旧データ `blocking_v2_percut.json` から世界を組み立て、上の道の追跡を物理で計算）。**以後は blocking.json を直接編集する**（再実行すると上書き）
- 確認：隣り合うカットの境目（前のカットの最後のコマと次の最初のコマ）と、同じ瞬間を映す 2 カットを並べる

## エディタの自動保存

- 本人が編集したカット（カメラ・見え方）と世界を、編集元の版の印つきでブラウザに保存する。Claude 側でそのカットを更新して公開したら新しい版が優先され、以前の編集はカット欄の「以前の編集を書き出す」から取り出せる

## スマホで開いたとき（幅 700px 以下）

- 左のカット一覧は上のプルダウンに、右の詳細（ビート・キー・姿勢）は「詳細」ボタンで開閉。物を選ぶと詳細が自動で開く
- 下のバーは詰め、JSON の書き出し・読み込みと「初期に戻す」は PC だけに出す
- カメラ視点は縦長の画面でも 9:16 の枠（以前は画面の高さいっぱいで縦横比がずれていた）。1 本指ドラッグ＝向き、ピンチ＝ズーム（レンズ）
- PC の表示は変えていない

## 通し（本編のつながり）を確かめる

- `blocking.json` の `edit.order`（画面の並び）と、各カットの `edit`（`in`/`out` はカット内の秒、`speed` は再生速度。C15 は 0.35）、`lines`（台詞・音。字幕の確認用）、`edit.silences`（音楽の無音区間、画面の秒）
- エディタ：「▶ 通しで見る」で、並び順に各カットの使う範囲だけをカメラ視点で続けて再生（字幕・画面の秒・無音の表示つき、最後は黒）。詳細の「本編で使う」で IN/OUT/速さを直せる（「ここを IN」「ここを OUT」で今の時刻を入れる）。下の帯の黄色い線が各カットで使う範囲
- 動画：`python3 render_edit.py` → `out/edit_preview.mp4`（全カットのレンダーをつないだ通し）と `out/edit_strip.jpg`

