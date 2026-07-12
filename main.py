"""エントリポイント

gunicorn / uvicorn は ``main:app`` を参照する。実体は app.api に定義する。
"""

from app.api import app

__all__ = ["app"]
