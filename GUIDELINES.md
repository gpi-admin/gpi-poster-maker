# GPI Poster Maker — 開発ガイドライン

> このファイルはプロジェクトの設計判断・実装ルール・既知の注意事項を記録する「生きたドキュメント」です。
> 設計変更があった際は **CLAUDE.md のルールに従い、このファイルを必ず更新してください。**

---

## 1. プロジェクト概要

岐阜県小児科研修セミナー（GPI）の告知ポスターを自動生成する Streamlit アプリ。
年 3 回のポスター制作を Webフォーム入力だけで完結させることが目標。

| 出力形式 | 解像度 / 品質 | ライブラリ |
|---------|-------------|-----------|
| プレビュー (PNG) | 794×1123 px (96 DPI) | SVG renderer + CairoSVG（統一） |
| 本番 PDF | A4 ベクター | SVG renderer + CairoSVG（統一） |
| 高解像度 PNG | 2480×3508 px (300 DPI) | SVG renderer + CairoSVG（統一） |

---

## 2. ポスター要素の変動分類（設計の根幹）

ポスターを構成する要素は変化の性質によって 6 種類に分類される。
この分類が UI 設計・LayoutEngine の複雑度・デフォルト値設定の判断基準となる。

---

### カテゴリ 1 — 不変な要素（コードに埋め込み、入力不要）

| 要素 | 内容 |
| --- | --- |
| **ヘッダー文字** | "Gifu Pediatric-residency Intensives"（上部バー） |
| **場所バッジ** | 丸/ピル型に「場所」と書かれた濃褐色バッジ |
| **フッター** | "お問い合わせ先  岐阜県小児科研修支援グループ  Mail ▶  {email}"。**「岐阜県小児科研修支援グループ」のみ** `FOOTER_GROUP_SCALE`（1.18）で少し大きく描画。 |

メールアドレス（`contact_email`）は PosterData に持つ。Step1 のデフォルトは `gpi.office.med@gmail.com`。

---

### カテゴリ 2 — 変更が少ない要素（デフォルト値あり、要確認）

| 要素 | 変化の性質 | デフォルト |
| --- | --- | --- |
| **会場情報** | 建物名・部屋名・住所。ほぼじゅうろくプラザ 小会議室1/2で固定。たまに変わる | `venue_building`, `venue_room`, `venue_address` で管理 |
| **Zoom案内** | "ハイブリッド開催" テキストは固定。**右側に表示する Zoom アイコンは `accent_light`（薄色）+ 白ロゴでテーマ連動** | `zoom_note` フィールド |
| **開催日時** | 毎回変わる。時刻（19:00-20:30）は基本不変。日付文字幅に合わせ自動フィット必要 | `event_date`, `time_range` |
| **セミナータイトル** | "20○○年度 第○回岐阜県小児科研修セミナー" — ○の中だけ変わる。位置・色は固定 | `year`, `session_num` から自動生成 |
| **バッジ色** | 開催時期・背景イラストに合わせてテーマ色を選択。**大バッジ（部・司会・座長・対象）は濃いめ、小バッジ（症例報告等）は薄めの色** | `accent` vs `accent_light` で実装済み |
| **対象** | 学生・初期研修医・後期研修医・小児科医は固定。眼科医・耳鼻科医等が追加される場合あり | `audience: List[str]` |

---

### カテゴリ 3 — 内容が大きく変わる要素（LayoutEngine が自動調整）

これらの変化はプログラムエリアの縦方向スペースに影響し、LayoutEngine がフォントスケール調整で吸収する。

