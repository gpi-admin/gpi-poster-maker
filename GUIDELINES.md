# GPI Poster Maker — 開発ガイドライン

> このファイルはプロジェクトの設計判断・実装ルール・既知の注意事項を記録する「生きたドキュメント」です。
> 設計変更があった際は **CLAUDE.md のルールに従い、このファイルを必ず更新してください。**

---

## 1. プロジェクト概要

岐阜県小児科研修セミナー（GPI）の告知ポスターを自動生成する Streamlit アプリ。
年 3 回のポスター制作を Webフォーム入力だけで完結させることが目標。

| 出力形式 | 解像度 / 品質 | ライブラリ |
|---------|-------------|-----------|
| プレビュー (PNG) | 794×1123 px (96 DPI) | Pillow |
| 本番 PDF | A4 ベクター（Illustrator 編集可 / 透過対応） | ReportLab |
| 高解像度 PNG | 2480×3508 px (300 DPI) | Pillow |

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
| **フッター** | "お問い合わせ先  岐阜県小児科研修支援グループ  Mail ▶  {email}" |

メールアドレス（`contact_email`）は PosterData に持つが、実質固定値。

---

### カテゴリ 2 — 変更が少ない要素（デフォルト値あり、要確認）

| 要素 | 変化の性質 | デフォルト |
| --- | --- | --- |
| **会場情報** | 建物名・部屋名・住所。ほぼじゅうろくプラザ 小会議室1/2で固定。たまに変わる | `venue_building`, `venue_room`, `venue_address` で管理 |
| **Zoom案内** | "&zoomミーティング" テキストはほぼ固定。**Zoomアイコンの配色はテーマに連動して変わる** | `zoom_note` フィールド |
| **開催日時** | 毎回変わる。時刻（19:00-20:30）は基本不変。日付文字幅に合わせ自動フィット必要 | `event_date`, `time_range` |
| **セミナータイトル** | "20○○年度 第○回岐阜県小児科研修セミナー" — ○の中だけ変わる。位置・色は固定 | `year`, `session_num` から自動生成 |
| **バッジ色** | 開催時期・背景イラストに合わせてテーマ色を選択。**大バッジ（部・司会・座長・対象）は濃いめ、小バッジ（症例報告等）は薄めの色** | `accent` vs `accent_light` で実装済み |
| **対象** | 学生・初期研修医・後期研修医・小児科医は固定。眼科医・耳鼻科医等が追加される場合あり | `audience: List[str]` |

---

### カテゴリ 3 — 内容が大きく変わる要素（LayoutEngine が自動調整）

これらの変化はプログラムエリアの縦方向スペースに影響し、LayoutEngine がフォントスケール調整で吸収する。

| 要素 | 変化の内容 | 注意点 |
| --- | --- | --- |
| **総合司会** | 所属・氏名が毎回変わる | 左カラムに配置。長い所属名は折り返し |
| **特別講演座長** | 無い回もある（任意） | `chair = None` の時は非表示 |
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

- 開催時期・背景テーマに合った可愛らしいイラストを 2 点程度配置
- スペースが余る場合：ビールのイラストを小さく追加（懇親会を示唆）
- `decorative_images: List[str]` にファイルパスを入れると左カラム下部に貼り付け
- ビール提案ロジック: `early_summer_green` / `summer_blue` テーマ時に `beer_mugs.png` を `suggested_decoratives` に含む

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
├── GUIDELINES.md             # ← このファイル
├── CLAUDE.md                 # Claude Code 動作ルール
├── requirements.txt
├── poster/
│   ├── models.py             # PosterData / Section / ContentItem
│   ├── layout.py             # 正規化座標定数 + LayoutEngine
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
| `PROG_TOP` | 0.230 | 動的レイアウト開始 Y（年度テキスト分の余白含む） |
| `PROG_BOT` | ≈0.958 | 動的レイアウト終了 Y |
| `PROG_H` | ≈0.728 | 動的レイアウト利用可能高さ |

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
| `affiliation` | 所属機関 |
| `name` | 発表者氏名 |
| `gap` | セクション間・コンテンツ間スペース |

**高さ計算は「実測」ベース:**

- `LayoutEngine` は `render_scale` ごとの仮想キャンバス（`PREVIEW_W/H * render_scale`）を前提に高さを計算する。
- `title` / `affiliation` は `wrap_text_jp` で実際の折り返し行を作成し、`draw_text_multiline` と同じ `line_spacing`（タイトル 1.35、所属 1.25）で高さを計測する。
- `name` は `draw_presenter(..., affiliation=\"\", name=...)` と同じロジック（`先生` 接尾の扱い含む）で1行/複数行高さを計測する。
- これにより、長いタイトルが複数行になっても所属行と重ならない。

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
force_bold_fonts(enabled=True)  # コンテキスト中は Regular→Bold, Bold→Black に昇格
```

フォントファイル: `assets/fonts/NotoSansJP/NotoSansJP-{weight}.otf`

**macOS 環境ではシステムの Hiragino フォント (`.ttc`) を優先的に使用する場合がある。**
テスト時は `ensure_fonts()` を必ず呼び出すこと。

PDF 生成時は `force_bold_fonts(True)` を使い、全テキストを太字寄りに描画してから A4 PDF に埋め込む。

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
├── title, affiliation, presenter_name
```

---

## 12. テスト方法

```bash
# Pillow プレビュー確認
python3 test_preview.py
# → test_output_preview.png を目視確認

# PDF 出力確認
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

- **PROG_TOP の値**: 年度テキスト用スペース確保のため `0.180`（デフォルト `0.038` から変更）。
  セクション数・コンテンツ量が多い場合、LayoutEngine は scale を下げて対応（最低 0.70）。

- **Streamlit 実行順序**: `app.py` は上から順に実行されるため、関数定義はすべて呼び出し箇所より前に配置すること。`_build_poster_data()` は `init_state()` の直後に定義。

- **第N部ラベルの短縮**: `draw_section_label_box` では "第X部" 部分のみ抽出して表示。
  "第2部（特別企画）" → "第2部" として縦積み。

- **DARK_BROWN のインポート**: `preview_renderer.py` では `from themes.color_themes import DARK_BROWN` をファイル末尾でインポートしている（循環インポート対策）。

- **右ストリップ年度テキストと第N部ボックスは独立して描画**: 年度テキストは step 6、ラベルボックスは step 9 で描画。layout 計算後にのみラベルボックスを描画できる。

- **LayoutEngine の実測高さ計算**: タイトル・所属・氏名の高さは文字数推定ではなく実際の折り返し行で計測する。これにより、長文タイトル時でも所属と重ならない。

- **Streamlit 保存/読み込み**: `_export_state()` / `_import_state()` は `with st.sidebar:` ブロックより**前**に定義する必要がある（実行順序の制約）。保存ファイルには `_version: "1.1"` を付与し、旧テーマキーは `_THEME_ALIASES` で自動変換する。
