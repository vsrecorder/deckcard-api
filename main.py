import os

import re
import requests
import logging
from collections import OrderedDict

import psycopg2
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

url = "https://www.pokemon-card.com/deck/result.html/deckID/"

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



def create_deckcards(deck_code):
    try:
        logger.info(f"Request start: {url + deck_code}")

        res = requests.get(url + deck_code, timeout=3)
        res.raise_for_status()

        logger.info(f"Request succeeded: {url + deck_code} (status={res.status_code})")

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

    bs = BeautifulSoup(res.text, "html.parser")

    deckcards = []
    card_name_dict = {}
    card_image_dict = {}
    card_count_dict = {}

    if len(bs.find_all('script', attrs={"type": "", "src": ""})) != 2:
        count = len(bs.find_all('script', attrs={"type": "", "src": ""}))
        logger.exception(f"Unexpected <script> tag count: expected = 2, actual = {count}")
        return JSONResponse(content={}, status_code=500)

    """
    <script>
    PCGDECK.searchItemName[44122]='サーフゴーex(SV3a 050/062)';
    PCGDECK.searchItemNameAlt[44122]='サーフゴーex';
    PCGDECK.searchItemCardPict[44122]='/assets/images/card_images/large/SV3a/044122_P_SAFUGOEX.jpg';
    PCGDECK.searchItemName[46253]='コレクレー(SV7a 024/064)';
    PCGDECK.searchItemNameAlt[46253]='コレクレー';
    PCGDECK.searchItemCardPict[46253]='/assets/images/card_images/large/SV7a/046253_P_KOREKURE.jpg';
    PCGDECK.searchItemName[47759]='ルナトーン(M1L 026/063)';
    PCGDECK.searchItemNameAlt[47759]='ルナトーン';
    PCGDECK.searchItemCardPict[47759]='/assets/images/card_images/large/M1L/047759_P_RUNATON.jpg';
    PCGDECK.searchItemName[47760]='ソルロック(M1L 027/063)';
    PCGDECK.searchItemNameAlt[47760]='ソルロック';
    PCGDECK.searchItemCardPict[47760]='/assets/images/card_images/large/M1L/047760_P_SORUROKKU.jpg';
    PCGDECK.searchItemName[44450]='テツノツツミ(SV4M 071/066)';
    PCGDECK.searchItemNameAlt[44450]='テツノツツミ';
    PCGDECK.searchItemCardPict[44450]='/assets/images/card_images/large/SV4M/044450_P_TETSUNOTSUTSUMI.jpg';
    PCGDECK.searchItemName[47988]='ゲノセクトex(SV11B 164/086)';
    PCGDECK.searchItemNameAlt[47988]='ゲノセクトex';
    PCGDECK.searchItemCardPict[47988]='/assets/images/card_images/large/SV11B/047988_P_GENOSEKUTOEX.jpg';
    PCGDECK.searchItemName[46058]='キチキギスex(SV6a 081/064)';
    PCGDECK.searchItemNameAlt[46058]='キチキギスex';
    PCGDECK.searchItemCardPict[46058]='/assets/images/card_images/large/SV6a/046058_P_KICHIKIGISUEX.jpg';
    PCGDECK.searchItemName[45403]='なかよしポフィン';
    PCGDECK.searchItemNameAlt[45403]='なかよしポフィン';
    PCGDECK.searchItemCardPict[45403]='/assets/images/card_images/large/SV-P/045403_T_NAKAYOSHIPOFUIN.jpg';
    PCGDECK.searchItemName[42616]='ネストボール';
    PCGDECK.searchItemNameAlt[42616]='ネストボール';
    PCGDECK.searchItemCardPict[42616]='/assets/images/card_images/large/SV1S/042616_T_NESUTOBORU.jpg';
    PCGDECK.searchItemName[48439]='ファイトゴング';
    PCGDECK.searchItemNameAlt[48439]='ファイトゴング';
    PCGDECK.searchItemCardPict[48439]='/assets/images/card_images/large/M1L/048439_T_FUAITOGONGU.jpg';
    PCGDECK.searchItemName[44306]='大地の器';
    PCGDECK.searchItemNameAlt[44306]='大地の器';
    PCGDECK.searchItemCardPict[44306]='/assets/images/card_images/large/SV4K/044306_T_DAICHINOUTSUWA.jpg';
    PCGDECK.searchItemName[46434]='推理セット';
    PCGDECK.searchItemNameAlt[46434]='推理セット';
    PCGDECK.searchItemCardPict[46434]='/assets/images/card_images/large/SV8/046434_T_SUIRISETTO.jpg';
    PCGDECK.searchItemName[44958]='スーパーエネルギー回収';
    PCGDECK.searchItemNameAlt[44958]='スーパーエネルギー回収';
    PCGDECK.searchItemCardPict[44958]='/assets/images/card_images/large/SV2D/044958_T_SUPAENERUGIKAISHIXYUU.jpg';
    PCGDECK.searchItemName[44955]='すごいつりざお';
    PCGDECK.searchItemNameAlt[44955]='すごいつりざお';
    PCGDECK.searchItemCardPict[44955]='/assets/images/card_images/large/SV2P/044955_T_SUGOITSURIZAO.jpg';
    PCGDECK.searchItemName[42695]='ピクニックバスケット';
    PCGDECK.searchItemNameAlt[42695]='ピクニックバスケット';
    PCGDECK.searchItemCardPict[42695]='/assets/images/card_images/large/SV1V/042695_T_PIKUNIKKUBASUKETTO.jpg';
    PCGDECK.searchItemName[46220]='プレシャスキャリー(ACE SPEC)';
    PCGDECK.searchItemNameAlt[46220]='プレシャスキャリー(ACE SPEC)';
    PCGDECK.searchItemCardPict[46220]='/assets/images/card_images/large/SVLN/046220_T_PURESHIXYASUKIXYARI.jpg';
    PCGDECK.searchItemName[48441]='ふうせん';
    PCGDECK.searchItemNameAlt[48441]='ふうせん';
    PCGDECK.searchItemCardPict[48441]='/assets/images/card_images/large/M1L/048441_T_FUUSEN.jpg';
    PCGDECK.searchItemName[42771]='げんきのハチマキ';
    PCGDECK.searchItemNameAlt[42771]='げんきのハチマキ';
    PCGDECK.searchItemCardPict[42771]='/assets/images/card_images/large/SVAW/042771_T_GENKINOHACHIMAKI.jpg';
    PCGDECK.searchItemName[43086]='ペパー';
    PCGDECK.searchItemNameAlt[43086]='ペパー';
    PCGDECK.searchItemCardPict[43086]='/assets/images/card_images/large/SV1V/043086_T_PEPA.jpg';
    PCGDECK.searchItemName[47526]='ロケット団のラムダ';
    PCGDECK.searchItemNameAlt[47526]='ロケット団のラムダ';
    PCGDECK.searchItemCardPict[47526]='/assets/images/card_images/large/SV10/047526_T_ROKETTODANNORAMUDA.jpg';
    PCGDECK.searchItemName[45562]='暗号マニアの解読';
    PCGDECK.searchItemNameAlt[45562]='暗号マニアの解読';
    PCGDECK.searchItemCardPict[45562]='/assets/images/card_images/large/SV5M/045562_T_ANGOUMANIANOKAIDOKU.jpg';
    PCGDECK.searchItemName[44465]='フトゥー博士のシナリオ';
    PCGDECK.searchItemNameAlt[44465]='フトゥー博士のシナリオ';
    PCGDECK.searchItemCardPict[44465]='/assets/images/card_images/large/SV4M/044465_T_FUTOUHAKASENOSHINARIO.jpg';
    PCGDECK.searchItemName[35737]='ジャッジマン';
    PCGDECK.searchItemNameAlt[35737]='ジャッジマン';
    PCGDECK.searchItemCardPict[35737]='/assets/images/card_images/large/SM7a/035737_T_JAJJIMAN.jpg';
    PCGDECK.searchItemName[43300]='ボスの指令';
    PCGDECK.searchItemNameAlt[43300]='ボスの指令';
    PCGDECK.searchItemCardPict[43300]='/assets/images/card_images/large/SV1a/043300_T_BOSUNOSHIREIGECHISU.jpg';
    PCGDECK.searchItemName[43036]='レッスンスタジオ';
    PCGDECK.searchItemNameAlt[43036]='レッスンスタジオ';
    PCGDECK.searchItemCardPict[43036]='/assets/images/card_images/large/SV1a/043036_T_RESSUNSUTAJIO.jpg';
    PCGDECK.searchItemName[42784]='基本闘エネルギー';
    PCGDECK.searchItemNameAlt[42784]='基本闘エネルギー';
    PCGDECK.searchItemCardPict[42784]='/assets/images/card_images/large/ENE/042784_E_KIHONTOUENERUGI.jpg';
    PCGDECK.searchItemName[42786]='基本鋼エネルギー';
    PCGDECK.searchItemNameAlt[42786]='基本鋼エネルギー';
    PCGDECK.searchItemCardPict[42786]='/assets/images/card_images/large/ENE/042786_E_KIHONHAGANEENERUGI.jpg';
    PCGDECK.viewItemMode=2;
    </script>
    """

    text = bs.find_all('script', attrs={"type": "", "src": ""})[-1]

    for item in str(text).strip().split(';'):
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

    if len(bs.find_all(id='inputArea')) != 1:
        count =len(bs.find_all(id='inputArea'))
        logger.exception(f"Unexpected 'inputArea' id count: expected = 1, actual = {count}")
        return JSONResponse(content={}, status_code=500)

    """
    <form id="inputArea" action="./deckRegister.php">
        <input type="hidden" name="deck_pke" id="deck_pke" value="44122_4_1-46253_4_1-47759_2_1-47760_2_1-44450_1_1-47988_1_1-46058_1_1" />
        <input type="hidden" name="deck_gds" id="deck_gds" value="45403_1_1-42616_2_1-48439_3_1-44306_3_1-46434_1_1-44958_4_1-44955_1_1-42695_1_1-46220_1_1" />
        <input type="hidden" name="deck_tool" id="deck_tool" value="48441_2_1-42771_1_1" />
        <input type="hidden" name="deck_tech" id="deck_tech" value="" />
        <input type="hidden" name="deck_sup" id="deck_sup" value="43086_4_1-47526_1_1-45562_1_1-44465_2_1-35737_1_1-43300_4_1" />
        <input type="hidden" name="deck_sta" id="deck_sta" value="43036_1_1" />
        <input type="hidden" name="deck_ene" id="deck_ene" value="42784_8_1-42786_3_1" />
        <input type="hidden" name="deck_ajs" id="deck_ajs" value="" />
        <input type="hidden" name="copyDeckID" id="copyDeckID" value="vv5kFf-8mYwSW-FVVVbw" />
    </form>
    """

    bs_input_area = BeautifulSoup(str(bs.find_all(id='inputArea')[0]), "html.parser")

    for item in bs_input_area.find_all('input'):
        if item['value'] and item['id'] != "copyDeckID":
            result = {
                k: int(v)
                for k, v in (val.rsplit('_', 1)[0].split('_') for val in item['value'].split('-'))
            }
            card_count_dict.update(result)

    total_card_count = 0

    for card_id, name in card_name_dict.items():
        card_info = {
            "id": int(card_id),
            "name": str(name).replace("(ACE SPEC)", ""),
            "detail_url": str("https://www.pokemon-card.com/card-search/details.php/card/" + str(card_id)),
            "image_url": str("https://www.pokemon-card.com" + str(card_image_dict[card_id])),
            "count": card_count_dict[card_id],
        }
        deckcards.append(card_info)
        total_card_count += card_count_dict[card_id]

    if total_card_count != 60:
        logger.exception(f"Unexpected deck cards count: expected = 60, actual = {total_card_count}")
        return JSONResponse(content={}, status_code=500)

    return deckcards



