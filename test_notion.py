"""
Notion API投稿のテストスクリプト。

最初の5件のみを Notion に登録してテストします。

  uv run python test_notion.py [--conference <id>]
"""

import argparse
import logging
import time

import requests
from dotenv import load_dotenv

from main import parse_programs
from notion_writer import NOTION_API_URL, NotionWriter

# ロギング設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def add_to_notion(writer: NotionWriter, pres):
    """1件を同期的に登録します。戻り値: (成功フラグ, ステータスコード, メッセージ)"""
    payload = {
        "parent": {"database_id": writer.database_id},
        "properties": writer.build_properties(pres),
    }
    try:
        response = requests.post(
            NOTION_API_URL, json=payload, headers=writer.headers, timeout=30
        )
        response.raise_for_status()
        return True, response.status_code, "成功"
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        if hasattr(e, "response") and e.response is not None:
            error_msg = f"{e.response.status_code}: {e.response.text}"
        return False, 0, error_msg


def main():
    load_dotenv()
    arg_parser = argparse.ArgumentParser(description="Notion登録のテスト（先頭5件）")
    arg_parser.add_argument("--conference", help="対象の学会ID")
    args = arg_parser.parse_args()

    try:
        logger.info("Notion API投稿のテストを開始します")

        _, conf, programs = parse_programs(args.conference, use_local=True)
        writer = NotionWriter(conf)
        logger.info(f"DATABASE_ID: {writer.database_id}")

        test_count = min(5, len(programs))
        test_programs = programs[:test_count]

        logger.info(f"\n最初の{test_count}件を Notion に登録します...")
        logger.info("=" * 60)

        success_count = 0
        fail_count = 0

        for i, prog in enumerate(test_programs, 1):
            logger.info(f"\n[{i}/{test_count}]")
            logger.info(f"  ID: {prog.id}")
            logger.info(f"  タイトル: {prog.title[:50]}...")
            logger.info(f"  著者: {prog.authors[:50]}...")

            success, status_code, message = add_to_notion(writer, prog)

            if success:
                success_count += 1
                logger.info(f"  ✓ 登録成功 (ステータス: {status_code})")
            else:
                fail_count += 1
                logger.error(f"  ✗ 登録失敗: {message}")

            if i < test_count:
                time.sleep(0.35)

        logger.info("\n" + "=" * 60)
        logger.info(f"テスト完了: 成功 {success_count}件, 失敗 {fail_count}件")
        logger.info("=" * 60)

        if success_count == test_count:
            logger.info("\n✓ すべてのテストが成功しました！")
            logger.info("本番実行する場合は以下のコマンドを実行してください：")
            logger.info("  uv run python main.py")
        else:
            logger.warning("\n⚠ エラーが発生しました。以下を確認してください：")
            logger.warning("  1. .env の NOTION_TOKEN が正しいか")
            logger.warning("  2. 登録先データベースID（config の notion.database_id_env / DATABASE_ID）が正しいか")
            logger.warning("  3. Notionデータベースのプロパティ名が property_map と一致しているか")
            logger.warning("  4. Notion統合がデータベースに接続されているか")

    except Exception as e:
        logger.error(f"エラーが発生しました: {e}", exc_info=True)
        exit(1)


if __name__ == "__main__":
    main()
