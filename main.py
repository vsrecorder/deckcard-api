import os

import re
import requests
import logging
from collections import OrderedDict

import psycopg
from psycopg_pool import ConnectionPool

from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from bs4 import BeautifulSoup

import cachetools

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

acespecs = [
    "ポケモン回収サイクロン",
    "ポケモン回収サイクロン(ACE SPEC)",
    "スクランブルスイッチ",
    "スクランブルスイッチ(ACE SPEC)",
    "マスターボール",
    "マスターボール(ACE SPEC)",
    "ヒーローマント",
    "ヒーローマント(ACE SPEC)",
    "リブートポッド",
    "リブートポッド(ACE SPEC)",
    "プライムキャッチャー",
    "プライムキャッチャー(ACE SPEC)",
    "ネオアッパーエネルギー",
    "ネオアッパーエネルギー(ACE SPEC)",
    "マキシマムベルト",
    "マキシマムベルト(ACE SPEC)",
    "覚醒のドラム",
    "覚醒のドラム(ACE SPEC)",
    "サバイブギプス",
    "サバイブギプス(ACE SPEC)",
    "ハイパーアロマ",
    "ハイパーアロマ(ACE SPEC)",
    "アンフェアスタンプ",
    "アンフェアスタンプ(ACE SPEC)",
    "レガシーエネルギー",
    "レガシーエネルギー(ACE SPEC)",
    "シークレットボックス",
    "シークレットボックス(ACE SPEC)",
    "ニュートラルセンター",
    "ニュートラルセンター(ACE SPEC)",
    "ポケバイタルA",
    "ポケバイタルA(ACE SPEC)",
    "デンジャラス光線",
    "デンジャラス光線(ACE SPEC)",
    "偉大な大樹",
    "偉大な大樹(ACE SPEC)",
    "デラックスボム",
    "デラックスボム(ACE SPEC)",
    "きらめく結晶",
    "きらめく結晶(ACE SPEC)",
    "パーフェクトミキサー",
    "パーフェクトミキサー(ACE SPEC)",
    "プレシャスキャリー",
    "プレシャスキャリー(ACE SPEC)",
    "リッチエネルギー",
    "リッチエネルギー(ACE SPEC)",
    "メガトンブロアー",
    "メガトンブロアー(ACE SPEC)",
    "エネルギー転送PRO",
    "エネルギー転送PRO(ACE SPEC)",
    "希望のアミュレット",
    "希望のアミュレット(ACE SPEC)",
    "ミラクルインカム",
    "ミラクルインカム(ACE SPEC)",
    "トレジャーガジェット",
    "トレジャーガジェット(ACE SPEC)",
    "つりざおMAX",
    "つりざおMAX(ACE SPEC)",
]

url = "https://xx8nnpgt.user.webaccel.jp/deck-result_html/"


def create_deckcards(deck_code):
    try:
        logger.info(f"Request start: {url + deck_code}")

        res = requests.get(url + deck_code, timeout=3)

        if res.status_code == 404:
            logger.info(f"Request failed: {url + deck_code} (status={res.status_code})")

            fallback_url = "https://www.pokemon-card.com/deck/result.html/deckID/"

            try:
                logger.warning(f"Not Found (404): {url + deck_code}")

                logger.info(f"Request start: {fallback_url + deck_code}")

                res = requests.get(fallback_url + deck_code, timeout=3)

                res.raise_for_status()

                logger.info(
                    f"Request succeeded: {fallback_url + deck_code} (status={res.status_code})"
                )

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout occurred: {fallback_url + deck_code}")
                return JSONResponse(content={}, status_code=504)

            except requests.exceptions.HTTPError as e:
                status = getattr(e.response, "status_code", 500)
                logger.error(
                    f"HTTPError: {fallback_url + deck_code} -> status {status}"
                )
                return JSONResponse(content={}, status_code=status)

            except requests.exceptions.ConnectionError as e:
                logger.error(f"ConnectionError: {fallback_url + deck_code} -> {e}")
                return JSONResponse(content={}, status_code=500)

            except requests.exceptions.RequestException as e:
                logger.exception(
                    f"Unexpected RequestException: {fallback_url + deck_code} -> {e}"
                )
                return JSONResponse(content={}, status_code=500)

        else:
            res.raise_for_status()

            logger.info(
                f"Request succeeded: {url + deck_code} (status={res.status_code})"
            )

    except requests.exceptions.Timeout:
        logger.warning(f"Timeout occurred: {url + deck_code}")
        return JSONResponse(content={}, status_code=504)

    except requests.exceptions.HTTPError as e:
        status = getattr(e.response, "status_code", 500)
        logger.error(f"HTTPError: {url + deck_code} -> status {status}")
        return JSONResponse(content={}, status_code=status)

    except requests.exceptions.ConnectionError as e:
        logger.error(f"ConnectionError: {url + deck_code} -> {e}")
        return JSONResponse(content={}, status_code=500)

    except requests.exceptions.RequestException as e:
        logger.exception(f"Unexpected RequestException: {url + deck_code} -> {e}")
        return JSONResponse(content={}, status_code=500)

    try:
        bs = BeautifulSoup(res.text, "html.parser")

        deckcards = []
        card_name_dict = {}
        card_image_dict = {}
        card_count_dict = {}

        if len(bs.find_all("script", attrs={"type": "", "src": ""})) != 2:
            count = len(bs.find_all("script", attrs={"type": "", "src": ""}))
            logger.exception(
                f"Unexpected <script> tag count: expected = 2, actual = {count}"
            )
            return JSONResponse(content={}, status_code=500)

        text = bs.find_all("script", attrs={"type": "", "src": ""})[-1]

        for item in str(text).strip().split(";"):
            line = item.strip()

            if not line:
                continue

            if "searchItemNameAlt" in line:
                match = re.search(r"\[(\d+)\]='([^']+)'", line)
                if match:
                    number = match.group(1)
                    name = match.group(2)
                    card_name_dict.update({number: name})

            if "searchItemCardPict" in line:
                match = re.search(r"\[(\d+)\]='([^']+)'", line)
                if match:
                    number = match.group(1)
                    name = match.group(2)
                    card_image_dict.update({number: name})

        if len(bs.find_all(id="inputArea")) != 1:
            count = len(bs.find_all(id="inputArea"))
            logger.exception(
                f"Unexpected 'inputArea' id count: expected = 1, actual = {count}"
            )
            return JSONResponse(content={}, status_code=500)

        bs_input_area = BeautifulSoup(
            str(bs.find_all(id="inputArea")[0]), "html.parser"
        )

        for item in bs_input_area.find_all("input"):
            if item["value"] and item["id"] != "copyDeckID":
                result = {
                    k: int(v)
                    for k, v in (
                        val.rsplit("_", 1)[0].split("_")
                        for val in item["value"].split("-")
                    )
                }
                card_count_dict.update(result)

        total_card_count = 0

        for card_id, name in card_name_dict.items():
            card_info = {
                "id": int(card_id),
                "name": str(name).replace("(ACE SPEC)", ""),
                "detail_url": str(
                    "https://www.pokemon-card.com/card-search/details.php/card/"
                    + str(card_id)
                ),
                "image_url": str(
                    "https://www.pokemon-card.com" + str(card_image_dict[card_id])
                ),
                "count": card_count_dict[card_id],
            }
            deckcards.append(card_info)
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

    except Exception:
        return JSONResponse(content={}, status_code=500)


