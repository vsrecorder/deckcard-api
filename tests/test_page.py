"""デッキ結果ページの読み取りとそのキャッシュ（DB接続に依存しない層のみ）"""

import cachetools
import pytest
from fastapi.responses import JSONResponse

from app.core.cache import ThreadSafeCache
from app.core.errors import DeckError
from app.scraping import page as page_module
from app.scraping.page import DeckPage, load_deck_page, parse_deck_page


def deck_html(
    pke="1001_4_1-1002_2_1",
    gds="2001_4_1",
    ene="3001_50_1",
    names=None,
    images=None,
    scripts=2,
    input_areas=1,
):
    """デッキ結果ページの、読み取りに関わる部分だけを持つHTMLを組み立てる。"""
    if names is None:
        names = {
            "1001": "ピカチュウex",
            "1002": "ゲンガー&amp;ミミッキュGX",
            "2001": "ハイパーボール",
            "3001": "基本雷エネルギー",
        }
    if images is None:
        images = {card_id: f"/assets/images/card_images/large/X/{card_id}.jpg" for card_id in names}

    js = "".join(f"PCGDECK.searchItemNameAlt[{k}]='{v}';" for k, v in names.items())
    js += "".join(f"PCGDECK.searchItemCardPict[{k}]='{v}';" for k, v in images.items())
    script_tags = "<script>var a=1;</script>" + f"<script>{js}</script>" * (scripts - 1)

    area = (
        '<div id="inputArea">'
        '<input type="hidden" id="deck_pke" value="{pke}">'
        '<input type="hidden" id="deck_gds" value="{gds}">'
        '<input type="hidden" id="deck_tool" value="">'
        '<input type="hidden" id="deck_ene" value="{ene}">'
        '<input type="hidden" id="deck_ajs" value="">'
        '<input type="text" id="copyDeckID" value="aaaaaa-bbbbbb-cccccc">'
        "</div>"
    ).format(pke=pke, gds=gds, ene=ene)

    return f"<html><head>{script_tags}</head><body>{area * input_areas}</body></html>"


@pytest.fixture
def cache(monkeypatch):
    """テストごとに空のキャッシュへ差し替える。"""
    fresh = ThreadSafeCache(cachetools.LRUCache(maxsize=10))
    monkeypatch.setattr(page_module, "deck_page_cache", fresh)
    return fresh


@pytest.fixture
def fetches(monkeypatch):
    """ページの取得を差し替え、取りに行ったデッキコードを記録する。"""
    calls = []
    pages = {}

    class Res:
        def __init__(self, text):
            self.text = text

    def fake_fetch(deck_code):
        calls.append(deck_code)
        value = pages[deck_code]
        return value if isinstance(value, JSONResponse) else Res(value)

    monkeypatch.setattr(page_module, "fetch_deck_html", fake_fetch)
    return calls, pages


def test_parse_reads_names_images_and_inputs():
    page = parse_deck_page(deck_html())

    names, images = page.card_dicts()
    assert names["1001"] == "ピカチュウex"
    # HTMLエンティティは復元される
    assert names["1002"] == "ゲンガー&ミミッキュGX"
    assert images["2001"] == "/assets/images/card_images/large/X/2001.jpg"

    # input 要素はページの並びのまま。カードとして扱わないものも含めて持つ
    # （どれを読み飛ばすかはレスポンスを組み立てる側が決める）
    assert page.input_items() == [
        {"id": "deck_pke", "value": "1001_4_1-1002_2_1"},
        {"id": "deck_gds", "value": "2001_4_1"},
        {"id": "deck_tool", "value": ""},
        {"id": "deck_ene", "value": "3001_50_1"},
        {"id": "deck_ajs", "value": ""},
        {"id": "copyDeckID", "value": "aaaaaa-bbbbbb-cccccc"},
    ]
    assert page.is_complete() is True


def test_roundtrip_keeps_content_and_order():
    """キャッシュに載せて戻しても、内容と辞書の並びが変わらない。

    ACE SPEC の判定は名前辞書を先頭から見て最初に当たったカードを返すので、
    並びが変わるとレスポンスが変わる。
    """
    names = {"900": "ん", "5": "あ", "1001": "ピカチュウex", "20": "い"}
    page = parse_deck_page(deck_html(pke="900_10_1-5_10_1", gds="1001_20_1", ene="20_20_1", names=names))
    assert page.is_complete() is True

    restored = DeckPage.loads(page.dumps())

    assert restored.card_dicts() == page.card_dicts()
    assert list(restored.card_dicts()[0]) == ["900", "5", "1001", "20"]
    assert restored.input_items() == page.input_items()
    assert restored.is_complete() is True


