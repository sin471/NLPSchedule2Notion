# 学会プログラム → Notion 自動登録ツール

学会プログラムのWebページから発表情報を抽出し、Notionデータベースに一括登録するツールです。

## 特徴

- **汎用設計**: 抽象基底クラスによるパーサーアーキテクチャで、様々な学会に対応可能
- **YAML設定**: 学会ごとのHTML構造やパース規則を設定ファイルで管理
- **非同期処理**: aiohttpによる並列処理で高速登録（799件を約6分で処理）

## 実行例

```bash
$ uv run python main.py
2026-02-07 01:34:21,879 - INFO - 使用する学会設定: 言語処理学会第31回年次大会（NLP2026）
2026-02-07 01:34:21,882 - INFO - パーサーを初期化: NLP2026Parser
2026-02-07 01:34:21,883 - INFO - プログラムデータの取得を開始します
2026-02-07 01:34:21,883 - INFO - ローカルHTMLファイルから読み込み: C:\Users\***\Programming\NLPSchedule2Notion\nlp2026_program.html
2026-02-07 01:34:22,410 - INFO - 発見されたセッション数: 60
2026-02-07 01:34:22,453 - INFO - 取得したプログラム数: 799
2026-02-07 01:34:22,454 - INFO - Notionへの登録を開始します（799件）
Notion登録中: 100%|████████████████████████████| 799/799 [06:33<00:00,  2.03件/s]
2026-02-07 01:40:55,482 - INFO - 処理完了: 成功 799件, 失敗 0件 (処理時間: 393.0秒)
```

## アーキテクチャ

### パーサー設計

本ツールは抽象基底クラス（`BaseConferenceParser`）を使用した拡張可能な設計を採用しています：

```
parsers/
├── __init__.py          # パッケージ初期化
├── base.py              # BaseConferenceParser（抽象基底クラス）
├── nlp2026.py           # NLP2026Parser（具体的な実装）
└── factory.py           # create_parser（ファクトリー関数）
```

新しい学会に対応する場合：
1. `parsers/`に新しいパーサークラスを作成（例：`jsai2026.py`）
2. `BaseConferenceParser`を継承し、`parse_program()`メソッドを実装
3. `factory.py`にパーサーを登録
4. `config.yaml`で`parser_class`を指定

## セットアップ

### 1. 依存関係のインストール

```bash
uv sync
```

### 2. 環境変数の設定

`.env`ファイルを作成し、以下を設定：

```env
# Notion API設定
NOTION_TOKEN=your_notion_token_here
DATABASE_ID=your_database_id_here
```

### 3. 学会設定の作成

`config.yaml.example`をコピーして`config.yaml`を作成：

```bash
cp config.yaml.example config.yaml
```

`config.yaml`を編集して、対象の学会に合わせて設定を調整します。

## 設定ファイル（config.yaml）の構造

```yaml
# 使用する学会設定を指定
active_conference: nlp2026

conferences:
  nlp2026:  # 学会ID（任意の識別子）
    name: "言語処理学会第31回年次大会（NLP2026）"
    url: "https://www.anlp.jp/proceedings/annual_meeting/2026/"
    year: 2026
    parser_class: "NLP2026Parser"  # 使用するパーサークラス

    selectors:
      # HTMLセレクタ（CSSセレクタ形式）
      sessions: "div.session1, div.session2"
      session_header: "div.session_header"
      session_title: "span.session_title"
      table: "table"

    table_structure:
      # テーブルのカラム番号（0始まり）
      id_column: 0        # 発表ID列
      title_column: 1     # タイトル列
      author_row_offset: 1  # 著者情報の行オフセット

    date_parsing:
      # 日時情報を抽出する正規表現
      pattern: "(\d+)/(\d+)\s*\([^)]+\)\s*(\d+):(\d+)-(\d+):(\d+)"
      venue_pattern: "([A-Z]会場)"

    cleanup:
      # 著者情報からクリーンアップする記号
      remove_symbols:
        - "○"
        - "◊"
        - "💻"
        - "J"
```

### 他の学会に対応させる方法

1. `conferences`セクションに新しい学会設定を追加
2. `active_conference`を新しい学会IDに変更
3. HTMLセレクタとパース設定を学会のWebページに合わせて調整

例：
```yaml
active_conference: jsai2026

conferences:
  jsai2026:
    name: "人工知能学会全国大会（JSAI2026）"
    url: "https://example.com/jsai2026/"
    year: 2026
    # ... その他の設定
```

## 使用方法

### プログラムデータの取得とNotion登録

```bash
uv run python main.py
```

実行すると以下の処理が行われます：

1. 設定ファイル（`config.yaml`）から学会設定を読み込み
2. 指定されたURLまたはローカルHTMLファイルからプログラムデータを取得
3. HTMLをパースして発表情報を抽出
4. Notion APIを使用してデータベースに一括登録

### Notionデータベースの設定

Notionデータベースには以下のプロパティを作成してください：

| プロパティ名 | タイプ | 説明 | 必須 |
|------------|--------|------|------|
| タイトル | Title | 発表タイトル | ✅ |
| ID | Text | 発表の識別子（例: P1-01） | ✅ |
| 著者 | Text | 発表者名 | ✅ |
| セッション | Text | セッション名 | ✅ |
| 日時 | Date | 発表の開始・終了時刻 | ✅ |
| 会場 | Text | 会場情報 | ✅ |
| 興味 | Checkbox | 個人用チェック（任意） | ❌ |

**注意**: プロパティ名は上記と完全に一致させる必要があります。

### 実行結果の確認

処理完了後、以下の情報が表示されます：
- 成功件数/失敗件数
- 処理時間
- 処理速度（件/秒）

進捗バーには以下が表示されます：
- リアルタイムの進捗率
- 完了数/全体数
- 経過時間と残り時間の推定
- 処理速度

## パフォーマンス

- **並列処理**: 3並列で非同期処理（Notion APIレート制限: 3req/sec）


## トラブルシューティング

### 設定ファイルが見つからない

```
エラー: config.yamlファイルが見つかりません
```

→ `config.yaml.example`をコピーして`config.yaml`を作成してください。

### HTMLセレクタが一致しない

```
発見されたセッション数: 0
```

→ `config.yaml`の`selectors`セクションを確認し、対象WebページのHTML構造に合わせて調整してください。

### 日時情報がパースできない

→ `date_parsing.pattern`の正規表現を、対象Webページの日時フォーマットに合わせて調整してください。

## ライセンス

MIT License

## 開発

### テスト

```bash
# HTMLパースのテスト
uv run python test_parse.py

# Notion登録のテスト
uv run python test_notion.py
```
