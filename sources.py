"""
プログラムHTMLの取得（ローカルファイル / URL）と保存

学会設定の `source` ブロックを参照し、ローカルファイル名やURLのハードコードを排除する。
"""

import logging
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent


def _local_path(conf_id: str, conf: dict[str, Any]) -> Path:
    """学会設定からローカルHTMLファイルのパスを解決します。"""
    source = conf.get("source", {})
    local_file = source.get("local_file") or f"html/{conf_id}_program.html"
    path = Path(local_file)
    if not path.is_absolute():
        path = BASE_DIR / path
    return path


def load_soup(
    conf_id: str, conf: dict[str, Any], use_local: bool = True
) -> BeautifulSoup:
    """
    プログラムHTMLを取得して BeautifulSoup を返します。

    Parameters:
    conf_id: 学会ID
    conf: 学会設定
    use_local: True ならローカルファイルから、False なら URL から取得

    Returns:
    BeautifulSoup: パース対象のHTML
    """
    if use_local:
        path = _local_path(conf_id, conf)
        if not path.exists():
            logger.error(f"HTMLファイルが見つかりません: {path}")
            logger.info("先に fetch_html.py を実行してHTMLファイルを取得してください")
            raise FileNotFoundError(f"HTMLファイルが見つかりません: {path}")
        logger.info(f"ローカルHTMLファイルから読み込み: {path}")
        html_content = path.read_text(encoding="utf-8")
        return BeautifulSoup(html_content, "html.parser")

    url = conf.get("source", {}).get("url")
    if not url:
        raise ValueError(f"学会設定 '{conf_id}' に source.url が指定されていません")
    logger.info(f"URLから取得: {url}")
    res = requests.get(url, timeout=30)
    res.raise_for_status()
    res.encoding = res.apparent_encoding
    return BeautifulSoup(res.text, "html.parser")


def save_html(url: str, output_path: Path) -> bool:
    """
    指定されたURLからHTMLを取得してファイルに保存します。

    Parameters:
    url: 取得するページのURL
    output_path: 保存先のファイルパス

    Returns:
    bool: 保存に成功した場合 True
    """
    try:
        logger.info(f"Fetching HTML from: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        response.encoding = response.apparent_encoding

        output_path.parent.mkdir(parents=True, exist_ok=True)
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


def resolve_local_path(conf_id: str, conf: dict[str, Any]) -> Path:
    """学会設定からローカルHTMLの保存先パスを返します（fetch_html.py 用）。"""
    return _local_path(conf_id, conf)
