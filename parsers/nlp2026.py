"""
NLP2026用の具体的なパーサー実装
"""

import logging
import re
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup

from .base import BaseConferenceParser

logger = logging.getLogger(__name__)


class NLP2026Parser(BaseConferenceParser):
    """
    言語処理学会第31回年次大会（NLP2026）のHTML構造に特化したパーサー

    HTML構造の特徴:
    - セッション情報は <div class="session1"> または <div class="session2"> に格納
    - セッションヘッダーは <div class="session_header"> に格納
    - セッション名は <span class="session_title"> に格納
    - 発表情報は <table> で2行構造（1行目：ID+タイトル、2行目：著者）
    """

    def parse_program(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        """
        NLP2026のHTML構造から全プログラムデータを抽出します。

        Parameters:
        soup (BeautifulSoup): パース対象のHTMLを含むBeautifulSoupオブジェクト

        Returns:
        list[dict[str, Any]]: プログラムデータのリスト
        """
        results = []
        selectors = self.config.get("selectors", {})
        table_structure = self.config.get("table_structure", {})

        # セッションを取得
        sessions = soup.select(selectors.get("sessions", "div.session1, div.session2"))
        logger.info(f"発見されたセッション数: {len(sessions)}")

        for session in sessions:
            # セッション情報を取得
            session_header = session.select_one(
                selectors.get("session_header", "div.session_header")
            )
            if not session_header:
                continue

            session_title_elem = session_header.select_one(
                selectors.get("session_title", "span.session_title")
            )
            if not session_title_elem:
                continue

            # セッション名を取得
            session_name = session_title_elem.get_text(strip=True)

            # セッションヘッダー全体のテキストから日時・会場情報を抽出
            session_header_text = session_header.get_text(separator=" ", strip=True)
            session_info = self._parse_session_info(session_header_text)

            # セッション内のテーブルを取得
            table = session.select_one(selectors.get("table", "table"))
            if not table:
                continue

            # テーブルから発表情報を抽出
            presentations = self._parse_table(table, table_structure)

            # セッション情報を各発表に付与
            for presentation in presentations:
                presentation.update(
                    {
                        "session_name": session_name,
                        "date_start": session_info["date_start"],
                        "date_end": session_info["date_end"],
                        "venue": session_info["venue"],
                    }
                )
                results.append(presentation)

        logger.info(f"取得したプログラム数: {len(results)}")
        return results

    def _parse_session_info(self, session_header_text: str) -> dict:
        """
        セッションヘッダーから日時・会場情報を抽出します。

        Parameters:
        session_header_text (str): セッションヘッダーのテキスト

        Returns:
        dict: 日時情報と会場の情報
            - date_start: 開始日時 ISO形式 (str | None)
            - date_end: 終了日時 ISO形式 (str | None)
            - venue: 会場 (str)
        """
        date_parsing = self.config.get("date_parsing", {})
        result = {"date_start": None, "date_end": None, "venue": ""}

        # 日時パターンマッチング
        date_pattern = date_parsing.get(
            "pattern", r"(\d+)/(\d+)\s*\([^)]+\)\s*(\d+):(\d+)-(\d+):(\d+)"
        )
        date_match = re.search(date_pattern, session_header_text)

        if date_match:
            month = int(date_match.group(1))
            day = int(date_match.group(2))
            start_hour = int(date_match.group(3))
            start_minute = int(date_match.group(4))
            end_hour = int(date_match.group(5))
            end_minute = int(date_match.group(6))

            year = self.config.get("year", 2026)
            result["date_start"] = (
                f"{year:04d}-{month:02d}-{day:02d}T{start_hour:02d}:{start_minute:02d}:00"
            )
            result["date_end"] = (
                f"{year:04d}-{month:02d}-{day:02d}T{end_hour:02d}:{end_minute:02d}:00"
            )

        # 会場パターン
        venue_pattern = date_parsing.get("venue_pattern", r"([A-Z]会場)")
        venue_match = re.search(venue_pattern, session_header_text)
        if venue_match:
            result["venue"] = venue_match.group(1).strip()

        return result

    def _parse_table(self, table, table_structure: dict) -> list[dict[str, Any]]:
        """
        テーブルから発表情報を抽出します（2行構造想定）。

        Parameters:
        table: BeautifulSoupのtable要素
        table_structure (dict): テーブル構造の設定

        Returns:
        list[dict[str, Any]]: 発表情報のリスト
        """
        results = []
        rows = table.find_all("tr")

        # テーブル構造の設定を取得
        id_col = table_structure.get("id_column", 0)
        title_col = table_structure.get("title_column", 1)
        author_offset = table_structure.get("author_row_offset", 1)

        # 2行ペアで処理（1行目：ID+タイトル、2行目：著者）
        i = 0
        while i < len(rows):
            row1 = rows[i]
            cols1 = row1.find_all("td")

            # 1行目に必要なセルがあることを確認
            if len(cols1) > max(id_col, title_col):
                presentation_id = cols1[id_col].get_text(strip=True)
                title = cols1[title_col].get_text(strip=True)

                # 次の行（著者情報）を取得
                authors = ""
                if i + author_offset < len(rows):
                    row2 = rows[i + author_offset]
                    cols2 = row2.find_all("td")
                    if len(cols2) > title_col:
                        authors = self.clean_author_info(
                            cols2[title_col].get_text(strip=True)
                        )
                        i += author_offset + 1  # 著者行分進める
                    else:
                        i += 1
                else:
                    i += 1

                # IDが有効な場合のみ追加（空でない、かつセッションIDの形式）
                if presentation_id and "-" in presentation_id:
                    results.append(
                        {
                            "id": presentation_id,
                            "title": title,
                            "authors": authors,
                        }
                    )
            else:
                i += 1

        return results