| 要素 | 変化の内容 | 注意点 |
| --- | --- | --- |
| **総合司会** | 所属・氏名が毎回変わる。氏名は敬称込みの自由入力で、改行で複数名を入力できる | 左カラムに配置。長い所属名は折り返し。氏名は折り返さず、幅を超える場合は自動縮小（13 章参照） |
| **特別講演座長** | 無い回もある（任意）。氏名の扱いは総合司会と同じ | `chair = None` の時は非表示 |
| **発表者氏名** | 敬称込みの自由入力（自動で「先生」は付かない）。改行で複数名（1行 = 1名）。行ごとに右寄せ | 敬称は氏名本体より小さく描画。幅超過時は自動縮小（13 章参照） |
| **発表サブタイトル** | 任意。タイトル直下に小さめで描画。空なら高さ 0 | `ContentItem.subtitle` |
| **文字サイズ倍率** | タイトル・サブタイトル・所属・氏名ごとにユーザーが 50〜150% で調整（司会・座長は所属・氏名） | 全体の自動縮小の上に掛かる（7 章参照） |
| **第1部の内容** | 基本は「症例報告1（10分）」「症例報告2（10分）」の2本でほぼ固定 | タイトル長で行数が変わる |
| **第2部の内容** | 「国内留学日誌（15分）」「中堅医師による病院紹介（15分）」等、内容が毎回変わる | 同上 |
| **第3部（特別企画）の内容** | シンプル（講演1本）の時もあれば、レクチャー＆実習で複数発表者になる場合もある | 複数 ContentItem に対応済み |
| **サブタイトルバッジ** | ラベルが変わると楕円/ピル幅が変わる。`fit_font_in_box` で自動サイズ調整 | 文字数が増えすぎると読みにくくなる |

**典型的なプログラム構成:**

```
第1部  症例報告1（10分）／症例報告2（10分）
第2部  国内留学日誌（15分） など
第3部（特別企画）  特別講演（50分） または レクチャー＆実習（60分）
```

---

### カテゴリ 4 — QR コード（毎回差し替え）

- `registration_url` に URL を入力 → `qr_generator.py` が自動生成
- QR が不要な場合は URL を空欄にすると非表示
- 左カラム下部に自動配置（利用可能スペースに合わせてサイズ調整）

---

### カテゴリ 5 — 装飾イラスト（空きスペースへの配置）

- 開催時期・背景テーマに合った可愛らしいイラストを **1 点** 配置
- `decorative_images: List[str]` の先頭1件のみを左カラム下部に貼り付け

---

### カテゴリ 6 — 背景イラスト（任意）

- デフォルトは背景なし（ベースのクリーム色）
- 背景イラストはユーザーが明示的に選択・アップロードした場合のみ描画される
- プリセット背景は `assets/illustrations/backgrounds/` から選択可能
- ユーザーが独自背景を指定可能（`background_image_path`）
- `bg_opacity` で透明度を調整（デフォルト 0.35）
- **PNG/PDF 書き出し時**は `transparent_bg=True` でレンダリングし、背景未指定領域を透過で出力する

---

## 3. ファイル構成

```
GPI_Poster_Maker/
├── app.py                    # Streamlit 7ステップフォーム
├── test_svg.py               # 本番経路（SVG）のテスト → test_output_svg.png
├── GUIDELINES.md             # ← このファイル
├── CLAUDE.md                 # Claude Code 動作ルール
├── requirements.txt
├── poster/
│   ├── models.py             # PosterData / Section / ContentItem / PersonInfo
│   ├── layout.py             # 正規化座標定数 + LayoutEngine + 氏名ブロック計測
│   ├── name_utils.py         # 氏名文字列の解析（改行分割・敬称セグメント化。純 Python）
│   ├── svg_renderer.py       # SVG 描画（本番経路。PNG / PDF の唯一のソース）
│   ├── email_text.py         # 告知メール文面の生成
│   ├── zoom_icon.py          # テーマ色 + 白ロゴの Zoom アイコン合成
│   ├── preview_renderer.py   # Pillow プレビュー描画（96 DPI）
│   ├── pdf_renderer.py       # PDF 出力（ベクター主体・テキスト編集可）
│   ├── elements_pillow.py    # Pillow 用描画関数（要素単位）
│   ├── elements_pdf.py       # ReportLab 用描画関数（要素単位）
│   ├── text_utils.py         # 日本語テキスト処理（折り返し・フィット）
│   └── qr_generator.py       # URL → QR PIL Image
├── generate_backgrounds.py   # 12テーマ分の背景画像を生成（グラデーション or Unsplash API）
├── themes/
│   └── color_themes.py       # 12テーマ + カスタム定義（後方互換エイリアスあり）
├── utils/
│   ├── font_manager.py       # Noto Sans JP 管理（自動DL・登録）
│   ├── state_migration.py    # 保存データ（JSON）の旧バージョン変換
│   └── image_utils.py        # 背景合成ユーティリティ
└── assets/
    ├── fonts/NotoSansJP/     # Regular / Bold / Black (.otf)
    ├── illustrations/
    │   ├── backgrounds/      # 季節背景画像
    │   ├── decorative/       # 装飾イラスト
    │   └── fixed/            # Zoom アイコン等
    └── uploaded/             # ユーザーアップロード（一時）
```

