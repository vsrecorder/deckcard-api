"""FastAPIアプリケーションとルーティング

ルーティングとキャッシュ参照のみを担い、実処理は services モジュールへ委譲する。
"""

import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.core.cache import (
    acespec_cache,
    deck_list_cache,
    deck_summary_cache,
    deckcards_cache,
)
from app.services import (
    create_deckcards,
    create_deckcards_detail,
    create_v1beta_acespec,
    create_v1beta_deckcards,
    create_v1beta_deckcards_detail,
    create_v1beta_deckcards_list,
    create_v1beta_deckcards_summary,
    find_acespec,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI()


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
