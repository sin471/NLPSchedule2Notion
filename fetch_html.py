"""
アクティブ学会（または --conference）のプログラムページからHTMLを取得し、
config の source.local_file にローカル保存するスクリプト。

開発時にリクエスト回数を減らすため、一度だけ実行してHTMLを保存します。
"""

import argparse
import logging

import sources
from config import get_active_conference, load_config

# ロギング設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="学会プログラムHTMLを取得して保存します")
    parser.add_argument(
        "--conference",
        help="対象の学会ID（config.yaml の active_conference を上書き）",
    )
    args = parser.parse_args()

    config = load_config()
    conf_id, conf = get_active_conference(config, args.conference)
    logger.info(f"対象の学会設定: {conf['name']}")

    url = conf.get("source", {}).get("url")
    if not url:
        logger.error(f"学会設定 '{conf_id}' に source.url が指定されていません")
        exit(1)

    output_path = sources.resolve_local_path(conf_id, conf)
    success = sources.save_html(url, output_path)

    if success:
        logger.info("HTML fetch completed successfully!")
    else:
        logger.error("HTML fetch failed.")
        exit(1)


if __name__ == "__main__":
    main()
