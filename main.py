from fastapi import FastAPI
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


def create_deckcard_list(deck_code):
    driver.get(url + deck_code)

    page_source_html = driver.page_source
    bs = BeautifulSoup(page_source_html, "html.parser")

    card_image_view_html = str(bs.find_all(id='cardImagesView')[0])
    bs = BeautifulSoup(card_image_view_html, "html.parser")

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
