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


# エンドポイントごとのレスポンスキャッシュ。
#
# 以前は4つとも一律 2000 件だったが、実際の使われ方は大きく偏っている
# (本番の nginx ログ4日ぶん、上流に届いた本数):
#
#   /detail   51,170本 (ユニーク 48,771)   ← シティリーグ結果ページが1ページに16件引く
#   /list        438本 (ユニーク    128)
#   /summary       0本
#   /acespec       0本  (webapp 側が1日のブラウザキャッシュを付けているため届かない)
#
# 総量は増やせない。ワーカーは gunicorn -w 2 で、稼働22日の実測は1本あたり約200MB、
# コンテナ全体で 398MiB / 上限 512m(78%)まで来ている。そこで一律に増やすのではなく、
# 使われていないぶんを削って /detail へ回す。1件は実測 6KB 前後なので、
# 差し引きではむしろ数MB減る。
#
# 上限を触るときは docker-compose.yml の mem_limit と実測(docker stats)を必ず併せて見ること。
acespec_cache = ThreadSafeCache(cachetools.LRUCache(maxsize=1000))

deck_list_cache = ThreadSafeCache(cachetools.LFUCache(maxsize=300))
deck_summary_cache = ThreadSafeCache(cachetools.LFUCache(maxsize=200))
deck_detail_cache = ThreadSafeCache(cachetools.LFUCache(maxsize=4000))

# pokemon_cardsマスタ（card_id -> (ability, attacks)）のキャッシュ。
# ほぼ不変のマスタデータだが、更新反映のため24時間のTTLを設ける。
# 無期限にしたい場合は cachetools.LRUCache(maxsize=20000) に差し替える。
pokemon_card_cache = ThreadSafeCache(
    cachetools.TTLCache(maxsize=20000, ttl=60 * 60 * 24)
)

# ACE SPECカードのIDの集合のキャッシュ。集合ひとつを丸ごと保持するのでmaxsizeは1。
# 新しいACE SPECの追加を取り込むため、こちらも24時間のTTLを設ける。
acespec_ids_cache = ThreadSafeCache(cachetools.TTLCache(maxsize=1, ttl=60 * 60 * 24))
