"""デッキカード情報を生成するサービス層

各エンドポイントに対応するレスポンス整形を担う。HTTP取得・HTMLパース・DB照会は
それぞれ fetcher / parser / db モジュールへ委譲する。
"""

import logging

import psycopg
from bs4 import BeautifulSoup
from fastapi.responses import JSONResponse

from app.core.cache import (
    acespec_cache,
    deck_list_cache,
    deck_summary_cache,
    deckcards_cache,
)
from app.core.constants import acespecs, card_detail_url, card_image_url
from app.core.db import fetch_pokemon_cards
from app.core.errors import DeckError
from app.scraping.fetcher import fetch_deck_html
from app.scraping.parser import get_input_area, parse_card_counts, parse_card_dicts

logger = logging.getLogger(__name__)

# input要素のうち、カードとして扱わないid
_SKIP_INPUT_IDS = {"deck_ajs", "copyDeckID"}


def create_deckcards(deck_code):
    res = fetch_deck_html(deck_code)
    if isinstance(res, JSONResponse):
        return res

    try:
        bs = BeautifulSoup(res.text, "html.parser")
        card_name_dict, card_image_dict = parse_card_dicts(bs)
        bs_input_area = get_input_area(bs)

        card_count_dict = {}
        for item in bs_input_area.find_all("input"):
            if item["value"] and item["id"] != "copyDeckID":
                card_count_dict.update(parse_card_counts(item["value"]))

        deckcards = []
        total_card_count = 0

        for card_id, name in card_name_dict.items():
            deckcards.append(
                {
                    "id": int(card_id),
                    "name": str(name).replace("(ACE SPEC)", ""),
                    "detail_url": card_detail_url(card_id),
                    "image_url": card_image_url(card_image_dict[card_id]),
                    "count": card_count_dict[card_id],
                }
            )
            total_card_count += card_count_dict[card_id]

        if total_card_count != 60:
            logger.exception(
                f"Unexpected deck cards count: expected = 60, actual = {total_card_count}"
            )
            return JSONResponse(content={}, status_code=500)

        # 結果をキャッシュ
        deckcards_cache[deck_code] = deckcards
        logger.info(f"[deckcards] cache store deck_code={deck_code}")

        return deckcards

    except DeckError as e:
        return JSONResponse(content=e.content, status_code=e.status_code)
    except Exception:
        return JSONResponse(content={}, status_code=500)


def create_deckcards_detail(deck_code):
    res = fetch_deck_html(deck_code)
    if isinstance(res, JSONResponse):
        return res

    try:
        bs = BeautifulSoup(res.text, "html.parser")
        card_name_dict, card_image_dict = parse_card_dicts(bs)
        bs_input_area = get_input_area(bs)

        ret_dict = {}
        total_card_count = 0

        for item in bs_input_area.find_all("input"):
            if item["id"] in _SKIP_INPUT_IDS:
                continue

            deckcards = []
            card_count_dict = {}
            card_type_count = 0

            if item["value"] and item["id"] != "copyDeckID":
                card_count_dict.update(parse_card_counts(item["value"]))

            # ポケモンは特性・ワザをまとめて1回のクエリで取得する（N+1回避）
            pokemon_cards = (
                fetch_pokemon_cards(card_count_dict.keys())
                if item["id"] == "deck_pke"
                else {}
            )

            for card_id, count in card_count_dict.items():
                card_info = {
                    "id": int(card_id),
                    "name": str(card_name_dict[card_id]).replace("(ACE SPEC)", ""),
                    "detail_url": card_detail_url(card_id),
                    "image_url": card_image_url(card_image_dict[card_id]),
                    "count": count,
                }

                if item["id"] == "deck_pke":
                    ability, attacks = pokemon_cards[int(card_id)]
                    card_info["ability"] = ability
                    card_info["attacks"] = attacks

                deckcards.append(card_info)
                card_type_count += count

            ret_dict.update(
                {item["id"]: deckcards, item["id"] + "_count": card_type_count}
            )
            total_card_count += card_type_count

        if total_card_count != 60:
            logger.exception(
                f"Unexpected deck cards count: expected = 60, actual = {total_card_count}"
            )
            return JSONResponse(content={}, status_code=500)

        return ret_dict

    except DeckError as e:
        return JSONResponse(content=e.content, status_code=e.status_code)
    except Exception:
        return JSONResponse(content={}, status_code=500)


