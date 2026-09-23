"""定数とURL組み立てヘルパー"""

import re

# デッキ結果ページの取得元URL（キャッシュ配信）
BASE_URL = "https://xx8nnpgt.user.webaccel.jp/deck-result_html/"

# 404時のフォールバック先（公式サイト）
FALLBACK_URL = "https://www.pokemon-card.com/deck/result.html/deckID/"

# カード詳細ページのURLプレフィックス
CARD_DETAIL_URL_PREFIX = "https://www.pokemon-card.com/card-search/details.php/card/"

# カード画像のURLプレフィックス
CARD_IMAGE_URL_PREFIX = "https://www.pokemon-card.com"


def card_detail_url(card_id):
    """カードIDから詳細ページURLを組み立てる"""
    return CARD_DETAIL_URL_PREFIX + str(card_id)


def card_image_url(image_path):
    """画像パスから画像URLを組み立てる"""
    return CARD_IMAGE_URL_PREFIX + str(image_path)


# ACE SPECカードの目印。cardsテーブルのカード名には必ず付与されている。
#
# 注意: デッキ結果ページ側のカード名にはこの目印が付かないことがある
# （例: リッチエネルギーはACE SPECだが 'リッチエネルギー' としか書かれていない）。
# そのためACE SPECかどうかの判定にページ側のカード名を使ってはならず、
# マスタ側を情報源とする :func:`app.core.db.fetch_acespec_ids` を使うこと。
# ここでは表示名から目印を落とす用途にのみ使う。
ACESPEC_SUFFIX = "(ACE SPEC)"


def strip_acespec(card_name):
    """カード名から "(ACE SPEC)" の目印を取り除く"""
    return str(card_name).replace(ACESPEC_SUFFIX, "")


# デッキコードとして受け付ける書式。公式のデッキコードは英数字とハイフンのみ。
# core-apiserver の entity.deckCodePattern (^[0-9A-Za-z-]+$) と揃える。
#
# 検証せずに URL へ連結すると、".." のような値で requests がパスを正規化し、
# 同一ホスト(配信元CDN・公式サイト)の別パスを取りに行かせられる。書式外は取得前に弾く。
DECK_CODE_PATTERN = re.compile(r"[0-9A-Za-z-]+")


def is_valid_deck_code(deck_code):
    """デッキコードが受け付けられる書式（英数字とハイフンのみ）か判定する。"""
    return isinstance(deck_code, str) and DECK_CODE_PATTERN.fullmatch(deck_code) is not None


def split_attacks(attack):
    """``pokemon_cards.attack``（"/" 区切り）をワザ名のリストにする。

    ワザを持たないポケモン（特性だけのカード）は空リストにする。
    ``"".split("/")`` は ``[""]`` を返すため、そのまま返すと「名前の無いワザが
    1 つある」ことになり、レスポンスの利用側と食い違う。

    実際に起きたこと(2026-09-23): メタモン(card_id=42378, ability='いきなりへんげ'、
    ワザ無し)で ``attacks: [""]`` を返していた。取り込みバッチ側のカードマスタは
    空リストにしているため、同じカードなのに毎回「値が違う」と判定され、
    114 デッキぶんの書き戻しが繰り返し発生していた。
    """
    if not attack or not attack.strip():
        return []
    return attack.split("/")
