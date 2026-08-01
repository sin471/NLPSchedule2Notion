"""
YANS2026用の具体的なパーサー実装

YANS（言語処理若手シンポジウム）のプログラムページは、はてなブログ製で
NLP系とは構造が根本的に異なる。<div class="entry-content"> 内に文書順で:

    <h2> シンポジウム2日目: 8/17 (月) 仙台国際センター 展示室1・2   … 日付・会場
    <h3> [11:45-12:45] ポスターセッション (1)                     … 時間帯・セッション名
    <ul><li><p>[S1-P01] タイトル<br/>著者 (所属), 著者 (所属)</p></li> … 発表

と並ぶ。日付は <h2>、時間は <h3>、発表は <li> と別々の要素にまたがるため、
文書順にステートフルに走査して状態（現在の日付・会場・セッション・時刻）を
保持しながら発表を組み立てる。
"""

import logging
import re

from bs4 import BeautifulSoup

from models import Presentation

from .base import BaseConferenceParser

logger = logging.getLogger(__name__)


class YANS2026Parser(BaseConferenceParser):
    """YANS2026（はてなブログ形式）のプログラムパーサー"""

    def parse_program(self, soup: BeautifulSoup) -> list[Presentation]:
        results: list[Presentation] = []

        root_selector = self.parsing.get("root", ".entry-content")
        day_tag = self.parsing.get("day_header", "h2")
        slot_tag = self.parsing.get("slot_header", "h3")
        list_tag = self.parsing.get("entry_list", "ul")

        session_filter = re.compile(
            self.parsing.get("session_filter", r"ポスターセッション|招待ポスター")
        )
        date_pattern = self.parsing.get(
            "date_pattern", r"(\d+)/(\d+)\s*\([月火水木金土日]\)"
        )
        venue_pattern = self.parsing.get("venue_pattern", r"(展示室[\d・]+)")
        time_pattern = self.parsing.get("time_pattern", r"\[(\d+):(\d+)-(\d+):(\d+)\]")
        id_title_pattern = self.parsing.get("id_title_pattern", r"^\[([^\]]+)\]\s*(.+)$")

        root = soup.select_one(root_selector)
        if root is None:
            logger.warning(f"ルート要素が見つかりません: {root_selector}")
            return results

        year = self.config.get("year", 2026)

        # 走査中の状態
        cur_month = cur_day = None
        cur_venue = ""
        cur_session = ""
        cur_time = None  # (sh, sm, eh, em)
        is_target = False  # 直近の slot が発表対象セッションか

        day_count = 0
        for el in root.find_all([day_tag, slot_tag, list_tag]):
            if el.name == day_tag:
                day_count += 1
                text = el.get_text(" ", strip=True)
                m = re.search(date_pattern, text)
                if m:
                    cur_month, cur_day = int(m.group(1)), int(m.group(2))
                vm = re.search(venue_pattern, text)
                cur_venue = vm.group(1) if vm else ""
                # 日が替わったらセッション状態をリセット
                cur_session, cur_time, is_target = "", None, False

            elif el.name == slot_tag:
                text = el.get_text(" ", strip=True)
                tm = re.search(time_pattern, text)
                cur_time = (
                    (int(tm.group(1)), int(tm.group(2)), int(tm.group(3)), int(tm.group(4)))
                    if tm
                    else None
                )
                # セッション名は時刻ブラケットを除いた残り
                cur_session = re.sub(time_pattern, "", text).strip()
                is_target = bool(session_filter.search(cur_session))

            elif el.name == list_tag:
                if not is_target:
                    continue
                for li in el.find_all("li", recursive=False):
                    pres = self._parse_entry(
                        li,
                        id_title_pattern,
                        cur_session,
                        cur_venue,
                        cur_month,
                        cur_day,
                        cur_time,
                        year,
                    )
                    if pres:
                        results.append(pres)

        logger.info(f"取得したプログラム数: {len(results)}")
        return results

    def _parse_entry(
        self,
        li,
        id_title_pattern: str,
        session_name: str,
        venue: str,
        month,
        day,
        time_tuple,
        year: int,
    ) -> Presentation | None:
        """1件の <li> を Presentation に変換します。対象外なら None。"""
        # <br/> を改行として取り出し、1行目=「[ID] タイトル」、以降=著者
        text = li.get_text(separator="\n", strip=True)
        if not text:
            return None
        parts = text.split("\n", 1)
        head = parts[0].strip()
        authors = self.clean_author_info(parts[1]) if len(parts) > 1 else ""

        m = re.match(id_title_pattern, head)
        if not m:
            return None
        pres_id = m.group(1).strip()
        title = m.group(2).strip()

        date_start, date_end = self._build_dates(month, day, time_tuple, year)

        return Presentation(
            id=pres_id,
            title=title,
            authors=authors,
            session_name=session_name,
            date_start=date_start,
            date_end=date_end,
            venue=venue,
        )

    @staticmethod
    def _build_dates(month, day, time_tuple, year: int):
        """日付・時刻から ISO8601（+09:00）の開始/終了日時を組み立てます。"""
        if month is None or day is None or time_tuple is None:
            return None, None
        sh, sm, eh, em = time_tuple
        start = f"{year:04d}-{month:02d}-{day:02d}T{sh:02d}:{sm:02d}:00+09:00"
        end = f"{year:04d}-{month:02d}-{day:02d}T{eh:02d}:{em:02d}:00+09:00"
        return start, end
