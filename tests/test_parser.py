"""parser のテスト（DB接続に依存しない層のみ）"""

import pathlib

from app.scraping.parser import is_deck_not_found

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def test_is_deck_not_found_true_for_official_error_page():
    """存在しないデッキコードで公式サイトが返す HTTP 200 のエラーページを検出する。

    このページはステータスが 200 で、<script> や inputArea も揃っているため
    解析自体は通る。目印で not found と判定できないと 60 枚チェックで 500 になる。
    """
    html = (FIXTURES / "deck_not_found.html").read_text(encoding="utf-8")
    assert is_deck_not_found(html) is True


def test_is_deck_not_found_false_for_normal_page():
    """正規のデッキ結果ページに現れる断片では not found と誤判定しない。"""
    normal = (
        "<html><head><title>デッキ</title></head>"
        "<body><div id='inputArea'>"
        "<input id='deck_pke' value='1234_1'></div></body></html>"
    )
    assert is_deck_not_found(normal) is False


def test_is_deck_not_found_requires_all_markers():
    """目印が一部しか現れない場合は not found と判定しない（誤検出を避ける）。"""
    # 「見つかりません」だけがどこかに現れても、エラーページの見出しが無ければ False
    assert is_deck_not_found("検索結果が見つかりませんでした") is False
    # 見出しだけでもう一方の文言が無ければ False
    assert is_deck_not_found("<h1>デッキコードエラー</h1>") is False
