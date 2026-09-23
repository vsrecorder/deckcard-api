"""constants のテスト（DB接続に依存しない層のみ）"""

from app.core.constants import split_attacks, strip_acespec


def test_split_attacks_splits_by_slash():
    assert split_attacks("ジェットヘッド/ファントムダイブ") == [
        "ジェットヘッド",
        "ファントムダイブ",
    ]


def test_split_attacks_single():
    assert split_attacks("ストームダイブ") == ["ストームダイブ"]


def test_split_attacks_empty_becomes_empty_list():
    """ワザを持たないポケモン（特性だけのカード）は空リストにする。

    "".split("/") は [""] を返す。そのまま返すと「名前の無いワザが 1 つある」
    ことになり、カードマスタ（空リスト）と食い違って、同じカードなのに
    毎回「値が違う」と判定されてしまう。
    """
    assert split_attacks("") == []
    assert split_attacks("   ") == []
    assert split_attacks(None) == []


def test_strip_acespec():
    assert strip_acespec("マキシマムベルト(ACE SPEC)") == "マキシマムベルト"
    assert strip_acespec("クイックボール") == "クイックボール"
