import asyncio
import logging
import os
import time
from pathlib import Path

import aiohttp
import requests
import yaml
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from tqdm.asyncio import tqdm

from parsers import create_parser

# ロギング設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 環境変数の読み込み
load_dotenv()

# 設定情報（環境変数から取得）
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")

# 必須環境変数のチェック
if not all([NOTION_TOKEN, DATABASE_ID]):
    logger.error("環境変数が設定されていません。.envファイルを確認してください。")
    raise ValueError("必須の環境変数が不足しています")

# 設定ファイルの読み込み
config_path = Path(__file__).parent / "config.yaml"
if not config_path.exists():
    logger.error(f"設定ファイルが見つかりません: {config_path}")
    logger.info("config.yaml.example を config.yaml にコピーして設定してください。")
    raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")

with open(config_path, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

# アクティブな学会設定を取得
active_conf_name = config.get("active_conference", "nlp2026")
if active_conf_name not in config.get("conferences", {}):
    logger.error(f"指定された学会設定が見つかりません: {active_conf_name}")
    raise ValueError(f"学会設定 '{active_conf_name}' が config.yaml に存在しません")

conf = config["conferences"][active_conf_name]
logger.info(f"使用する学会設定: {conf['name']}")

# パーサーインスタンスを作成
parser = create_parser(conf)

# 学会固有の設定を変数に格納
PROGRAM_URL = conf["url"]

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}


def get_program_data(use_local_file: bool = True):
    """
    プログラムデータを取得します。

    Parameters:
    use_local_file (bool): Trueの場合はローカルHTMLファイルから、Falseの場合はURLから取得

    Returns:
    list: プログラムデータのリスト
    """
    try:
        if use_local_file:
            # ローカルHTMLファイルから読み込み
            html_file = Path(__file__).parent / "nlp2026_program.html"
            if not html_file.exists():
                logger.error(f"HTMLファイルが見つかりません: {html_file}")
                logger.info("先にfetch_html.pyを実行してHTMLファイルを取得してください")
                raise FileNotFoundError(f"HTMLファイルが見つかりません: {html_file}")

            logger.info(f"ローカルHTMLファイルから読み込み: {html_file}")
            html_content = html_file.read_text(encoding="utf-8")
            soup = BeautifulSoup(html_content, "html.parser")
        else:
            # URLから取得
            logger.info(f"URLから取得: {PROGRAM_URL}")
            res = requests.get(PROGRAM_URL, timeout=30)
            res.raise_for_status()
            res.encoding = res.apparent_encoding
            soup = BeautifulSoup(res.text, "html.parser")

        # パーサーを使ってプログラムデータを抽出
        results = parser.parse_program(soup)
        return results

    except Exception as e:
        logger.error(f"プログラムデータの取得に失敗しました: {e}")
        raise


def add_to_notion(data):
    """
    Notionデータベースにデータを追加します（非推奨：非同期版を使用してください）。

    Parameters:
    data (dict): 追加するデータ（id, title, authors, session_name, date_start, date_end, venueを含む）

    Returns:
    int: HTTPステータスコード
    """
    url = "https://api.notion.com/v1/pages"

    # プロパティを構築
    properties = {
        "タイトル": {"title": [{"text": {"content": data["title"]}}]},
        "ID": {"rich_text": [{"text": {"content": data["id"]}}]},
        "著者": {"rich_text": [{"text": {"content": data["authors"]}}]},
        "セッション": {"rich_text": [{"text": {"content": data["session_name"]}}]},
        "会場": {"rich_text": [{"text": {"content": data["venue"]}}]},
    }

    # 日時プロパティを追加（日付情報がある場合のみ）
    if data.get("date_start") and data.get("date_end"):
        properties["日時"] = {
            "date": {
                "start": data["date_start"],
                "end": data["date_end"],
            }
        }

    payload = {"parent": {"database_id": DATABASE_ID}, "properties": properties}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.status_code
    except requests.exceptions.RequestException as e:
        logger.error(f"Notion APIへの投稿に失敗しました: {e}")
        if hasattr(e, "response") and e.response is not None:
            logger.error(f"レスポンス: {e.response.text}")
        raise