---

## 3. 座標系（正規化座標）

**全レイアウト定数は 0.0〜1.0 の正規化座標**で定義し、各レンダラーが単位系に変換する。

```
(0,0) = 左上, (1,1) = 右下

Pillow:    n * PREVIEW_H (1123 px)  または  n * PREVIEW_W (794 px)
ReportLab: n * PDF_H     (841.89 pt) または  n * PDF_W     (595.27 pt)
```

変換ヘルパー（`layout.py`）:
- `n_to_px(value, axis)` — 正規化 → プレビュー px
- `n_to_pt(value, axis)` — 正規化 → PDF pt

---

## 4. カラムレイアウト（横方向）

```
0%       41.5%         52%    57%                   100%
|  左     |  タイトル帯  | 右スト |  プログラムエリア   |
|  カラム |  縦書き帯    | リップ |  発表内容・時刻    |
```

※ 縦バー（旧 DIV_X / DIV_W）は廃止。タイトル帯がその位置を兼ねる。

| 定数 | 値 | 説明 |
| --- | --- | --- |
| `LEFT_W` | 0.415 | 左カラム幅（0〜41.5%） |
| `TITLE_X` | 0.415 | メインタイトル帯左端（= 左カラム右端）**変更禁止** |
| `TITLE_W` | 0.105 | メインタイトル帯幅（41.5〜52%） |
| `SECT_X` | 0.520 | 右ストリップ左端（= TITLE_X + TITLE_W） |
| `SECT_W` | 0.050 | 右ストリップ幅（52〜57%） |
| `PROG_X` | 0.570 | プログラムエリア左端（= SECT_X + SECT_W） |
| `PROG_W` | 0.430 | プログラムエリア幅（57〜100%） |

---

## 5. 縦方向レイアウト

| 定数 | 値 | 説明 |
|------|-----|------|
| `HEADER_H` | 0.030 | 上部バー高さ |
| `FOOTER_H` | 0.034 | 下部バー高さ |
| `FOOTER_GROUP_SCALE` | 1.18 | フッター「岐阜県小児科研修支援グループ」部分のフォント倍率（他は 1.0） |
| `PROG_TOP` | 0.230 | 動的レイアウト開始 Y（年度テキスト分の余白含む） |
| `PROG_BOT` | ≈0.958 | 動的レイアウト終了 Y |
| `PROG_H` | ≈0.728 | 動的レイアウト利用可能高さ |

Zoom セクション用定数（`layout.py`）:
- `ZOOM_TEXT_SHIFT_RATIO = 0.060`（中央から左へずらす量）
- `ZOOM_ICON_SIZE_SCALE = 1.45`（アイコンサイズ倍率）
- `ZOOM_ICON_RIGHT_PAD = 0.040`（右余白）
- `ZOOM_TEXT_ICON_GAP = 0.040`（テキストとアイコンの最小間隔）
- `ZOOM_ICON_LOGO_SCALE = 0.80`（白ロゴサイズ倍率）
- `ZOOM_ICON_ROTATE_DEG = 8.0`（アイコングループを反時計回りに傾ける角度）