def create_deckcards_detail(deck_code):
    try:
        logger.info(f"Request start: {url + deck_code}")

        res = requests.get(url + deck_code, timeout=3)

        if res.status_code == 404:
            logger.info(f"Request failed: {url + deck_code} (status={res.status_code})")

            fallback_url = "https://www.pokemon-card.com/deck/result.html/deckID/"

            try:
                logger.warning(f"Not Found (404): {url + deck_code}")

                logger.info(f"Request start: {fallback_url + deck_code}")

                res = requests.get(fallback_url + deck_code, timeout=3)

                res.raise_for_status()

                logger.info(
                    f"Request succeeded: {fallback_url + deck_code} (status={res.status_code})"
                )

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout occurred: {fallback_url + deck_code}")
                return JSONResponse(content={}, status_code=504)

            except requests.exceptions.HTTPError as e:
                status = getattr(e.response, "status_code", 500)
                logger.error(
                    f"HTTPError: {fallback_url + deck_code} -> status {status}"
                )
                return JSONResponse(content={}, status_code=status)

            except requests.exceptions.ConnectionError as e:
                logger.error(f"ConnectionError: {fallback_url + deck_code} -> {e}")
                return JSONResponse(content={}, status_code=500)

            except requests.exceptions.RequestException as e:
                logger.exception(
                    f"Unexpected RequestException: {fallback_url + deck_code} -> {e}"
                )
                return JSONResponse(content={}, status_code=500)

        else:
            res.raise_for_status()

            logger.info(
                f"Request succeeded: {url + deck_code} (status={res.status_code})"
            )

    except requests.exceptions.Timeout:
        logger.warning(f"Timeout occurred: {url + deck_code}")
        return JSONResponse(content={}, status_code=504)

    except requests.exceptions.HTTPError as e:
        status = getattr(e.response, "status_code", 500)
        logger.error(f"HTTPError: {url + deck_code} -> status {status}")
        return JSONResponse(content={}, status_code=status)

    except requests.exceptions.ConnectionError as e:
        logger.error(f"ConnectionError: {url + deck_code} -> {e}")
        return JSONResponse(content={}, status_code=500)

    except requests.exceptions.RequestException as e:
        logger.exception(f"Unexpected RequestException: {url + deck_code} -> {e}")
        return JSONResponse(content={}, status_code=500)

    try:
        bs = BeautifulSoup(res.text, "html.parser")

        card_name_dict = {}
        card_image_dict = {}

        if len(bs.find_all("script", attrs={"type": "", "src": ""})) != 2:
            count = len(bs.find_all("script", attrs={"type": "", "src": ""}))
            logger.exception(
                f"Unexpected <script> tag count: expected = 2, actual = {count}"
            )
            return JSONResponse(content={}, status_code=500)

        text = bs.find_all("script", attrs={"type": "", "src": ""})[-1]

        for item in str(text).strip().split(";"):
            line = item.strip()

            if not line:
                continue

            if "searchItemNameAlt" in line:
                match = re.search(r"\[(\d+)\]='([^']+)'", line)
                if match:
                    number = match.group(1)
                    name = match.group(2)
                    card_name_dict.update({number: name})

            if "searchItemCardPict" in line:
                match = re.search(r"\[(\d+)\]='([^']+)'", line)
                if match:
                    number = match.group(1)
                    name = match.group(2)
                    card_image_dict.update({number: name})

        if len(bs.find_all(id="inputArea")) != 1:
            count = len(bs.find_all(id="inputArea"))
            logger.exception(
                f"Unexpected 'inputArea' id count: expected = 1, actual = {count}"
            )
            return JSONResponse(content={}, status_code=500)

        bs_input_area = BeautifulSoup(
            str(bs.find_all(id="inputArea")[0]), "html.parser"
        )

        ret_dict = {}
        total_card_count = 0

        for item in bs_input_area.find_all("input"):
            if item["id"] == "deck_ajs" or item["id"] == "copyDeckID":
                continue

            deckcards = []
            card_count_dict = {}
            card_type_count = 0

            if item["value"] and item["id"] != "copyDeckID":
                result = {
                    k: int(v)
                    for k, v in (
                        val.rsplit("_", 1)[0].split("_")
                        for val in item["value"].split("-")
                    )
                }
                card_count_dict.update(result)

            for card_id, count in card_count_dict.items():
                if item["id"] == "deck_pke":
                    with pool.connection() as conn:
                        with conn.cursor() as cur:
                            ability = ""
                            attacks = []

                            sql = "SELECT ability, attack FROM pokemon_cards WHERE id = %s"
                            cur.execute(sql, (card_id,))
                            row = cur.fetchone()

                            if row is None:
                                logger.exception(
                                    f"Record not found: pokemon_cards.id={card_id}"
                                )
                                return JSONResponse(content={}, status_code=500)

                            ability = row[0]
                            attacks = row[1].split("/")

                    card_info = {
                        "id": int(card_id),
                        "name": str(card_name_dict[card_id]).replace("(ACE SPEC)", ""),
                        "detail_url": str(
                            "https://www.pokemon-card.com/card-search/details.php/card/"
                            + str(card_id)
                        ),
                        "image_url": str(
                            "https://www.pokemon-card.com"
                            + str(card_image_dict[card_id])
                        ),
                        "count": count,
                        "ability": ability,
                        "attacks": attacks,
                    }

                    deckcards.append(card_info)
                    card_type_count += count
                else:
                    card_info = {
                        "id": int(card_id),
                        "name": str(card_name_dict[card_id]).replace("(ACE SPEC)", ""),
                        "detail_url": str(
                            "https://www.pokemon-card.com/card-search/details.php/card/"
                            + str(card_id)
                        ),
                        "image_url": str(
                            "https://www.pokemon-card.com"
                            + str(card_image_dict[card_id])
                        ),
                        "count": count,
                    }

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

    except Exception:
        return JSONResponse(content={}, status_code=500)