def create_v1beta_deckcards(deck_code):
    res = fetch_deck_html(deck_code)
    if isinstance(res, JSONResponse):
        return res

    try:
        bs = BeautifulSoup(res.text, "html.parser")
        card_name_dict, card_image_dict = parse_card_dicts(bs)
        bs_input_area = get_input_area(bs)

        ret_list = []
        total_card_count = 0

        for item in bs_input_area.find_all("input"):
            if item["id"] in _SKIP_INPUT_IDS:
                continue

            deckcards = []
            card_count_dict = {}
            card_type_count = 0

            if item["value"] and item["id"] != "copyDeckID":
                card_count_dict.update(parse_card_counts(item["value"]))

            # ポケモンは特性・ワザをまとめて1回のクエリで取得する（N+1回避）
            pokemon_cards = (
                fetch_pokemon_cards(card_count_dict.keys())
                if item["id"] == "deck_pke"
                else {}
            )

            for card_id, count in card_count_dict.items():
                card_info = {
                    "card_id": int(card_id),
                    "card_name": str(card_name_dict[card_id]).replace("(ACE SPEC)", ""),
                    "card_count": count,
                    "detail_url": card_detail_url(card_id),
                    "image_url": card_image_url(card_image_dict[card_id]),
                }

                if item["id"] == "deck_pke":
                    ability, attacks = pokemon_cards[int(card_id)]
                    card_info["ability"] = ability
                    card_info["attacks"] = attacks

                deckcards.append(card_info)
                card_type_count += count

            ret_list.extend(deckcards)
            total_card_count += card_type_count

        if total_card_count != 60:
            logger.exception(
                f"Unexpected deck cards count: expected = 60, actual = {total_card_count}"
            )
            return JSONResponse(content=[], status_code=500)

        return ret_list

    except DeckError as e:
        return JSONResponse(content=e.content, status_code=e.status_code)
    except Exception:
        return JSONResponse(content=[], status_code=500)


def create_v1beta_deckcards_detail(deck_code):
    res = fetch_deck_html(deck_code)
    if isinstance(res, JSONResponse):
        return res

    try:
        bs = BeautifulSoup(res.text, "html.parser")
        card_name_dict, card_image_dict = parse_card_dicts(bs)
        bs_input_area = get_input_area(bs)

        ret_dict = {}
        total_card_count = 0

        for item in bs_input_area.find_all("input"):
            if item["id"] in _SKIP_INPUT_IDS:
                continue

            deckcards = []
            card_count_dict = {}
            card_type_count = 0

            if item["value"] and item["id"] != "copyDeckID":
                card_count_dict.update(parse_card_counts(item["value"]))

            # ポケモンは特性・ワザをまとめて1回のクエリで取得する（N+1回避）
            pokemon_cards = (
                fetch_pokemon_cards(card_count_dict.keys())
                if item["id"] == "deck_pke"
                else {}
            )

            for card_id, count in card_count_dict.items():
                card_info = {
                    "card_id": int(card_id),
                    "card_name": str(card_name_dict[card_id]).replace("(ACE SPEC)", ""),
                    "card_count": count,
                    "detail_url": card_detail_url(card_id),
                    "image_url": card_image_url(card_image_dict[card_id]),
                }

                if item["id"] == "deck_pke":
                    ability, attacks = pokemon_cards[int(card_id)]
                    card_info["ability"] = ability
                    card_info["attacks"] = attacks

                deckcards.append(card_info)
                card_type_count += count

            key = str(item["id"]).replace("deck", "card")
            ret_dict.update({key: deckcards, key + "_count": card_type_count})
            total_card_count += card_type_count

        for card_id, card_name in card_name_dict.items():
            if card_name in acespecs:
                card_name = card_name.replace("(ACE SPEC)", "")
                ret_dict.update(
                    {
                        "card_acespec": {
                            "card_id": int(card_id),
                            "card_name": str(card_name),
                        }
                    }
                )
                break

        if total_card_count != 60:
            logger.exception(
                f"Unexpected deck cards count: expected = 60, actual = {total_card_count}"
            )
            return JSONResponse(content={}, status_code=500)

        return ret_dict

    except DeckError as e:
        return JSONResponse(content=e.content, status_code=e.status_code)
    except Exception:
        return JSONResponse(content={}, status_code=500)


