"""共通の例外定義"""


class DeckError(Exception):
    """デッキ解析処理中のエラー。

    HTTPレスポンスに変換するためのステータスコードとボディを保持する。
    サービス層でキャッチして ``JSONResponse`` に変換する。
    """

    def __init__(self, status_code=500, content=None):
        self.status_code = status_code
        self.content = {} if content is None else content
        super().__init__(f"DeckError(status_code={status_code})")