def create_v1beta_deckcards(deck_code):
    try:
        logger.info(f"Request start: {url + deck_code}")

        res = requests.get(url + deck_code, timeout=3)

        if res.status_code == 404:
            logger.info(f"Request failed: {url + deck_code} (status={res.status_code})")

            fallback_url = "https://www.pokemon-card.com/deck/result.html/deckID/"

            try:
                logger.warning(f"Not Found (404): {url + deck_code}")

                logger.info(f"Request start: {fallback_url + deck_code}")

                res = requests.get(fallback_url + deck_code, timeout=3)

                res.raise_for_status()

                logger.info(
                    f"Request succeeded: {fallback_url + deck_code} (status={res.status_code})"
                )

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout occurred: {fallback_url + deck_code}")
                return JSONResponse(content={}, status_code=504)

            except requests.exceptions.HTTPError as e:
                status = getattr(e.response, "status_code", 500)
                logger.error(
                    f"HTTPError: {fallback_url + deck_code} -> status {status}"
                )
                return JSONResponse(content={}, status_code=status)

            except requests.exceptions.ConnectionError as e:
                logger.error(f"ConnectionError: {fallback_url + deck_code} -> {e}")
                return JSONResponse(content={}, status_code=500)

            except requests.exceptions.RequestException as e:
                logger.exception(
                    f"Unexpected RequestException: {fallback_url + deck_code} -> {e}"
                )
                return JSONResponse(content={}, status_code=500)

        else:
            res.raise_for_status()

            logger.info(
                f"Request succeeded: {url + deck_code} (status={res.status_code})"
            )

    except requests.exceptions.Timeout:
        logger.warning(f"Timeout occurred: {url + deck_code}")
        return JSONResponse(content={}, status_code=504)

    except requests.exceptions.HTTPError as e:
        status = getattr(e.response, "status_code", 500)
        logger.error(f"HTTPError: {url + deck_code} -> status {status}")
        return JSONResponse(content={}, status_code=status)

    except requests.exceptions.ConnectionError as e:
        logger.error(f"ConnectionError: {url + deck_code} -> {e}")
        return JSONResponse(content={}, status_code=500)

    except requests.exceptions.RequestException as e:
        logger.exception(f"Unexpected RequestException: {url + deck_code} -> {e}")
        return JSONResponse(content={}, status_code=500)

    try:
        bs = BeautifulSoup(res.text, "html.parser")

        card_name_dict = {}
        card_image_dict = {}

        if len(bs.find_all("script", attrs={"type": "", "src": ""})) != 2:
            count = len(bs.find_all("script", attrs={"type": "", "src": ""}))
            logger.exception(
                f"Unexpected <script> tag count: expected = 2, actual = {count}"
            )
            return JSONResponse(content={}, status_code=500)

        text = bs.find_all("script", attrs={"type": "", "src": ""})[-1]

        for item in str(text).strip().split(";"):
            line = item.strip()

            if not line:
                continue

            if "searchItemNameAlt" in line:
                match = re.search(r"\[(\d+)\]='([^']+)'", line)
                if match:
                    number = match.group(1)
                    name = match.group(2)
                    card_name_dict.update({number: name})

            if "searchItemCardPict" in line:
                match = re.search(r"\[(\d+)\]='([^']+)'", line)
                if match:
                    number = match.group(1)
                    name = match.group(2)
                    card_image_dict.update({number: name})

        if len(bs.find_all(id="inputArea")) != 1:
            count = len(bs.find_all(id="inputArea"))
            logger.exception(
                f"Unexpected 'inputArea' id count: expected = 1, actual = {count}"
            )
            return JSONResponse(content={}, status_code=500)

        bs_input_area = BeautifulSoup(
            str(bs.find_all(id="inputArea")[0]), "html.parser"
        )

        ret_list = []
        total_card_count = 0

        for item in bs_input_area.find_all("input"):
            if item["id"] == "deck_ajs" or item["id"] == "copyDeckID":
                continue

            deckcards = []
            card_count_dict = {}
            card_type_count = 0

            if item["value"] and item["id"] != "copyDeckID":
                result = {
                    k: int(v)
                    for k, v in (
                        val.rsplit("_", 1)[0].split("_")
                        for val in item["value"].split("-")
                    )
                }
                card_count_dict.update(result)

            for card_id, count in card_count_dict.items():
                if item["id"] == "deck_pke":
                    with pool.connection() as conn:
                        with conn.cursor() as cur:
                            ability = ""
                            attacks = []

                            sql = "SELECT ability, attack FROM pokemon_cards WHERE id = %s"
                            cur.execute(sql, (card_id,))
                            row = cur.fetchone()

                            if row is None:
                                logger.exception(
                                    f"Record not found: pokemon_cards.id={card_id}"
                                )
                                return JSONResponse(content={}, status_code=500)

                            ability = row[0]
                            attacks = row[1].split("/")

                    card_info = {
                        "card_id": int(card_id),
                        "card_name": str(card_name_dict[card_id]).replace(
                            "(ACE SPEC)", ""
                        ),
                        "card_count": count,
                        "detail_url": str(
                            "https://www.pokemon-card.com/card-search/details.php/card/"
                            + str(card_id)
                        ),
                        "image_url": str(
                            "https://www.pokemon-card.com"
                            + str(card_image_dict[card_id])
                        ),
                        "ability": ability,
                        "attacks": attacks,
                    }

                    deckcards.append(card_info)
                    card_type_count += count
                else:
                    card_info = {
                        "card_id": int(card_id),
                        "card_name": str(card_name_dict[card_id]).replace(
                            "(ACE SPEC)", ""
                        ),
                        "card_count": count,
                        "detail_url": str(
                            "https://www.pokemon-card.com/card-search/details.php/card/"
                            + str(card_id)
                        ),
                        "image_url": str(
                            "https://www.pokemon-card.com"
                            + str(card_image_dict[card_id])
                        ),
                    }

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

    except Exception:
        return JSONResponse(content=[], status_code=500)