def create_v1beta_deckcards_list(deck_code):
    res = fetch_deck_html(deck_code)
    if isinstance(res, JSONResponse):
        return res

    try:
        bs = BeautifulSoup(res.text, "html.parser")
        card_name_dict, card_image_dict = parse_card_dicts(bs)
        bs_input_area = get_input_area(bs)

        ret_list = []
        total_card_count = 0

        for item in bs_input_area.find_all("input"):
            if item["id"] in _SKIP_INPUT_IDS:
                continue

            deckcards = []
            card_count_dict = {}
            card_type_count = 0

            if item["value"] and item["id"] != "copyDeckID":
                card_count_dict.update(parse_card_counts(item["value"]))

            # ポケモンは特性・ワザをまとめて1回のクエリで取得する（N+1回避）
            pokemon_cards = {}
            if item["id"] == "deck_pke":
                try:
                    pokemon_cards = fetch_pokemon_cards(card_count_dict.keys())
                except DeckError as e:
                    return JSONResponse(content=e.content, status_code=e.status_code)
                except psycopg.Error as e:
                    logger.exception("PostgreSQL error occurred.")
                    logger.error("=== PostgreSQL Error ===")
                    logger.error(f"Message: {e}")
                    logger.error(f"SQLSTATE: {e.sqlstate}")
                    logger.error(f"Diag message: {e.diag.message_primary}")
                    logger.error(f"Detail: {e.diag.message_detail}")
                    logger.error(f"Hint: {e.diag.message_hint}")
                    logger.error("========================", exc_info=True)
                    return JSONResponse(content={}, status_code=500)
                except Exception:
                    logger.exception("Unexpected error while fetching pokemon cards.")
                    return JSONResponse(content={}, status_code=500)

            for card_id, count in card_count_dict.items():
                if item["id"] == "deck_pke":
                    ability, attacks = pokemon_cards[int(card_id)]

                    for _ in range(count):
                        deckcards.append(
                            {
                                "card_id": int(card_id),
                                "card_name": str(card_name_dict[card_id]).replace(
                                    "(ACE SPEC)", ""
                                ),
                                "detail_url": card_detail_url(card_id),
                                "image_url": card_image_url(card_image_dict[card_id]),
                                "ability": ability,
                                "attacks": attacks,
                            }
                        )
                        card_type_count += 1
                else:
                    for _ in range(count):
                        deckcards.append(
                            {
                                "card_id": int(card_id),
                                "card_name": str(card_name_dict[card_id]).replace(
                                    "(ACE SPEC)", ""
                                ),
                                "detail_url": card_detail_url(card_id),
                                "image_url": card_image_url(card_image_dict[card_id]),
                            }
                        )
                        card_type_count += 1

            ret_list.extend(deckcards)
            total_card_count += card_type_count

        if total_card_count != 60:
            logger.exception(
                f"Unexpected deck cards count: expected = 60, actual = {total_card_count}"
            )
            return JSONResponse(content=[], status_code=500)

        # 結果をキャッシュ
        deck_list_cache[deck_code] = ret_list
        logger.info(f"[deckcards/list] cache store deck_code={deck_code}")

        return ret_list

    except DeckError as e:
        return JSONResponse(content=e.content, status_code=e.status_code)
    except Exception:
        return JSONResponse(content=[], status_code=500)


