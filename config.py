"""
設定ファイル（config.yaml）の読込・アクティブ学会の選択・検証
"""

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).parent / "config.yaml"


def load_config(path: Path | str = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    """
    config.yaml を読み込みます。

    Parameters:
    path: 設定ファイルのパス

    Returns:
    dict: パース済みの設定

    Raises:
    FileNotFoundError: 設定ファイルが存在しない場合
    """
    path = Path(path)
    if not path.exists():
        logger.error(f"設定ファイルが見つかりません: {path}")
        logger.info("config.yaml.example を config.yaml にコピーして設定してください。")
        raise FileNotFoundError(f"設定ファイルが見つかりません: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_active_conference(
    config: dict[str, Any], name: str | None = None
) -> tuple[str, dict[str, Any]]:
    """
    アクティブな学会設定を取得します。

    Parameters:
    config: load_config() で読み込んだ設定
    name: 学会ID。指定時は config の active_conference より優先（CLI の --conference 用）

    Returns:
    tuple: (学会ID, 学会設定dict)

    Raises:
    ValueError: 指定された学会設定が存在しない、または parser_class が欠落している場合
    """
    conferences = config.get("conferences", {})
    active_name = name or config.get("active_conference")

    if not active_name:
        raise ValueError(
            "アクティブな学会が指定されていません。"
            "config.yaml の active_conference か --conference を指定してください。"
        )

    if active_name not in conferences:
        available = ", ".join(conferences.keys()) or "(なし)"
        logger.error(f"指定された学会設定が見つかりません: {active_name}")
        raise ValueError(
            f"学会設定 '{active_name}' が config.yaml に存在しません。"
            f"利用可能な学会: {available}"
        )

    conf = conferences[active_name]
    if not conf.get("parser_class"):
        raise ValueError(
            f"学会設定 '{active_name}' に parser_class が指定されていません。\n"
            "例: parser_class: 'NLP2026Parser'"
        )

    return active_name, conf