def create_v1beta_deckcards_detail(deck_code):
    try:
        logger.info(f"Request start: {url + deck_code}")

        res = requests.get(url + deck_code, timeout=3)

        if res.status_code == 404:
            logger.info(f"Request failed: {url + deck_code} (status={res.status_code})")

            fallback_url = "https://www.pokemon-card.com/deck/result.html/deckID/"

            try:
                logger.warning(f"Not Found (404): {url + deck_code}")

                logger.info(f"Request start: {fallback_url + deck_code}")

                res = requests.get(fallback_url + deck_code, timeout=3)

                res.raise_for_status()

                logger.info(
                    f"Request succeeded: {fallback_url + deck_code} (status={res.status_code})"
                )

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout occurred: {fallback_url + deck_code}")
                return JSONResponse(content={}, status_code=504)

            except requests.exceptions.HTTPError as e:
                status = getattr(e.response, "status_code", 500)
                logger.error(
                    f"HTTPError: {fallback_url + deck_code} -> status {status}"
                )
                return JSONResponse(content={}, status_code=status)

            except requests.exceptions.ConnectionError as e:
                logger.error(f"ConnectionError: {fallback_url + deck_code} -> {e}")
                return JSONResponse(content={}, status_code=500)

            except requests.exceptions.RequestException as e:
                logger.exception(
                    f"Unexpected RequestException: {fallback_url + deck_code} -> {e}"
                )
                return JSONResponse(content={}, status_code=500)

        else:
            res.raise_for_status()

            logger.info(
                f"Request succeeded: {url + deck_code} (status={res.status_code})"
            )

    except requests.exceptions.Timeout:
        logger.warning(f"Timeout occurred: {url + deck_code}")
        return JSONResponse(content={}, status_code=504)

    except requests.exceptions.HTTPError as e:
        status = getattr(e.response, "status_code", 500)
        logger.error(f"HTTPError: {url + deck_code} -> status {status}")
        return JSONResponse(content={}, status_code=status)

    except requests.exceptions.ConnectionError as e:
        logger.error(f"ConnectionError: {url + deck_code} -> {e}")
        return JSONResponse(content={}, status_code=500)

    except requests.exceptions.RequestException as e:
        logger.exception(f"Unexpected RequestException: {url + deck_code} -> {e}")
        return JSONResponse(content={}, status_code=500)

    try:
        bs = BeautifulSoup(res.text, "html.parser")

        card_name_dict = {}
        card_image_dict = {}

        if len(bs.find_all("script", attrs={"type": "", "src": ""})) != 2:
            count = len(bs.find_all("script", attrs={"type": "", "src": ""}))
            logger.exception(
                f"Unexpected <script> tag count: expected = 2, actual = {count}"
            )
            return JSONResponse(content={}, status_code=500)

        text = bs.find_all("script", attrs={"type": "", "src": ""})[-1]

        for item in str(text).strip().split(";"):
            line = item.strip()

            if not line:
                continue

            if "searchItemNameAlt" in line:
                match = re.search(r"\[(\d+)\]='([^']+)'", line)
                if match:
                    number = match.group(1)
                    name = match.group(2)
                    card_name_dict.update({number: name})

            if "searchItemCardPict" in line:
                match = re.search(r"\[(\d+)\]='([^']+)'", line)
                if match:
                    number = match.group(1)
                    name = match.group(2)
                    card_image_dict.update({number: name})

        if len(bs.find_all(id="inputArea")) != 1:
            count = len(bs.find_all(id="inputArea"))
            logger.exception(
                f"Unexpected 'inputArea' id count: expected = 1, actual = {count}"
            )
            return JSONResponse(content={}, status_code=500)

        bs_input_area = BeautifulSoup(
            str(bs.find_all(id="inputArea")[0]), "html.parser"
        )

        ret_dict = {}
        total_card_count = 0

        for item in bs_input_area.find_all("input"):
            if item["id"] == "deck_ajs" or item["id"] == "copyDeckID":
                continue

            deckcards = []
            card_count_dict = {}
            card_type_count = 0

            if item["value"] and item["id"] != "copyDeckID":
                result = {
                    k: int(v)
                    for k, v in (
                        val.rsplit("_", 1)[0].split("_")
                        for val in item["value"].split("-")
                    )
                }
                card_count_dict.update(result)

            for card_id, count in card_count_dict.items():
                if item["id"] == "deck_pke":
                    with pool.connection() as conn:
                        with conn.cursor() as cur:
                            ability = ""
                            attacks = []

                            sql = "SELECT ability, attack FROM pokemon_cards WHERE id = %s"
                            cur.execute(sql, (card_id,))
                            row = cur.fetchone()

                            if row is None:
                                logger.exception(
                                    f"Record not found: pokemon_cards.id={card_id}"
                                )
                                return JSONResponse(content={}, status_code=500)

                            ability = row[0]
                            attacks = row[1].split("/")

                    card_info = {
                        "card_id": int(card_id),
                        "card_name": str(card_name_dict[card_id]).replace(
                            "(ACE SPEC)", ""
                        ),
                        "card_count": count,
                        "detail_url": str(
                            "https://www.pokemon-card.com/card-search/details.php/card/"
                            + str(card_id)
                        ),
                        "image_url": str(
                            "https://www.pokemon-card.com"
                            + str(card_image_dict[card_id])
                        ),
                        "ability": ability,
                        "attacks": attacks,
                    }

                    deckcards.append(card_info)
                    card_type_count += count
                else:
                    card_info = {
                        "card_id": int(card_id),
                        "card_name": str(card_name_dict[card_id]).replace(
                            "(ACE SPEC)", ""
                        ),
                        "card_count": count,
                        "detail_url": str(
                            "https://www.pokemon-card.com/card-search/details.php/card/"
                            + str(card_id)
                        ),
                        "image_url": str(
                            "https://www.pokemon-card.com"
                            + str(card_image_dict[card_id])
                        ),
                    }

                    deckcards.append(card_info)
                    card_type_count += count

            ret_dict.update(
                {
                    str(item["id"]).replace("deck", "card"): deckcards,
                    str(item["id"]).replace("deck", "card") + "_count": card_type_count,
                }
            )
            total_card_count += card_type_count

        for card_id, card_name in card_name_dict.items():
            if card_name in acespecs:
                card_name = card_name.replace("(ACE SPEC)", "")
                card_info = {
                    "card_id": int(card_id),
                    "card_name": str(card_name),
                }

                ret_dict.update({"card_acespec": card_info})
                break

        if total_card_count != 60:
            logger.exception(
                f"Unexpected deck cards count: expected = 60, actual = {total_card_count}"
            )
            return JSONResponse(content={}, status_code=500)

        return ret_dict

    except Exception:
        return JSONResponse(content={}, status_code=500)


