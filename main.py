from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from selenium import webdriver 
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from bs4 import BeautifulSoup

url = "https://www.pokemon-card.com/deck/result.html/deckID/"
driver_path = "/usr/local/bin/chromedriver-linux64/chromedriver"
service = webdriver.chrome.service.Service(executable_path=driver_path)

options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

# プロセス数削減のための追加フラグ
options.add_argument("--single-process")
options.add_argument("--disable-site-isolation-trials")
options.add_argument("--disable-gpu")
options.add_argument("--no-zygote")

driver = webdriver.Chrome(service=service, options=options)
driver.set_window_size(950, 800)


acespecs = [
    "ポケモン回収サイクロン(ACE SPEC)",
    "スクランブルスイッチ(ACE SPEC)",
    "マスターボール(ACE SPEC)",
    "ヒーローマント(ACE SPEC)",
    "リブートポッド(ACE SPEC)",
    "プライムキャッチャー(ACE SPEC)",
    "ネオアッパーエネルギー(ACE SPEC)",
    "マキシマムベルト(ACE SPEC)",
    "覚醒のドラム(ACE SPEC)",
    "サバイブギプス(ACE SPEC)",
    "ハイパーアロマ(ACE SPEC)",
    "アンフェアスタンプ(ACE SPEC)",
    "レガシーエネルギー(ACE SPEC)",
    "シークレットボックス(ACE SPEC)",
    "ニュートラルセンター(ACE SPEC)",
    "ポケバイタルA(ACE SPEC)",
    "デンジャラス光線(ACE SPEC)",
    "偉大な大樹(ACE SPEC)",
    "デラックスボム(ACE SPEC)",
    "きらめく結晶(ACE SPEC)",
    "パーフェクトミキサー(ACE SPEC)",
    "プレシャスキャリー(ACE SPEC)",
    "リッチエネルギー(ACE SPEC)",
    "メガトンブロアー(ACE SPEC)",
    "エネルギー転送PRO(ACE SPEC)",
    "希望のアミュレット(ACE SPEC)",
    "ミラクルインカム(ACE SPEC)",
    "トレジャーガジェット(ACE SPEC)",
    "つりざおMAX(ACE SPEC)",
]


def find_acespec(deck_code):
    list = create_deckcard_list(deck_code)

    for card in list:
        if card["name"] in acespecs:
            return card

    return JSONResponse(content={}, status_code=200)


def create_deckcard_list(deck_code):
    driver.get(url + deck_code)

    # ページ読み込み待機：https://selenium-python.readthedocs.io/waits.html
    try:
        WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.ID, "cardImagesView"))
        )
    except TimeoutException:
        raise HTTPException(status_code=500)

    bs = BeautifulSoup(driver.page_source, "html.parser")

    if len(bs.find_all(id='cardImagesView')) == 1:
        bs = BeautifulSoup(str(bs.find_all(id='cardImagesView')[0]), "html.parser")
    else:
        bs = BeautifulSoup(str(bs.find_all(id='cardImagesView')), "html.parser")

    card_list = []
    for item in bs.find_all(class_="Grid_item"):
        bs = BeautifulSoup(str(item), "html.parser")
        bs = BeautifulSoup(str(bs.table), "html.parser")

        it = iter(bs.find_all("tr"))
        for tr_tag_1, tr_tag_2 in zip(it, it):
            bs = BeautifulSoup(str(tr_tag_1), "html.parser")
            img_tag = bs.find("img")
            card_info = {
                "name": str(img_tag.get("alt")),
                "detail_url": str("https://www.pokemon-card.com/card-search/details.php/card/" + ((str(img_tag.get("src")).split('/'))[6].split('_'))[0]),
                "image_url": str("https://www.pokemon-card.com" + str(img_tag.get("src"))),
                "count": int(tr_tag_2.text[:-1]),
            }
            card_list.append(card_info)

    return card_list



app = FastAPI()

@app.get("/deckcards/{deck_code}")
async def read_item(deck_code):
    return create_deckcard_list(deck_code)

@app.get("/deckcards/{deck_code}/acespec")
async def read_item(deck_code):
    return find_acespec(deck_code)