"""
学会プログラム → Notion 自動登録ツール（エントリポイント）

config.yaml のアクティブ学会（または --conference）を対象に、
プログラムHTMLを取得・パースして Notion データベースへ一括登録する。
"""

import argparse
import asyncio
import logging
import time

from dotenv import load_dotenv

import sources
from config import get_active_conference, load_config
from models import Presentation
from notion_writer import NotionWriter
from parsers import create_parser

# ロギング設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def parse_programs(conference: str | None, use_local: bool) -> tuple[str, dict, list[Presentation]]:
    """
    設定を読み込み、プログラムを取得・パースします。

    Returns:
    tuple: (学会ID, 学会設定, 発表リスト)
    """
    config = load_config()
    conf_id, conf = get_active_conference(config, conference)
    logger.info(f"使用する学会設定: {conf['name']}")

    parser = create_parser(conf)
    soup = sources.load_soup(conf_id, conf, use_local=use_local)
    presentations = parser.parse_program(soup)
    return conf_id, conf, presentations


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="学会プログラムを Notion に一括登録します")
    p.add_argument(
        "--conference",
        help="対象の学会ID（config.yaml の active_conference を上書き）",
    )
    p.add_argument(
        "--no-local",
        action="store_true",
        help="ローカルHTMLではなくURLから直接取得する",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Notionに登録せず、パース結果の件数のみ表示する",
    )
    return p


def main():
    load_dotenv()
    args = _build_arg_parser().parse_args()

    try:
        logger.info("プログラムデータの取得を開始します")
        conf_id, conf, presentations = parse_programs(
            args.conference, use_local=not args.no_local
        )

        if args.dry_run:
            logger.info(
                f"[dry-run] パース結果: {len(presentations)}件（Notion登録はスキップ）"
            )
            return

        logger.info(f"Notionへの登録を開始します（{len(presentations)}件）")
        start_time = time.time()

        writer = NotionWriter(conf)
        success_count, fail_count = asyncio.run(writer.batch(presentations))

        elapsed_time = time.time() - start_time
        logger.info(
            f"処理完了: 成功 {success_count}件, 失敗 {fail_count}件 "
            f"(処理時間: {elapsed_time:.1f}秒)"
        )

    except Exception as e:
        logger.error(f"エラーが発生しました: {e}")
        exit(1)


if __name__ == "__main__":
    main()