def create_v1beta_deckcards_list(deck_code):
    try:
        logger.info(f"Request start: {url + deck_code}")

        res = requests.get(url + deck_code, timeout=3)

        if res.status_code == 404:
            logger.info(f"Request failed: {url + deck_code} (status={res.status_code})")

            fallback_url = "https://www.pokemon-card.com/deck/result.html/deckID/"

            try:
                logger.warning(f"Not Found (404): {url + deck_code}")

                logger.info(f"Request start: {fallback_url + deck_code}")

                res = requests.get(fallback_url + deck_code, timeout=3)

                res.raise_for_status()

                logger.info(
                    f"Request succeeded: {fallback_url + deck_code} (status={res.status_code})"
                )

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout occurred: {fallback_url + deck_code}")
                return JSONResponse(content={}, status_code=504)

            except requests.exceptions.HTTPError as e:
                status = getattr(e.response, "status_code", 500)
                logger.error(
                    f"HTTPError: {fallback_url + deck_code} -> status {status}"
                )
                return JSONResponse(content={}, status_code=status)

            except requests.exceptions.ConnectionError as e:
                logger.error(f"ConnectionError: {fallback_url + deck_code} -> {e}")
                return JSONResponse(content={}, status_code=500)

            except requests.exceptions.RequestException as e:
                logger.exception(
                    f"Unexpected RequestException: {fallback_url + deck_code} -> {e}"
                )
                return JSONResponse(content={}, status_code=500)

        else:
            res.raise_for_status()

            logger.info(
                f"Request succeeded: {url + deck_code} (status={res.status_code})"
            )

    except requests.exceptions.Timeout:
        logger.warning(f"Timeout occurred: {url + deck_code}")
        return JSONResponse(content={}, status_code=504)

    except requests.exceptions.HTTPError as e:
        status = getattr(e.response, "status_code", 500)
        logger.error(f"HTTPError: {url + deck_code} -> status {status}")
        return JSONResponse(content={}, status_code=status)

    except requests.exceptions.ConnectionError as e:
        logger.error(f"ConnectionError: {url + deck_code} -> {e}")
        return JSONResponse(content={}, status_code=500)

    except requests.exceptions.RequestException as e:
        logger.exception(f"Unexpected RequestException: {url + deck_code} -> {e}")
        return JSONResponse(content={}, status_code=500)

    try:
        bs = BeautifulSoup(res.text, "html.parser")

        card_name_dict = {}
        card_image_dict = {}

        if len(bs.find_all("script", attrs={"type": "", "src": ""})) != 2:
            count = len(bs.find_all("script", attrs={"type": "", "src": ""}))
            logger.exception(
                f"Unexpected <script> tag count: expected = 2, actual = {count}"
            )
            return JSONResponse(content={}, status_code=500)

        text = bs.find_all("script", attrs={"type": "", "src": ""})[-1]

        for item in str(text).strip().split(";"):
            line = item.strip()

            if not line:
                continue

            if "searchItemNameAlt" in line:
                match = re.search(r"\[(\d+)\]='([^']+)'", line)
                if match:
                    number = match.group(1)
                    name = match.group(2)
                    card_name_dict.update({number: name})

            if "searchItemCardPict" in line:
                match = re.search(r"\[(\d+)\]='([^']+)'", line)
                if match:
                    number = match.group(1)
                    name = match.group(2)
                    card_image_dict.update({number: name})

        if len(bs.find_all(id="inputArea")) != 1:
            count = len(bs.find_all(id="inputArea"))
            logger.exception(
                f"Unexpected 'inputArea' id count: expected = 1, actual = {count}"
            )
            return JSONResponse(content={}, status_code=500)

        bs_input_area = BeautifulSoup(
            str(bs.find_all(id="inputArea")[0]), "html.parser"
        )

        ret_list = []
        total_card_count = 0

        for item in bs_input_area.find_all("input"):
            if item["id"] == "deck_ajs" or item["id"] == "copyDeckID":
                continue

            deckcards = []
            card_count_dict = {}
            card_type_count = 0

            if item["value"] and item["id"] != "copyDeckID":
                result = {
                    k: int(v)
                    for k, v in (
                        val.rsplit("_", 1)[0].split("_")
                        for val in item["value"].split("-")
                    )
                }
                card_count_dict.update(result)

            for card_id, count in card_count_dict.items():
                if item["id"] == "deck_pke":
                    try:
                        with pool.connection() as conn:
                            with conn.cursor() as cur:
                                ability = ""
                                attacks = []

                                sql = "SELECT ability, attack FROM pokemon_cards WHERE id = %s"
                                cur.execute(sql, (card_id,))
                                row = cur.fetchone()

                                if row is None:
                                    logger.exception(
                                        f"Record not found: pokemon_cards.id={card_id}"
                                    )
                                    return JSONResponse(content={}, status_code=500)

                                ability = row[0]
                                attacks = row[1].split("/")

                        for i in range(count):
                            card_info = {
                                "card_id": int(card_id),
                                "card_name": str(card_name_dict[card_id]).replace(
                                    "(ACE SPEC)", ""
                                ),
                                "detail_url": str(
                                    "https://www.pokemon-card.com/card-search/details.php/card/"
                                    + str(card_id)
                                ),
                                "image_url": str(
                                    "https://www.pokemon-card.com"
                                    + str(card_image_dict[card_id])
                                ),
                                "ability": ability,
                                "attacks": attacks,
                            }

                            deckcards.append(card_info)
                            card_type_count += 1
                    except psycopg.Error as e:
                        logger.exception(
                            f"PostgreSQL error occurred. card_id={card_id}"
                        )
                        logger.error("=== PostgreSQL Error ===")
                        logger.error(f"Message: {e}")
                        logger.error(f"SQLSTATE: {e.sqlstate}")
                        logger.error(f"Diag message: {e.diag.message_primary}")
                        logger.error(f"Detail: {e.diag.message_detail}")
                        logger.error(f"Hint: {e.diag.message_hint}")
                        logger.error(f"card_id: {card_id}")
                        logger.error("========================", exc_info=True)

                    except Exception:
                        logger.exception(f"Unexpected error. card_id={card_id}")
                        return JSONResponse(content={}, status_code=500)
                else:
                    for i in range(count):
                        card_info = {
                            "card_id": int(card_id),
                            "card_name": str(card_name_dict[card_id]).replace(
                                "(ACE SPEC)", ""
                            ),
                            "detail_url": str(
                                "https://www.pokemon-card.com/card-search/details.php/card/"
                                + str(card_id)
                            ),
                            "image_url": str(
                                "https://www.pokemon-card.com"
                                + str(card_image_dict[card_id])
                            ),
                        }

                        deckcards.append(card_info)
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

    except Exception:
        return JSONResponse(content=[], status_code=500)


