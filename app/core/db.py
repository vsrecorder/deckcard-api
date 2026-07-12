"""データベース接続とカード情報の照会"""

import logging
import os

from dotenv import load_dotenv
from psycopg_pool import ConnectionPool

from app.core.cache import pokemon_card_cache
from app.core.errors import DeckError

logger = logging.getLogger(__name__)

load_dotenv()

host = os.getenv("DB_HOSTNAME")
port = os.getenv("DB_PORT")
user = os.getenv("DB_USER_NAME")
password = os.getenv("DB_USER_PASSWORD")
dbname = os.getenv("DB_NAME")
dsn = "host={} port={} user={} password={} dbname={} sslmode=disable".format(
    host, port, user, password, dbname
)

pool = ConnectionPool(
    conninfo=dsn,
    min_size=5,
    max_size=10,
    timeout=5,
)


def fetch_pokemon_cards(card_ids):
    """pokemon_cardsテーブルから複数カードの特性とワザを一括取得する。

    N+1クエリを避けるため、``WHERE id = ANY(%s)`` で1回のクエリにまとめる。

    Args:
        card_ids: カードIDのイテラブル（str/intが混在していても可）。
    Returns:
        {card_id(int): (ability, attacks)} の辞書。
        abilityは特性文字列、attacksはワザ名のリスト。
    Raises:
        DeckError: いずれかのIDのレコードが見つからない場合（500）。
    """
    # 重複を排除しつつint化する
    ids = sorted({int(card_id) for card_id in card_ids})

    if not ids:
        return {}

    # まずキャッシュから引き、未ヒットのIDだけをDBへ問い合わせる
    result = {}
    missing_ids = []
    for card_id in ids:
        cached = pokemon_card_cache.get(card_id)
        if cached is not None:
            result[card_id] = cached
        else:
            missing_ids.append(card_id)

    if missing_ids:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                sql = "SELECT id, ability, attack FROM pokemon_cards WHERE id = ANY(%s)"
                cur.execute(sql, (missing_ids,))
                rows = cur.fetchall()

        for row in rows:
            value = (row[1], row[2].split("/"))
            result[row[0]] = value
            # 取得できたカードはキャッシュに格納する
            pokemon_card_cache[row[0]] = value

    # 取得できなかったIDがあれば従来と同じく500として扱う
    not_found = [card_id for card_id in ids if card_id not in result]
    if not_found:
        logger.exception(f"Record not found: pokemon_cards.id={not_found}")
        raise DeckError()

    return result


def fetch_pokemon_card(card_id):
    """pokemon_cardsテーブルから単一カードの特性とワザを取得する。

    一括取得版 :func:`fetch_pokemon_cards` の薄いラッパー。

    Returns:
        (ability, attacks): abilityは特性文字列、attacksはワザ名のリスト。
    Raises:
        DeckError: レコードが見つからない場合（500）。
    """
    return fetch_pokemon_cards([card_id])[int(card_id)]
