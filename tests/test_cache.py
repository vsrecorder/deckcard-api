"""キャッシュのTTL

レスポンスキャッシュは「公式ページから読んだカード構成」と「DBから引いた
特性・ワザ」を合成した結果を丸ごと持つ。TTLが無いとマスタを更新しても古い
合成結果を返し続け、同じカードなのに引くデッキによって値が違う状態になる
（2026-09-23 に実際に起きた）。ここではTTLが付いていること、そして期限が
来たら本当に消えることを固定する。
"""

import cachetools
import pytest

from app.core.cache import (
    CACHE_TTL_SECONDS,
    ThreadSafeCache,
    acespec_cache,
    acespec_ids_cache,
    deck_detail_cache,
    deck_list_cache,
    deck_summary_cache,
    pokemon_card_cache,
)


@pytest.mark.parametrize(
    "name, cache",
    [
        ("deck_detail_cache", deck_detail_cache),
        ("deck_list_cache", deck_list_cache),
        ("deck_summary_cache", deck_summary_cache),
        ("acespec_cache", acespec_cache),
        ("pokemon_card_cache", pokemon_card_cache),
        ("acespec_ids_cache", acespec_ids_cache),
    ],
)
def test_all_caches_have_ttl(name, cache):
    """すべてのキャッシュがTTLを持つ。

    どれか一つでもTTLを落とすと、そのエンドポイントだけマスタ更新が
    反映されなくなる。追加したキャッシュもここに足すこと。
    """
    assert cache.ttl == CACHE_TTL_SECONDS, f"{name} にTTLが無い（または値が違う）"


def test_entry_expires_after_ttl():
    """TTLを過ぎたエントリは取り出せない。"""
    now = {"t": 0.0}
    cache = ThreadSafeCache(
        cachetools.TTLCache(maxsize=10, ttl=CACHE_TTL_SECONDS, timer=lambda: now["t"])
    )

    cache["D8ac8K-1B1IPX-Y8cYDD"] = {"ability": "フォトンバリア"}
    assert cache.get("D8ac8K-1B1IPX-Y8cYDD") == {"ability": "フォトンバリア"}

    # 期限の直前はまだ残っている
    now["t"] = CACHE_TTL_SECONDS - 1
    assert cache.get("D8ac8K-1B1IPX-Y8cYDD") is not None

    # 期限を過ぎたら消える（次に引いたときDBから引き直される）
    now["t"] = CACHE_TTL_SECONDS + 1
    assert cache.get("D8ac8K-1B1IPX-Y8cYDD") is None


def test_get_returns_default_for_missing_key():
    """未格納のキーは例外ではなく default を返す（参照は get に一本化している）。"""
    cache = ThreadSafeCache(cachetools.TTLCache(maxsize=10, ttl=CACHE_TTL_SECONDS))
    assert cache.get("未格納") is None
    assert cache.get("未格納", "既定値") == "既定値"
