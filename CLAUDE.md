# CLAUDE.md

学会プログラムのWebページから発表情報を抽出し、Notionデータベースへ一括登録するツール。
現在は **NLP系（言語処理学会 年次大会 NLP 20XX）** と **YANS（言語処理若手シンポジウム）** に対応。

## コマンド

```bash
uv sync                                          # 依存インストール（Python 3.13, uv 管理）
uv run python init_db.py --conference <id> --parent-page <page_id>  # Notion DB を自動作成（初回のみ）
uv run python fetch_html.py --conference <id>    # プログラムHTMLを html/ に保存（開発用）
uv run python test_parse.py --conference <id>    # パースのみ検証（Notion登録なし）
uv run python test_notion.py --conference <id>   # 先頭5件だけ登録テスト
uv run python main.py --conference <id>          # 本番一括登録
uv run python main.py --dry-run                  # 登録せず件数のみ
uv run python main.py --no-local                 # ローカルHTMLでなくURLから取得
```

`--conference` 省略時は `config.yaml` の `active_conference` を使用。

## アーキテクチャ

レイヤ分割し、パーサー層は正規化データ型 `Presentation` を返す**共通契約**とする。
取得層・登録層は `Presentation` のみに依存し、学会ごとの差異を意識しない。

```
models.py         Presentation データクラス（パーサー ⇔ Notion登録 の契約）
config.py         config.yaml 読込・アクティブ学会選択・検証
sources.py        HTML取得（ローカル/URL）と保存。ファイル名/URLは config 駆動
notion_writer.py  NotionWriter: property_map 駆動でプロパティ構築 + 非同期バッチ登録
notion_schema.py  property_map から Notion DB を自動作成（init_db.py が使用）
parsers/
  base.py         BaseConferenceParser（抽象）。self.parsing で学会固有設定を参照
  nlp2026.py      NLP2026Parser（テーブル構造）
  yans2026.py     YANS2026Parser（文書順ステートフル走査）
  factory.py      parser_class 名 → インスタンス生成（_import_parsers で登録）
main.py           エントリポイント（オーケストレーション + argparse）
fetch_html.py     開発用HTML保存スクリプト
```

各学会設定は `source` / `parsing` / `notion` の3ブロック（`config.yaml.example` 参照）。
`parsing` の中身はパーサーが自由に解釈する（スキーマは共通化しない）。

## 設計判断（重要 — 変更前に読むこと）

- **なぜ `Presentation` 契約を導入したか**: 学会ごとにHTML構造が根本的に異なるため、
  「ゆるい dict」でなく型付きの中間表現で取得層と登録層を分離した。登録層は構造差を知らない。
- **なぜ `parsing` ブロックを parser 固有にしたか**: 旧設計は `selectors`/`table_structure`
  という **NLP固有のテーブル前提** を全学会共通スキーマとして強制しており、これが汎用化の障害だった。
  構造が違う学会（YANS）は表現不能。→ `parsing` は各パーサーが解釈する自由形式に変更。
  共通スキーマを再導入して汎用化を後退させないこと。
- **NLP と YANS で走査モデルが根本的に違う**:
  - NLP: `div.session*` コンテナごとに header + `<table>`（2行1組: ID+タイトル / 著者）。
    日時・会場はセッションヘッダ内に完結。
  - YANS: はてなブログ。`<div class="entry-content">` 内にフラットな文書順で
    `<h2>`(日付・会場) → `<h3>`(時間帯・セッション名) → `<ul><li><p>[ID] タイトル<br>著者</p>`。
    **日付・時間・発表が別要素にまたがる**ため、文書順に状態（日付/会場/セッション/時刻）を
    保持しながら走査する（`YANS2026Parser`）。セッション連番や日付跨りは文書順から自然に導出され
    ハードコード不要。`session_filter`（正規表現）にマッチした `<h3>` 直後の `<ul>` のみ発表として拾う。
- **Notion DB を学会ごとに分離**: `notion.database_id`（直接）→ `notion.database_id_env`
  （環境変数名）→ 環境変数 `DATABASE_ID` の順で解決（`NotionWriter._resolve_database_id`）。
- **プロパティ対応を config 駆動化**: 旧実装は Notion プロパティ名（タイトル/ID/著者…）を
  ハードコードしていた。`notion.property_map`（項目→{name,type}）で解決。
  型は `title`/`rich_text`/`date`/`select`/`checkbox`。`date` は `date_start`/`date_end` を使用。
- **レート制限**: Notion API 3req/sec。`NotionWriter` は semaphore=3 + 各POST後 `sleep(0.35)`。
  この並列数・待機は変更しないこと（実測 799件を約6分）。

## 新しい学会を追加する手順

1. `parsers/<id>.py` に `BaseConferenceParser` を継承したクラスを作成
2. `parse_program(soup) -> list[Presentation]` を実装（設定は `self.parsing` から読む）
3. `parsers/factory.py` の `_import_parsers()` に import + `_PARSER_REGISTRY` 登録
4. `config.yaml` に `conferences.<id>`（`source`/`parsing`/`notion`）を追加

既存パーサーで済むなら 4 のみ。

## 注意点 / gotcha

- `config.yaml`・`html/`・`.env` は **`.gitignore` 対象**（コミットされない）。テンプレは
  `config.yaml.example`。
- Notion 登録には `.env` に `NOTION_TOKEN` と登録先DBの環境変数が必要。
- Notion 側DBのプロパティ名は `property_map` の `name` と**完全一致**が必要。
- パースが 0 件のときは `parsing` のセレクタ/正規表現がページ構造と合っているか確認。
- 日時は全て `+09:00`（JST）固定で ISO8601 生成。
