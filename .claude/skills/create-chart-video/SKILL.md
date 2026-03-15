---
name: create-chart-video
description: CSVデータからショート動画（縦型MP4）を生成する。ユーザーがチャート動画を作りたいときに使用。bar_race / animated_bar / animated_line の3チャートタイプ対応。
allowed-tools: Bash, Read
---

# create-chart-video スキル

カレントディレクトリの CSV ファイルを読み込み、AI がデータを分析して最適なチャートタイプを推薦し、縦型 MP4 動画（1080×1920px）を生成します。

## セットアップ確認

まず Python 環境と必要ライブラリを確認します。

```bash
python --version 2>&1 || echo "ERROR: Python が見つかりません"
```

必要ライブラリが未インストールの場合はセットアップします。

```bash
cd "$CLAUDE_SKILL_DIR/../.." && python -c "import bar_chart_race, matplotlib, moviepy, pandas, anthropic" 2>&1 | grep -q "ModuleNotFoundError" && echo "⚠️ 依存ライブラリが不足しています。インストールします..." && pip install -r requirements.txt
```

## 動画生成の実行

```bash
cd "$CLAUDE_SKILL_DIR/../.." && python main.py
```

## 使い方

1. チャート動画を生成したい CSV ファイルをカレントディレクトリに置く
2. `/create-chart-video` を実行する
3. 対話形式でチャートタイプ・カラーテーマを選択する
4. `output/` ディレクトリに MP4 が生成される

## 前提条件

- `ANTHROPIC_API_KEY` 環境変数が設定済みであること
- FFmpeg がインストール済みであること（`pip install imageio-ffmpeg` で導入可能）

## トラブルシューティング

| 症状 | 対処 |
|------|------|
| `ANTHROPIC_API_KEY が設定されていません` | `export ANTHROPIC_API_KEY='your-key'` を実行 |
| `FFmpeg が見つかりません` | `pip install imageio-ffmpeg` を実行 |
| `CSVファイルが見つかりません` | CSV をカレントディレクトリに配置して再実行 |
| ライブラリが見つからない | `pip install -r requirements.txt` を実行 |
