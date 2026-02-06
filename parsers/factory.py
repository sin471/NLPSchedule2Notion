"""
パーサーファクトリー - 設定に基づいてパーサーインスタンスを生成
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BaseConferenceParser

logger = logging.getLogger(__name__)

# パーサークラスのレジストリ
_PARSER_REGISTRY = {}


def register_parser(parser_name: str):
    """
    パーサークラスを登録するデコレータ

    Usage:
        @register_parser("nlp2026")
        class NLP2026Parser(BaseConferenceParser):
            ...
    """

    def decorator(parser_class):
        _PARSER_REGISTRY[parser_name] = parser_class
        return parser_class

    return decorator


def create_parser(config: dict) -> "BaseConferenceParser":
    """
    設定に基づいて適切なパーサーインスタンスを生成します。

    Parameters:
    config (dict): config.yamlの学会固有設定
        必須キー: "parser_class" - パーサークラス名（例: "NLP2026Parser"）

    Returns:
    BaseConferenceParser: パーサーインスタンス

    Raises:
    ValueError: parser_classが指定されていないか、未登録のパーサー名の場合
    """
    parser_class_name = config.get("parser_class")

    if not parser_class_name:
        raise ValueError(
            "config.yamlにparser_classが指定されていません。\n"
            "例: parser_class: 'NLP2026Parser'"
        )

    # レジストリが空の場合、パーサーモジュールをインポート
    if not _PARSER_REGISTRY:
        _import_parsers()

    if parser_class_name not in _PARSER_REGISTRY:
        available_parsers = ", ".join(_PARSER_REGISTRY.keys())
        raise ValueError(
            f"未登録のパーサークラス: {parser_class_name}\n"
            f"利用可能なパーサー: {available_parsers}"
        )

    parser_class = _PARSER_REGISTRY[parser_class_name]
    logger.info(f"パーサーを初期化: {parser_class_name}")

    return parser_class(config)


def _import_parsers():
    """
    すべてのパーサーモジュールをインポートしてレジストリに登録します。
    """
    from .nlp2026 import NLP2026Parser

    # デコレータを使わずに手動登録
    _PARSER_REGISTRY["NLP2026Parser"] = NLP2026Parser