def create_deckcards_detail(conn, deck_code):
    try:
        logger.info(f"Request start: {url + deck_code}")

        res = requests.get(url + deck_code, timeout=3)
        res.raise_for_status()

        logger.info(f"Request succeeded: {url + deck_code} (status={res.status_code})")

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


    bs = BeautifulSoup(res.text, "html.parser")

    card_name_dict = {}
    card_image_dict = {}

    if len(bs.find_all('script', attrs={"type": "", "src": ""})) != 2:
        count = len(bs.find_all('script', attrs={"type": "", "src": ""}))
        logger.exception(f"Unexpected <script> tag count: expected = 2, actual = {count}")
        return JSONResponse(content={}, status_code=500)

    """
    <script>
    PCGDECK.searchItemName[44122]='サーフゴーex(SV3a 050/062)';
    PCGDECK.searchItemNameAlt[44122]='サーフゴーex';
    PCGDECK.searchItemCardPict[44122]='/assets/images/card_images/large/SV3a/044122_P_SAFUGOEX.jpg';
    PCGDECK.searchItemName[46253]='コレクレー(SV7a 024/064)';
    PCGDECK.searchItemNameAlt[46253]='コレクレー';
    PCGDECK.searchItemCardPict[46253]='/assets/images/card_images/large/SV7a/046253_P_KOREKURE.jpg';
    PCGDECK.searchItemName[47759]='ルナトーン(M1L 026/063)';
    PCGDECK.searchItemNameAlt[47759]='ルナトーン';
    PCGDECK.searchItemCardPict[47759]='/assets/images/card_images/large/M1L/047759_P_RUNATON.jpg';
    PCGDECK.searchItemName[47760]='ソルロック(M1L 027/063)';
    PCGDECK.searchItemNameAlt[47760]='ソルロック';
    PCGDECK.searchItemCardPict[47760]='/assets/images/card_images/large/M1L/047760_P_SORUROKKU.jpg';
    PCGDECK.searchItemName[44450]='テツノツツミ(SV4M 071/066)';
    PCGDECK.searchItemNameAlt[44450]='テツノツツミ';
    PCGDECK.searchItemCardPict[44450]='/assets/images/card_images/large/SV4M/044450_P_TETSUNOTSUTSUMI.jpg';
    PCGDECK.searchItemName[47988]='ゲノセクトex(SV11B 164/086)';
    PCGDECK.searchItemNameAlt[47988]='ゲノセクトex';
    PCGDECK.searchItemCardPict[47988]='/assets/images/card_images/large/SV11B/047988_P_GENOSEKUTOEX.jpg';
    PCGDECK.searchItemName[46058]='キチキギスex(SV6a 081/064)';
    PCGDECK.searchItemNameAlt[46058]='キチキギスex';
    PCGDECK.searchItemCardPict[46058]='/assets/images/card_images/large/SV6a/046058_P_KICHIKIGISUEX.jpg';
    PCGDECK.searchItemName[45403]='なかよしポフィン';
    PCGDECK.searchItemNameAlt[45403]='なかよしポフィン';
    PCGDECK.searchItemCardPict[45403]='/assets/images/card_images/large/SV-P/045403_T_NAKAYOSHIPOFUIN.jpg';
    PCGDECK.searchItemName[42616]='ネストボール';
    PCGDECK.searchItemNameAlt[42616]='ネストボール';
    PCGDECK.searchItemCardPict[42616]='/assets/images/card_images/large/SV1S/042616_T_NESUTOBORU.jpg';
    PCGDECK.searchItemName[48439]='ファイトゴング';
    PCGDECK.searchItemNameAlt[48439]='ファイトゴング';
    PCGDECK.searchItemCardPict[48439]='/assets/images/card_images/large/M1L/048439_T_FUAITOGONGU.jpg';
    PCGDECK.searchItemName[44306]='大地の器';
    PCGDECK.searchItemNameAlt[44306]='大地の器';
    PCGDECK.searchItemCardPict[44306]='/assets/images/card_images/large/SV4K/044306_T_DAICHINOUTSUWA.jpg';
    PCGDECK.searchItemName[46434]='推理セット';
    PCGDECK.searchItemNameAlt[46434]='推理セット';
    PCGDECK.searchItemCardPict[46434]='/assets/images/card_images/large/SV8/046434_T_SUIRISETTO.jpg';
    PCGDECK.searchItemName[44958]='スーパーエネルギー回収';
    PCGDECK.searchItemNameAlt[44958]='スーパーエネルギー回収';
    PCGDECK.searchItemCardPict[44958]='/assets/images/card_images/large/SV2D/044958_T_SUPAENERUGIKAISHIXYUU.jpg';
    PCGDECK.searchItemName[44955]='すごいつりざお';
    PCGDECK.searchItemNameAlt[44955]='すごいつりざお';
    PCGDECK.searchItemCardPict[44955]='/assets/images/card_images/large/SV2P/044955_T_SUGOITSURIZAO.jpg';
    PCGDECK.searchItemName[42695]='ピクニックバスケット';
    PCGDECK.searchItemNameAlt[42695]='ピクニックバスケット';
    PCGDECK.searchItemCardPict[42695]='/assets/images/card_images/large/SV1V/042695_T_PIKUNIKKUBASUKETTO.jpg';
    PCGDECK.searchItemName[46220]='プレシャスキャリー(ACE SPEC)';
    PCGDECK.searchItemNameAlt[46220]='プレシャスキャリー(ACE SPEC)';
    PCGDECK.searchItemCardPict[46220]='/assets/images/card_images/large/SVLN/046220_T_PURESHIXYASUKIXYARI.jpg';
    PCGDECK.searchItemName[48441]='ふうせん';
    PCGDECK.searchItemNameAlt[48441]='ふうせん';
    PCGDECK.searchItemCardPict[48441]='/assets/images/card_images/large/M1L/048441_T_FUUSEN.jpg';
    PCGDECK.searchItemName[42771]='げんきのハチマキ';
    PCGDECK.searchItemNameAlt[42771]='げんきのハチマキ';
    PCGDECK.searchItemCardPict[42771]='/assets/images/card_images/large/SVAW/042771_T_GENKINOHACHIMAKI.jpg';
    PCGDECK.searchItemName[43086]='ペパー';
    PCGDECK.searchItemNameAlt[43086]='ペパー';
    PCGDECK.searchItemCardPict[43086]='/assets/images/card_images/large/SV1V/043086_T_PEPA.jpg';
    PCGDECK.searchItemName[47526]='ロケット団のラムダ';
    PCGDECK.searchItemNameAlt[47526]='ロケット団のラムダ';
    PCGDECK.searchItemCardPict[47526]='/assets/images/card_images/large/SV10/047526_T_ROKETTODANNORAMUDA.jpg';
    PCGDECK.searchItemName[45562]='暗号マニアの解読';
    PCGDECK.searchItemNameAlt[45562]='暗号マニアの解読';
    PCGDECK.searchItemCardPict[45562]='/assets/images/card_images/large/SV5M/045562_T_ANGOUMANIANOKAIDOKU.jpg';
    PCGDECK.searchItemName[44465]='フトゥー博士のシナリオ';
    PCGDECK.searchItemNameAlt[44465]='フトゥー博士のシナリオ';
    PCGDECK.searchItemCardPict[44465]='/assets/images/card_images/large/SV4M/044465_T_FUTOUHAKASENOSHINARIO.jpg';
    PCGDECK.searchItemName[35737]='ジャッジマン';
    PCGDECK.searchItemNameAlt[35737]='ジャッジマン';
    PCGDECK.searchItemCardPict[35737]='/assets/images/card_images/large/SM7a/035737_T_JAJJIMAN.jpg';
    PCGDECK.searchItemName[43300]='ボスの指令';
    PCGDECK.searchItemNameAlt[43300]='ボスの指令';
    PCGDECK.searchItemCardPict[43300]='/assets/images/card_images/large/SV1a/043300_T_BOSUNOSHIREIGECHISU.jpg';
    PCGDECK.searchItemName[43036]='レッスンスタジオ';
    PCGDECK.searchItemNameAlt[43036]='レッスンスタジオ';
    PCGDECK.searchItemCardPict[43036]='/assets/images/card_images/large/SV1a/043036_T_RESSUNSUTAJIO.jpg';
    PCGDECK.searchItemName[42784]='基本闘エネルギー';
    PCGDECK.searchItemNameAlt[42784]='基本闘エネルギー';
    PCGDECK.searchItemCardPict[42784]='/assets/images/card_images/large/ENE/042784_E_KIHONTOUENERUGI.jpg';
    PCGDECK.searchItemName[42786]='基本鋼エネルギー';
    PCGDECK.searchItemNameAlt[42786]='基本鋼エネルギー';
    PCGDECK.searchItemCardPict[42786]='/assets/images/card_images/large/ENE/042786_E_KIHONHAGANEENERUGI.jpg';
    PCGDECK.viewItemMode=2;
    </script>
    """

    text = bs.find_all('script', attrs={"type": "", "src": ""})[-1]

    for item in str(text).strip().split(';'):
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

    if len(bs.find_all(id='inputArea')) != 1:
        count =len(bs.find_all(id='inputArea'))
        logger.exception(f"Unexpected 'inputArea' id count: expected = 1, actual = {count}")
        return JSONResponse(content={}, status_code=500)

    """
    <form id="inputArea" action="./deckRegister.php">
        <input type="hidden" name="deck_pke" id="deck_pke" value="44122_4_1-46253_4_1-47759_2_1-47760_2_1-44450_1_1-47988_1_1-46058_1_1" />
        <input type="hidden" name="deck_gds" id="deck_gds" value="45403_1_1-42616_2_1-48439_3_1-44306_3_1-46434_1_1-44958_4_1-44955_1_1-42695_1_1-46220_1_1" />
        <input type="hidden" name="deck_tool" id="deck_tool" value="48441_2_1-42771_1_1" />
        <input type="hidden" name="deck_tech" id="deck_tech" value="" />
        <input type="hidden" name="deck_sup" id="deck_sup" value="43086_4_1-47526_1_1-45562_1_1-44465_2_1-35737_1_1-43300_4_1" />
        <input type="hidden" name="deck_sta" id="deck_sta" value="43036_1_1" />
        <input type="hidden" name="deck_ene" id="deck_ene" value="42784_8_1-42786_3_1" />
        <input type="hidden" name="deck_ajs" id="deck_ajs" value="" />
        <input type="hidden" name="copyDeckID" id="copyDeckID" value="vv5kFf-8mYwSW-FVVVbw" />
    </form>
    """

    bs_input_area = BeautifulSoup(str(bs.find_all(id='inputArea')[0]), "html.parser")

    ret_dict = {}
    total_card_count = 0

    for item in bs_input_area.find_all('input'):
        if item['id'] == "deck_ajs" or item['id'] == "copyDeckID":
            continue

        deckcards = []
        card_count_dict = {}
        card_type_count = 0

        if item['value'] and item['id'] != "copyDeckID":
            result = {
                k: int(v)
                for k, v in (val.rsplit('_', 1)[0].split('_') for val in item['value'].split('-'))
            }
            card_count_dict.update(result)

        for card_id, count in card_count_dict.items():
            if item['id'] == "deck_pke":
                with conn.cursor() as cur:
                    ability = ""
                    attacks = []
                    sql = "SELECT ability, attack FROM pokemon_cards WHERE id = %s"
                    cur.execute(sql, (card_id,))
                    row = cur.fetchone()

                    if row is None:
                        logger.exception(f"Record not found: pokemon_cards.id={card_id}")
                        return JSONResponse(content={}, status_code=500)
                    else:
                        ability = row[0]
                        attacks = row[1].split('/')

                    cur.close()

                card_info = {
                    "id": int(card_id),
                    "name": str(card_name_dict[card_id]).replace("(ACE SPEC)", ""),
                    "detail_url": str("https://www.pokemon-card.com/card-search/details.php/card/" + str(card_id)),
                    "image_url": str("https://www.pokemon-card.com" + str(card_image_dict[card_id])),
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
                    "detail_url": str("https://www.pokemon-card.com/card-search/details.php/card/" + str(card_id)),
                    "image_url": str("https://www.pokemon-card.com" + str(card_image_dict[card_id])),
                    "count": count,
                }

                deckcards.append(card_info)
                card_type_count += count

        ret_dict.update({item['id']: deckcards, item['id']+"_count": card_type_count})
        total_card_count += card_type_count

    if total_card_count != 60:
        logger.exception(f"Unexpected deck cards count: expected = 60, actual = {total_card_count}")
        return JSONResponse(content={}, status_code=500)

    return ret_dict



