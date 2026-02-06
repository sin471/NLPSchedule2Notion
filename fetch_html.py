"""
NLP2026のプログラムページからHTMLを取得してローカルに保存するスクリプト。

開発時にリクエスト回数を減らすため、一度だけ実行してHTMLファイルを保存します。
"""

import logging
from pathlib import Path

import requests

# ロギング設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def fetch_and_save_html(url: str, output_path: Path) -> bool:
    """
    指定されたURLからHTMLを取得してファイルに保存します。

    Parameters:
    url (str): 取得するページのURL
    output_path (Path): 保存先のファイルパス

    Returns:
    bool: 保存に成功した場合True、失敗した場合False
    """
    try:
        logger.info(f"Fetching HTML from: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # エンコーディングを自動検出
        response.encoding = response.apparent_encoding

        # HTMLをファイルに保存
        output_path.write_text(response.text, encoding="utf-8")

        logger.info(f"HTML saved to: {output_path}")
        logger.info(f"File size: {output_path.stat().st_size} bytes")

        return True

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch HTML: {e}")
        return False
    except IOError as e:
        logger.error(f"Failed to save HTML: {e}")
        return False


def main():
    """メイン処理"""
    url = "https://www.anlp.jp/proceedings/annual_meeting/2026/"
    output_path = Path(__file__).parent / "nlp2026_program.html"

    success = fetch_and_save_html(url, output_path)

    if success:
        logger.info("HTML fetch completed successfully!")
    else:
        logger.error("HTML fetch failed.")
        exit(1)


if __name__ == "__main__":
    main()
