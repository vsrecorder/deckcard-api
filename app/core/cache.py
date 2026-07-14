"""レスポンスキャッシュ

サービス層でのキャッシュ格納と、ルート層でのキャッシュ参照の双方で共有する。
"""

import threading

import cachetools


class ThreadSafeCache:
    """cachetoolsのキャッシュをロックで保護するラッパー。

    FastAPIの同期エンドポイント（``async`` でない ``def``）はスレッドプール上で
    並行実行されるため、スレッドセーフでないcachetoolsのキャッシュをそのまま
    共有すると内部状態が壊れて ``KeyError`` を送出することがある。

    参照は :meth:`get` に一本化している。``in`` で存在確認してから ``[]`` で取り出すと、
    その隙に別スレッドのevictionが挟まって ``KeyError`` になるため。
    """

    def __init__(self, cache):
        self._cache = cache
        self._lock = threading.Lock()

    def get(self, key, default=None):
        """キーを1回のロックで参照する。未格納なら ``default`` を返す。"""
        with self._lock:
            return self._cache.get(key, default)

    def __setitem__(self, key, value):
        with self._lock:
            self._cache[key] = value

    def __len__(self):
        with self._lock:
            return len(self._cache)


deckcards_cache = ThreadSafeCache(cachetools.LRUCache(maxsize=2000))
acespec_cache = ThreadSafeCache(cachetools.LRUCache(maxsize=2000))

deck_list_cache = ThreadSafeCache(cachetools.LFUCache(maxsize=2000))
deck_summary_cache = ThreadSafeCache(cachetools.LFUCache(maxsize=2000))

# pokemon_cardsマスタ（card_id -> (ability, attacks)）のキャッシュ。
# ほぼ不変のマスタデータだが、更新反映のため24時間のTTLを設ける。
# 無期限にしたい場合は cachetools.LRUCache(maxsize=20000) に差し替える。
pokemon_card_cache = ThreadSafeCache(
    cachetools.TTLCache(maxsize=20000, ttl=60 * 60 * 24)
)

# ACE SPECカードのIDの集合のキャッシュ。集合ひとつを丸ごと保持するのでmaxsizeは1。
# 新しいACE SPECの追加を取り込むため、こちらも24時間のTTLを設ける。
acespec_ids_cache = ThreadSafeCache(cachetools.TTLCache(maxsize=1, ttl=60 * 60 * 24))
