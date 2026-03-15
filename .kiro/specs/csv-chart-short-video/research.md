# リサーチ & 設計決定ログ

---
**Purpose**: csv-chart-short-video の設計調査と技術的意思決定の記録

---

## サマリー

- **Feature**: `csv-chart-short-video`
- **Discovery Scope**: New Feature（グリーンフィールド）
- **主要な発見**:
  - `bar_chart_race` ライブラリがバーレースチャートに最適（専用ライブラリ、シンプルAPI）
  - 汎用アニメーションは `matplotlib.animation.FuncAnimation` + FFmpegWriter で対応
  - 1080×1920（9:16）の縦型出力は `figsize=(10.8, 19.2)` + `dpi=100` で実現
  - フェード効果など高度な合成は `moviepy` が有用
  - Claude API（`anthropic` SDK）でデータ分析・チャートタイプ推薦が実装可能
  - Claude Code スキルは `.claude/skills/{name}/SKILL.md` にフロントマター形式で定義

---

## リサーチログ

### チャートアニメーションライブラリの選定

- **Context**: 複数チャートタイプ（棒グラフ、折れ線、バーレース）に対応する必要がある
- **Sources Consulted**:
  - bar_chart_race PyPI / GitHub
  - matplotlib animation 公式ドキュメント
  - plotly animations 公式ドキュメント
- **Findings**:
  - `bar_chart_race` はバーレース専用。シンプルな API で MP4 出力可能。matplotlib バックエンド使用。
  - `matplotlib.animation.FuncAnimation` は汎用。棒グラフ・折れ線どちらも対応。手動実装が必要。
  - `plotly` は Web 向け。MP4 直接出力には Kaleido など追加ツールが必要で複雑。
- **Implications**: バーレースは `bar_chart_race`、それ以外は `matplotlib` で使い分けるハイブリッド設計が最適

### 動画レンダリング（MP4出力）

- **Context**: 生成したアニメーションを MP4 形式で出力する必要がある
- **Sources Consulted**: imageio-ffmpeg PyPI、matplotlib FFMpegWriter ドキュメント、moviepy ドキュメント
- **Findings**:
  - `matplotlib.animation.FFMpegWriter` が最もシンプルで直接的
  - `imageio_ffmpeg` はクロスプラットフォームで FFmpeg バイナリを自動管理
  - `moviepy` はフェードイン・アウト、テキストオーバーレイなど高度な合成に優れる
  - H.264 コーデック（`libx264`）+ ビットレート 3000kbps で 20MB 以下の MP4 が実現可能
- **Implications**: 基本フローは `FFMpegWriter`、フェード効果は `moviepy` で後処理する2段階構成が最善

### 縦型フォーマット（1080×1920）

- **Context**: TikTok/YouTube Shorts 向けに 9:16 縦型フォーマットが必要
- **Findings**:
  - matplotlib: `figsize=(10.8, 19.2)`, `dpi=100` → 1080×1920px
  - FFmpeg コーデックは 2 の倍数解像度を要求するが 1080×1920 は問題なし
  - `bar_chart_race` の `figsize` パラメータで同様に縦型指定可能
- **Implications**: 全チャートジェネレーターに統一して `figsize=(10.8, 19.2)`, `dpi=100` を適用

### Claude API による AI データ分析

- **Context**: CSV データを解析してチャートタイプを自動推薦する AI 機能が必要
- **Sources Consulted**: anthropic Python SDK 公式ドキュメント
- **Findings**:
  - `anthropic` SDK の `client.messages.create()` でシンプルにメッセージ送受信可能
  - データ構造（列名・型・行数・時系列有無）を JSON でプロンプトに含めると精度が高い
  - `claude-haiku-4-5-20251001` は高速・低コストで分析タスクに適切
  - 構造化出力（JSON形式）を指定することで推薦結果のパースが容易
- **Implications**: DataAnalyzer コンポーネントが CSV メタデータを構造化して Claude に送信し、JSON 形式で推薦を受け取る設計が安定

### Claude Code スキル定義

