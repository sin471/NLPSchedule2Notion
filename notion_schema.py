"""
Notionデータベースの自動作成

config の notion.property_map から、Notion API でデータベースを生成する。
main.py の登録で使う NOTION_TOKEN と同じインテグレーションで作成するため、
作成したDBにはそのまま登録できる（権限共有の追加作業が不要）。
"""

import logging
import os
from typing import Any

import requests

from notion_writer import DEFAULT_PROPERTY_MAP

logger = logging.getLogger(__name__)

NOTION_DATABASES_URL = "https://api.notion.com/v1/databases"

# property_map の type → Notion データベーススキーマ定義
_TYPE_SCHEMA = {
    "title": {"title": {}},
    "rich_text": {"rich_text": {}},
    "date": {"date": {}},
    "select": {"select": {}},
    "checkbox": {"checkbox": {}},
    "number": {"number": {}},
    "url": {"url": {}},
}


def build_database_properties(property_map: dict[str, Any]) -> dict[str, Any]:
    """
    property_map から Notion データベース作成用の properties スキーマを構築します。

    Raises:
    ValueError: title 型が存在しない、または未対応の型が含まれる場合
    """
    properties: dict[str, Any] = {}
    title_count = 0
    for source, spec in property_map.items():
        name = spec["name"]
        prop_type = spec["type"]
        if prop_type == "title":
            title_count += 1
        if prop_type not in _TYPE_SCHEMA:
            raise ValueError(
                f"未対応のプロパティ型です: {prop_type}（{source}）。"
                f"対応型: {', '.join(_TYPE_SCHEMA)}"
            )
        properties[name] = _TYPE_SCHEMA[prop_type]

    if title_count != 1:
        raise ValueError(
            f"title 型のプロパティは丁度1つ必要です（現在: {title_count}個）。"
            "property_map を確認してください。"
        )
    return properties


def create_database(
    conf: dict[str, Any],
    parent_page_id: str,
    token: str | None = None,
    title: str | None = None,
) -> str:
    """
    学会設定の property_map に基づいて Notion データベースを作成します。

    Parameters:
    conf: 学会設定（notion.property_map を含む）
    parent_page_id: 作成先の親ページID（インテグレーションが編集権限を持つこと）
    token: Notion APIトークン（省略時は環境変数 NOTION_TOKEN）
    title: DBのタイトル（省略時は conf["name"]）

    Returns:
    str: 作成されたデータベースID
    """
    token = token or os.getenv("NOTION_TOKEN")
    if not token:
        raise ValueError("NOTION_TOKEN が設定されていません。")

    property_map = conf.get("notion", {}).get("property_map", DEFAULT_PROPERTY_MAP)
    db_title = title or conf.get("name", "学会プログラム")

    payload = {
        "parent": {"type": "page_id", "page_id": parent_page_id},
        "title": [{"type": "text", "text": {"content": db_title}}],
        "properties": build_database_properties(property_map),
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }

    logger.info(f"データベースを作成します: '{db_title}'（親ページ: {parent_page_id}）")
    response = requests.post(NOTION_DATABASES_URL, json=payload, headers=headers, timeout=30)
    if response.status_code != 200:
        logger.error(f"データベース作成に失敗しました: {response.status_code}\n{response.text}")
        response.raise_for_status()

    database_id = response.json()["id"]
    logger.info(f"データベースを作成しました: {database_id}")
    return database_id
