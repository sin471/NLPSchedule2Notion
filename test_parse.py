"""
パース処理のテストスクリプト。

Notionに登録せずに、HTMLから正しくデータが抽出できるか確認します。

  uv run python test_parse.py [--conference <id>]
"""

import argparse
import logging

from main import parse_programs

# ロギング設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="プログラム抽出のテスト")
    parser.add_argument("--conference", help="対象の学会ID")
    args = parser.parse_args()

    try:
        logger.info("プログラムデータの抽出テストを開始します")

        _, _, programs = parse_programs(args.conference, use_local=True)

        logger.info(f"\n{'='*60}")
        logger.info(f"取得した発表数: {len(programs)}件")
        logger.info(f"{'='*60}\n")

        # 最初の10件を表示
        logger.info("最初の10件を表示:")
        for i, prog in enumerate(programs[:10], 1):
            logger.info(f"\n[{i}]")
            logger.info(f"  ID: {prog.id}")
            logger.info(f"  タイトル: {prog.title}")
            logger.info(f"  著者: {prog.authors}")
            logger.info(f"  セッション: {prog.session_name}")
            logger.info(f"  日時: {prog.date_start} → {prog.date_end}")
            logger.info(f"  会場: {prog.venue}")

        # 統計情報
        logger.info(f"\n{'='*60}")
        logger.info("統計情報:")
        logger.info(f"  総発表数: {len(programs)}件")

        # セッションプレフィックスごとの集計
        sessions: dict[str, int] = {}
        for prog in programs:
            prefix = prog.id.split("-")[0] if "-" in prog.id else "その他"
            sessions[prefix] = sessions.get(prefix, 0) + 1

        logger.info(f"  セッション数: {len(sessions)}")
        logger.info("\n  IDプレフィックスごとの発表数:")
        for session, count in sorted(sessions.items()):
            logger.info(f"    {session}: {count}件")

        logger.info(f"{'='*60}\n")

        # エラーチェック
        errors = []
        for prog in programs:
            if not prog.title:
                errors.append(f"タイトルが空: ID={prog.id}")
            if not prog.authors:
                errors.append(f"著者が空: ID={prog.id}, タイトル={prog.title}")

        if errors:
            logger.warning(f"\n警告: {len(errors)}件のエラーが見つかりました:")
            for error in errors[:5]:
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