**PROG_TOP = 0.230 の根拠**: 右ストリップ上部に "2025年度" を縦積み描画するため、
ヘッダー下（≈34px）からプログラム開始（≈258px）までの ≈224px が年度テキスト領域となる。

---

## 6. 描画レイヤー順（preview_renderer.py）

1. ベースキャンバス（プレビュー: クリームホワイト / 書き出し透過モード: 透明）
2. 背景イラスト（指定時のみ alpha blend）
3. ヘッダーバー・フッターバー
4. **縦書きメインタイトル帯**（TITLE_X〜TITLE_X+TITLE_W、37〜50%）— 文字積み方式
5. **右ストリップ: 年度テキスト**（固定位置, SECT_X〜SECT_X+SECT_W の上部 PROG_TOP まで）
6. 左カラム: 場所バッジ・会場名・住所・Zoom・日時・司会・座長・対象・QR
7. プログラムエリア: 参加費無料テキスト + 動的レイアウト（LayoutEngine）
8. **右ストリップ: 第N部ラベルボックス**（セクション Y 位置に合わせて動的配置）
9. 装飾イラスト（最前面）

※ 縦バー（`draw_center_divider`）は廃止。

---

## 7. 動的レイアウトエンジン（LayoutEngine）

`poster/layout.py` の `LayoutEngine.compute()` がプログラムエリアの配置を計算する。

```
1. フォントスケール 1.0 から試行
2. 全ブロック高さの合計が PROG_H 以内か確認
3. 収まらなければ scale を 0.05 ずつ下げて再試行（最小 0.70）
4. 収まった時点で Y 座標を順番に割り当て
```

**Block 種別:**

| kind | 内容 |
|------|------|
| `section_time` | セクション時刻ヘッダー（"19:00 - 19:20"） |
| `sub_badge` | 発表種別バッジ（"症例報告1（10分）"） |
| `title` | 発表タイトル（長文は自動折り返し） |
| `subtitle` | 発表サブタイトル（`title` の直後に必ず 1 つ存在。空なら高さ 0） |
| `affiliation` | 所属機関 |
| `name` | 発表者氏名（改行で複数行。行ごとに右寄せ） |
| `gap` | セクション間・コンテンツ間スペース |

**Block.data の主なキー:**

| kind | キー |
|------|------|
| `title` / `subtitle` / `affiliation` | `text`, `scale`（全体の自動縮小）, `content_scale`（セクション別）, `user_scale`（ユーザー倍率・clamp 済み）, `lines`（実測した折り返し行） |
| `name` | `text`, `scale`, `content_scale`, `user_scale`, `lines`（`parse_name_block` の結果。`[[(text, is_honorific), ...], ...]`）, `fit`（幅超過時の縮小率。収まれば 1.0） |

レンダラー（SVG / 旧 Pillow / 旧 ReportLab）はこの Block 契約に従って描画する。

**フォントサイズ定数（`layout.py`、正規化高さ）:**

| 定数 | 値 | 用途 |
|------|-----|------|
| `FS_PROG_TITLE` | 0.024 | 発表タイトル |
| `FS_PROG_SUBTITLE` | 0.019 | 発表サブタイトル（タイトルの約 0.8 倍） |
| `FS_PRESENTER` | 0.018 | 所属 |
| `FS_PRES_NAME` | 0.022 | 発表者氏名。プログラム発表者名と司会/座長名（`FS_MC_NAME`）の双方で同値 |

**氏名・文字サイズ関連の定数（`layout.py`）:**

| 定数 | 値 | 説明 |
|------|-----|------|
| `USER_FONT_SCALE_MIN` / `USER_FONT_SCALE_MAX` | 0.5 / 1.5 | ユーザー指定倍率の有効範囲（`clamp_user_scale` で丸める。不正値・None は 1.0） |
| `HONORIFIC_SCALE` | 0.85 | 敬称の氏名本体に対するサイズ比 |
| `HONORIFIC_MIN_SIZE` | 8.0 | 敬称フォントサイズの下限（pt / px） |
| `NAME_FIT_MIN` | 0.6 | 氏名が幅に収まらない場合の自動縮小の下限倍率 |
| `NAME_LINE_ADVANCE_PROG` | 1.25 | プログラム発表者名の行送り（行高 × この値） |
| `NAME_LINE_ADVANCE_MC` | 1.2 | 左カラム（総合司会・座長）氏名の行送り |
| `NAME_MC_RIGHT_MARGIN` | 1.0 | 左カラム氏名の右マージン（fit 前の氏名サイズ × この値） |
| `PROG_SUBTITLE_SPACING` | 1.35 | サブタイトルの行間（タイトルも 1.35、所属は 1.25） |

