"""
Notion登録層

Presentation を Notion のページプロパティに変換し、非同期バッチで登録する。
プロパティ名⇔データ項目の対応は config の `notion.property_map` で駆動する。
"""

import asyncio
import logging
import os
from typing import Any

import aiohttp
from tqdm.asyncio import tqdm

from models import Presentation

logger = logging.getLogger(__name__)

NOTION_API_URL = "https://api.notion.com/v1/pages"

# property_map 未指定時のデフォルト（現行の6プロパティ）
DEFAULT_PROPERTY_MAP = {
    "title": {"name": "タイトル", "type": "title"},
    "id": {"name": "ID", "type": "rich_text"},
    "authors": {"name": "著者", "type": "rich_text"},
    "session_name": {"name": "セッション", "type": "rich_text"},
    "venue": {"name": "会場", "type": "rich_text"},
    "date": {"name": "日時", "type": "date"},
}


class NotionWriter:
    """設定に基づいて Notion にプログラムを登録するクラス。"""

    def __init__(
        self,
        conf: dict[str, Any],
        token: str | None = None,
        concurrency: int = 3,
        request_interval: float = 0.35,
    ):
        """
        Parameters:
        conf: 学会設定（notion ブロックを含む）
        token: Notion APIトークン（省略時は環境変数 NOTION_TOKEN）
        concurrency: 同時実行数（Notion APIレート制限 3req/sec に合わせ既定3）
        request_interval: 各リクエスト後の待機秒数
        """
        notion_conf = conf.get("notion", {})
        self.token = token or os.getenv("NOTION_TOKEN")
        self.database_id = self._resolve_database_id(notion_conf)
        self.property_map = notion_conf.get("property_map", DEFAULT_PROPERTY_MAP)
        self.concurrency = concurrency
        self.request_interval = request_interval

        if not self.token:
            raise ValueError("NOTION_TOKEN が設定されていません。")
        if not self.database_id:
            raise ValueError(
                "登録先データベースIDが解決できません。config の notion.database_id / "
                "notion.database_id_env、または環境変数 DATABASE_ID を設定してください。"
            )

        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

    @staticmethod
    def _resolve_database_id(notion_conf: dict[str, Any]) -> str | None:
        """データベースIDを config → 環境変数(指定名) → DATABASE_ID の順で解決。"""
        if notion_conf.get("database_id"):
            return notion_conf["database_id"]
        env_name = notion_conf.get("database_id_env")
        if env_name and os.getenv(env_name):
            return os.getenv(env_name)
        return os.getenv("DATABASE_ID")

    def build_properties(self, pres: Presentation) -> dict[str, Any]:
        """
        Presentation を property_map に従って Notion プロパティ辞書に変換します。
        """
        properties: dict[str, Any] = {}
        for source, spec in self.property_map.items():
            prop_name = spec["name"]
            prop_type = spec["type"]
            built = self._build_property(source, prop_type, pres)
            if built is not None:
                properties[prop_name] = built
        return properties

    def _build_property(
        self, source: str, prop_type: str, pres: Presentation
    ) -> dict[str, Any] | None:
        """1プロパティ分の Notion JSON を生成します。値が無い date は None を返し省略。"""
        if prop_type == "date":
            if pres.date_start and pres.date_end:
                return {"date": {"start": pres.date_start, "end": pres.date_end}}
            if pres.date_start:
                return {"date": {"start": pres.date_start}}
            return None

        value = self._resolve_value(source, pres)

        if prop_type == "title":
            return {"title": [{"text": {"content": value}}]}
        if prop_type == "rich_text":
            return {"rich_text": [{"text": {"content": value}}]}
        if prop_type == "select":
            return {"select": {"name": value}} if value else None
        if prop_type == "checkbox":
            return {"checkbox": bool(value)}

        logger.warning(f"未対応のプロパティ型です: {prop_type}（{source}）")
        return None

    @staticmethod
    def _resolve_value(source: str, pres: Presentation) -> str:
        """source キーから Presentation の値（または extra）を取り出します。"""
        if hasattr(pres, source):
            return getattr(pres, source) or ""
        return str(pres.extra.get(source, ""))

    async def _add_one(self, session, pres, semaphore, index, total, progress):
        """1件を非同期登録します。戻り値: (成功フラグ, Presentation)"""
        payload = {
            "parent": {"database_id": self.database_id},
            "properties": self.build_properties(pres),
        }
        async with semaphore:  # レート制限を適用
            try:
                async with session.post(
                    NOTION_API_URL, json=payload, headers=self.headers
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(
                            f"[{index}/{total}] 登録失敗: {pres.title}\n"
                            f"  ステータス: {response.status}\n"
                            f"  レスポンス: {error_text}"
                        )
                        if progress:
                            progress.update(1)
                        return (False, pres)

                    # レート制限対策: 各リクエスト後に少し待機（約3リクエスト/秒）
                    await asyncio.sleep(self.request_interval)
                    if progress:
                        progress.update(1)
                    return (True, pres)
            except Exception as e:
                logger.error(f"[{index}/{total}] 登録失敗: {pres.title} - {e}")
                if progress:
                    progress.update(1)
                return (False, pres)

    async def batch(self, presentations: list[Presentation]) -> tuple[int, int]:
        """
        複数の発表を並列で Notion に登録します。

        Returns:
        tuple: (成功件数, 失敗件数)
        """
        semaphore = asyncio.Semaphore(self.concurrency)
        async with aiohttp.ClientSession() as session:
            with tqdm(total=len(presentations), desc="Notion登録中", unit="件") as progress:
                tasks = [
                    self._add_one(session, pres, semaphore, i, len(presentations), progress)
                    for i, pres in enumerate(presentations, 1)
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = sum(1 for r in results if isinstance(r, tuple) and r[0])
        fail_count = len(results) - success_count
        return success_count, fail_count
