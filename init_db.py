"""
Notionデータベース初期化スクリプト

学会設定の property_map からNotion上にデータベースを自動作成する。
出力された database_id を .env の該当環境変数に設定すれば登録できる。

  uv run python init_db.py --conference yans2026 --parent-page <page_id>

親ページID（--parent-page）は、Notion連携（インテグレーション）が編集権限を持つ
ページのIDを指定する。省略時は config の notion.parent_page_id、
または環境変数 NOTION_PARENT_PAGE_ID を使用する。
"""

import argparse
import logging
import os

from dotenv import load_dotenv

from config import get_active_conference, load_config
from notion_schema import create_database

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Notionデータベースを自動作成します")
    parser.add_argument("--conference", help="対象の学会ID")
    parser.add_argument("--parent-page", help="作成先の親ページID")
    parser.add_argument("--title", help="DBタイトル（省略時は学会名）")
    args = parser.parse_args()

    config = load_config()
    conf_id, conf = get_active_conference(config, args.conference)

    parent_page_id = (
        args.parent_page
        or conf.get("notion", {}).get("parent_page_id")
        or os.getenv("NOTION_PARENT_PAGE_ID")
    )
    if not parent_page_id:
        logger.error(
            "親ページIDが指定されていません。--parent-page か "
            "config の notion.parent_page_id、環境変数 NOTION_PARENT_PAGE_ID を指定してください。"
        )
        exit(1)

    try:
        database_id = create_database(conf, parent_page_id, title=args.title)
    except Exception as e:
        logger.error(f"データベース作成に失敗しました: {e}")
        exit(1)

    env_name = conf.get("notion", {}).get("database_id_env", "DATABASE_ID")
    logger.info("=" * 60)
    logger.info(f"作成完了！ database_id: {database_id}")
    logger.info(f".env に以下を設定してください:\n  {env_name}={database_id}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
