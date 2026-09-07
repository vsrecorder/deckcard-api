"""デッキ結果ページのHTTP取得

キャッシュ配信元を優先的に参照し、404の場合は公式サイトへフォールバックする。
"""

import logging

import requests
from fastapi.responses import JSONResponse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.core.constants import BASE_URL, FALLBACK_URL

logger = logging.getLogger(__name__)

# 接続タイムアウト5秒 / 読み込みタイムアウト10秒
REQUEST_TIMEOUT = (5, 10)

# 一時的な失敗（接続エラー・5xx）に対するリトライ設定
# total=2 で最大2回まで再試行し、指数バックオフ（0.5s → 1.0s）で待機する
_retry = Retry(
    total=2,
    connect=2,
    read=2,
    status=2,
    backoff_factor=0.5,
    status_forcelist=(500, 502, 503, 504),
    allowed_methods=("GET",),
    raise_on_status=False,
)


# コネクションプールの本数。
#
# 未指定だと urllib3 の既定(10)になる。webapp のシティリーグ結果ページは1ページぶんの
# デッキコードをまとめて引きに来るため、この API には同時に十数本が届く。プールが尽きると
# urllib3 は「Connection pool is full」を出し、あぶれた接続は再利用されずに毎回
# TLS ハンドシェイクからやり直しになる(本番ログでも実際に発生していた)。
#
# ワーカーごとに1つの Session を共有するので、gunicorn のワーカー数ではなく
# 「1ワーカーが同時に抱えうる本数」で決める。呼び出し側の同時実行数(16)に余裕を持たせた値。
POOL_SIZE = 32


def _build_session():
    """リトライ設定を適用した requests.Session を生成する。"""
    session = requests.Session()
    adapter = HTTPAdapter(
        max_retries=_retry,
        pool_connections=POOL_SIZE,
        pool_maxsize=POOL_SIZE,
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


# モジュールロード時に1つのSessionを生成して使い回す（コネクションプールを共有）
_session = _build_session()


def fetch_deck_html(deck_code):
    """デッキコードからデッキ結果ページのHTMLレスポンスを取得する。

    Returns:
        requests.Response: 取得成功時のレスポンス。
        JSONResponse: 取得失敗時のエラーレスポンス。呼び出し側は
            ``isinstance(res, JSONResponse)`` で失敗を判定する。
    """
    try:
        logger.info(f"Request start: {BASE_URL + deck_code}")

        res = _session.get(BASE_URL + deck_code, timeout=REQUEST_TIMEOUT)

        if res.status_code == 404:
            logger.info(
                f"Request failed: {BASE_URL + deck_code} (status={res.status_code})"
            )

            try:
                logger.warning(f"Not Found (404): {BASE_URL + deck_code}")

                logger.info(f"Request start: {FALLBACK_URL + deck_code}")

                res = _session.get(FALLBACK_URL + deck_code, timeout=REQUEST_TIMEOUT)

                res.raise_for_status()

                logger.info(
                    f"Request succeeded: {FALLBACK_URL + deck_code} (status={res.status_code})"
                )

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout occurred: {FALLBACK_URL + deck_code}")
                return JSONResponse(content={}, status_code=504)

            except requests.exceptions.HTTPError as e:
                status = getattr(e.response, "status_code", 500)
                logger.error(
                    f"HTTPError: {FALLBACK_URL + deck_code} -> status {status}"
                )
                return JSONResponse(content={}, status_code=status)

            except requests.exceptions.ConnectionError as e:
                logger.error(f"ConnectionError: {FALLBACK_URL + deck_code} -> {e}")
                return JSONResponse(content={}, status_code=500)

            except requests.exceptions.RequestException as e:
                logger.exception(
                    f"Unexpected RequestException: {FALLBACK_URL + deck_code} -> {e}"
                )
                return JSONResponse(content={}, status_code=500)

        else:
            res.raise_for_status()

            logger.info(
                f"Request succeeded: {BASE_URL + deck_code} (status={res.status_code})"
            )

    except requests.exceptions.Timeout:
        logger.warning(f"Timeout occurred: {BASE_URL + deck_code}")
        return JSONResponse(content={}, status_code=504)

    except requests.exceptions.HTTPError as e:
        status = getattr(e.response, "status_code", 500)
        logger.error(f"HTTPError: {BASE_URL + deck_code} -> status {status}")
        return JSONResponse(content={}, status_code=status)

    except requests.exceptions.ConnectionError as e:
        logger.error(f"ConnectionError: {BASE_URL + deck_code} -> {e}")
        return JSONResponse(content={}, status_code=500)

    except requests.exceptions.RequestException as e:
        logger.exception(f"Unexpected RequestException: {BASE_URL + deck_code} -> {e}")
        return JSONResponse(content={}, status_code=500)

    return res