def test_loads_returns_independent_objects():
    """復元したものを書き換えても、キャッシュの中身や他の復元結果に影響しない。"""
    data = parse_deck_page(deck_html()).dumps()

    first = DeckPage.loads(data)
    first.card_dicts()[0]["1001"] = "書き換え"
    first.input_items().clear()

    second = DeckPage.loads(data)
    assert second.card_dicts()[0]["1001"] == "ピカチュウex"
    assert len(second.input_items()) == 6


def test_script_count_error_is_raised_where_card_dicts_are_read():
    """<script> の数が想定と違うページは、名前辞書を取り出すところで DeckError になる。"""
    page = parse_deck_page(deck_html(scripts=3))

    with pytest.raises(DeckError):
        page.card_dicts()
    assert page.is_complete() is False


def test_input_area_error_does_not_block_card_dicts():
    """inputArea が1個でないページでも、名前辞書は読める（ACE SPEC は input を読まない）。"""
    page = parse_deck_page(deck_html(input_areas=2))

    assert page.card_dicts()[0]["1001"] == "ピカチュウex"
    with pytest.raises(DeckError):
        page.input_items()
    assert page.is_complete() is False


@pytest.mark.parametrize(
    "kwargs",
    [
        {"ene": "3001_49_1"},  # 59枚
        {"ene": "3001_51_1"},  # 61枚
        {"pke": "", "gds": "", "ene": ""},  # 0枚（メンテナンス中のページなど）
        {"pke": "1001_4_1-9999_2_1"},  # 名前の無いカードを含む
        {"images": {"1001": "/a.jpg"}},  # 画像の無いカードを含む
        {"ene": "壊れた値"},
    ],
)
def test_incomplete_pages_are_not_complete(kwargs):
    assert parse_deck_page(deck_html(**kwargs)).is_complete() is False


def test_input_without_value_attribute_keeps_key_error():
    """value 属性の無い input 要素は、キーを持たない（参照すると KeyError。以前と同じ）。"""
    html = deck_html().replace('<input type="hidden" id="deck_tool" value="">', '<input type="hidden" id="deck_tool">')
    page = parse_deck_page(html)

    assert {"id": "deck_tool"} in page.input_items()
    assert page.is_complete() is False


def test_load_fetches_once_and_then_uses_cache(cache, fetches):
    calls, pages = fetches
    pages["aaaaaa-bbbbbb-cccccc"] = deck_html()

    first = load_deck_page("aaaaaa-bbbbbb-cccccc")
    second = load_deck_page("aaaaaa-bbbbbb-cccccc")

    assert calls == ["aaaaaa-bbbbbb-cccccc"]
    assert second.card_dicts() == first.card_dicts()
    assert second.input_items() == first.input_items()


def test_load_does_not_cache_incomplete_page(cache, fetches):
    """60枚にならないページは持たない。直ったあとに取り直せるよう、毎回取りに行く。"""
    calls, pages = fetches
    pages["aaaaaa-bbbbbb-cccccc"] = deck_html(ene="3001_49_1")

    page = load_deck_page("aaaaaa-bbbbbb-cccccc")
    load_deck_page("aaaaaa-bbbbbb-cccccc")

    # 読み取った内容はそのまま返す（500 にするのはレスポンスを組み立てる側）
    assert page.input_items()[3] == {"id": "deck_ene", "value": "3001_49_1"}
    assert len(calls) == 2
    assert len(cache) == 0


def test_load_returns_fetch_failure_without_caching(cache, fetches):
    calls, pages = fetches
    pages["zzzzzz-zzzzzz-zzzzzz"] = JSONResponse(content={}, status_code=404)

    res = load_deck_page("zzzzzz-zzzzzz-zzzzzz")
    load_deck_page("zzzzzz-zzzzzz-zzzzzz")

    assert isinstance(res, JSONResponse) and res.status_code == 404
    assert len(calls) == 2
    assert len(cache) == 0