async def add_to_notion_async(session, data, semaphore, index, total, progress=None):
    """
    Notionデータベースにデータを非同期で追加します。

    Parameters:
    session (aiohttp.ClientSession): HTTPセッション
    data (dict): 追加するデータ
    semaphore (asyncio.Semaphore): レート制限用セマフォ
    index (int): 現在のインデックス
    total (int): 全体の件数
    progress (tqdm): 進捗バーオブジェクト

    Returns:
    tuple: (成功/失敗, データ)
    """
    url = "https://api.notion.com/v1/pages"

    # プロパティを構築
    properties = {
        "タイトル": {"title": [{"text": {"content": data["title"]}}]},
        "ID": {"rich_text": [{"text": {"content": data["id"]}}]},
        "著者": {"rich_text": [{"text": {"content": data["authors"]}}]},
        "セッション": {"rich_text": [{"text": {"content": data["session_name"]}}]},
        "会場": {"rich_text": [{"text": {"content": data["venue"]}}]},
    }

    # 日時プロパティを追加（日付情報がある場合のみ）
    if data.get("date_start") and data.get("date_end"):
        properties["日時"] = {
            "date": {
                "start": data["date_start"],
                "end": data["date_end"],
            }
        }

    payload = {"parent": {"database_id": DATABASE_ID}, "properties": properties}

    async with semaphore:  # レート制限を適用
        try:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status != 200:
                    # エラーレスポンスの詳細を取得
                    error_text = await response.text()
                    logger.error(
                        f"[{index}/{total}] 登録失敗: {data['title']}\n"
                        f"  ステータス: {response.status}\n"
                        f"  レスポンス: {error_text}"
                    )
                    if progress:
                        progress.update(1)
                    return (False, data)
                
                # レート制限対策: 各リクエスト後に少し待機（約3リクエスト/秒）
                await asyncio.sleep(0.35)
                if progress:
                    progress.update(1)
                return (True, data)
        except Exception as e:
            logger.error(f"[{index}/{total}] 登録失敗: {data['title']} - {e}")
            if progress:
                progress.update(1)
            return (False, data)


async def batch_add_to_notion(programs):
    """
    複数のプログラムを並列でNotionに追加します。

    Parameters:
    programs (list): プログラムデータのリスト

    Returns:
    tuple: (成功件数, 失敗件数)
    """
    # Notion APIのレート制限: 3リクエスト/秒
    # セマフォで同時実行数を制御（3並列）
    semaphore = asyncio.Semaphore(3)

    async with aiohttp.ClientSession() as session:
        # 進捗バーを作成
        with tqdm(total=len(programs), desc="Notion登録中", unit="件") as progress:
            tasks = [
                add_to_notion_async(session, program, semaphore, i, len(programs), progress)
                for i, program in enumerate(programs, 1)
            ]

            # すべてのタスクを実行
            results = await asyncio.gather(*tasks, return_exceptions=True)

        # 結果を集計
        success_count = sum(1 for r in results if isinstance(r, tuple) and r[0])
        fail_count = len(results) - success_count

        return success_count, fail_count


# 実行
if __name__ == "__main__":
    try:
        logger.info("プログラムデータの取得を開始します")
        programs = get_program_data(use_local_file=True)

        logger.info(f"Notionへの登録を開始します（{len(programs)}件）")
        start_time = time.time()

        # 非同期バッチ処理で一括登録
        success_count, fail_count = asyncio.run(batch_add_to_notion(programs))

        elapsed_time = time.time() - start_time
        logger.info(
            f"処理完了: 成功 {success_count}件, 失敗 {fail_count}件 "
            f"(処理時間: {elapsed_time:.1f}秒)"
        )

    except Exception as e:
        logger.error(f"エラーが発生しました: {e}")
        exit(1)
