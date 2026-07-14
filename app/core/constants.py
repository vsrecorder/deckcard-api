"""定数とURL組み立てヘルパー"""

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
