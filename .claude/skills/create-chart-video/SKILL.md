---
name: create-chart-video
description: CSVデータからショート動画（縦型MP4）を生成する。ユーザーがチャート動画を作りたいときに使用。bar_race / animated_bar / animated_line の3チャートタイプ対応。
---

# create-chart-video スキル

CSVを読み込んでデータを分析し、最適なチャートタイプを選んで縦型MP4動画（1080×1920px）を生成します。**Anthropic APIは不要** — Claude Code 自身がデータを分析します。

## 実行手順

### ステップ1: 依存ライブラリを確認する

```bash
cd "$CLAUDE_SKILL_DIR/../.." && python -c "import bar_chart_race, matplotlib, moviepy, pandas" 2>&1
```

エラーが出た場合は先に実行してください:
```bash
cd "$CLAUDE_SKILL_DIR/../.." && pip install -r requirements.txt
```

### ステップ2: CSVファイルを探す

プロジェクトルートと `data/` フォルダの両方を検索します:

```bash
find "$CLAUDE_SKILL_DIR/../.." -maxdepth 2 -name "*.csv" ! -name ".gitkeep" 2>/dev/null || echo "CSVファイルが見つかりません"
```

CSVが複数あればユーザーにどれを使うか確認します。見つからない場合は「`data/` フォルダかプロジェクトルートにCSVを置いてください」と案内して終了します。

### ステップ3: CSVを読んでデータを分析する

Read ツールでCSVファイルを開き、以下を把握します:

- **列名**: どの列がX軸（時系列や項目名）でどの列がY軸（数値）か
- **行数**: データ件数
- **時系列の有無**: 日付や月のような列があるか
- **カテゴリ数**: Y軸候補の列が何個あるか

### ステップ4: チャートタイプを選択する

以下の基準で判断してユーザーに提案します:

| チャートタイプ | 向いているデータ |
|---|---|
| `bar_race` | 時系列 × 複数カテゴリ（順位変動）← 最もバズりやすい |
| `animated_bar` | カテゴリ比較（時系列なし、または1時点のみ） |
| `animated_line` | 時系列推移（カテゴリ1〜2個） |

提案した内容をユーザーに確認し、変更があれば反映します。

### ステップ5: カラーテーマを選ぶ

ユーザーに投稿先を確認してテーマを提案します:

- `dark` — ダーク（YouTube Shorts向け・背景黒）
- `pastel` — パステル（TikTok向け・背景白・明るい色）
- `default` — デフォルト（汎用・matplotlib標準色）

### ステップ6: 動画を生成する

上記で決定した情報を引数に渡して実行します:

```bash
cd "$CLAUDE_SKILL_DIR/../.." && python main.py \
  --csv "<CSVファイルのパス>" \
  --chart-type "<bar_race|animated_bar|animated_line>" \
  --x-col "<X軸の列名>" \
  --y-cols "<Y軸列名1,Y軸列名2,...>" \
  --theme "<dark|pastel|default>"
```

生成完了後、`output/` ディレクトリに保存されたファイルパス・サイズ・動画尺をユーザーに伝えます。

## プロジェクトのフォルダ規約

このプロジェクトではデータとアウトプットをプロジェクト単位のサブフォルダで管理します:

```
data/
└── {プロジェクト名}/        ← CSVと events.csv をここにまとめる
    ├── my_data.csv
    └── events.csv           ← イベントアノテーション（任意）

output/
└── {csv_stem}/              ← 動画生成時に自動作成
    └── my_data_20260316.mp4
```

新しいデータを追加する場合は `data/新プロジェクト名/` フォルダを作成し、そこにCSVを置くよう案内してください。

## オプション: イベントアノテーション（animated_line のみ）

CSVと同じフォルダに `events.csv` を置くと、アニメーションがその年に達したときに縦線＋ラベルが自動表示されます。

```csv
period,text
1991,バブル崩壊
2008,リーマンショック
2020,コロナ禍
```

- `period` はX軸の値と一致させる（データに存在しない値は最近傍に自動スナップ）
- ユーザーがイベントを追加したい場合は、このファイルを編集するよう案内する

## トラブルシューティング

| 症状 | 対処 |
|------|------|
| `FFmpeg が見つかりません` | `pip install imageio-ffmpeg` を実行 |
| `CSVファイルが見つかりません` | `data/` フォルダかプロジェクトルートにCSVを配置して再実行 |
| ライブラリが見つからない | `pip install -r requirements.txt` を実行 |
| メモリ不足 | CSVの行数を減らすか、`--output-dir` で空き容量の多い場所を指定 |
