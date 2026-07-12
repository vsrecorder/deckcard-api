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


# ACE SPECカードの一覧（表記ゆれ対応で通常表記と "(ACE SPEC)" 付きの両方を保持）
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