def create_v1beta_deckcards(conn, deck_code):
    try:
        logger.info(f"Request start: {url + deck_code}")

        res = requests.get(url + deck_code, timeout=3)
        res.raise_for_status()

        logger.info(f"Request succeeded: {url + deck_code} (status={res.status_code})")

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


    bs = BeautifulSoup(res.text, "html.parser")

    card_name_dict = {}
    card_image_dict = {}

    if len(bs.find_all('script', attrs={"type": "", "src": ""})) != 2:
        count = len(bs.find_all('script', attrs={"type": "", "src": ""}))
        logger.exception(f"Unexpected <script> tag count: expected = 2, actual = {count}")
        return JSONResponse(content={}, status_code=500)

    """
    <script>
    PCGDECK.searchItemName[44122]='サーフゴーex(SV3a 050/062)';
    PCGDECK.searchItemNameAlt[44122]='サーフゴーex';
    PCGDECK.searchItemCardPict[44122]='/assets/images/card_images/large/SV3a/044122_P_SAFUGOEX.jpg';
    PCGDECK.searchItemName[46253]='コレクレー(SV7a 024/064)';
    PCGDECK.searchItemNameAlt[46253]='コレクレー';
    PCGDECK.searchItemCardPict[46253]='/assets/images/card_images/large/SV7a/046253_P_KOREKURE.jpg';
    PCGDECK.searchItemName[47759]='ルナトーン(M1L 026/063)';
    PCGDECK.searchItemNameAlt[47759]='ルナトーン';
    PCGDECK.searchItemCardPict[47759]='/assets/images/card_images/large/M1L/047759_P_RUNATON.jpg';
    PCGDECK.searchItemName[47760]='ソルロック(M1L 027/063)';
    PCGDECK.searchItemNameAlt[47760]='ソルロック';
    PCGDECK.searchItemCardPict[47760]='/assets/images/card_images/large/M1L/047760_P_SORUROKKU.jpg';
    PCGDECK.searchItemName[44450]='テツノツツミ(SV4M 071/066)';
    PCGDECK.searchItemNameAlt[44450]='テツノツツミ';
    PCGDECK.searchItemCardPict[44450]='/assets/images/card_images/large/SV4M/044450_P_TETSUNOTSUTSUMI.jpg';
    PCGDECK.searchItemName[47988]='ゲノセクトex(SV11B 164/086)';
    PCGDECK.searchItemNameAlt[47988]='ゲノセクトex';
    PCGDECK.searchItemCardPict[47988]='/assets/images/card_images/large/SV11B/047988_P_GENOSEKUTOEX.jpg';
    PCGDECK.searchItemName[46058]='キチキギスex(SV6a 081/064)';
    PCGDECK.searchItemNameAlt[46058]='キチキギスex';
    PCGDECK.searchItemCardPict[46058]='/assets/images/card_images/large/SV6a/046058_P_KICHIKIGISUEX.jpg';
    PCGDECK.searchItemName[45403]='なかよしポフィン';
    PCGDECK.searchItemNameAlt[45403]='なかよしポフィン';
    PCGDECK.searchItemCardPict[45403]='/assets/images/card_images/large/SV-P/045403_T_NAKAYOSHIPOFUIN.jpg';
    PCGDECK.searchItemName[42616]='ネストボール';
    PCGDECK.searchItemNameAlt[42616]='ネストボール';
    PCGDECK.searchItemCardPict[42616]='/assets/images/card_images/large/SV1S/042616_T_NESUTOBORU.jpg';
    PCGDECK.searchItemName[48439]='ファイトゴング';
    PCGDECK.searchItemNameAlt[48439]='ファイトゴング';
    PCGDECK.searchItemCardPict[48439]='/assets/images/card_images/large/M1L/048439_T_FUAITOGONGU.jpg';
    PCGDECK.searchItemName[44306]='大地の器';
    PCGDECK.searchItemNameAlt[44306]='大地の器';
    PCGDECK.searchItemCardPict[44306]='/assets/images/card_images/large/SV4K/044306_T_DAICHINOUTSUWA.jpg';
    PCGDECK.searchItemName[46434]='推理セット';
    PCGDECK.searchItemNameAlt[46434]='推理セット';
    PCGDECK.searchItemCardPict[46434]='/assets/images/card_images/large/SV8/046434_T_SUIRISETTO.jpg';
    PCGDECK.searchItemName[44958]='スーパーエネルギー回収';
    PCGDECK.searchItemNameAlt[44958]='スーパーエネルギー回収';
    PCGDECK.searchItemCardPict[44958]='/assets/images/card_images/large/SV2D/044958_T_SUPAENERUGIKAISHIXYUU.jpg';
    PCGDECK.searchItemName[44955]='すごいつりざお';
    PCGDECK.searchItemNameAlt[44955]='すごいつりざお';
    PCGDECK.searchItemCardPict[44955]='/assets/images/card_images/large/SV2P/044955_T_SUGOITSURIZAO.jpg';
    PCGDECK.searchItemName[42695]='ピクニックバスケット';
    PCGDECK.searchItemNameAlt[42695]='ピクニックバスケット';
    PCGDECK.searchItemCardPict[42695]='/assets/images/card_images/large/SV1V/042695_T_PIKUNIKKUBASUKETTO.jpg';
    PCGDECK.searchItemName[46220]='プレシャスキャリー(ACE SPEC)';
    PCGDECK.searchItemNameAlt[46220]='プレシャスキャリー(ACE SPEC)';
    PCGDECK.searchItemCardPict[46220]='/assets/images/card_images/large/SVLN/046220_T_PURESHIXYASUKIXYARI.jpg';
    PCGDECK.searchItemName[48441]='ふうせん';
    PCGDECK.searchItemNameAlt[48441]='ふうせん';
    PCGDECK.searchItemCardPict[48441]='/assets/images/card_images/large/M1L/048441_T_FUUSEN.jpg';
    PCGDECK.searchItemName[42771]='げんきのハチマキ';
    PCGDECK.searchItemNameAlt[42771]='げんきのハチマキ';
    PCGDECK.searchItemCardPict[42771]='/assets/images/card_images/large/SVAW/042771_T_GENKINOHACHIMAKI.jpg';
    PCGDECK.searchItemName[43086]='ペパー';
    PCGDECK.searchItemNameAlt[43086]='ペパー';
    PCGDECK.searchItemCardPict[43086]='/assets/images/card_images/large/SV1V/043086_T_PEPA.jpg';
    PCGDECK.searchItemName[47526]='ロケット団のラムダ';
    PCGDECK.searchItemNameAlt[47526]='ロケット団のラムダ';
    PCGDECK.searchItemCardPict[47526]='/assets/images/card_images/large/SV10/047526_T_ROKETTODANNORAMUDA.jpg';
    PCGDECK.searchItemName[45562]='暗号マニアの解読';
    PCGDECK.searchItemNameAlt[45562]='暗号マニアの解読';
    PCGDECK.searchItemCardPict[45562]='/assets/images/card_images/large/SV5M/045562_T_ANGOUMANIANOKAIDOKU.jpg';
    PCGDECK.searchItemName[44465]='フトゥー博士のシナリオ';
    PCGDECK.searchItemNameAlt[44465]='フトゥー博士のシナリオ';
    PCGDECK.searchItemCardPict[44465]='/assets/images/card_images/large/SV4M/044465_T_FUTOUHAKASENOSHINARIO.jpg';
    PCGDECK.searchItemName[35737]='ジャッジマン';
    PCGDECK.searchItemNameAlt[35737]='ジャッジマン';
    PCGDECK.searchItemCardPict[35737]='/assets/images/card_images/large/SM7a/035737_T_JAJJIMAN.jpg';
    PCGDECK.searchItemName[43300]='ボスの指令';
    PCGDECK.searchItemNameAlt[43300]='ボスの指令';
    PCGDECK.searchItemCardPict[43300]='/assets/images/card_images/large/SV1a/043300_T_BOSUNOSHIREIGECHISU.jpg';
    PCGDECK.searchItemName[43036]='レッスンスタジオ';
    PCGDECK.searchItemNameAlt[43036]='レッスンスタジオ';
    PCGDECK.searchItemCardPict[43036]='/assets/images/card_images/large/SV1a/043036_T_RESSUNSUTAJIO.jpg';
    PCGDECK.searchItemName[42784]='基本闘エネルギー';
    PCGDECK.searchItemNameAlt[42784]='基本闘エネルギー';
    PCGDECK.searchItemCardPict[42784]='/assets/images/card_images/large/ENE/042784_E_KIHONTOUENERUGI.jpg';
    PCGDECK.searchItemName[42786]='基本鋼エネルギー';
    PCGDECK.searchItemNameAlt[42786]='基本鋼エネルギー';
    PCGDECK.searchItemCardPict[42786]='/assets/images/card_images/large/ENE/042786_E_KIHONHAGANEENERUGI.jpg';
    PCGDECK.viewItemMode=2;
    </script>
    """

    text = bs.find_all('script', attrs={"type": "", "src": ""})[-1]

    for item in str(text).strip().split(';'):
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

    if len(bs.find_all(id='inputArea')) != 1:
        count =len(bs.find_all(id='inputArea'))
        logger.exception(f"Unexpected 'inputArea' id count: expected = 1, actual = {count}")
        return JSONResponse(content={}, status_code=500)

    """
    <form id="inputArea" action="./deckRegister.php">
        <input type="hidden" name="deck_pke" id="deck_pke" value="44122_4_1-46253_4_1-47759_2_1-47760_2_1-44450_1_1-47988_1_1-46058_1_1" />
        <input type="hidden" name="deck_gds" id="deck_gds" value="45403_1_1-42616_2_1-48439_3_1-44306_3_1-46434_1_1-44958_4_1-44955_1_1-42695_1_1-46220_1_1" />
        <input type="hidden" name="deck_tool" id="deck_tool" value="48441_2_1-42771_1_1" />
        <input type="hidden" name="deck_tech" id="deck_tech" value="" />
        <input type="hidden" name="deck_sup" id="deck_sup" value="43086_4_1-47526_1_1-45562_1_1-44465_2_1-35737_1_1-43300_4_1" />
        <input type="hidden" name="deck_sta" id="deck_sta" value="43036_1_1" />
        <input type="hidden" name="deck_ene" id="deck_ene" value="42784_8_1-42786_3_1" />
        <input type="hidden" name="deck_ajs" id="deck_ajs" value="" />
        <input type="hidden" name="copyDeckID" id="copyDeckID" value="vv5kFf-8mYwSW-FVVVbw" />
    </form>
    """

    bs_input_area = BeautifulSoup(str(bs.find_all(id='inputArea')[0]), "html.parser")

    ret_list = []
    total_card_count = 0

    for item in bs_input_area.find_all('input'):
        if item['id'] == "deck_ajs" or item['id'] == "copyDeckID":
            continue

        deckcards = []
        card_count_dict = {}
        card_type_count = 0

        if item['value'] and item['id'] != "copyDeckID":
            result = {
                k: int(v)
                for k, v in (val.rsplit('_', 1)[0].split('_') for val in item['value'].split('-'))
            }
            card_count_dict.update(result)

        for card_id, count in card_count_dict.items():
            if item['id'] == "deck_pke":
                with conn.cursor() as cur:
                    ability = ""
                    attacks = []
                    sql = "SELECT ability, attack FROM pokemon_cards WHERE id = %s"
                    cur.execute(sql, (card_id,))
                    row = cur.fetchone()

                    if row is None:
                        logger.exception(f"Record not found: pokemon_cards.id={card_id}")
                        return JSONResponse(content={}, status_code=500)
                    else:
                        ability = row[0]
                        attacks = row[1].split('/')

                    cur.close()

                card_info = {
                    "card_id": int(card_id),
                    "card_name": str(card_name_dict[card_id]).replace("(ACE SPEC)", ""),
                    "card_count": count,
                    "detail_url": str("https://www.pokemon-card.com/card-search/details.php/card/" + str(card_id)),
                    "image_url": str("https://www.pokemon-card.com" + str(card_image_dict[card_id])),
                    "ability": ability,
                    "attacks": attacks,
                }

                deckcards.append(card_info)
                card_type_count += count
            else:
                card_info = {
                    "card_id": int(card_id),
                    "card_name": str(card_name_dict[card_id]).replace("(ACE SPEC)", ""),
                    "card_count": count,
                    "detail_url": str("https://www.pokemon-card.com/card-search/details.php/card/" + str(card_id)),
                    "image_url": str("https://www.pokemon-card.com" + str(card_image_dict[card_id])),
                }

                deckcards.append(card_info)
                card_type_count += count

        ret_list.extend(deckcards)
        total_card_count += card_type_count

    if total_card_count != 60:
        logger.exception(f"Unexpected deck cards count: expected = 60, actual = {total_card_count}")
        return JSONResponse(content={}, status_code=500)

    return ret_list



