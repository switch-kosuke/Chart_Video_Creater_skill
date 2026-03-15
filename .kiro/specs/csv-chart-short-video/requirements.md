# 要件定義書

## はじめに

CSVデータからアニメーション付きチャート動画を生成するPythonアプリケーション。
TikTok・YouTube Shortsなどのショート動画プラットフォームに最適化した縦型（9:16）・短尺フォーマットで、データの変化を視覚的かつ魅力的に表現する動画を自動生成する。
Claude Code のカスタムスキル（`/create-chart-video`）として実行でき、AIがデータを分析して最適なチャートタイプを自動選択するインタラクティブなUXを提供する。

また、`events.csv` で特定バーへのイベント吹き出しアノテーションを動画上に表示できる。

---

## 要件

### 要件 1: CSVファイルの自動検出と選択

**目的:** 動画クリエイターとして、コマンドを叩くだけでCSVファイルを自動検出してほしい。それにより、ファイルパスを毎回入力する手間なく動画生成を開始できる。

#### 受け入れ基準
1. When ユーザーが `/create-chart-video` を実行した場合, the ChartVideoApp shall カレントディレクトリ内のCSVファイルを自動検出し、番号付きリストで表示する
2. If カレントディレクトリにCSVファイルが1つだけ存在する場合, the ChartVideoApp shall 自動的にそのファイルを選択してユーザーに通知する
3. If カレントディレクトリにCSVファイルが存在しない場合, the ChartVideoApp shall CSVファイルが見つからない旨のエラーメッセージとファイルの配置方法を表示する
4. When ユーザーが番号またはファイル名でCSVを選択した場合, the ChartVideoApp shall 選択されたファイルを読み込みデータ分析フェーズへ進む
5. The ChartVideoApp shall UTF-8およびShift-JISエンコーディングのCSVファイルを処理できる

---

### 要件 2: AIによるデータ分析とチャートタイプ自動選択

**目的:** 動画クリエイターとして、AIにデータを分析させて最適なチャートタイプを選んでほしい。それにより、視聴者を最も引き付ける動画を専門知識なしに作れる。

#### 受け入れ基準
1. When CSVファイルが選択された場合, the ChartVideoApp shall データの構造（列数・行数・データ型・時系列有無・カテゴリ数）を分析する
2. When データ分析が完了した場合, the ChartVideoApp shall 分析結果に基づいて最適なチャートタイプを1つ選択し、選択理由を一言で表示する
3. The ChartVideoApp shall 少なくとも以下のチャートタイプから選択できる: バーレースチャート（時系列×順位変動）、棒グラフアニメーション（カテゴリ比較）、折れ線グラフアニメーション（時系列推移）
4. The ChartVideoApp shall AIによる推薦チャートタイプと推薦理由を表示した上で、ユーザーが確認または変更できる
5. If データがチャート生成に不適切な形式の場合, the ChartVideoApp shall 具体的な問題点と修正方法をユーザーに提示する

---

### 要件 3: カラーテーマ選択

**目的:** 動画クリエイターとして、投稿先プラットフォームに合ったカラーテーマを簡単に選びたい。それにより、プラットフォームの視聴者層に刺さるビジュアルを実現できる。

#### 受け入れ基準
1. The ChartVideoApp shall 少なくとも以下のカラーテーマを提供する: ダーク（YouTube向け）、パステル（TikTok向け）、デフォルト（汎用）
2. When ユーザーがテーマを選択した場合, the ChartVideoApp shall 選択されたテーマを適用して動画生成を開始する
3. If ユーザーがテーマ選択をスキップした場合, the ChartVideoApp shall デフォルトテーマを自動適用する
4. The ChartVideoApp shall 各テーマの用途説明（例: "YouTube向け"）を選択肢と一緒に表示する

---

### 要件 4: アニメーション付きチャート動画の生成

