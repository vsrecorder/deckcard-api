"""デッキ結果ページのHTMLパース"""

import html
import logging
import re

from bs4 import BeautifulSoup

from app.core.errors import DeckError

logger = logging.getLogger(__name__)


def _item_pattern(key):
    """script内の `PCGDECK.<key>[番号]='値'` を抽出する正規表現を生成する。

    値はJS文字列リテラルなので、``\\'`` によるエスケープを考慮して
    エスケープされていない ``'`` までを1つの値として取り出す。
    """
    return re.compile(rf"{key}\[(\d+)\]\s*=\s*'((?:[^'\\]|\\.)*)'")


_NAME_PATTERN = _item_pattern("searchItemNameAlt")
_IMAGE_PATTERN = _item_pattern("searchItemCardPict")


def _unescape(value):
    """script内の値からJSエスケープとHTMLエンティティを解除する。

    カード名は ``ゲンガー&amp;ミミッキュGX`` のようにHTMLエンティティ化されて
    埋め込まれているため、``&`` などへ復元する必要がある。
    """
    # JSのバックスラッシュエスケープ（\' など）を解除する
    value = re.sub(r"\\(.)", r"\1", value)

    return html.unescape(value)


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

    text = str(scripts[-1])

    # `;` で分割してから走査すると、カード名に含まれるHTMLエンティティ（`&amp;`）の
    # 末尾の `;` で値が途切れてしまうため、script全体に対して直接マッチさせる
    card_name_dict = {
        card_id: _unescape(value) for card_id, value in _NAME_PATTERN.findall(text)
    }
    card_image_dict = {
        card_id: _unescape(value) for card_id, value in _IMAGE_PATTERN.findall(text)
    }

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
