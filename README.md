# 学会プログラム → Notion 自動登録ツール

学会プログラムのWebページから発表情報を抽出し、Notionデータベースに一括登録するツールです。

現在は以下の学会に対応しています。学会ごとに構造が大きく異なっても、パーサークラスを
差し替えるだけで対応できる設計になっています。

- **NLP系（言語処理学会 年次大会, NLP 20XX）** … セッションコンテナ + テーブル構造
- **YANS（言語処理若手シンポジウム）** … はてなブログ形式の文書順フラット構造

## 特徴

- **汎用アーキテクチャ**: パーサー層は正規化データ型 `Presentation` を返す共通契約。学会固有の
  HTML構造はパーサークラスに閉じ込め、取得・登録層から独立。
- **設定駆動**: HTML取得元（`source`）、パース規則（`parsing`）、Notionプロパティ対応
  （`notion.property_map`）をすべて `config.yaml` で管理。
- **学会ごとにNotion DB分離**: 学会別にデータベースIDを指定可能。
- **非同期処理**: aiohttpによる並列処理で高速登録（799件を約6分で処理）。

## アーキテクチャ

```
models.py           # Presentation データクラス（パーサー ⇔ Notion登録 の共通契約）
config.py           # config.yaml の読込・アクティブ学会の選択・検証
sources.py          # プログラムHTMLの取得（ローカル/URL）と保存
notion_writer.py    # NotionWriter: property_map からプロパティ構築＋非同期バッチ登録
parsers/
├── base.py         # BaseConferenceParser（抽象基底クラス）
├── nlp2026.py      # NLP2026Parser（テーブル構造）
├── yans2026.py     # YANS2026Parser（文書順ステートフル走査）
└── factory.py      # create_parser（parser_class 名からインスタンス生成）
main.py             # エントリポイント（オーケストレーション + CLI）
fetch_html.py       # プログラムHTMLをローカル保存する開発用スクリプト
```

### 新しい学会に対応する場合

1. `parsers/` に新しいパーサークラスを作成し `BaseConferenceParser` を継承
2. `parse_program(soup) -> list[Presentation]` を実装（学会固有設定は `self.parsing` で参照）
3. `parsers/factory.py` の `_import_parsers()` に登録
4. `config.yaml` の `conferences.<id>` に `source` / `parsing` / `notion` を追加

既存パーサーで対応できる場合は 4 のみでOKです。

## セットアップ

### 1. 依存関係のインストール

```bash
uv sync
```

### 2. 環境変数の設定

`.env` ファイルを作成し、以下を設定：

```env
# Notion API設定
NOTION_TOKEN=your_notion_token_here

# 登録先データベース（学会ごとに分離する場合）
NLP_DATABASE_ID=your_nlp_database_id
YANS_DATABASE_ID=your_yans_database_id

# 上記が無い場合のフォールバック
DATABASE_ID=your_default_database_id
```

登録先DBは `config.yaml` の `notion.database_id`（直接指定）→ `notion.database_id_env`
（環境変数名）→ 環境変数 `DATABASE_ID` の順で解決されます。

### 3. 学会設定の作成

```bash
cp config.yaml.example config.yaml
```

`config.yaml` を編集して、対象の学会やアクティブ学会を調整します。

## 設定ファイル（config.yaml）の構造

各学会は `source` / `parsing` / `notion` の3ブロックで構成します。

```yaml
active_conference: yans2026     # --conference で上書き可能

conferences:
  yans2026:
    name: "第21回言語処理若手シンポジウム（YANS2026）"
    parser_class: "YANS2026Parser"
    year: 2026

    source:                     # HTML取得元
      url: "https://yans.anlp.jp/entry/yans2026program"
      local_file: "html/yans2026_program.html"
      use_local: true           # main.py --no-local でURL取得に切替

    parsing:                    # パーサー固有設定（パーサーが解釈）
      root: ".entry-content"
      day_header: "h2"          # 日付・会場
      slot_header: "h3"         # 時間帯・セッション名
      entry_list: "ul"         # 発表リスト
      session_filter: 'ポスターセッション|招待ポスター'
      date_pattern: '(\d+)/(\d+)\s*\([月火水木金土日]\)'
      venue_pattern: '(展示室[\d・]+)'
      time_pattern: '\[(\d+):(\d+)-(\d+):(\d+)\]'
      id_title_pattern: '^\[([^\]]+)\]\s*(.+)$'

    notion:
      database_id_env: "YANS_DATABASE_ID"
      property_map:             # Presentation の項目 → Notion プロパティ名/型
        title:        { name: "タイトル",   type: title }
        id:           { name: "ID",         type: rich_text }
        authors:      { name: "著者",       type: rich_text }
        session_name: { name: "セッション", type: rich_text }
        venue:        { name: "会場",       type: rich_text }
        date:         { name: "日時",       type: date }
```

NLP系（テーブル構造）の `parsing` は `selectors` / `table_structure` / `date_parsing` /
`cleanup` を使います。詳細は `config.yaml.example` を参照してください。

`property_map` の `type` は `title` / `rich_text` / `date` / `select` / `checkbox` に対応。
`date` 型は `Presentation.date_start` / `date_end` を使用します。

## 使用方法

### プログラムHTMLの取得（任意）

開発時にリクエストを減らすため、事前にHTMLをローカル保存できます。

```bash
uv run python fetch_html.py                      # アクティブ学会
uv run python fetch_html.py --conference yans2026 # 学会を指定
```

### Notion登録

```bash
uv run python main.py                        # アクティブ学会をローカルHTMLから登録
uv run python main.py --conference yans2026  # 学会を指定
uv run python main.py --no-local             # URLから直接取得して登録
uv run python main.py --dry-run              # 登録せずパース件数のみ確認
```

処理の流れ：

1. `config.yaml` から学会設定を読み込み（`--conference` で上書き可）
2. ローカルHTMLまたはURLからプログラムを取得
3. パーサーで発表情報（`Presentation`）を抽出
4. `NotionWriter` が `property_map` に従いプロパティを構築し、非同期一括登録

### Notionデータベースの設定

デフォルト設定では以下のプロパティを作成してください（`property_map` で変更可能）：

| プロパティ名 | タイプ | 説明 |
|------------|--------|------|
| タイトル | Title | 発表タイトル |
| ID | Text | 発表の識別子（例: P1-01 / S1-P01） |
| 著者 | Text | 発表者名（所属含む） |
| セッション | Text | セッション名 |
| 会場 | Text | 会場情報 |
| 日時 | Date | 発表の開始・終了時刻 |

**注意**: プロパティ名は `property_map` の `name` と完全に一致させる必要があります。

## パフォーマンス

- **並列処理**: 3並列で非同期処理（Notion APIレート制限: 3req/sec）

## トラブルシューティング

- **設定ファイルが見つからない** → `config.yaml.example` を `config.yaml` にコピー。
- **HTMLファイルが見つからない** → 先に `fetch_html.py` を実行、または `--no-local` でURL取得。
- **発見された発表数が 0** → `parsing` のセレクタ/正規表現を対象ページの構造に合わせて調整。
- **登録先DBが解決できない** → `notion.database_id_env` の環境変数か `DATABASE_ID` を設定。
- **Notion登録が失敗する** → プロパティ名が `property_map` と一致しているか、統合がDBに接続されているか確認。

## 開発 / テスト

```bash
# HTMLパースのテスト（Notion登録なし）
uv run python test_parse.py --conference yans2026

# Notion登録のテスト（先頭5件のみ）
uv run python test_notion.py --conference yans2026
```

## ライセンス

MIT License
