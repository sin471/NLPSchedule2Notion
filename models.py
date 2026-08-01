"""
学会プログラムの正規化データモデル

パーサー層とNotion登録層の間で受け渡す共通契約。
各パーサーは学会固有のHTML構造を解釈し、この `Presentation` のリストを返す。
Notion登録層は `Presentation` のみに依存し、学会ごとの差異を意識しない。
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Presentation:
    """
    1件の発表を表す正規化データ。

    Attributes:
        id: 発表ID（例: "P1-01", "S1-P01"）
        title: 発表タイトル
        authors: 著者情報（所属含む文字列）
        session_name: セッション名
        date_start: 開始日時 ISO8601形式（例: "2026-08-17T11:45:00+09:00"）。不明なら None
        date_end: 終了日時 ISO8601形式。不明なら None
        venue: 会場
        extra: 学会固有の追加情報（将来拡張用。例: 発表種別）
    """

    id: str
    title: str
    authors: str
    session_name: str
    date_start: str | None
    date_end: str | None
    venue: str
    extra: dict[str, Any] = field(default_factory=dict)