def create_v1beta_deckcards_detail(conn, deck_code):
    try:
        logger.info(f"Request start: {url + deck_code}")

        res = requests.get(url + deck_code, timeout=3)
        res.raise_for_status()

        logger.info(f"Request succeeded: {url + deck_code} (status={res.status_code})")

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


    bs = BeautifulSoup(res.text, "html.parser")

    card_name_dict = {}
    card_image_dict = {}

    if len(bs.find_all('script', attrs={"type": "", "src": ""})) != 2:
        count = len(bs.find_all('script', attrs={"type": "", "src": ""}))
        logger.exception(f"Unexpected <script> tag count: expected = 2, actual = {count}")
        return JSONResponse(content={}, status_code=500)

    """
    <script>
    PCGDECK.searchItemName[44122]='サーフゴーex(SV3a 050/062)';
    PCGDECK.searchItemNameAlt[44122]='サーフゴーex';
    PCGDECK.searchItemCardPict[44122]='/assets/images/card_images/large/SV3a/044122_P_SAFUGOEX.jpg';
    PCGDECK.searchItemName[46253]='コレクレー(SV7a 024/064)';
    PCGDECK.searchItemNameAlt[46253]='コレクレー';
    PCGDECK.searchItemCardPict[46253]='/assets/images/card_images/large/SV7a/046253_P_KOREKURE.jpg';
    PCGDECK.searchItemName[47759]='ルナトーン(M1L 026/063)';
    PCGDECK.searchItemNameAlt[47759]='ルナトーン';
    PCGDECK.searchItemCardPict[47759]='/assets/images/card_images/large/M1L/047759_P_RUNATON.jpg';
    PCGDECK.searchItemName[47760]='ソルロック(M1L 027/063)';
    PCGDECK.searchItemNameAlt[47760]='ソルロック';
    PCGDECK.searchItemCardPict[47760]='/assets/images/card_images/large/M1L/047760_P_SORUROKKU.jpg';
    PCGDECK.searchItemName[44450]='テツノツツミ(SV4M 071/066)';
    PCGDECK.searchItemNameAlt[44450]='テツノツツミ';
    PCGDECK.searchItemCardPict[44450]='/assets/images/card_images/large/SV4M/044450_P_TETSUNOTSUTSUMI.jpg';
    PCGDECK.searchItemName[47988]='ゲノセクトex(SV11B 164/086)';
    PCGDECK.searchItemNameAlt[47988]='ゲノセクトex';
    PCGDECK.searchItemCardPict[47988]='/assets/images/card_images/large/SV11B/047988_P_GENOSEKUTOEX.jpg';
    PCGDECK.searchItemName[46058]='キチキギスex(SV6a 081/064)';
    PCGDECK.searchItemNameAlt[46058]='キチキギスex';
    PCGDECK.searchItemCardPict[46058]='/assets/images/card_images/large/SV6a/046058_P_KICHIKIGISUEX.jpg';
    PCGDECK.searchItemName[45403]='なかよしポフィン';
    PCGDECK.searchItemNameAlt[45403]='なかよしポフィン';
    PCGDECK.searchItemCardPict[45403]='/assets/images/card_images/large/SV-P/045403_T_NAKAYOSHIPOFUIN.jpg';
    PCGDECK.searchItemName[42616]='ネストボール';
    PCGDECK.searchItemNameAlt[42616]='ネストボール';
    PCGDECK.searchItemCardPict[42616]='/assets/images/card_images/large/SV1S/042616_T_NESUTOBORU.jpg';
    PCGDECK.searchItemName[48439]='ファイトゴング';
    PCGDECK.searchItemNameAlt[48439]='ファイトゴング';
    PCGDECK.searchItemCardPict[48439]='/assets/images/card_images/large/M1L/048439_T_FUAITOGONGU.jpg';
    PCGDECK.searchItemName[44306]='大地の器';
    PCGDECK.searchItemNameAlt[44306]='大地の器';
    PCGDECK.searchItemCardPict[44306]='/assets/images/card_images/large/SV4K/044306_T_DAICHINOUTSUWA.jpg';
    PCGDECK.searchItemName[46434]='推理セット';
    PCGDECK.searchItemNameAlt[46434]='推理セット';
    PCGDECK.searchItemCardPict[46434]='/assets/images/card_images/large/SV8/046434_T_SUIRISETTO.jpg';
    PCGDECK.searchItemName[44958]='スーパーエネルギー回収';
    PCGDECK.searchItemNameAlt[44958]='スーパーエネルギー回収';
    PCGDECK.searchItemCardPict[44958]='/assets/images/card_images/large/SV2D/044958_T_SUPAENERUGIKAISHIXYUU.jpg';
    PCGDECK.searchItemName[44955]='すごいつりざお';
    PCGDECK.searchItemNameAlt[44955]='すごいつりざお';
    PCGDECK.searchItemCardPict[44955]='/assets/images/card_images/large/SV2P/044955_T_SUGOITSURIZAO.jpg';
    PCGDECK.searchItemName[42695]='ピクニックバスケット';
    PCGDECK.searchItemNameAlt[42695]='ピクニックバスケット';
    PCGDECK.searchItemCardPict[42695]='/assets/images/card_images/large/SV1V/042695_T_PIKUNIKKUBASUKETTO.jpg';
    PCGDECK.searchItemName[46220]='プレシャスキャリー(ACE SPEC)';
    PCGDECK.searchItemNameAlt[46220]='プレシャスキャリー(ACE SPEC)';
    PCGDECK.searchItemCardPict[46220]='/assets/images/card_images/large/SVLN/046220_T_PURESHIXYASUKIXYARI.jpg';
    PCGDECK.searchItemName[48441]='ふうせん';
    PCGDECK.searchItemNameAlt[48441]='ふうせん';
    PCGDECK.searchItemCardPict[48441]='/assets/images/card_images/large/M1L/048441_T_FUUSEN.jpg';
    PCGDECK.searchItemName[42771]='げんきのハチマキ';
    PCGDECK.searchItemNameAlt[42771]='げんきのハチマキ';
    PCGDECK.searchItemCardPict[42771]='/assets/images/card_images/large/SVAW/042771_T_GENKINOHACHIMAKI.jpg';
    PCGDECK.searchItemName[43086]='ペパー';
    PCGDECK.searchItemNameAlt[43086]='ペパー';
    PCGDECK.searchItemCardPict[43086]='/assets/images/card_images/large/SV1V/043086_T_PEPA.jpg';
    PCGDECK.searchItemName[47526]='ロケット団のラムダ';
    PCGDECK.searchItemNameAlt[47526]='ロケット団のラムダ';
    PCGDECK.searchItemCardPict[47526]='/assets/images/card_images/large/SV10/047526_T_ROKETTODANNORAMUDA.jpg';
    PCGDECK.searchItemName[45562]='暗号マニアの解読';
    PCGDECK.searchItemNameAlt[45562]='暗号マニアの解読';
    PCGDECK.searchItemCardPict[45562]='/assets/images/card_images/large/SV5M/045562_T_ANGOUMANIANOKAIDOKU.jpg';
    PCGDECK.searchItemName[44465]='フトゥー博士のシナリオ';
    PCGDECK.searchItemNameAlt[44465]='フトゥー博士のシナリオ';
    PCGDECK.searchItemCardPict[44465]='/assets/images/card_images/large/SV4M/044465_T_FUTOUHAKASENOSHINARIO.jpg';
    PCGDECK.searchItemName[35737]='ジャッジマン';
    PCGDECK.searchItemNameAlt[35737]='ジャッジマン';
    PCGDECK.searchItemCardPict[35737]='/assets/images/card_images/large/SM7a/035737_T_JAJJIMAN.jpg';
    PCGDECK.searchItemName[43300]='ボスの指令';
    PCGDECK.searchItemNameAlt[43300]='ボスの指令';
    PCGDECK.searchItemCardPict[43300]='/assets/images/card_images/large/SV1a/043300_T_BOSUNOSHIREIGECHISU.jpg';
    PCGDECK.searchItemName[43036]='レッスンスタジオ';
    PCGDECK.searchItemNameAlt[43036]='レッスンスタジオ';
    PCGDECK.searchItemCardPict[43036]='/assets/images/card_images/large/SV1a/043036_T_RESSUNSUTAJIO.jpg';
    PCGDECK.searchItemName[42784]='基本闘エネルギー';
    PCGDECK.searchItemNameAlt[42784]='基本闘エネルギー';
    PCGDECK.searchItemCardPict[42784]='/assets/images/card_images/large/ENE/042784_E_KIHONTOUENERUGI.jpg';
    PCGDECK.searchItemName[42786]='基本鋼エネルギー';
    PCGDECK.searchItemNameAlt[42786]='基本鋼エネルギー';
    PCGDECK.searchItemCardPict[42786]='/assets/images/card_images/large/ENE/042786_E_KIHONHAGANEENERUGI.jpg';
    PCGDECK.viewItemMode=2;
    </script>
    """

    text = bs.find_all('script', attrs={"type": "", "src": ""})[-1]

    for item in str(text).strip().split(';'):
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

    if len(bs.find_all(id='inputArea')) != 1:
        count =len(bs.find_all(id='inputArea'))
        logger.exception(f"Unexpected 'inputArea' id count: expected = 1, actual = {count}")
        return JSONResponse(content={}, status_code=500)

    """
    <form id="inputArea" action="./deckRegister.php">
        <input type="hidden" name="deck_pke" id="deck_pke" value="44122_4_1-46253_4_1-47759_2_1-47760_2_1-44450_1_1-47988_1_1-46058_1_1" />
        <input type="hidden" name="deck_gds" id="deck_gds" value="45403_1_1-42616_2_1-48439_3_1-44306_3_1-46434_1_1-44958_4_1-44955_1_1-42695_1_1-46220_1_1" />
        <input type="hidden" name="deck_tool" id="deck_tool" value="48441_2_1-42771_1_1" />
        <input type="hidden" name="deck_tech" id="deck_tech" value="" />
        <input type="hidden" name="deck_sup" id="deck_sup" value="43086_4_1-47526_1_1-45562_1_1-44465_2_1-35737_1_1-43300_4_1" />
        <input type="hidden" name="deck_sta" id="deck_sta" value="43036_1_1" />
        <input type="hidden" name="deck_ene" id="deck_ene" value="42784_8_1-42786_3_1" />
        <input type="hidden" name="deck_ajs" id="deck_ajs" value="" />
        <input type="hidden" name="copyDeckID" id="copyDeckID" value="vv5kFf-8mYwSW-FVVVbw" />
    </form>
    """

    bs_input_area = BeautifulSoup(str(bs.find_all(id='inputArea')[0]), "html.parser")

    ret_dict = {}
    total_card_count = 0

    for item in bs_input_area.find_all('input'):
        if item['id'] == "deck_ajs" or item['id'] == "copyDeckID":
            continue

        deckcards = []
        card_count_dict = {}
        card_type_count = 0

        if item['value'] and item['id'] != "copyDeckID":
            result = {
                k: int(v)
                for k, v in (val.rsplit('_', 1)[0].split('_') for val in item['value'].split('-'))
            }
            card_count_dict.update(result)

        for card_id, count in card_count_dict.items():
            if item['id'] == "deck_pke":
                with conn.cursor() as cur:
                    ability = ""
                    attacks = []
                    sql = "SELECT ability, attack FROM pokemon_cards WHERE id = %s"
                    cur.execute(sql, (card_id,))
                    row = cur.fetchone()

                    if row is None:
                        logger.exception(f"Record not found: pokemon_cards.id={card_id}")
                        return JSONResponse(content={}, status_code=500)
                    else:
                        ability = row[0]
                        attacks = row[1].split('/')

                    cur.close()

                card_info = {
                    "card_id": int(card_id),
                    "card_name": str(card_name_dict[card_id]).replace("(ACE SPEC)", ""),
                    "card_count": count,
                    "detail_url": str("https://www.pokemon-card.com/card-search/details.php/card/" + str(card_id)),
                    "image_url": str("https://www.pokemon-card.com" + str(card_image_dict[card_id])),
                    "ability": ability,
                    "attacks": attacks,
                }

                deckcards.append(card_info)
                card_type_count += count
            else:
                card_info = {
                    "card_id": int(card_id),
                    "card_name": str(card_name_dict[card_id]).replace("(ACE SPEC)", ""),
                    "card_count": count,
                    "detail_url": str("https://www.pokemon-card.com/card-search/details.php/card/" + str(card_id)),
                    "image_url": str("https://www.pokemon-card.com" + str(card_image_dict[card_id])),
                }

                deckcards.append(card_info)
                card_type_count += count

        ret_dict.update({str(item['id']).replace("deck", "card"): deckcards, str(item['id']).replace("deck", "card")+"_count": card_type_count})
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
        logger.exception(f"Unexpected deck cards count: expected = 60, actual = {total_card_count}")
        return JSONResponse(content={}, status_code=500)

    return ret_dict


