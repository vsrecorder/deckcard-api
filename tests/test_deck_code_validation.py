"""デッキコードの書式検証のテスト（DB・ネットワークに依存しない）"""

from fastapi.responses import JSONResponse

from app.core.constants import is_valid_deck_code
from app.scraping import fetcher


def test_is_valid_deck_code_accepts_alphanumeric_and_hyphen():
    assert is_valid_deck_code("xxxxxx") is True
    assert is_valid_deck_code("abc-123-DEF") is True
    assert is_valid_deck_code("MgHRLg-abc123-9nQ") is True


def test_is_valid_deck_code_rejects_other_characters():
    assert is_valid_deck_code("") is False
    assert is_valid_deck_code("..") is False
    assert is_valid_deck_code("a/b") is False
    assert is_valid_deck_code("a@b") is False
    assert is_valid_deck_code("a b") is False
    assert is_valid_deck_code("abc?x=1") is False
    assert is_valid_deck_code("café") is False
    # 末尾の改行を $ で通してしまわないこと（fullmatch を使っている）
    assert is_valid_deck_code("abc\n") is False


def test_fetch_deck_html_rejects_invalid_code_without_network(monkeypatch):
    """書式外のコードは外部取得の前に 400 で弾く（ネットワークを叩かない）。"""

    def _fail(*args, **kwargs):
        raise AssertionError("network must not be called for an invalid deck code")

    # 書式検証をすり抜けて外部取得へ進んだら、この差し替えで即座に失敗する
    monkeypatch.setattr(fetcher._session, "get", _fail)

    res = fetcher.fetch_deck_html("../etc")

    assert isinstance(res, JSONResponse)
    assert res.status_code == 400