def create_v1beta_deckcards_summary(deck_code):
    try:
        logger.info(f"Request start: {url + deck_code}")

        res = requests.get(url + deck_code, timeout=3)

        if res.status_code == 404:
            logger.info(f"Request failed: {url + deck_code} (status={res.status_code})")

            fallback_url = "https://www.pokemon-card.com/deck/result.html/deckID/"

            try:
                logger.warning(f"Not Found (404): {url + deck_code}")

                logger.info(f"Request start: {fallback_url + deck_code}")

                res = requests.get(fallback_url + deck_code, timeout=3)

                res.raise_for_status()

                logger.info(
                    f"Request succeeded: {fallback_url + deck_code} (status={res.status_code})"
                )

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout occurred: {fallback_url + deck_code}")
                return JSONResponse(content={}, status_code=504)

            except requests.exceptions.HTTPError as e:
                status = getattr(e.response, "status_code", 500)
                logger.error(
                    f"HTTPError: {fallback_url + deck_code} -> status {status}"
                )
                return JSONResponse(content={}, status_code=status)

            except requests.exceptions.ConnectionError as e:
                logger.error(f"ConnectionError: {fallback_url + deck_code} -> {e}")
                return JSONResponse(content={}, status_code=500)

            except requests.exceptions.RequestException as e:
                logger.exception(
                    f"Unexpected RequestException: {fallback_url + deck_code} -> {e}"
                )
                return JSONResponse(content={}, status_code=500)

        else:
            res.raise_for_status()

            logger.info(
                f"Request succeeded: {url + deck_code} (status={res.status_code})"
            )

    except requests.exceptions.Timeout:
        logger.warning(f"Timeout occurred: {url + deck_code}")
        return JSONResponse(content={}, status_code=504)

    except requests.exceptions.HTTPError as e:
        status = getattr(e.response, "status_code", 500)
        logger.error(f"HTTPError: {url + deck_code} -> status {status}")
        return JSONResponse(content={}, status_code=status)

    except requests.exceptions.ConnectionError as e:
        logger.error(f"ConnectionError: {url + deck_code} -> {e}")
        return JSONResponse(content={}, status_code=500)

    except requests.exceptions.RequestException as e:
        logger.exception(f"Unexpected RequestException: {url + deck_code} -> {e}")
        return JSONResponse(content={}, status_code=500)

    try:
        bs = BeautifulSoup(res.text, "html.parser")

        card_name_dict = {}
        card_image_dict = {}

        if len(bs.find_all("script", attrs={"type": "", "src": ""})) != 2:
            count = len(bs.find_all("script", attrs={"type": "", "src": ""}))
            logger.exception(
                f"Unexpected <script> tag count: expected = 2, actual = {count}"
            )
            return JSONResponse(content={}, status_code=500)

        text = bs.find_all("script", attrs={"type": "", "src": ""})[-1]

        for item in str(text).strip().split(";"):
            line = item.strip()

            if not line:
                continue

            if "searchItemNameAlt" in line:
                match = re.search(r"\[(\d+)\]='([^']+)'", line)
                if match:
                    number = match.group(1)
                    name = match.group(2)
                    card_name_dict.update({number: name})

            if "searchItemCardPict" in line:
                match = re.search(r"\[(\d+)\]='([^']+)'", line)
                if match:
                    number = match.group(1)
                    name = match.group(2)
                    card_image_dict.update({number: name})

        if len(bs.find_all(id="inputArea")) != 1:
            count = len(bs.find_all(id="inputArea"))
            logger.exception(
                f"Unexpected 'inputArea' id count: expected = 1, actual = {count}"
            )
            return JSONResponse(content={}, status_code=500)

        bs_input_area = BeautifulSoup(
            str(bs.find_all(id="inputArea")[0]), "html.parser"
        )

        ret_dict = {}
        total_card_count = 0

        for item in bs_input_area.find_all("input"):
            if item["id"] == "deck_ajs" or item["id"] == "copyDeckID":
                continue

            deckcards = []
            card_count_dict = {}
            card_type_count = 0

            if item["value"] and item["id"] != "copyDeckID":
                result = {
                    k: int(v)
                    for k, v in (
                        val.rsplit("_", 1)[0].split("_")
                        for val in item["value"].split("-")
                    )
                }
                card_count_dict.update(result)

            for card_id, count in card_count_dict.items():
                if item["id"] == "deck_pke":
                    with pool.connection() as conn:
                        with conn.cursor() as cur:
                            ability = ""
                            attacks = []

                            sql = "SELECT ability, attack FROM pokemon_cards WHERE id = %s"
                            cur.execute(sql, (card_id,))
                            row = cur.fetchone()

                            if row is None:
                                logger.exception(
                                    f"Record not found: pokemon_cards.id={card_id}"
                                )
                                return JSONResponse(content={}, status_code=500)

                            ability = row[0]
                            attacks = row[1].split("/")

                    card_info = {
                        "card_id": int(card_id),
                        "card_name": str(card_name_dict[card_id]).replace(
                            "(ACE SPEC)", ""
                        ),
                        "card_count": count,
                        "detail_url": str(
                            "https://www.pokemon-card.com/card-search/details.php/card/"
                            + str(card_id)
                        ),
                        "image_url": str(
                            "https://www.pokemon-card.com"
                            + str(card_image_dict[card_id])
                        ),
                        "ability": ability,
                        "attacks": attacks,
                    }

                    deckcards.append(card_info)
                    card_type_count += count
                else:
                    card_info = {
                        "card_id": int(card_id),
                        "card_name": str(card_name_dict[card_id]).replace(
                            "(ACE SPEC)", ""
                        ),
                        "card_count": count,
                        "detail_url": str(
                            "https://www.pokemon-card.com/card-search/details.php/card/"
                            + str(card_id)
                        ),
                        "image_url": str(
                            "https://www.pokemon-card.com"
                            + str(card_image_dict[card_id])
                        ),
                    }

                    deckcards.append(card_info)
                    card_type_count += count

            if item["id"] == "deck_pke":
                result = OrderedDict()

                for card in deckcards:
                    key = (
                        card.get("card_name"),
                        card.get("ability", ""),
                        tuple(sorted(card.get("attacks", []))),  # attacksは順不同
                    )

                    if key not in result:
                        result[key] = card.copy()
                    else:
                        result[key]["card_count"] += card["card_count"]
            else:
                result = OrderedDict()

                for card in deckcards:
                    key = card["card_name"]

                    if key not in result:
                        result[key] = card.copy()
                    else:
                        result[key]["card_count"] += card["card_count"]

            ret_dict.update(
                {
                    str(item["id"]).replace("deck", "card"): list(result.values()),
                    str(item["id"]).replace("deck", "card") + "_count": card_type_count,
                }
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

app = FastAPI()


deckcards_cache = cachetools.LRUCache(maxsize=2000)
acespec_cache = cachetools.LRUCache(maxsize=2000)

deck_list_cache = cachetools.LFUCache(maxsize=2000)
deck_summary_cache = cachetools.LFUCache(maxsize=2000)


@app.get("/deckcards/{deck_code}")
def create_deckcards_app(deck_code):
    if deck_code in deckcards_cache:
        logger.info(f"[deckcards] cache hit deck_code={deck_code}")
        return deckcards_cache[deck_code]
    else:
        logger.info(f"[deckcards] cache miss deck_code={deck_code}")
        return create_deckcards(deck_code)


@app.get("/deckcards/{deck_code}/acespec")
def find_acespec_app(deck_code):
    return find_acespec(deck_code)


@app.get("/deckcards/{deck_code}/detail")
def create_deckcards_detail_app(deck_code):
    return create_deckcards_detail(deck_code)


@app.get("/api/v1beta/deckcards/{deck_code}")
def create_v1beta_deckcards_app(deck_code):
    return create_v1beta_deckcards(deck_code)


@app.get("/api/v1beta/deckcards/{deck_code}/acespec")
def create_v1beta_deckcards_acespec_app(deck_code):
    if deck_code in acespec_cache:
        logger.info(f"[acespec] cache hit deck_code={deck_code}")
        return acespec_cache[deck_code]
    else:
        logger.info(f"[acespec] cache miss deck_code={deck_code}")
        return create_v1beta_acespec(deck_code)


@app.get("/api/v1beta/deckcards/{deck_code}/detail")
def create_v1beta_deckcards_detail_app(deck_code):
    return create_v1beta_deckcards_detail(deck_code)


@app.get("/api/v1beta/deckcards/{deck_code}/list")
def create_v1beta_deckcards_list_app(deck_code):
    if deck_code in deck_list_cache:
        logger.info(f"[deckcards/list] cache hit deck_code={deck_code}")
        return deck_list_cache[deck_code]
    else:
        logger.info(f"[deckcards/list] cache miss deck_code={deck_code}")
        return create_v1beta_deckcards_list(deck_code)


@app.get("/api/v1beta/deckcards/{deck_code}/summary")
def create_v1beta_deckcards_summary_app(deck_code):
    if deck_code in deck_summary_cache:
        logger.info(f"[deckcards/summary] cache hit deck_code={deck_code}")
        return deck_summary_cache[deck_code]
    else:
        logger.info(f"[deckcards/summary] cache miss deck_code={deck_code}")
        return create_v1beta_deckcards_summary(deck_code)


@app.get("/health")
def health():
    return JSONResponse(content={}, status_code=200)