def create_v1beta_deckcards_list(conn, deck_code):
    try:
        logger.info(f"Request start: {url + deck_code}")

        res = requests.get(url + deck_code, timeout=3)
        res.raise_for_status()

        logger.info(f"Request succeeded: {url + deck_code} (status={res.status_code})")

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


    bs = BeautifulSoup(res.text, "html.parser")

    card_name_dict = {}
    card_image_dict = {}

    if len(bs.find_all('script', attrs={"type": "", "src": ""})) != 2:
        count = len(bs.find_all('script', attrs={"type": "", "src": ""}))
        logger.exception(f"Unexpected <script> tag count: expected = 2, actual = {count}")
        return JSONResponse(content={}, status_code=500)

    """
    <script>
    PCGDECK.searchItemName[44122]='サーフゴーex(SV3a 050/062)';
    PCGDECK.searchItemNameAlt[44122]='サーフゴーex';
    PCGDECK.searchItemCardPict[44122]='/assets/images/card_images/large/SV3a/044122_P_SAFUGOEX.jpg';
    PCGDECK.searchItemName[46253]='コレクレー(SV7a 024/064)';
    PCGDECK.searchItemNameAlt[46253]='コレクレー';
    PCGDECK.searchItemCardPict[46253]='/assets/images/card_images/large/SV7a/046253_P_KOREKURE.jpg';
    PCGDECK.searchItemName[47759]='ルナトーン(M1L 026/063)';
    PCGDECK.searchItemNameAlt[47759]='ルナトーン';
    PCGDECK.searchItemCardPict[47759]='/assets/images/card_images/large/M1L/047759_P_RUNATON.jpg';
    PCGDECK.searchItemName[47760]='ソルロック(M1L 027/063)';
    PCGDECK.searchItemNameAlt[47760]='ソルロック';
    PCGDECK.searchItemCardPict[47760]='/assets/images/card_images/large/M1L/047760_P_SORUROKKU.jpg';
    PCGDECK.searchItemName[44450]='テツノツツミ(SV4M 071/066)';
    PCGDECK.searchItemNameAlt[44450]='テツノツツミ';
    PCGDECK.searchItemCardPict[44450]='/assets/images/card_images/large/SV4M/044450_P_TETSUNOTSUTSUMI.jpg';
    PCGDECK.searchItemName[47988]='ゲノセクトex(SV11B 164/086)';
    PCGDECK.searchItemNameAlt[47988]='ゲノセクトex';
    PCGDECK.searchItemCardPict[47988]='/assets/images/card_images/large/SV11B/047988_P_GENOSEKUTOEX.jpg';
    PCGDECK.searchItemName[46058]='キチキギスex(SV6a 081/064)';
    PCGDECK.searchItemNameAlt[46058]='キチキギスex';
    PCGDECK.searchItemCardPict[46058]='/assets/images/card_images/large/SV6a/046058_P_KICHIKIGISUEX.jpg';
    PCGDECK.searchItemName[45403]='なかよしポフィン';
    PCGDECK.searchItemNameAlt[45403]='なかよしポフィン';
    PCGDECK.searchItemCardPict[45403]='/assets/images/card_images/large/SV-P/045403_T_NAKAYOSHIPOFUIN.jpg';
    PCGDECK.searchItemName[42616]='ネストボール';
    PCGDECK.searchItemNameAlt[42616]='ネストボール';
    PCGDECK.searchItemCardPict[42616]='/assets/images/card_images/large/SV1S/042616_T_NESUTOBORU.jpg';
    PCGDECK.searchItemName[48439]='ファイトゴング';
    PCGDECK.searchItemNameAlt[48439]='ファイトゴング';
    PCGDECK.searchItemCardPict[48439]='/assets/images/card_images/large/M1L/048439_T_FUAITOGONGU.jpg';
    PCGDECK.searchItemName[44306]='大地の器';
    PCGDECK.searchItemNameAlt[44306]='大地の器';
    PCGDECK.searchItemCardPict[44306]='/assets/images/card_images/large/SV4K/044306_T_DAICHINOUTSUWA.jpg';
    PCGDECK.searchItemName[46434]='推理セット';
    PCGDECK.searchItemNameAlt[46434]='推理セット';
    PCGDECK.searchItemCardPict[46434]='/assets/images/card_images/large/SV8/046434_T_SUIRISETTO.jpg';
    PCGDECK.searchItemName[44958]='スーパーエネルギー回収';
    PCGDECK.searchItemNameAlt[44958]='スーパーエネルギー回収';
    PCGDECK.searchItemCardPict[44958]='/assets/images/card_images/large/SV2D/044958_T_SUPAENERUGIKAISHIXYUU.jpg';
    PCGDECK.searchItemName[44955]='すごいつりざお';
    PCGDECK.searchItemNameAlt[44955]='すごいつりざお';
    PCGDECK.searchItemCardPict[44955]='/assets/images/card_images/large/SV2P/044955_T_SUGOITSURIZAO.jpg';
    PCGDECK.searchItemName[42695]='ピクニックバスケット';
    PCGDECK.searchItemNameAlt[42695]='ピクニックバスケット';
    PCGDECK.searchItemCardPict[42695]='/assets/images/card_images/large/SV1V/042695_T_PIKUNIKKUBASUKETTO.jpg';
    PCGDECK.searchItemName[46220]='プレシャスキャリー(ACE SPEC)';
    PCGDECK.searchItemNameAlt[46220]='プレシャスキャリー(ACE SPEC)';
    PCGDECK.searchItemCardPict[46220]='/assets/images/card_images/large/SVLN/046220_T_PURESHIXYASUKIXYARI.jpg';
    PCGDECK.searchItemName[48441]='ふうせん';
    PCGDECK.searchItemNameAlt[48441]='ふうせん';
    PCGDECK.searchItemCardPict[48441]='/assets/images/card_images/large/M1L/048441_T_FUUSEN.jpg';
    PCGDECK.searchItemName[42771]='げんきのハチマキ';
    PCGDECK.searchItemNameAlt[42771]='げんきのハチマキ';
    PCGDECK.searchItemCardPict[42771]='/assets/images/card_images/large/SVAW/042771_T_GENKINOHACHIMAKI.jpg';
    PCGDECK.searchItemName[43086]='ペパー';
    PCGDECK.searchItemNameAlt[43086]='ペパー';
    PCGDECK.searchItemCardPict[43086]='/assets/images/card_images/large/SV1V/043086_T_PEPA.jpg';
    PCGDECK.searchItemName[47526]='ロケット団のラムダ';
    PCGDECK.searchItemNameAlt[47526]='ロケット団のラムダ';
    PCGDECK.searchItemCardPict[47526]='/assets/images/card_images/large/SV10/047526_T_ROKETTODANNORAMUDA.jpg';
    PCGDECK.searchItemName[45562]='暗号マニアの解読';
    PCGDECK.searchItemNameAlt[45562]='暗号マニアの解読';
    PCGDECK.searchItemCardPict[45562]='/assets/images/card_images/large/SV5M/045562_T_ANGOUMANIANOKAIDOKU.jpg';
    PCGDECK.searchItemName[44465]='フトゥー博士のシナリオ';
    PCGDECK.searchItemNameAlt[44465]='フトゥー博士のシナリオ';
    PCGDECK.searchItemCardPict[44465]='/assets/images/card_images/large/SV4M/044465_T_FUTOUHAKASENOSHINARIO.jpg';
    PCGDECK.searchItemName[35737]='ジャッジマン';
    PCGDECK.searchItemNameAlt[35737]='ジャッジマン';
    PCGDECK.searchItemCardPict[35737]='/assets/images/card_images/large/SM7a/035737_T_JAJJIMAN.jpg';
    PCGDECK.searchItemName[43300]='ボスの指令';
    PCGDECK.searchItemNameAlt[43300]='ボスの指令';
    PCGDECK.searchItemCardPict[43300]='/assets/images/card_images/large/SV1a/043300_T_BOSUNOSHIREIGECHISU.jpg';
    PCGDECK.searchItemName[43036]='レッスンスタジオ';
    PCGDECK.searchItemNameAlt[43036]='レッスンスタジオ';
    PCGDECK.searchItemCardPict[43036]='/assets/images/card_images/large/SV1a/043036_T_RESSUNSUTAJIO.jpg';
    PCGDECK.searchItemName[42784]='基本闘エネルギー';
    PCGDECK.searchItemNameAlt[42784]='基本闘エネルギー';
    PCGDECK.searchItemCardPict[42784]='/assets/images/card_images/large/ENE/042784_E_KIHONTOUENERUGI.jpg';
    PCGDECK.searchItemName[42786]='基本鋼エネルギー';
    PCGDECK.searchItemNameAlt[42786]='基本鋼エネルギー';
    PCGDECK.searchItemCardPict[42786]='/assets/images/card_images/large/ENE/042786_E_KIHONHAGANEENERUGI.jpg';
    PCGDECK.viewItemMode=2;
    </script>
    """

    text = bs.find_all('script', attrs={"type": "", "src": ""})[-1]

    for item in str(text).strip().split(';'):
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

    if len(bs.find_all(id='inputArea')) != 1:
        count =len(bs.find_all(id='inputArea'))
        logger.exception(f"Unexpected 'inputArea' id count: expected = 1, actual = {count}")
        return JSONResponse(content={}, status_code=500)

    """
    <form id="inputArea" action="./deckRegister.php">
        <input type="hidden" name="deck_pke" id="deck_pke" value="44122_4_1-46253_4_1-47759_2_1-47760_2_1-44450_1_1-47988_1_1-46058_1_1" />
        <input type="hidden" name="deck_gds" id="deck_gds" value="45403_1_1-42616_2_1-48439_3_1-44306_3_1-46434_1_1-44958_4_1-44955_1_1-42695_1_1-46220_1_1" />
        <input type="hidden" name="deck_tool" id="deck_tool" value="48441_2_1-42771_1_1" />
        <input type="hidden" name="deck_tech" id="deck_tech" value="" />
        <input type="hidden" name="deck_sup" id="deck_sup" value="43086_4_1-47526_1_1-45562_1_1-44465_2_1-35737_1_1-43300_4_1" />
        <input type="hidden" name="deck_sta" id="deck_sta" value="43036_1_1" />
        <input type="hidden" name="deck_ene" id="deck_ene" value="42784_8_1-42786_3_1" />
        <input type="hidden" name="deck_ajs" id="deck_ajs" value="" />
        <input type="hidden" name="copyDeckID" id="copyDeckID" value="vv5kFf-8mYwSW-FVVVbw" />
    </form>
    """

    bs_input_area = BeautifulSoup(str(bs.find_all(id='inputArea')[0]), "html.parser")

    ret_list = []
    total_card_count = 0

    for item in bs_input_area.find_all('input'):
        if item['id'] == "deck_ajs" or item['id'] == "copyDeckID":
            continue

        deckcards = []
        card_count_dict = {}
        card_type_count = 0

        if item['value'] and item['id'] != "copyDeckID":
            result = {
                k: int(v)
                for k, v in (val.rsplit('_', 1)[0].split('_') for val in item['value'].split('-'))
            }
            card_count_dict.update(result)

        for card_id, count in card_count_dict.items():
            if item['id'] == "deck_pke":
                with conn.cursor() as cur:
                    ability = ""
                    attacks = []
                    sql = "SELECT ability, attack FROM pokemon_cards WHERE id = %s"
                    cur.execute(sql, (card_id,))
                    row = cur.fetchone()

                    if row is None:
                        logger.exception(f"Record not found: pokemon_cards.id={card_id}")
                        return JSONResponse(content={}, status_code=500)
                    else:
                        ability = row[0]
                        attacks = row[1].split('/')

                    cur.close()

                for i in range(count):
                    card_info = {
                        "card_id": int(card_id),
                        "card_name": str(card_name_dict[card_id]).replace("(ACE SPEC)", ""),
                        "detail_url": str("https://www.pokemon-card.com/card-search/details.php/card/" + str(card_id)),
                        "image_url": str("https://www.pokemon-card.com" + str(card_image_dict[card_id])),
                        "ability": ability,
                        "attacks": attacks,
                    }

                    deckcards.append(card_info)
                    card_type_count += 1
            else:
                for i in range(count):
                    card_info = {
                        "card_id": int(card_id),
                        "card_name": str(card_name_dict[card_id]).replace("(ACE SPEC)", ""),
                        "detail_url": str("https://www.pokemon-card.com/card-search/details.php/card/" + str(card_id)),
                        "image_url": str("https://www.pokemon-card.com" + str(card_image_dict[card_id])),
                    }

                    deckcards.append(card_info)
                    card_type_count += 1

        ret_list.extend(deckcards)
        total_card_count += card_type_count

    if total_card_count != 60:
        logger.exception(f"Unexpected deck cards count: expected = 60, actual = {total_card_count}")
        return JSONResponse(content={}, status_code=500)

    return ret_list