**文字サイズの決まり方:**

```
実フォントサイズ = 基準定数 × キャンバス高さ × scale × content_scale × user_scale
```

- `scale`: 全体の自動縮小（1.0 → 0.70）
- `content_scale`: `SECTION_CONTENT_SCALES`（セクション別）
- `user_scale`: `ContentItem.title_scale / subtitle_scale / affiliation_scale / name_scale`（1.0 = 100%）。`LayoutEngine` が `clamp_user_scale` で 0.5〜1.5 に丸める唯一の箇所
- 氏名ではさらに幅超過時の `fit`（下限 `NAME_FIT_MIN`）が掛かる

**高さ計算は「実測」ベース:**

- `LayoutEngine` は `render_scale` ごとの仮想キャンバス（`PREVIEW_W/H * render_scale`）を前提に高さを計算する。`use_reportlab=True` の場合は ReportLab（BIZ UD Gothic）メトリクスで計測する（SVG レンダラーが使用）。
- `title` / `subtitle` / `affiliation` は実際の折り返し行（`wrap_text_jp` 相当）を作成し、行間（タイトル 1.35、サブタイトル `PROG_SUBTITLE_SPACING`、所属 1.25）で高さを計測する。空文字の場合は行なし・高さ 0。
- `name` は `parse_name_block` で行・セグメントに分解し、`rl_name_fit` で `fit` を決め、`rl_name_metrics` → `rl_name_block_height(metrics, NAME_LINE_ADVANCE_PROG)` で高さを求める。1 行の高さは `max(氏名本体の文字高, 敬称の文字高)`、行送りはこれに `NAME_LINE_ADVANCE_PROG` を掛けた値。
- これにより、長いタイトルが複数行になっても所属行と重ならない。

**氏名ブロックの計測・描画ヘルパー（`layout.py`）:**

- `NameBlockMetrics`: `lines`, `fit`, `name_size`, `hon_size`, `name_asc`, `name_h`, `hon_asc`, `hon_h`, `line_h`, `seg_widths`, `line_widths`
- `honorific_size(name_size)`: 敬称サイズ（`max(HONORIFIC_MIN_SIZE, name_size * HONORIFIC_SCALE)`）
- `rl_name_fit(lines, base_size, max_w)`: 最も幅の広い行が `max_w` を超える場合の一律縮小率（`NAME_FIT_MIN` 以上、収まれば 1.0）
- `rl_name_metrics(lines, base_size, fit)`: 寸法の算出（`base_size` は fit 適用前）
- `rl_name_block_height(metrics, advance)`: ブロック全体の高さ（空なら 0）

`svg_renderer.py` の `_draw_name_block` は `rl_name_metrics` の結果をそのまま使い、1 行 = 1 名・右寄せ・本体と敬称は下端揃えで描画する。総合司会・座長（`draw_person_row`）も同じヘルパーを通る。

---

## 8. 右ストリップの設計仕様

### 年度テキスト（固定位置）
- 描画関数: `draw_year_label_strip(draw, year_text, x, y_top, y_bot, strip_w)`
- 範囲: `header_h + ph(0.006)` 〜 `prog_top_y - ph(0.010)`
- フォントサイズ: `(avail_h // num_chars) - 4` で自動算出（領域に等分配置）
- テキスト: "2025年度"（6文字を縦積み、各文字を X 中央寄せ）