**目的:** 動画クリエイターとして、視聴者を引き付けるアニメーションが付いた動画を自動生成してほしい。それにより、手動での動画編集なしに高品質なショート動画を量産できる。

#### 受け入れ基準
1. The ChartVideoApp shall データの各ステップ間をスムーズに補間（イージング）したアニメーションを生成する
2. When バーレースチャートが選択された場合, the ChartVideoApp shall 各フレームでデータ値に基づいてバーの順位を動的に並び替える
3. The ChartVideoApp shall 縦型フォーマット（1080×1920px、9:16アスペクト比）のMP4動画を生成する
4. The ChartVideoApp shall 動画の冒頭・末尾にフェードイン・フェードアウト効果を自動適用する
5. The ChartVideoApp shall デフォルト30秒・30fpsの動画を生成する
6. While 動画生成中, the ChartVideoApp shall 進捗状況をプログレスバーで表示する

---

### 要件 5: 動画ファイルの出力

**目的:** 動画クリエイターとして、生成完了後すぐに使えるMP4ファイルを受け取りたい。それにより、SNSへの投稿作業にすぐ移れる。

#### 受け入れ基準
1. The ChartVideoApp shall `output/` ディレクトリにMP4形式で動画を保存する
2. If `output/` ディレクトリが存在しない場合, the ChartVideoApp shall 自動的にディレクトリを作成する
3. The ChartVideoApp shall 出力ファイル名を `{元のCSVファイル名}_{YYYYMMDD}.mp4` の形式で自動命名する
4. When 動画の生成が完了した場合, the ChartVideoApp shall 出力ファイルパス・ファイルサイズ・動画尺を表示する
5. The ChartVideoApp shall 出力動画のファイルサイズを20MB以下に最適化する

---

### 要件 6: イベントアノテーション（吹き出し）

**目的:** 動画クリエイターとして、特定のバーで起きた出来事を吹き出しで表示したい。それにより、データの変化の「なぜ」を視聴者に伝えられる動画が作れる。

#### 受け入れ基準
1. The ChartVideoApp shall `events.csv`（`period`, `category`, `text` 列）を読み込み、メイン CSV の日付と照合してアノテーションを生成する
2. When 該当フレームに達した場合, the ChartVideoApp shall 指定カテゴリのバー右端に矢印付き吹き出しをフェードインで表示する
3. The ChartVideoApp shall 吹き出しを約30フレーム（1秒）表示した後にフェードアウトする
4. The ChartVideoApp shall 吹き出しのデザインを半透明の角丸ボックス + バーへの矢印（`ax.annotate`）で実装する
5. If `events.csv` が存在しない場合, the ChartVideoApp shall アノテーションなしで通常通り動画を生成する
6. The ChartVideoApp shall 縦型フォーマット（1080×1920px）に収まるようテキストを折り返し表示する

---

### 要件 7: Claude Code カスタムスキルとしての実行

**目的:** Claude Code ユーザーとして、`/create-chart-video` というスラッシュコマンドで全工程を実行したい。それにより、ターミナル操作に慣れていなくても直感的に動画生成できる。

#### 受け入れ基準
1. The ChartVideoApp shall Claude Code のカスタムスキル（`.claude/skills/create-chart-video.md`）として定義され、`/create-chart-video` コマンドで起動できる
2. The ChartVideoApp shall スキル実行時にPythonスクリプトを呼び出してインタラクティブなフローを開始する
3. When ユーザーが各ステップで入力を求められる場合, the ChartVideoApp shall 選択肢を明確に番号付きで表示する
4. The ChartVideoApp shall 各ステップでユーザーが「スキップ」または「デフォルト値で続行」を選択できる
5. If Pythonの実行環境または必要なライブラリが不足している場合, the ChartVideoApp shall セットアップ手順をユーザーに案内する
6. When `events.csv` がカレントディレクトリに存在する場合, the ChartVideoApp shall 自動的に読み込んでアノテーション付き動画を生成することをユーザーに通知する