def create_v1beta_deckcards_summary(conn, deck_code):
    try:
        logger.info(f"Request start: {url + deck_code}")

        res = requests.get(url + deck_code, timeout=3)
        res.raise_for_status()

        logger.info(f"Request succeeded: {url + deck_code} (status={res.status_code})")

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


    bs = BeautifulSoup(res.text, "html.parser")

    card_name_dict = {}
    card_image_dict = {}

    if len(bs.find_all('script', attrs={"type": "", "src": ""})) != 2:
        count = len(bs.find_all('script', attrs={"type": "", "src": ""}))
        logger.exception(f"Unexpected <script> tag count: expected = 2, actual = {count}")
        return JSONResponse(content={}, status_code=500)

    """
    <script>
    PCGDECK.searchItemName[44122]='サーフゴーex(SV3a 050/062)';
    PCGDECK.searchItemNameAlt[44122]='サーフゴーex';
    PCGDECK.searchItemCardPict[44122]='/assets/images/card_images/large/SV3a/044122_P_SAFUGOEX.jpg';
    PCGDECK.searchItemName[46253]='コレクレー(SV7a 024/064)';
    PCGDECK.searchItemNameAlt[46253]='コレクレー';
    PCGDECK.searchItemCardPict[46253]='/assets/images/card_images/large/SV7a/046253_P_KOREKURE.jpg';
    PCGDECK.searchItemName[47759]='ルナトーン(M1L 026/063)';
    PCGDECK.searchItemNameAlt[47759]='ルナトーン';
    PCGDECK.searchItemCardPict[47759]='/assets/images/card_images/large/M1L/047759_P_RUNATON.jpg';
    PCGDECK.searchItemName[47760]='ソルロック(M1L 027/063)';
    PCGDECK.searchItemNameAlt[47760]='ソルロック';
    PCGDECK.searchItemCardPict[47760]='/assets/images/card_images/large/M1L/047760_P_SORUROKKU.jpg';
    PCGDECK.searchItemName[44450]='テツノツツミ(SV4M 071/066)';
    PCGDECK.searchItemNameAlt[44450]='テツノツツミ';
    PCGDECK.searchItemCardPict[44450]='/assets/images/card_images/large/SV4M/044450_P_TETSUNOTSUTSUMI.jpg';
    PCGDECK.searchItemName[47988]='ゲノセクトex(SV11B 164/086)';
    PCGDECK.searchItemNameAlt[47988]='ゲノセクトex';
    PCGDECK.searchItemCardPict[47988]='/assets/images/card_images/large/SV11B/047988_P_GENOSEKUTOEX.jpg';
    PCGDECK.searchItemName[46058]='キチキギスex(SV6a 081/064)';
    PCGDECK.searchItemNameAlt[46058]='キチキギスex';
    PCGDECK.searchItemCardPict[46058]='/assets/images/card_images/large/SV6a/046058_P_KICHIKIGISUEX.jpg';
    PCGDECK.searchItemName[45403]='なかよしポフィン';
    PCGDECK.searchItemNameAlt[45403]='なかよしポフィン';
    PCGDECK.searchItemCardPict[45403]='/assets/images/card_images/large/SV-P/045403_T_NAKAYOSHIPOFUIN.jpg';
    PCGDECK.searchItemName[42616]='ネストボール';
    PCGDECK.searchItemNameAlt[42616]='ネストボール';
    PCGDECK.searchItemCardPict[42616]='/assets/images/card_images/large/SV1S/042616_T_NESUTOBORU.jpg';
    PCGDECK.searchItemName[48439]='ファイトゴング';
    PCGDECK.searchItemNameAlt[48439]='ファイトゴング';
    PCGDECK.searchItemCardPict[48439]='/assets/images/card_images/large/M1L/048439_T_FUAITOGONGU.jpg';
    PCGDECK.searchItemName[44306]='大地の器';
    PCGDECK.searchItemNameAlt[44306]='大地の器';
    PCGDECK.searchItemCardPict[44306]='/assets/images/card_images/large/SV4K/044306_T_DAICHINOUTSUWA.jpg';
    PCGDECK.searchItemName[46434]='推理セット';
    PCGDECK.searchItemNameAlt[46434]='推理セット';
    PCGDECK.searchItemCardPict[46434]='/assets/images/card_images/large/SV8/046434_T_SUIRISETTO.jpg';
    PCGDECK.searchItemName[44958]='スーパーエネルギー回収';
    PCGDECK.searchItemNameAlt[44958]='スーパーエネルギー回収';
    PCGDECK.searchItemCardPict[44958]='/assets/images/card_images/large/SV2D/044958_T_SUPAENERUGIKAISHIXYUU.jpg';
    PCGDECK.searchItemName[44955]='すごいつりざお';
    PCGDECK.searchItemNameAlt[44955]='すごいつりざお';
    PCGDECK.searchItemCardPict[44955]='/assets/images/card_images/large/SV2P/044955_T_SUGOITSURIZAO.jpg';
    PCGDECK.searchItemName[42695]='ピクニックバスケット';
    PCGDECK.searchItemNameAlt[42695]='ピクニックバスケット';
    PCGDECK.searchItemCardPict[42695]='/assets/images/card_images/large/SV1V/042695_T_PIKUNIKKUBASUKETTO.jpg';
    PCGDECK.searchItemName[46220]='プレシャスキャリー(ACE SPEC)';
    PCGDECK.searchItemNameAlt[46220]='プレシャスキャリー(ACE SPEC)';
    PCGDECK.searchItemCardPict[46220]='/assets/images/card_images/large/SVLN/046220_T_PURESHIXYASUKIXYARI.jpg';
    PCGDECK.searchItemName[48441]='ふうせん';
    PCGDECK.searchItemNameAlt[48441]='ふうせん';
    PCGDECK.searchItemCardPict[48441]='/assets/images/card_images/large/M1L/048441_T_FUUSEN.jpg';
    PCGDECK.searchItemName[42771]='げんきのハチマキ';
    PCGDECK.searchItemNameAlt[42771]='げんきのハチマキ';
    PCGDECK.searchItemCardPict[42771]='/assets/images/card_images/large/SVAW/042771_T_GENKINOHACHIMAKI.jpg';
    PCGDECK.searchItemName[43086]='ペパー';
    PCGDECK.searchItemNameAlt[43086]='ペパー';
    PCGDECK.searchItemCardPict[43086]='/assets/images/card_images/large/SV1V/043086_T_PEPA.jpg';
    PCGDECK.searchItemName[47526]='ロケット団のラムダ';
    PCGDECK.searchItemNameAlt[47526]='ロケット団のラムダ';
    PCGDECK.searchItemCardPict[47526]='/assets/images/card_images/large/SV10/047526_T_ROKETTODANNORAMUDA.jpg';
    PCGDECK.searchItemName[45562]='暗号マニアの解読';
    PCGDECK.searchItemNameAlt[45562]='暗号マニアの解読';
    PCGDECK.searchItemCardPict[45562]='/assets/images/card_images/large/SV5M/045562_T_ANGOUMANIANOKAIDOKU.jpg';
    PCGDECK.searchItemName[44465]='フトゥー博士のシナリオ';
    PCGDECK.searchItemNameAlt[44465]='フトゥー博士のシナリオ';
    PCGDECK.searchItemCardPict[44465]='/assets/images/card_images/large/SV4M/044465_T_FUTOUHAKASENOSHINARIO.jpg';
    PCGDECK.searchItemName[35737]='ジャッジマン';
    PCGDECK.searchItemNameAlt[35737]='ジャッジマン';
    PCGDECK.searchItemCardPict[35737]='/assets/images/card_images/large/SM7a/035737_T_JAJJIMAN.jpg';
    PCGDECK.searchItemName[43300]='ボスの指令';
    PCGDECK.searchItemNameAlt[43300]='ボスの指令';
    PCGDECK.searchItemCardPict[43300]='/assets/images/card_images/large/SV1a/043300_T_BOSUNOSHIREIGECHISU.jpg';
    PCGDECK.searchItemName[43036]='レッスンスタジオ';
    PCGDECK.searchItemNameAlt[43036]='レッスンスタジオ';
    PCGDECK.searchItemCardPict[43036]='/assets/images/card_images/large/SV1a/043036_T_RESSUNSUTAJIO.jpg';
    PCGDECK.searchItemName[42784]='基本闘エネルギー';
    PCGDECK.searchItemNameAlt[42784]='基本闘エネルギー';
    PCGDECK.searchItemCardPict[42784]='/assets/images/card_images/large/ENE/042784_E_KIHONTOUENERUGI.jpg';
    PCGDECK.searchItemName[42786]='基本鋼エネルギー';
    PCGDECK.searchItemNameAlt[42786]='基本鋼エネルギー';
    PCGDECK.searchItemCardPict[42786]='/assets/images/card_images/large/ENE/042786_E_KIHONHAGANEENERUGI.jpg';
    PCGDECK.viewItemMode=2;
    </script>
    """

    text = bs.find_all('script', attrs={"type": "", "src": ""})[-1]

    for item in str(text).strip().split(';'):
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

    if len(bs.find_all(id='inputArea')) != 1:
        count =len(bs.find_all(id='inputArea'))
        logger.exception(f"Unexpected 'inputArea' id count: expected = 1, actual = {count}")
        return JSONResponse(content={}, status_code=500)

    """
    <form id="inputArea" action="./deckRegister.php">
        <input type="hidden" name="deck_pke" id="deck_pke" value="44122_4_1-46253_4_1-47759_2_1-47760_2_1-44450_1_1-47988_1_1-46058_1_1" />
        <input type="hidden" name="deck_gds" id="deck_gds" value="45403_1_1-42616_2_1-48439_3_1-44306_3_1-46434_1_1-44958_4_1-44955_1_1-42695_1_1-46220_1_1" />
        <input type="hidden" name="deck_tool" id="deck_tool" value="48441_2_1-42771_1_1" />
        <input type="hidden" name="deck_tech" id="deck_tech" value="" />
        <input type="hidden" name="deck_sup" id="deck_sup" value="43086_4_1-47526_1_1-45562_1_1-44465_2_1-35737_1_1-43300_4_1" />
        <input type="hidden" name="deck_sta" id="deck_sta" value="43036_1_1" />
        <input type="hidden" name="deck_ene" id="deck_ene" value="42784_8_1-42786_3_1" />
        <input type="hidden" name="deck_ajs" id="deck_ajs" value="" />
        <input type="hidden" name="copyDeckID" id="copyDeckID" value="vv5kFf-8mYwSW-FVVVbw" />
    </form>
    """

    bs_input_area = BeautifulSoup(str(bs.find_all(id='inputArea')[0]), "html.parser")

    ret_dict = {}
    total_card_count = 0

    for item in bs_input_area.find_all('input'):
        if item['id'] == "deck_ajs" or item['id'] == "copyDeckID":
            continue

        deckcards = []
        card_count_dict = {}
        card_type_count = 0

        if item['value'] and item['id'] != "copyDeckID":
            result = {
                k: int(v)
                for k, v in (val.rsplit('_', 1)[0].split('_') for val in item['value'].split('-'))
            }
            card_count_dict.update(result)

        for card_id, count in card_count_dict.items():
            if item['id'] == "deck_pke":
                with conn.cursor() as cur:
                    ability = ""
                    attacks = []
                    sql = "SELECT ability, attack FROM pokemon_cards WHERE id = %s"
                    cur.execute(sql, (card_id,))
                    row = cur.fetchone()

                    if row is None:
                        logger.exception(f"Record not found: pokemon_cards.id={card_id}")
                        return JSONResponse(content={}, status_code=500)
                    else:
                        ability = row[0]
                        attacks = row[1].split('/')

                    cur.close()

                card_info = {
                    "card_id": int(card_id),
                    "card_name": str(card_name_dict[card_id]).replace("(ACE SPEC)", ""),
                    "card_count": count,
                    "detail_url": str("https://www.pokemon-card.com/card-search/details.php/card/" + str(card_id)),
                    "image_url": str("https://www.pokemon-card.com" + str(card_image_dict[card_id])),
                    "ability": ability,
                    "attacks": attacks,
                }

                deckcards.append(card_info)
                card_type_count += count
            else:
                card_info = {
                    "card_id": int(card_id),
                    "card_name": str(card_name_dict[card_id]).replace("(ACE SPEC)", ""),
                    "card_count": count,
                    "detail_url": str("https://www.pokemon-card.com/card-search/details.php/card/" + str(card_id)),
                    "image_url": str("https://www.pokemon-card.com" + str(card_image_dict[card_id])),
                }

                deckcards.append(card_info)
                card_type_count += count

        if item['id'] == "deck_pke":
            result = OrderedDict()

            for card in deckcards:
                key = (
                    card.get("card_name"),
                    card.get("ability", ""),
                    tuple(sorted(card.get("attacks", [])))  # attacksは順不同
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


        ret_dict.update({str(item['id']).replace("deck", "card"): list(result.values()), str(item['id']).replace("deck", "card")+"_count": card_type_count})
        total_card_count += card_type_count

    if total_card_count != 60:
        logger.exception(f"Unexpected deck cards count: expected = 60, actual = {total_card_count}")
        return JSONResponse(content={}, status_code=500)

    return ret_dict



def find_acespec(deck_code):
    deckcards = create_deckcards(deck_code)

    for card in deckcards:
        if card["name"] in acespecs:
            card["name"] = card["name"].replace("(ACE SPEC)", "")
            del card["count"]
            return card

    return JSONResponse(content={}, status_code=204)



def create_v1beta_acespec(conn, deck_code):
    deckcards = create_v1beta_deckcards(conn, deck_code)

    for card in deckcards:
        if card["card_name"] in acespecs:
            card["card_name"] = card["card_name"].replace("(ACE SPEC)", "")
            del card["card_count"]
            return card

    return JSONResponse(content={}, status_code=204)



load_dotenv()

host = os.getenv("DB_HOSTNAME")
port = os.getenv("DB_PORT")
user = os.getenv("DB_USER_NAME")
password = os.getenv("DB_USER_PASSWORD")
dbname = os.getenv("DB_NAME")
dsn = "host={} port={} user={} password={} dbname={} sslmode=disable".format(host, port, user, password, dbname)

conn = psycopg2.connect(dsn)

app = FastAPI()


@app.get("/deckcards/{deck_code}")
def create_deckcards_app(deck_code):
    return create_deckcards(deck_code)

@app.get("/deckcards/{deck_code}/acespec")
def find_acespec_app(deck_code):
    return find_acespec(deck_code)

@app.get("/deckcards/{deck_code}/detail")
def create_deckcards_detail_app(deck_code):
    return create_deckcards_detail(conn, deck_code)


@app.get("/api/v1beta/deckcards/{deck_code}")
def create_v1beta_deckcards_app(deck_code):
    return create_v1beta_deckcards(conn, deck_code)

@app.get("/api/v1beta/deckcards/{deck_code}/acespec")
def create_v1beta_deckcards_acespec_app(deck_code):
    return create_v1beta_acespec(conn, deck_code)

@app.get("/api/v1beta/deckcards/{deck_code}/detail")
def create_v1beta_deckcards_detail_app(deck_code):
    return create_v1beta_deckcards_detail(conn, deck_code)

@app.get("/api/v1beta/deckcards/{deck_code}/list")
def create_v1beta_deckcards_list_app(deck_code):
    return create_v1beta_deckcards_list(conn, deck_code)

@app.get("/api/v1beta/deckcards/{deck_code}/summary")
def create_v1beta_deckcards_summary_app(deck_code):
    return create_v1beta_deckcards_summary(conn, deck_code)

@app.get("/health")
def health():
    return JSONResponse(content={}, status_code=200)