from fastapi import FastAPI, HTTPException
from selenium import webdriver 
from bs4 import BeautifulSoup

url = "https://www.pokemon-card.com/deck/result.html/deckID/"
driver_path = "/usr/local/bin/chromedriver-linux64/chromedriver"
service = webdriver.chrome.service.Service(executable_path=driver_path)

options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(service=service, options=options)
driver.set_window_size(950, 800)


acespecs = [
    "ポケモン回収サイクロン",
    "スクランブルスイッチ",
    "マスターボール",
    "ヒーローマント",
    "リブートポッド",
    "プライムキャッチャー",
    "ネオアッパーエネルギー",
    "マキシマムベルト",
    "覚醒のドラム",
    "サバイブギプス",
    "ハイパーアロマ",
    "アンフェアスタンプ",
    "レガシーエネルギー",
    "シークレットボックス",
    "ニュートラルセンター",
    "ポケバイタルA",
    "デンジャラス光線",
    "偉大な大樹",
    "デラックスボム",
    "きらめく結晶",
    "パーフェクトミキサー",
    "プレシャスキャリー",
    "リッチエネルギー",
    "メガトンブロアー",
    "エネルギー転送PRO",
    "希望のアミュレット",
    "ミラクルインカム",
    "トレジャーガジェット",
    "つりざおMAX",
]

def find_acespec(deck_code):
    list = create_deckcard_list(deck_code)


    for card in list:
        if card["name"] in acespecs:
            return card

    raise HTTPException(status_code=404)


def create_deckcard_list(deck_code):
    driver.get(url + deck_code)

    bs = BeautifulSoup(driver.page_source, "html.parser")
    
    if len(bs.find_all(id='cardImagesView')) == 1:
        bs = BeautifulSoup(str(bs.find_all(id='cardImagesView')[0]), "html.parser")
    else:
        bs = BeautifulSoup(str(bs.find_all(id='cardImagesView')), "html.parser")

    card_list = []
    for item in bs.find_all(class_="Grid_item"):
        bs = BeautifulSoup(str(item), "html.parser")
        bs = BeautifulSoup(str(bs.table), "html.parser")
        counter = 0
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