### 第N部ラベルボックス（動的位置）
- 描画関数: `draw_section_label_box(canvas, x, y_start, y_end, strip_w, label, theme, pad=5)`
- 位置: LayoutEngine が返す各セクションの `y_start` から次のセクション（or フッター）まで
- デザイン: テーマカラー（`accent`）の角丸長方形（radius = bw // 4）
- ラベル: `label` 中の "第X部" 部分のみ抽出・縦積み（例: "第2部（特別企画）" → "第2部"）
- フォントサイズ: `int(bw * 0.44)`

---

## 9. テーマカラーシステム

`themes/color_themes.py` に 12テーマ + カスタムを定義。
背景画像は `generate_backgrounds.py` で生成（`assets/illustrations/backgrounds/`）。

| テーマキー | 季節 | 月の目安 |
|-----------|------|---------|
| `spring_sakura` | 春（桜） | 3〜4月 |
| `spring_fresh` | 春（新緑） | 4〜5月 |
| `early_summer_wisteria` | 初夏（藤） | 5月 |
| `summer_hydrangea` | 梅雨（紫陽花） | 6月 |
| `summer_ocean` | 夏（海） | 7〜8月 |
| `summer_night` | 夏夜（銀河） | 8月 |
| `early_autumn_cosmos` | 初秋（コスモス） | 9月 |
| `autumn_leaves` | 秋（紅葉） | 10〜11月 |
| `autumn_ginkgo` | 秋（銀杏） | 11月 |
| `winter_snow` | 冬（雪景色） | 12〜1月 |
| `winter_christmas` | 冬（クリスマス） | 12月 |
| `new_year_sunrise` | 新春（初日の出） | 1〜2月 |
| `custom` | カスタム | 任意 |

**後方互換エイリアス**（旧キーで保存されたデータは自動変換される）:

- `spring_pink` → `spring_sakura`
- `early_summer_green` → `early_summer_wisteria`
- `summer_blue` → `summer_night`
- `autumn_orange` → `autumn_leaves`

テーマオブジェクトのキー: `accent`, `accent_light`, `title_bar`, `zoom_color`, `bg_image`
（Zoom アイコン背景は `accent_light` を使用）

固定色:
- `DARK_BROWN = (80, 50, 30)` — メインテキスト・場所バッジ
- `WHITE = (255, 255, 255)`
- `LIGHT_CREAM_BG = (245, 241, 234)` — ポスター地色

---

## 10. フォント管理

`utils/font_manager.py` が Noto Sans JP を管理する。

```python
get_pillow_font(weight, size)  # weight: "Regular" | "Bold" | "Black"
ensure_fonts()                  # 初回実行時にフォントをDLしてキャッシュ
force_bold_fonts(enabled=True)  # 太字モードON/OFFを一時切替（既定ON）
```

フォントファイル: `assets/fonts/NotoSansJP/NotoSansJP-{weight}.otf`

**macOS 環境ではシステムの Hiragino フォント (`.ttc`) を優先的に使用する場合がある。**
テスト時は `ensure_fonts()` を必ず呼び出すこと。
`cairosvg` レンダリングでは `Hiragino Sans` の `font-weight` 指定が太字に反映されにくいため、SVG生成時（`embed_fonts=False`）に `Hiragino Sans W6` / `Hiragino Mincho ProN W6` を system family として使用する。

本実装では太字モードが既定でONのため、Pillow描画は `Regular→Bold`, `Bold→Black` に自動昇格する。
PDFは基本的に通常のテキスト描画で出力する。  
`BIZ UDMincho` は Bold バリアントがないため、SVG描画では `font-weight="400"` を維持しつつ、
同色ストローク（`stroke-width = max(0.52, size * 0.04)`）で疑似太字化して
年度テキスト・縦書きタイトルの太さを確保する。

---

## 11. データモデル（poster/models.py）

