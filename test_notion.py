"""
Notion API投稿のテストスクリプト。

最初の5件のみをNotionに登録してテストします。
"""

import logging
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

from main import DATABASE_ID, get_program_data, headers

# ロギング設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def add_to_notion(data):
    """
    Notionデータベースにデータを追加します。

    Parameters:
    data (dict): 追加するデータ（id, title, authorsを含む）

    Returns:
    tuple: (成功フラグ, ステータスコード, レスポンステキスト)
    """
    url = "https://api.notion.com/v1/pages"
    payload = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "タイトル": {"title": [{"text": {"content": data["title"]}}]},
            "ID": {"rich_text": [{"text": {"content": data["id"]}}]},
            "著者": {"rich_text": [{"text": {"content": data["authors"]}}]},
            "ステータス": {"select": {"name": "未確認"}},
        },
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return True, response.status_code, "成功"
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        if hasattr(e, "response") and e.response is not None:
            error_msg = f"{e.response.status_code}: {e.response.text}"
        return False, 0, error_msg


def main():
    """メイン処理"""
    try:
        # 環境変数のチェック
        load_dotenv()
        notion_token = os.getenv("NOTION_TOKEN")
        database_id = os.getenv("DATABASE_ID")

        if not notion_token or not database_id:
            logger.error(
                "環境変数が設定されていません。.envファイルを確認してください。"
            )
            logger.error(f"NOTION_TOKEN: {'設定済み' if notion_token else '未設定'}")
            logger.error(f"DATABASE_ID: {'設定済み' if database_id else '未設定'}")
            return

        logger.info("Notion API投稿のテストを開始します")
        logger.info(f"DATABASE_ID: {database_id}")

        # データを取得
        programs = get_program_data(use_local_file=True)

        # 最初の5件のみをテスト
        test_count = 5
        test_programs = programs[:test_count]

        logger.info(f"\n最初の{test_count}件をNotionに登録します...")
        logger.info("=" * 60)

        success_count = 0
        fail_count = 0

        for i, prog in enumerate(test_programs, 1):
            logger.info(f"\n[{i}/{test_count}]")
            logger.info(f"  ID: {prog['id']}")
            logger.info(f"  タイトル: {prog['title'][:50]}...")
            logger.info(f"  著者: {prog['authors'][:50]}...")

            success, status_code, message = add_to_notion(prog)

            if success:
                success_count += 1
                logger.info(f"  ✓ 登録成功 (ステータス: {status_code})")
            else:
                fail_count += 1
                logger.error(f"  ✗ 登録失敗: {message}")

            # API制限対策
            if i < test_count:
                time.sleep(0.35)

        logger.info("\n" + "=" * 60)
        logger.info(f"テスト完了: 成功 {success_count}件, 失敗 {fail_count}件")
        logger.info("=" * 60)

        if success_count == test_count:
            logger.info("\n✓ すべてのテストが成功しました！")
            logger.info("本番実行する場合は以下のコマンドを実行してください：")
            logger.info("  uv run main.py")
        else:
            logger.warning("\n⚠ エラーが発生しました。以下を確認してください：")
            logger.warning("  1. .envファイルのNOTION_TOKENが正しいか")
            logger.warning("  2. DATABASE_IDが正しいか")
            logger.warning("  3. Notionデータベースのプロパティ名が正しいか")
            logger.warning("     - タイトル (Title型)")
            logger.warning("     - ID (Rich Text型)")
            logger.warning("     - 著者 (Rich Text型)")
            logger.warning("     - ステータス (Select型、選択肢に「未確認」が必要)")
            logger.warning("  4. Notion統合がデータベースに接続されているか")

    except Exception as e:
        logger.error(f"エラーが発生しました: {e}", exc_info=True)
        exit(1)


if __name__ == "__main__":
    main()
