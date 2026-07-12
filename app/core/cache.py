"""レスポンスキャッシュ

サービス層でのキャッシュ格納と、ルート層でのキャッシュ参照の双方で共有する。
"""

import cachetools

deckcards_cache = cachetools.LRUCache(maxsize=2000)
acespec_cache = cachetools.LRUCache(maxsize=2000)

deck_list_cache = cachetools.LFUCache(maxsize=2000)
deck_summary_cache = cachetools.LFUCache(maxsize=2000)

# pokemon_cardsマスタ（card_id -> (ability, attacks)）のキャッシュ。
# ほぼ不変のマスタデータだが、更新反映のため24時間のTTLを設ける。
# 無期限にしたい場合は cachetools.LRUCache(maxsize=20000) に差し替える。
pokemon_card_cache = cachetools.TTLCache(maxsize=20000, ttl=60 * 60 * 24)
