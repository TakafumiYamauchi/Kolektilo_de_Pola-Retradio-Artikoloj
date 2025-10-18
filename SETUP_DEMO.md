# Pola Retradio スクレイピングツール - セットアップ＆実演ガイド

## 概要

このツールは、[Pola Retradio](https://pola-retradio.org/)（ポーランドのエスペラント語ラジオサイト）から指定期間の記事を自動収集し、本文を統合して複数の形式で出力するツールです。

## 主な機能

- ✅ **期間指定での完全収集**: RSS/Feed と月別アーカイブの両方から収集
- ✅ **本文抽出に最適化**: WordPress + Elegant Themes構造に対応
- ✅ **複数の出力形式**: Markdown / TXT / CSV / JSONL
- ✅ **低負荷設計**: User-Agent明示、遅延設定、HTTPリトライ対応
- ✅ **2つのインターフェース**: CLI（コマンドライン）とStreamlit（ブラウザUI）

## セットアップ手順

### 1. 必要な環境

- Python 3.9以上
- インターネット接続

### 2. 依存パッケージのインストール

```bash
cd /home/y/my_work_202510/Pola\ Retradio/GPT5pro
source ../.venv/bin/activate
pip install -r requirements.txt
```

### 3. インストールされるパッケージ

- requests: HTTP通信
- beautifulsoup4 / lxml: HTMLパース
- feedparser: RSSフィード解析
- dateparser / python-dateutil: 日付解析（エスペラント対応）
- tqdm: プログレスバー
- streamlit / pandas: ブラウザUI用
- requests-cache: HTTPキャッシュ（オプション）

## 使用方法

### 方法1: CLIツール（コマンドライン）

#### 基本的な使い方

```bash
python scraper.py --start 2025-10-15 --end 2025-10-17 --out output --throttle 2.0
```

#### 主なオプション

- `--start YYYY-MM-DD`: 開始日（必須）
- `--end YYYY-MM-DD`: 終了日（必須）
- `--out DIR`: 出力ディレクトリ（デフォルト: output）
- `--method both|feed|archive`: 収集方法（デフォルト: both）
- `--throttle SECONDS`: リクエスト間隔（秒）（デフォルト: 1.0）
- `--max-pages N`: ページ送りの最大回数
- `--include-audio`: MP3等の音声リンクも記録
- `--no-cache`: HTTPキャッシュを無効化

#### 実行例

```bash
# 2025年10月15日から10月17日までの記事を収集
python scraper.py --start 2025-10-15 --end 2025-10-17 --out output --throttle 2.0
```

#### 出力ファイル

`output/`ディレクトリに以下のファイルが生成されます：

- `pola_retradio_2025-10-15_2025-10-17.md` - Markdown形式
- `pola_retradio_2025-10-15_2025-10-17.txt` - テキスト形式
- `pola_retradio_2025-10-15_2025-10-17.csv` - CSV形式
- `pola_retradio_2025-10-15_2025-10-17.jsonl` - JSONL形式

### 方法2: Streamlit UI（ブラウザ）

#### 起動方法

```bash
streamlit run streamlit_app.py --server.port=8502
```

#### アクセス

ブラウザで以下のいずれかのURLにアクセス：

- ローカル: http://localhost:8502
- ネットワーク: http://172.22.159.198:8502
- 外部: http://61.89.29.12:8502

#### 操作方法

1. **開始日**と**終了日**を選択
2. **収集方法**を選択（both/feed/archive）
3. **リクエスト間隔**を設定（推奨: 1.0秒以上）
4. 「収集を実行する」ボタンをクリック
5. テーブル形式で結果を確認
6. Markdown/TXT/CSV/JSONLのダウンロードボタンからファイルをダウンロード

## 実演結果

### CLI実行結果

```
[INFO] URL 収集中: 2025-10-15 ～ 2025-10-17 (both)
[INFO] 候補 URL: 20 件
[1/20] Fetch: https://pola-retradio.org/2025/09/lodzo-de-multaj-kulturoj/
...
[20/20] Fetch: https://pola-retradio.org/2025/10/e_elsendo-el-la-15-10-2025/
[INFO] 抽出完了: 19 本
[DONE] MD: output/pola_retradio_2025-10-15_2025-10-17.md
[DONE] TXT: output/pola_retradio_2025-10-15_2025-10-17.txt
[DONE] CSV: output/pola_retradio_2025-10-15_2025-10-17.csv
[DONE] JSONL: output/pola_retradio_2025-10-15_2025-10-17.jsonl
```

### 生成されたファイルサイズ

```
-rw-r--r-- 1 y y 4.2K pola_retradio_2025-10-15_2025-10-17.csv
-rw-r--r-- 1 y y  36K pola_retradio_2025-10-15_2025-10-17.jsonl
-rw-r--r-- 1 y y  34K pola_retradio_2025-10-15_2025-10-17.md
-rw-r--r-- 1 y y  33K pola_retradio_2025-10-15_2025-10-17.txt
```

## 実装の工夫

### タイムゾーン処理の修正

オリジナルのコードにはタイムゾーン対応/非対応のdatetimeオブジェクト間の比較エラーがありました。以下の箇所を修正：

1. **retradio_lib.py**（重複排除とソート処理）
2. **scraper.py**（記事のソート処理）
3. **streamlit_app.py**（記事のソート処理）

修正方法：タイムゾーン情報を削除して統一的に比較できるようにしました。

```python
# 修正後のコード例
def sort_key(a):
    if a.published:
        pub_naive = a.published.replace(tzinfo=None) if a.published.tzinfo else a.published
        return (pub_naive, a.url)
    return (datetime.max, a.url)
```

## トラブルシューティング

### ポートが使用中の場合

```bash
# 別のポートを指定
streamlit run streamlit_app.py --server.port=8503
```

### 古い投稿が拾えない場合

```bash
# アーカイブ中心の収集に切り替え
python scraper.py --start 2025-10-01 --end 2025-10-15 --method archive --max-pages 10
```

### 本文が短い/空の場合

`retradio_lib.py`の本文セレクタを追加・調整してください。

## 注意事項

### 著作権・利用規約

- 収集対象のコンテンツはPola Retradioの著作物です
- **個人の学習・研究用途**での利用を推奨します
- サイトの利用規約とrobots.txtを確認してください

### 負荷への配慮

- `--throttle`を1秒以上に設定してください（推奨: 2.0秒）
- 長期間の一括収集は避け、月単位で分割してください
- 深夜帯など、サーバーへの負荷が少ない時間帯の利用を検討してください

## ライセンス

MIT License - 詳細は`LICENSE`ファイルを参照

## クレジット

- オリジナル作者: ChatGPT (GPT-5 Pro)
- 修正・実演: Claude (Sonnet 4.5)

## 参考リンク

- [Pola Retradio公式サイト](https://pola-retradio.org/)
- [Streamlit Documentation](https://docs.streamlit.io/)