```python
PosterData
├── year: int                     # 年度 (e.g., 2025)
├── session_num: int              # 回数 (e.g., 1)
├── theme_key: str
├── event_date: str               # "2025年 5月23日(金)"
├── time_range: str               # "19:00 - 20:30"
├── venue_building, venue_room, venue_address
├── registration_url, zoom_note
├── mc: Optional[PersonInfo]      # 総合司会
├── chair: Optional[PersonInfo]   # 特別講演座長（任意）
├── audience: List[str]
├── sections: List[Section]
├── contact_email
├── bg_opacity: float
├── background_image_path
├── decorative_images: List[str]
└── custom_accent_color / custom_accent_light

Section
├── label: str          # "第1部", "第2部（特別企画）"
├── time_start / time_end
└── contents: List[ContentItem]

ContentItem
├── badge_label: str    # "症例報告1（10分）"
├── title: str          # 改行可
├── affiliation: str    # 改行可
├── presenter_name: str # 敬称込みの自由入力（自動で「先生」は付かない）。改行で複数名（1行 = 1名）
├── subtitle: str = ""  # 任意・改行可。タイトル直下に小さめで描画
└── title_scale / subtitle_scale / affiliation_scale / name_scale: float = 1.0
                        # ユーザー指定の文字サイズ倍率（1.0 = 100%）。有効範囲 0.5〜1.5 は layout.py で clamp

PersonInfo（総合司会・座長）
├── affiliation: str    # 改行可
├── name: str           # 敬称込みの自由入力。改行で複数名
└── affiliation_scale / name_scale: float = 1.0
```

氏名の解析（`poster/name_utils.py`、純 Python）:
- `split_name_lines(name)`: 改行で分割し、各行を strip して空行を除く
- `split_honorific_segments(line)`: 1 行を `(テキスト, 敬称か)` のセグメント列に分ける。敬称セグメントは `" 先生"` のように直前の空白を半角スペース 1 個に正規化した形
- `parse_name_block(name)`: 行ごとのセグメント列のリスト
- 敬称として認識するのは `HONORIFICS = ("先生", "様", "氏", "さん")` で、直前にスペース（半角/全角）が 1 つ以上あり、直後が行末・スペース・区切り文字（`、,，・/／）)`）のもの

保存データ（JSON）は `_version: "1.2"`。変換処理は `utils/state_migration.py` の `migrate_saved_state`。

---

## 12. テスト方法

```bash
# 本番経路（SVG → CairoSVG）の確認 ← アプリが実際に使う出力経路
.venv/bin/python test_svg.py
# → test_output_svg.png を目視確認
#   氏名の敬称・複数名・自動縮小、サブタイトル、文字サイズ倍率を検証する。
#   name_utils / clamp_user_scale の単体 assert と、LayoutEngine の Block 契約
#   （subtitle の存在、name の lines / fit、ブロックが重ならず連続すること）の assert を含む

# Pillow プレビュー確認（旧レンダラー）
python3 test_preview.py
# → test_output_preview.png を目視確認

# PDF 出力確認（旧 ReportLab レンダラー）
python3 test_pdf.py
# → test_output.pdf を Adobe Illustrator で開き、
#   テキスト・図形が個別選択可能であることを確認

# Streamlit アプリ起動
streamlit run app.py
# または 起動.command をダブルクリック（macOS）
```

---

## 13. 既知の注意事項・設計決定

- **縦書き実装（文字積み方式）**: `draw_vertical_title` は各文字を縦に積み上げる方式を採用。以前の回転方式（`rotate(-90°)`）は廃止。文字積みにより各文字が直立した正規の縦書きになる。`draw_year_label_strip` も同じ方式。
- **縦書き長音符の中央補正**: `ー` は回転描画時に視覚補正としてわずかに左へオフセットして、タイトル帯の中央に見えるよう調整する。

- **PROG_TOP の値**: 年度テキスト用スペース確保のため `0.180`（デフォルト `0.038` から変更）。
  セクション数・コンテンツ量が多い場合、LayoutEngine は scale を下げて対応（最低 0.70）。

- **Streamlit 実行順序**: `app.py` は上から順に実行されるため、関数定義はすべて呼び出し箇所より前に配置すること。`_build_poster_data()` は `init_state()` の直後に定義。

