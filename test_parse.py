"""
パース処理のテストスクリプト。

Notionに登録せずに、HTMLから正しくデータが抽出できるか確認します。
"""

import logging
from pathlib import Path

from main import get_program_data

# ロギング設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """メイン処理"""
    try:
        logger.info("プログラムデータの抽出テストを開始します")

        # データを取得
        programs = get_program_data(use_local_file=True)

        logger.info(f"\n{'='*60}")
        logger.info(f"取得した発表数: {len(programs)}件")
        logger.info(f"{'='*60}\n")

        # 最初の10件を表示
        logger.info("最初の10件を表示:")
        for i, prog in enumerate(programs[:10], 1):
            logger.info(f"\n[{i}]")
            logger.info(f"  ID: {prog['id']}")
            logger.info(f"  タイトル: {prog['title']}")
            logger.info(f"  著者: {prog['authors']}")
            logger.info(f"  セッション: {prog['session_name']}")
            logger.info(f"  日時: {prog['date_start']} → {prog['date_end']}")
            logger.info(f"  会場: {prog['venue']}")

        # 統計情報
        logger.info(f"\n{'='*60}")
        logger.info("統計情報:")
        logger.info(f"  総発表数: {len(programs)}件")

        # セッションごとの集計
        sessions = {}
        for prog in programs:
            session_prefix = prog["id"].split("-")[0] if "-" in prog["id"] else "その他"
            sessions[session_prefix] = sessions.get(session_prefix, 0) + 1

        logger.info(f"  セッション数: {len(sessions)}セッション")
        logger.info("\n  セッションごとの発表数:")
        for session, count in sorted(sessions.items()):
            logger.info(f"    {session}: {count}件")

        logger.info(f"{'='*60}\n")

        # エラーチェック
        errors = []
        for prog in programs:
            if not prog["title"]:
                errors.append(f"タイトルが空: ID={prog['id']}")
            if not prog["authors"]:
                errors.append(f"著者が空: ID={prog['id']}, タイトル={prog['title']}")

        if errors:
            logger.warning(f"\n警告: {len(errors)}件のエラーが見つかりました:")
            for error in errors[:5]:  # 最初の5件のみ表示
                logger.warning(f"  {error}")
            if len(errors) > 5:
                logger.warning(f"  ... 他 {len(errors) - 5}件")
        else:
            logger.info("✓ すべてのデータが正常に抽出されました")

    except Exception as e:
        logger.error(f"エラーが発生しました: {e}", exc_info=True)
        exit(1)


if __name__ == "__main__":
    main()
