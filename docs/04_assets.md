# 04 アセット（Higgsfield エレメント）

アカウント：theaonea1。エレメントは画像ビューア「…」→「エレメントを作成」→「画像エレメント」→名前・説明・カテゴリー。
プロンプトでは `@名前` と打って候補から選ぶ（**候補が正しいか送信前に確認**）。

## 現役

| エレメント | 種別 | 内容 | 画像 |
|---|---|---|---|
| @Sho | キャラクター | 日本人の若い男性、AIコンサルタント風。マット版を採用 | （Higgsfield 内） |
| @Vance | キャラクター | ベテラン諜報員、ダークスーツ | （Higgsfield 内） |
| @RoadsterW4 | 小道具 | ヒーローカー。4 面シート（側面／後ろ／前3/4／ガルウイング全開） | assets/cars/roadster_w4_sheet.jpg |
| @VanceGT | 小道具 | 銀の 60 年代英国 GT、右ハン、防弾ガラスにひび、弾痕 | assets/cars/vance_coupe_silver.jpg |
| @CliffRoadDay2 | ロケーション | 10/19 作り直し。崖道、夕方。左に垂直の石灰岩、右に石の縁石の上の白いガードレールと海。太陽は画面の外、フレア・光の筋なし | assets/locations/cliffroadday_v2.jpg |
| @HarborCafe | ロケーション | 港のカフェのテーブル／岸壁／上に道のある崖 | （Higgsfield 内） |

## 旧版（使わない）

@CliffRoadDay（**画像そのものに逆光のオレンジの光の筋が 2 本写っていた** → 生成に赤い横筋が出る原因。10/19 @CliffRoadDay2 に交代。C01 v4 はこれで作った）、@Roadster（赤）、@RoadsterW（白・丸い）、@RoadsterW2（角張ってはいるが実物と差）、@CliffRoad（夜）、VanceCoupe（緑・未登録）

## 予定

- @RoadsterCabin（ロケーション）：最初に通った車内カットの 1 フレームを登録。C14・C16・C18 の内装を揃える

## 生成プロンプト（通った版）

### @RoadsterW4（Seedream 5.0 lite、1:1）

```
Automotive design model sheet, 4 panels on a neutral dark grey studio background, of one original futuristic electric 2+2 coupe. No brand, no logos, no badges, no text, no license plate. PROPORTIONS (most important): extremely low and wide, roof only slightly higher than the tops of the wheels, like a low 1970s wedge concept car with 2020s stealth-aircraft surfacing; long low hood, very short overhangs, wheelbase long, cabin pushed forward. SURFACES: flat planes meeting at hard creases, no rounded fenders, no air intakes, no vents; a single sharp horizontal character line runs along the full body side at mid-height. TWO-TONE: satin pearl off-white upper body; lower body, sills, bumpers and diffuser in dark matte graphite. GLASS: one dark gold-tinted canopy - windshield, side windows and roof read as a single smooth dark glass band, no visible pillars; the roof peaks just behind the windshield then runs as a straight diagonal line down to a chopped vertical Kamm tail. DOORS: gullwing doors hinged at the roof centerline that lift the roof glass with them. WHEELS: large wheels with five Y-shaped twin spokes (10 thin spokes), black with brushed silver and bronze faces, wide tires, angular wheel arches with flat tops. FRONT: a flat flush face, no grille, no headlights, only one thin full-width white light line along the bottom edge of the nose. REAR: wide flat squared tail, a thin full-width red light bar, a two-piece swan-neck rear wing on two pylons, and below it a dark diffuser with FOUR round steel thruster nozzles in a horizontal row at center. PANELS: (1) exact side profile, (2) rear 3/4 view at low camera height, (3) front 3/4 view at low camera height, (4) front view with both gullwing doors open. Soft studio lighting, photorealistic automotive product photography, 85mm lens, identical design in every panel.
```

効いた書き方：比率を冒頭に数値的に／ツートン／ガラスを「一枚のキャノピー」／横一本のキャラクターライン。
効かなかった：ホイールの Y 字 10 本（6 本になりがち）。

### @VanceGT

```
Vehicle model sheet of an original 1960s-style British grand touring coupe, right-hand drive, invented design, no brand, no badges, no emblems, no text. Long bonnet with a subtle power bulge, oval wide-mouth grille with fine horizontal chrome bars, two round headlights set in recessed cowls, delicate chrome bumpers with overriders, fastback roofline tapering to a short Kamm tail with small round tail lamps, knock-off wire-spoke wheels, thin chrome window trim. Paint: classic silver-birch metallic with patina. Battle-worn: the windshield and side windows are laminated armored glass with dense spiderweb cracks and bullet impact stars but not shattered; several bullet dents on the doors and bonnet. Layout: front 3/4 view, side profile, rear 3/4 view, and a close detail of the cracked windshield, all on a neutral dark grey studio background, soft even lighting, photorealistic automotive studio photography, 50mm lens, consistent design across all views.
```

## 実物ロードスターの観察メモ（公式ギャラリーより、言葉で）

- 極端に低く広い。ルーフはタイヤの上端より少し高い程度
- 面は折り紙のように平ら。ふくらみ・インテーク・ベントなし。横に一本の鋭いライン
- ツートン：上はサテンのオフホワイト、下（サイド下・バンパー・ディフューザー）はダークグラファイト
- ガラスは金色がかった一枚のキャノピー。ピラーが見えない。ルーフは A ピラー直後が頂点で直線的に後ろへ下がり、垂直に切れたカムテール
- ドアはルーフのガラスごと上に開くガルウイング
- ホイールは Y 字ツインスポーク 10 本、黒にシルバー／ブロンズ
- 前：完全にフラットな面。グリル・ヘッドライトなし。最下部に細い白の一文字ライト
- 後ろ：平らな四角い尻。細い赤の一文字テール。二枚羽のスワンネック・リアウイング（支柱 2 本）。ディフューザー中央に丸いノズル 4 本が横一列
- スラスターの噴射は純白の蒸気（炎・青い光なし）。ジャンプ時は四隅から真下に噴く

### @CliffRoadDay2（Seedream 5.0 lite、1:1、10/19）

```
Location reference photo, photorealistic, of an original Mediterranean coastal cliff road in late afternoon. A narrow two-lane asphalt road with a white center line runs straight away from the camera at eye level. On the LEFT, a sheer vertical pale limestone cliff wall rises straight up out of frame, rough textured rock, no overhang. On the RIGHT, a low white steel guardrail on a short stone curb, and beyond it a steep drop to the calm blue sea far below; the horizon is low. Warm low sun from the right side, OUTSIDE the frame behind the camera, raking golden light across the cliff face and long soft shadows across the road. Clear sky with a few thin high clouds. Clean lens: no lens flare, no light leaks, no orange or red streaks, no sun in frame, no glare. No cars, no people, no signs, no text. 24mm lens, sharp, natural colors, fine film grain.
```

効いた書き方：太陽を「画面の外・カメラの後ろ」に置く（逆光をやめる）、"Clean lens" と筋の色まで名指しで禁止。