- **第N部ラベルの短縮**: `draw_section_label_box` では "第X部" 部分のみ抽出して表示。
  "第2部（特別企画）" → "第2部" として縦積み。

- **DARK_BROWN のインポート**: `preview_renderer.py` では `from themes.color_themes import DARK_BROWN` をファイル末尾でインポートしている（循環インポート対策）。

- **右ストリップ年度テキストと第N部ボックスは独立して描画**: 年度テキストは step 6、ラベルボックスは step 9 で描画。layout 計算後にのみラベルボックスを描画できる。

- **LayoutEngine の実測高さ計算**: タイトル・所属・氏名の高さは文字数推定ではなく実際の折り返し行で計測する。これにより、長文タイトル時でも所属と重ならない。

- **Streamlit 保存/読み込み**: `_export_state()` / `_import_state()` は `with st.sidebar:` ブロックより**前**に定義する必要がある（実行順序の制約）。保存ファイルには `_version: "1.2"` を付与し、旧テーマキーは `_THEME_ALIASES` で自動変換する。

- **保存データ v1.2 と旧データの「先生」補完**: v1.1 以前は描画時に氏名へ「先生」を自動付与していたが、v1.2 以降は氏名を入力どおり描画する。`_import_state()` は読み込み時に `migrate_saved_state`（`utils/state_migration.py`）を通し、`_version` が無い・1.2 未満・壊れている場合に限り、司会・座長・各発表の氏名の各非空行へ末尾が「先生」でなければ `" 先生"` を補完する（旧版と同じ見た目を保つため）。1.2 以上はそのまま。入力は変更せずコピーを返す。

- **敬称は自動付与しない**: 氏名は敬称込みの自由入力。「先生」「様」などを勝手に足さない（`app.py` の入力欄の案内、`email_text.py` も同様）。メール文面は複数名を「、」で連結する。

- **敬称の自動縮小の認識条件**: 敬称は氏名本体の `HONORIFIC_SCALE`（0.85）倍で描く。認識するのは「直前にスペース（半角/全角）が 1 つ以上あり、直後が行末・スペース・区切り文字」の `先生` / `様` / `氏` / `さん` のみ。スペースなしで続く場合（「山田太郎先生」）や語の一部（「山田 さんま」）は敬称扱いしない（通常サイズ）。

- **氏名は折り返さず自動縮小**: 氏名は 1 行 = 1 名で折り返さない。最も幅の広い行が利用幅を超える場合、ブロック全体を一律に縮小する（`rl_name_fit`、下限 `NAME_FIT_MIN` = 0.6）。下限でも収まらない長さははみ出す（既知の制約）。総合司会・座長も同じルール。長すぎる場合は改行で名前を分けるか「サイズ%」を調整する。

- **ユーザー倍率の clamp 位置**: プログラム内の文字サイズ倍率は `LayoutEngine` が `clamp_user_scale`（0.5〜1.5）で丸める。左カラム（総合司会・座長）は `LayoutEngine` を通らないため、`svg_renderer.py` の `draw_person_row` 側で丸める。`app.py` 側も入力を 50〜150% に丸める（`_pct_to_scale`）。

- **計測と描画は `rl_name_metrics` を共有**: `LayoutEngine(use_reportlab=True)` の氏名高さ計測と `svg_renderer.py` の描画（`_draw_name_block`）は、同じ `rl_name_fit` / `rl_name_metrics` を通す。計算式を二重管理しないことで、計測と描画のズレ（重なり・余白不足）を防ぐ。`Block.data["fit"]` は計測時の値を描画でそのまま使う。

- **パスワード認証（fail-close）**: `app.py` は起動直後に `_check_password()` を実行し、`st.secrets` に `password` / `passcode`（大文字・ネスト含む）が見つからない場合はアプリを停止する。WebApp で未設定時に無認証で使えてしまう状態を防ぐ設計。ローカルで一時的に無認証起動したい場合のみ環境変数 `GPI_ALLOW_UNLOCKED=1` を使う。