- **Context**: `/create-chart-video` スラッシュコマンドとして実行できるスキルが必要
- **Sources Consulted**: Claude Code Skills ドキュメント
- **Findings**:
  - スキルは `.claude/skills/{name}/SKILL.md` に YAML フロントマター + Markdown 形式で定義
  - `$ARGUMENTS` で引数、`${CLAUDE_SKILL_DIR}` でスクリプトパスを参照可能
  - `allowed-tools` でスキルが使用可能なツールを制限できる
  - スキルは Python スクリプトを Bash ツールで呼び出せる
- **Implications**: スキルは薄いオーケストレーター層として定義し、実ロジックは Python に委譲する設計

---

## アーキテクチャパターン評価

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| パイプライン型 | CSV読み込み→分析→生成→出力の一方向フロー | シンプル、各ステージが独立してテスト可能 | 途中キャンセルの実装が必要 | 採用 |
| イベント駆動型 | 各ステージをイベントで疎結合 | 拡張性高い | 今回の規模には過剰 | 不採用 |
| モノリシックスクリプト | 1ファイルで全処理 | 手軽 | テスト困難、保守性低 | 不採用 |

---

## 設計決定

### Decision: チャートアニメーションライブラリのハイブリッド使用

- **Context**: 複数チャートタイプをサポートしつつ、バーレースの高品質な実装が必要
- **Alternatives Considered**:
  1. `bar_chart_race` のみ — バーレース以外に対応不可
  2. `matplotlib` のみ — バーレースを手動実装する必要あり
  3. `bar_chart_race` + `matplotlib` — ハイブリッド
- **Selected Approach**: `bar_chart_race`（バーレース）+ `matplotlib FuncAnimation`（棒グラフ・折れ線）
- **Rationale**: 各ライブラリの強みを活かし、全要件のチャートタイプをカバーできる
- **Trade-offs**: 依存ライブラリが増えるが、コード品質と保守性が向上
- **Follow-up**: `bar_chart_race` と `matplotlib` の figsize/dpi 設定を統一するユーティリティが必要

### Decision: 動画後処理に moviepy を採用

- **Context**: フェードイン・アウト効果（要件 4.4）の実装方法
- **Alternatives Considered**:
  1. matplotlib で手動フレーム合成 — 実装複雑
  2. moviepy で後処理 — シンプルな API で実現可能
  3. FFmpeg コマンド直接呼び出し — 依存性管理が困難
- **Selected Approach**: matplotlib/bar_chart_race で生成した一時 MP4 を moviepy で後処理
- **Rationale**: moviepy は Python ネイティブで扱いやすく、フェード効果を数行で実装可能
- **Trade-offs**: 一時ファイルが発生するが、処理後に削除

### Decision: AI モデルに claude-haiku を使用

- **Context**: CSV データ分析とチャートタイプ推薦に AI を使用する
- **Alternatives Considered**:
  1. `claude-opus-4-6` — 最高品質だが遅くコスト高
  2. `claude-haiku-4-5-20251001` — 高速・低コスト、分析タスクに十分な精度
  3. ルールベース分類 — AI 不使用、精度が低い
- **Selected Approach**: `claude-haiku-4-5-20251001`
- **Rationale**: データ構造分析・チャートタイプ推薦は軽量タスクのため Haiku で十分
- **Trade-offs**: 高度な自然言語理解が必要な場合は Sonnet/Opus にフォールバック可能

---

## リスクと緩和策

- FFmpeg が未インストール — `imageio_ffmpeg` で自動管理。インストール確認処理を追加
- Claude API キー未設定 — 起動時に `ANTHROPIC_API_KEY` 環境変数チェック、未設定なら設定手順を表示
- bar_chart_race の figsize とチャートレイアウトの不整合 — 共通の `VerticalVideoConfig` 値クラスで統一
- 大容量 CSV（10000行以上）での処理遅延 — 分析用にサンプリング（先頭100行）してAI送信

---

## 参考文献

- [bar-chart-race GitHub](https://github.com/dexplo/bar_chart_race)
- [matplotlib animation 公式](https://matplotlib.org/stable/users/explain/animations/animations.html)
- [moviepy 公式](https://zulko.github.io/moviepy/)
- [anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python)
- [Claude Code Skills ドキュメント](https://docs.anthropic.com/en/docs/claude-code/skills)
