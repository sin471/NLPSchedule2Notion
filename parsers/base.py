"""
学会プログラムパーサーの抽象基底クラス
"""

from abc import ABC, abstractmethod
from typing import Any

from bs4 import BeautifulSoup


class BaseConferenceParser(ABC):
    """
    学会プログラムパーサーの抽象基底クラス

    各学会のHTML構造に応じた具体的なパーサークラスは、
    このクラスを継承して実装してください。
    """

    def __init__(self, config: dict):
        """
        Parameters:
        config (dict): config.yamlの学会固有設定
        """
        self.config = config

    @abstractmethod
    def parse_program(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        """
        BeautifulSoupオブジェクトから全プログラムデータを抽出します。

        Parameters:
        soup (BeautifulSoup): パース対象のHTMLを含むBeautifulSoupオブジェクト

        Returns:
        list[dict[str, Any]]: プログラムデータのリスト
            各要素は以下のキーを持つ辞書:
            - id: 発表ID (str)
            - title: タイトル (str)
            - authors: 著者情報 (str)
            - session_name: セッション名 (str)
            - date_start: 開始日時 ISO形式 (str | None)
            - date_end: 終了日時 ISO形式 (str | None)
            - venue: 会場 (str)
        """
        pass

    def clean_author_info(self, author_text: str) -> str:
        """
        著者情報から記号を削除してクリーンアップします。

        Parameters:
        author_text (str): 元の著者情報テキスト

        Returns:
        str: クリーンアップされた著者情報
        """
        cleaned = author_text
        for symbol in self.config.get("cleanup", {}).get("remove_symbols", []):
            cleaned = cleaned.replace(symbol, "")
        # 連続する空白を1つに
        cleaned = " ".join(cleaned.split())
        return cleaned.strip()
