"""デッキ結果ページのHTMLパース"""

import logging
import re

from bs4 import BeautifulSoup

from app.core.errors import DeckError

logger = logging.getLogger(__name__)

# script内の `[番号]='値'` を抽出する正規表現
_ITEM_PATTERN = re.compile(r"\[(\d+)\]='([^']+)'")


def parse_card_dicts(bs):
    """カード名辞書と画像辞書を抽出する。

    Returns:
        (card_name_dict, card_image_dict): いずれも {カードID(str): 値} の辞書。
    Raises:
        DeckError: 想定した ``<script>`` タグ数でない場合（500）。
    """
    scripts = bs.find_all("script", attrs={"type": "", "src": ""})

    if len(scripts) != 2:
        logger.exception(
            f"Unexpected <script> tag count: expected = 2, actual = {len(scripts)}"
        )
        raise DeckError()

    text = scripts[-1]

    card_name_dict = {}
    card_image_dict = {}

    for item in str(text).strip().split(";"):
        line = item.strip()

        if not line:
            continue

        if "searchItemNameAlt" in line:
            match = _ITEM_PATTERN.search(line)
            if match:
                card_name_dict[match.group(1)] = match.group(2)

        if "searchItemCardPict" in line:
            match = _ITEM_PATTERN.search(line)
            if match:
                card_image_dict[match.group(1)] = match.group(2)

    return card_name_dict, card_image_dict


def get_input_area(bs):
    """inputArea要素をパースしたBeautifulSoupを返す。

    Raises:
        DeckError: inputArea要素が1個でない場合（500）。
    """
    areas = bs.find_all(id="inputArea")

    if len(areas) != 1:
        logger.exception(
            f"Unexpected 'inputArea' id count: expected = 1, actual = {len(areas)}"
        )
        raise DeckError()

    return BeautifulSoup(str(areas[0]), "html.parser")


def parse_card_counts(value):
    """input要素のvalue文字列を {カードID(str): 枚数(int)} の辞書に変換する。"""
    return {
        k: int(v)
        for k, v in (
            val.rsplit("_", 1)[0].split("_") for val in value.split("-")
        )
    }