def create_v1beta_deckcards_summary(deck_code):
    res = fetch_deck_html(deck_code)
    if isinstance(res, JSONResponse):
        return res

    try:
        bs = BeautifulSoup(res.text, "html.parser")
        card_name_dict, card_image_dict = parse_card_dicts(bs)
        bs_input_area = get_input_area(bs)

        ret_dict = {}
        total_card_count = 0

        for item in bs_input_area.find_all("input"):
            if item["id"] in _SKIP_INPUT_IDS:
                continue

            deckcards = []
            card_count_dict = {}
            card_type_count = 0

            if item["value"] and item["id"] != "copyDeckID":
                card_count_dict.update(parse_card_counts(item["value"]))

            # ポケモンは特性・ワザをまとめて1回のクエリで取得する（N+1回避）
            pokemon_cards = (
                fetch_pokemon_cards(card_count_dict.keys())
                if item["id"] == "deck_pke"
                else {}
            )

            for card_id, count in card_count_dict.items():
                card_info = {
                    "card_id": int(card_id),
                    "card_name": str(card_name_dict[card_id]).replace("(ACE SPEC)", ""),
                    "card_count": count,
                    "detail_url": card_detail_url(card_id),
                    "image_url": card_image_url(card_image_dict[card_id]),
                }

                if item["id"] == "deck_pke":
                    ability, attacks = pokemon_cards[int(card_id)]
                    card_info["ability"] = ability
                    card_info["attacks"] = attacks

                deckcards.append(card_info)
                card_type_count += count

            # 同一カードを集約する。ポケモンは特性・ワザ（順不同）まで一致した場合のみ集約する
            aggregated = {}
            for card in deckcards:
                if item["id"] == "deck_pke":
                    key = (
                        card.get("card_name"),
                        card.get("ability", ""),
                        tuple(sorted(card.get("attacks", []))),
                    )
                else:
                    key = card["card_name"]

                if key not in aggregated:
                    aggregated[key] = card.copy()
                else:
                    aggregated[key]["card_count"] += card["card_count"]

            key = str(item["id"]).replace("deck", "card")
            ret_dict.update(
                {key: list(aggregated.values()), key + "_count": card_type_count}
            )
            total_card_count += card_type_count

        if total_card_count != 60:
            logger.exception(
                f"Unexpected deck cards count: expected = 60, actual = {total_card_count}"
            )
            return JSONResponse(content={}, status_code=500)

        # 結果をキャッシュ
        deck_summary_cache[deck_code] = ret_dict
        logger.info(f"[deckcards/summary] cache store deck_code={deck_code}")

        return ret_dict

    except DeckError as e:
        return JSONResponse(content=e.content, status_code=e.status_code)
    except Exception:
        return JSONResponse(content={}, status_code=500)


def find_acespec(deck_code):
    try:
        deckcards = create_deckcards(deck_code)

        if isinstance(deckcards, JSONResponse):
            return deckcards

        for card in deckcards:
            if card["name"] in acespecs:
                card["name"] = card["name"].replace("(ACE SPEC)", "")
                del card["count"]
                return card

        return JSONResponse(content={}, status_code=204)
    except Exception:
        return JSONResponse(content={}, status_code=500)


def create_v1beta_acespec(deck_code):
    try:
        deckcards = create_v1beta_deckcards(deck_code)

        if isinstance(deckcards, JSONResponse):
            return deckcards

        for card in deckcards:
            if card["card_name"] in acespecs:
                card["card_name"] = card["card_name"].replace("(ACE SPEC)", "")
                del card["card_count"]

                # 結果をキャッシュ
                acespec_cache[deck_code] = card
                logger.info(f"[acespec] cache store deck_code={deck_code}")

                return card

        return JSONResponse(content={}, status_code=204)
    except Exception:
        return JSONResponse(content={}, status_code=500)
