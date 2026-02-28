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
| 本番 PDF | A4 ベクター | ReportLab |
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

### カテゴリ 6 — 背景イラスト（季節・半透明）

- 開催時期に合う風景・自然イラストを **最背面に半透明（opacity≈0.30〜0.40）** で配置
- テキストを邪魔しない「おしゃれで控えめな」背景が選定基準
- テーマ選択で `bg_image` が自動決定される（`assets/illustrations/backgrounds/`）
- ユーザーが独自背景を指定可能（`background_image_path` で上書き）
- `bg_opacity` で透明度を調整（デフォルト 0.35）

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
│   ├── pdf_renderer.py       # ReportLab ベクター PDF 出力
│   ├── elements_pillow.py    # Pillow 用描画関数（要素単位）
│   ├── elements_pdf.py       # ReportLab 用描画関数（要素単位）
│   ├── text_utils.py         # 日本語テキスト処理（折り返し・フィット）
│   └── qr_generator.py       # URL → QR PIL Image
├── themes/
│   └── color_themes.py       # 5テーマ + カスタム定義
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
0%      37%  39.2%      60.8%    76.5%        100%
|  左   | 縦  |  プログラム  |メインタイトル| 右ストリップ |
|  カラム| バー|  エリア     | 縦書き帯     | 年度+第N部   |
```

| 定数 | 値 | 説明 |
|------|-----|------|
| `LEFT_W` | 0.370 | 左カラム幅 |
| `DIV_X` | 0.370 | 縦バー左端 X |
| `DIV_W` | 0.022 | 縦バー幅 |
| `PROG_X` | 0.392 | プログラムエリア左端 (= DIV_X + DIV_W) |
| `TITLE_X` | 0.608 | メインタイトル帯左端 |
| `TITLE_W` | 0.157 | メインタイトル帯幅 |
| `SECT_X` | 0.765 | 右ストリップ左端 (= TITLE_X + TITLE_W) |
| `SECT_W` | 0.235 | 右ストリップ幅 |
| `PROG_W` | ≈0.216 | プログラムエリア幅 (= TITLE_X - PROG_X) |

---

## 5. 縦方向レイアウト

| 定数 | 値 | 説明 |
|------|-----|------|
| `HEADER_H` | 0.030 | 上部バー高さ |
| `FOOTER_H` | 0.034 | 下部バー高さ |
| `PROG_TOP` | 0.180 | 動的レイアウト開始 Y（年度テキスト分の余白含む） |
| `PROG_BOT` | ≈0.958 | 動的レイアウト終了 Y |
| `PROG_H` | ≈0.778 | 動的レイアウト利用可能高さ |

**PROG_TOP = 0.180 の根拠**: 右ストリップ上部に "2025年度" を縦積み描画するため、
ヘッダー下（≈34px）からプログラム開始（≈202px）までの ≈168px が年度テキスト領域となる。

---

## 6. 描画レイヤー順（preview_renderer.py）

1. ベースキャンバス（クリームホワイト背景）
2. 背景イラスト（alpha blend, デフォルト opacity=0.35）
3. ヘッダーバー・フッターバー
4. 中央縦バー（テーマカラー）
5. **縦書きメインタイトル帯**（TITLE_X〜TITLE_X+TITLE_W）
6. **右ストリップ: 年度テキスト**（固定位置, PROG_TOP 以前）
7. 左カラム: 場所バッジ・会場名・住所・Zoom・日時・司会・座長・対象・QR
8. プログラムエリア: 参加費無料テキスト + 動的レイアウト（LayoutEngine）
9. **右ストリップ: 第N部ラベルボックス**（セクション Y 位置に合わせて動的配置）
10. 装飾イラスト（最前面）

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

`themes/color_themes.py` に 5テーマ + カスタムを定義。

| テーマキー | 季節 | 月の目安 |
|-----------|------|---------|
| `spring_pink` | 春（桜） | 3〜5月 |
| `early_summer_green` | 初夏（山） | 5〜6月 |
| `summer_blue` | 夏（銀河） | 7〜8月 |
| `autumn_orange` | 秋（紅葉） | 9〜11月 |
| `winter_christmas` | 冬（クリスマス） | 12〜2月 |
| `custom` | カスタム | 任意 |

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
```

フォントファイル: `assets/fonts/NotoSansJP/NotoSansJP-{weight}.otf`

**macOS 環境ではシステムの Hiragino フォント (`.ttc`) を優先的に使用する場合がある。**
テスト時は `ensure_fonts()` を必ず呼び出すこと。

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
#   テキスト・楕円バッジが個別選択可能であることを確認

# Streamlit アプリ起動
streamlit run app.py
# または 起動.command をダブルクリック（macOS）
```

---

## 13. 既知の注意事項・設計決定

- **縦書き実装**: 横書きで一時キャンバスに描画し `-90°` 回転（`rotate(-90, expand=True)`）。
  `rotate(90)` では逆向き（下から上）になるため注意。

- **PROG_TOP の値**: 年度テキスト用スペース確保のため `0.180`（デフォルト `0.038` から変更）。
  セクション数・コンテンツ量が多い場合、LayoutEngine は scale を下げて対応（最低 0.70）。

- **Streamlit 実行順序**: `app.py` は上から順に実行されるため、関数定義はすべて呼び出し箇所より前に配置すること。`_build_poster_data()` は `init_state()` の直後に定義。

- **第N部ラベルの短縮**: `draw_section_label_box` では "第X部" 部分のみ抽出して表示。
  "第2部（特別企画）" → "第2部" として縦積み。

- **DARK_BROWN のインポート**: `preview_renderer.py` では `from themes.color_themes import DARK_BROWN` をファイル末尾でインポートしている（循環インポート対策）。

- **右ストリップ年度テキストと第N部ボックスは独立して描画**: 年度テキストは step 6、ラベルボックスは step 9 で描画。layout 計算後にのみラベルボックスを描画できる。
