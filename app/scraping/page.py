"""デッキ結果ページから読み取った内容（デッキの構成）とそのキャッシュ

デッキ結果ページのうちレスポンスに使うのは、カード名・カード画像のパスと、区分ごとの
「カードID_枚数」の並びだけ。これらはデッキコードが同じなら変わらない（デッキコードは
作成時の構成に対して発行され、配信元に保存したHTMLも一度書いたら上書きしない）。

そこで、読み取った内容だけを :data:`app.core.cache.deck_page_cache` に期限なしで持ち、
ページの取得とHTMLの解析をデッキコードごとに1回で済ませる。

ここに持つのはページ由来の値だけで、カードマスタ（DB）由来の値は一切持たない。
特性・ワザ・ACE SPEC の判定は、これまでどおりレスポンスを組み立てるたびにマスタ
（TTL付きの pokemon_card_cache / acespec_ids_cache）から引く。レスポンスキャッシュの
TTL（マスタ更新の反映）はそのまま効く。
"""

import json
import logging
import zlib

from bs4 import BeautifulSoup
from fastapi.responses import JSONResponse

from app.core.cache import deck_page_cache
from app.scraping.fetcher import fetch_deck_html
from app.scraping.parser import get_input_area, parse_card_counts, parse_card_dicts

logger = logging.getLogger(__name__)

# input要素のうち、カードとして扱わないid
SKIP_INPUT_IDS = {"deck_ajs", "copyDeckID"}

# input要素から持ち回る属性。レスポンスの組み立てが読むのはこの2つだけ
_INPUT_ATTRS = ("id", "value")


class DeckPage:
    """デッキ結果ページから読み取った内容。

    解析に失敗したページも表せる。失敗は読み取った時点では送出せず、以前の実装で
    その値を取り出していた箇所（:meth:`card_dicts` / :meth:`input_items`）で送出する。
    エンドポイントによって使う値が違い（ACE SPEC は input 要素を読まない）、
    どの失敗がどのレスポンスになるかを変えないため。
    """

    def __init__(
        self, card_names, card_images, inputs, card_dicts_error=None, inputs_error=None
    ):
        self._card_names = card_names
        self._card_images = card_images
        self._inputs = inputs
        self._card_dicts_error = card_dicts_error
        self._inputs_error = inputs_error

    def card_dicts(self):
        """カード名辞書と画像辞書 ``({カードID(str): 名前}, {カードID(str): 画像パス})``。

        Raises:
            DeckError: 想定した ``<script>`` タグ数でなかったページ（500）。
        """
        if self._card_dicts_error is not None:
            raise self._card_dicts_error

        return self._card_names, self._card_images

    def input_items(self):
        """inputArea の input 要素の並び ``[{"id": ..., "value": ...}, ...]``。

        属性を持たない input 要素では、そのキーも持たない（参照すると ``KeyError``。
        以前の BeautifulSoup の要素と同じ）。

        Raises:
            DeckError: inputArea 要素が1個でなかったページ（500）。
        """
        if self._inputs_error is not None:
            raise self._inputs_error

        return self._inputs

    def is_complete(self):
        """レスポンスを組み立てられる、正常なデッキのページか。

        キャッシュに載せてよいかの判定に使う。60枚そろっていて、すべてのカードの
        名前と画像が読めたページだけを True にする。メンテナンス中のページや
        解析に失敗したページを期限なしで持ち続けないため。
        """
        if self._card_dicts_error is not None or self._inputs_error is not None:
            return False

        try:
            total = 0
            for item in self._inputs:
                if item["id"] in SKIP_INPUT_IDS:
                    continue
                if not item["value"]:
                    continue
                for card_id, count in parse_card_counts(item["value"]).items():
                    if card_id not in self._card_names:
                        return False
                    if card_id not in self._card_images:
                        return False
                    total += count
        except Exception:
            return False

        return total == 60

    def dumps(self):
        """キャッシュに載せるバイト列にする（:meth:`is_complete` が True のページ用）。

        JSON にして圧縮する。Python のオブジェクトのまま持つより一桁小さい
        （2026-11-25 の実測: 1件あたり JSON で約 3KB、圧縮して約 1.2KB）。
        辞書の並びは JSON でも保たれる（ACE SPEC の判定は名前辞書を先頭から見るので、
        並びを変えてはならない）。
        """
        text = json.dumps(
            [self._card_names, self._card_images, self._inputs],
            ensure_ascii=False,
            separators=(",", ":"),
        )

        return zlib.compress(text.encode("utf-8"), 1)

    @classmethod
    def loads(cls, data):
        """:meth:`dumps` のバイト列から復元する。呼ぶたびに新しいオブジェクトを作る。"""
        card_names, card_images, inputs = json.loads(zlib.decompress(data))

        return cls(card_names, card_images, inputs)


def parse_deck_page(html_text):
    """デッキ結果ページのHTMLから :class:`DeckPage` を読み取る。例外は送出しない。"""
    try:
        bs = BeautifulSoup(html_text, "html.parser")
        card_names, card_images = parse_card_dicts(bs)
    except Exception as e:
        # 以前の実装はここで処理を打ち切っていた（inputArea は見ない）
        return DeckPage(None, None, None, card_dicts_error=e)

    try:
        input_area = get_input_area(bs)
        inputs = [
            {attr: item[attr] for attr in _INPUT_ATTRS if attr in item.attrs}
            for item in input_area.find_all("input")
        ]
    except Exception as e:
        return DeckPage(card_names, card_images, None, inputs_error=e)

    return DeckPage(card_names, card_images, inputs)


def load_deck_page(deck_code):
    """デッキコードのページの内容を返す。キャッシュに無ければ取得して読み取る。

    Returns:
        DeckPage: 読み取った内容。
        JSONResponse: ページの取得に失敗した場合（:func:`fetch_deck_html` と同じ）。
    """
    cached = deck_page_cache.get(deck_code)
    if cached is not None:
        logger.info(f"[deck page] cache hit deck_code={deck_code}")
        return DeckPage.loads(cached)

    res = fetch_deck_html(deck_code)
    if isinstance(res, JSONResponse):
        return res

    page = parse_deck_page(res.text)

    if page.is_complete():
        deck_page_cache[deck_code] = page.dumps()
        logger.info(f"[deck page] cache store deck_code={deck_code}")

    return page
