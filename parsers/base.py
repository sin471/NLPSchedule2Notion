"""
学会プログラムパーサーの抽象基底クラス
"""

from abc import ABC, abstractmethod

from bs4 import BeautifulSoup

from models import Presentation


class BaseConferenceParser(ABC):
    """
    学会プログラムパーサーの抽象基底クラス

    各学会のHTML構造に応じた具体的なパーサークラスは、
    このクラスを継承して parse_program() を実装してください。

    学会固有のパース設定は config の `parsing` ブロックに置き、
    `self.parsing` を通じて参照します。
    """

    def __init__(self, config: dict):
        """
        Parameters:
        config (dict): config.yaml の学会固有設定（1学会分）
        """
        self.config = config
        # 学会固有のパース設定。旧形式（parsing ブロック無し）にもフォールバック。
        self.parsing = config.get("parsing", config)

    @abstractmethod
    def parse_program(self, soup: BeautifulSoup) -> list[Presentation]:
        """
        BeautifulSoup オブジェクトから全プログラムデータを抽出します。

        Parameters:
        soup (BeautifulSoup): パース対象のHTMLを含む BeautifulSoup オブジェクト

        Returns:
        list[Presentation]: 発表データのリスト
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
        for symbol in self.parsing.get("cleanup", {}).get("remove_symbols", []):
            cleaned = cleaned.replace(symbol, "")
        # 連続する空白を1つに
        cleaned = " ".join(cleaned.split())
        return cleaned.strip()
