# 📻 Pola Retradio 記事収集・統合ツール

**対象サイト**: [https://pola-retradio.org/](https://pola-retradio.org/)

Pola Retradio（ポーラ・レトラディオ）公式サイトに掲載された **エスペラント記事** を、
**指定した期間** に基づいて **漏れなく収集** し、本文を **1つの文書にまとめて出力** するためのツール一式です。  
**Streamlit のオンラインアプリ**としても、**ローカルのシンプルな CLI** としても動作します。

---

## 主な特徴

- ✅ **期間指定での完全収集**：RSS/Feed と **月別アーカイブ**の HTML を併用して URL を洗い出し、取りこぼしを最小化。
- ✅ **本文抽出に最適化**：WordPress + Elegant Themes 系の構造に合わせ、本文（エスペラント）だけを丁寧に抽出。
- ✅ **複数の出力形式**：Markdown / TXT / CSV / JSONL を同時に出力。
- ✅ **低負荷＆安定運用**：User-Agent 明示・遅延（throttle）・HTTP リトライ・オプションのキャッシュに対応。
- ✅ **どこでも動作**：Streamlit（無料の Community Cloud でも可） or ローカル Python さえあればOK。

> サイト側には [RSS フィード](/feed/) や、**月別アーカイブ（/YYYY/MM/）** が用意されています。本ツールは両方を活用してURLを収集します。

---

## 1) かんたんお試し（ローカル CLI）

1. Python 3.9+ を用意します（Windows/Mac/Linux いずれも可）。
2. このフォルダで依存をインストール：
   ```bash
   pip install -r requirements.txt
   ```
3. 期間を指定して実行：
   ```bash
   python scraper.py --start 2025-10-01 --end 2025-10-15 --out output
   ```
   - URL 収集方式は `--method both`（既定）、`feed`、`archive` から選べます。
   - 1 リクエストごとの間隔は `--throttle`（秒、既定は 1.0）。
   - MP3 などの音声リンクも記録したい場合は `--include-audio`。
   - `--days 30` のように指定すると「終了日から過去30日分」を簡単に取得できます（`--end` を省略した場合は今日が終了日になります）。
   - `--split-by year` で年ごとに、`--split-by month` で年月ごとに出力ファイルを自動分割できます。長期間（例: 2011年以降の全記事）を取得する際に便利です。
     ```bash
     # 2011年から現在までを年単位で分割して出力
     python scraper.py --start 2011-01-01 --end 2025-12-31 --split-by year --out archive --throttle 1.0
     ```
   - 実行ログには feed / archive から収集できた件数、重複除去数、期間外として除外した件数、処理時間（URL 収集・本文取得の内訳）がまとめて表示されます。

4. `output/` に以下が生成されます：
   - `pola_retradio_YYYY-MM-DD_YYYY-MM-DD.md`（統合 Markdown）
   - `... .txt` / `... .csv` / `... .jsonl`

> **注意**: 長い期間（例：2011年〜現在）を一度に収集する場合、取得に時間がかかります。`--split-by year` 等を活用してファイルを分割しつつ、必要に応じて `--throttle` を大きめに設定してください。

---

## 2) Streamlit アプリ（オンラインでもローカルでも）

- ローカルで起動：
  ```bash
  streamlit run streamlit_app.py
  ```
  ブラウザに UI が開きます。開始日・終了日を選んで「収集を実行する」を押すと、
  テーブル表示と **Markdown/TXT/CSV/JSONL のダウンロードボタン**が現れます。
  feed / archive の内訳や除外件数、公開日の最小・最大値も画面上に表示されます。

### 多言語 UI（参考）

ユーザー向け表示のみを多言語化したバージョンを同梱しています（内部ロジックは同一）。

- 韓国語版（KO）
  ```bash
  streamlit run GPT5pro/streamlit_app_ko.py
  ```
- エスペラント版（EO）
  ```bash
  streamlit run GPT5pro/streamlit_app_eo.py
  ```

- **Streamlit Community Cloud** にデプロイする場合：
  1. 本リポジトリ（このフォルダ）を GitHub にプッシュ
  2. Streamlit Cloud で 「New app」→ リポジトリを選択 → `streamlit_app.py` をエントリに指定
  3. そのままデプロイ（無料枠で可）

---

## 抽出の仕組み（確実性を高める工夫）

- **RSS フィード**：`/feed/?paged=N` を自動でたどり、アイテムの公開日とリンクを収集します。
- フィードから取得できる `content:encoded` を優先的に利用し、十分な本文がある場合はページ本体へのアクセスを省略します（公開日が範囲外のときのみページにアクセスして再確認）。
- **月別アーカイブ**：`/YYYY/MM/` を **月ごと** に巡回し、必要があれば `page/2/` 以降も追跡します。
- **日付の判定**：`<time>` 要素 → 記事内のメタ → URL/タイトルの数値やエスペラント月名から自動推定。  
  例: `E_elsendo el la 15.10.2025` / `Oktobro 5, 2025` など。
- **本文抽出**：`.entry-content` / `.post-content` / `.et_pb_post_content` / `.et_pb_text_inner` などを優先し、
  見出し・段落・リストをテキスト化。共有ボタンやコメント案内等は除外。

---

## オプションと拡張

- `--max-pages N`：フィードやアーカイブのページ送りを **N ページ**までに制限。
- `--no-cache`   ：HTTP キャッシュ（requests-cache）を使わない。
- `--include-audio`：本文のメタに `mp3` 等の音声リンクも併記。
- `--split-by {none,year,month}`：長期間を扱うときに出力ファイルを分割（デフォルトは `none`）。
- 生成物の並び順は **公開日**（不明な場合は URL）でソート。

---

## ライセンスと利用上の注意

- 本ツールは **MIT License** で配布します（下記参照）。
- 収集対象のコンテンツは Pola Retradio の著作物です。**個人の学習・研究用途**での利用を推奨します。
- 公開情報の取得とはいえ、**robots.txt** やサイトの**利用規約**に留意し、**低負荷**を保ってください。
- 大量取得時は `--throttle` を十分に長く取る、期間を分割する、深夜帯を避ける等の配慮をお願いします。

---

## トラブルシュート

- **古い投稿が拾えない**：`--method archive` で月別アーカイブ巡回を中心に、`--max-pages` を緩めて再実行。
- **本文が短い/空**：テーマ変更等でクラス名が変わることがあります。`retradio_lib.py` の抽出セレクタを追加してください。
- **Windows で lxml のビルドに失敗**：近年は wheel 配布が整備されています。`pip` を最新化してから再試行してください。

---

## 既知の仕様

- WordPress 側の **RSS フィード**や**月別アーカイブ**の存在はサイトに確認できます。  
  トップページのサイドバーに **「Arkivoj（アーカイブ）」「RSS」** の記載があります。
  - 例: トップのページ下部に「Arkivoj（月別一覧）」と「RSS」のリンク（サイト右欄）。
- 本ツールは **特定のカテゴリー**のみを対象にする機能も拡張可能です（必要ならご相談ください）。

---

## クレジット

- 作者: ChatGPT (GPT-5 Pro) が生成した参照実装。

MIT License の全文は `LICENSE` を参照してください。
