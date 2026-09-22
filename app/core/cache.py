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

    @property
    def ttl(self):
        """有効期限（秒）。TTLを持たないキャッシュなら ``None``。"""
        return getattr(self._cache, "ttl", None)


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
#
# maxsize は据え置いたままTTLを足した(2026-09-23)。TTLCacheは1件あたり有効期限の
# リンクを余分に持つが、1件6KBのレスポンスに対して数十バイトなので総量は変わらない。
# 期限切れは参照時に遅延削除されるため、引かれないキーはmaxsizeに達するまで残る。
# キャッシュの有効期限（秒）。マスタの更新を取り込むためのもの。
#
# レスポンスキャッシュには必ずこれを付ける。デッキのレスポンスは
# 「公式ページから読んだカード構成」と「DBから引いた特性・ワザ・ACE SPEC」を
# 合成した結果を丸ごと保持しており、TTLが無いとマスタを更新しても古い合成結果を
# 返し続けるため。
#
# 実際に起きた事故(2026-09-23): deck_detail_cache だけTTLが無く、
# pokemon_cards の特性・ワザの抽出を直したあとも、既にキャッシュに乗っていた
# デッキは古い ability='' を返し続けた。同じカードなのに、引くデッキによって
# 返る値が違う状態になり、シティリーグ結果の取り込みバッチが古い card_key を
# 索引して vslab のカード辞書から漏れた。
#
# 内側の pokemon_card_cache にTTLがあっても効かない。外側のレスポンスキャッシュに
# ヒットした時点で、内側は参照されないため。
CACHE_TTL_SECONDS = 60 * 60 * 24

acespec_cache = ThreadSafeCache(
    cachetools.TTLCache(maxsize=1000, ttl=CACHE_TTL_SECONDS)
)

deck_list_cache = ThreadSafeCache(
    cachetools.TTLCache(maxsize=300, ttl=CACHE_TTL_SECONDS)
)
deck_summary_cache = ThreadSafeCache(
    cachetools.TTLCache(maxsize=200, ttl=CACHE_TTL_SECONDS)
)
deck_detail_cache = ThreadSafeCache(
    cachetools.TTLCache(maxsize=4000, ttl=CACHE_TTL_SECONDS)
)

# pokemon_cardsマスタ（card_id -> (ability, attacks)）のキャッシュ。
pokemon_card_cache = ThreadSafeCache(
    cachetools.TTLCache(maxsize=20000, ttl=CACHE_TTL_SECONDS)
)

# ACE SPECカードのIDの集合のキャッシュ。集合ひとつを丸ごと保持するのでmaxsizeは1。
acespec_ids_cache = ThreadSafeCache(
    cachetools.TTLCache(maxsize=1, ttl=CACHE_TTL_SECONDS)
)
