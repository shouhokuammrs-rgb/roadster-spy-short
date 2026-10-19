# CLAUDE.md — このリポジトリで作業する Claude へ

これは「Roadster × Spy」AI ショート動画（54秒・9:16）の制作リポジトリ。成果物より **判断と学びの記録** が主目的。

## 最初に読む

1. README.md（全体像・いまどこにいるか）
2. docs/02_workflow.md（フェーズと手順）、docs/ref_blender_bridge_method.md（プリビズ主役の方法）
3. docs/03_prompting.md（Seedance プロンプトの知見）
4. docs/06_open_questions.md（未決・忘れやすい前提）

## 会話のルール

- 説明は日本語。Higgsfield に渡すプロンプトだけ英語
- 「いい感じ」で通さない。生成物は **コマ割り（0.5秒ごと）** を作って、動き・視線・連続性を確認してから評価する
- 1 カット＝1 生成。**3 役分担**：配置・カメラ・タイミングは参照動画（グレーボックス）、外観はエレメント、プロンプト本文は連続性＋体の動き（視線・手・体重・反応）＋DO NOT だけ（prompts/TEMPLATE.md）
- グレーボックスは **自分でコマ割りを読んで直し、合ってから** 本人に見せる（docs/02_workflow.md P2.5）
- **直すときは生成からやり直さない。先に Blender（世界）を直し、レンダーとコマ割りで確かめてから、それをプロンプトに言語化して生成する**（10/19 本人方針）。生成にだけある出来事・動き・向きを作らない。採用した生成は世界と同じ時刻で並べて照合する（gen/Cxx_world_vs_vN.jpg）
- 動きは **1 本の世界の時間** に置く（previs/blocking.json の world）。カットはカメラ＋時間の窓。カットの都合で世界の物を動かさない（ずらすなら cuts[].view に例外として書く）（docs/08_world_timeline.md）
- 実名・ロゴ・既存曲・公式写真のアップロードは使わない（オリジナルで"匂い"を出す）
- クレジットを使ったら docs/05_log.md に 1 行。学び・判断はその日のうちに docs/00_decisions.md と docs/03_prompting.md へ

## 固定の前提（毎回これに合わせる）

- ヒーローカー @RoadsterW4：白いウェッジ、ガルウイング、金ガラス、左ハンドル、噴射は **白い蒸気**（炎・青光なし）
- Vance の車 @VanceGT：銀の 60 年代英国 GT、右ハンドル、防弾ガラスにひび
- 崖道 @CliffRoadDay2（10/19 作り直し。旧 @CliffRoadDay は使わない）：海は進行方向右、岩壁は左、崖は垂直で上に道。夕方
- 敵：黒い私服の男たち **片側 4 人・黒 SUV 片側 2 台**（前後で 8 人・4 台。各 SUV のボンネットの陰に 2 人）、ヘルメット・防具なし、台詞なし。配置は previs/blocking.json の meta.formation
- ガラス：外から撮るカットは中を写さない（ロードスター＝金の反射、SUV＝黒スモーク、クーペ＝暗いグレー）。写すのは人の動作が主役の C02・C07・C13a/b・C14b だけ（blocking.json の meta.glass）
- 視点：Sho の主観は使わない。同じ視点を 2 カット続けない
- 音：台詞は日本語音声＋英語字幕。Seedance の音声は捨てる。無音 2 箇所（煙幕 C09／ランチャー〜回転 C14b–C16。画面の秒は編集から計算＝blocking.json の edit.silences）。黒で終わる
- カットの長さ：規則と仮の声の長さから出す（previs/shot_length.py、docs/09_shot_length.md）。感覚で IN/OUT を決めない

## 環境メモ

- Higgsfield は内蔵ブラウザで操作（ビューポート 1400×900、終わったら desktop に戻す）。`@` 候補は送信前に確認
- Blender は `pip install bpy` で headless レンダー可（previs/README.md）
