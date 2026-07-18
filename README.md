# deckcard-api

ポケモンカードゲームの**デッキコード**から、そのデッキに含まれるカード情報（カード名・枚数・画像・詳細URL・特性・ワザなど）を取得して JSON で返す API サーバです。

対戦記録サービス [vsrecorder](../CLAUDE.md) の一部として、デッキ登録機能を支える役割を担います。

## 何をしているか

ポケモンカード公式サイトで発行される**デッキコード**を受け取り、以下の流れでデッキの中身を解析して返します。

1. デッキコードを使って、デッキ結果ページの HTML を取得する（`app/scraping/fetcher.py`）
   - まずキャッシュ配信元（WebAccel）を参照し、404 の場合のみ公式サイトへフォールバックする
   - タイムアウト・リトライ（指数バックオフ・5xx 再試行）・コネクションプールを備える
2. 取得した HTML を解析し、カード名・カード画像・カード枚数を抽出する（`app/scraping/parser.py`）
   - ページ内の `<script>` から `searchItemNameAlt` / `searchItemCardPict` を正規表現で取り出す
   - `inputArea` 内の `<input>` の value からカードIDと枚数を復元する
3. ポケモンカードについては、DB（PostgreSQL の `pokemon_cards` テーブル）から**特性・ワザ**を補完する（`app/core/db.py`）
   - `WHERE id = ANY(...)` で一括取得し、N+1 クエリを回避
   - マスタデータはアプリ内キャッシュ（24時間 TTL）で再利用
4. エンドポイントごとに整形して JSON レスポンスを返す（`app/services.py`）
   - 合計枚数が 60 枚でない場合は異常とみなし 500 を返す
   - 結果はエンドポイント単位でメモリキャッシュ（LRU / LFU）する

## API エンドポイント

`{deck_code}` にデッキコードを指定します。

> **旧形式（`/deckcards/*`、公開パス `/api/v1/deckcards/*`）は廃止しました。** 以下の v1beta 形式へ移行してください。

### v1beta 形式

| メソッド | パス | 内容 |
| --- | --- | --- |
| GET | `/api/v1beta/deckcards/{deck_code}` | カード一覧（`card_id` / `card_name` などのキー名） |
| GET | `/api/v1beta/deckcards/{deck_code}/acespec` | ACE SPEC カードを1枚返す |
| GET | `/api/v1beta/deckcards/{deck_code}/detail` | 種別ごとに分類し、特性・ワザと ACE SPEC 情報を付与 |
| GET | `/api/v1beta/deckcards/{deck_code}/list` | 枚数分だけカードを展開したリスト（1枚=1要素） |
| GET | `/api/v1beta/deckcards/{deck_code}/summary` | 同一カード（ポケモンは特性・ワザ一致まで判定）を集約したリスト |

### その他

| メソッド | パス | 内容 |
| --- | --- | --- |
| GET | `/health` | ヘルスチェック（常に 200） |

## 技術スタック

- **言語 / フレームワーク**: Python 3.11 / [FastAPI](https://fastapi.tiangolo.com/)
- **HTML 解析**: BeautifulSoup4
- **HTTP クライアント**: requests（リトライ・タイムアウト設定あり）
- **データベース**: PostgreSQL（psycopg 3 + コネクションプール）
- **キャッシュ**: cachetools（LRU / LFU / TTL）
- **サーバ**: gunicorn + uvicorn worker
- **依存管理**: Poetry

## ディレクトリ構成

```
deckcard-api/
├── main.py                  エントリポイント（main:app を公開）
├── app/
│   ├── api.py               FastAPI ルーティング（キャッシュ参照のみ）
│   ├── services.py          各エンドポイントのレスポンス整形（サービス層）
│   ├── scraping/
│   │   ├── fetcher.py       デッキ結果ページの HTTP 取得
│   │   └── parser.py        HTML パース
│   └── core/
│       ├── constants.py     URL 定義・ACE SPEC 一覧・URL 組み立て
│       ├── db.py            PostgreSQL 接続とカード情報照会
│       ├── cache.py         レスポンスキャッシュ定義
│       └── errors.py        共通例外（DeckError）
├── Dockerfile
├── docker-compose.yml
├── Makefile
└── pyproject.toml
```

## セットアップと起動

### 環境変数

`.env.sample` を参考に `.env` を作成し、DB 接続情報を設定します。

```
DB_HOSTNAME=
DB_PORT=
DB_USER_NAME=
DB_USER_PASSWORD=
DB_NAME=
```

### ローカル起動

```bash
make install   # 依存インストール（poetry install）
make run       # gunicorn + uvicorn worker で 0.0.0.0:8080 に起動
```

### Docker で起動

```bash
make image-local   # ローカルイメージをビルド
make up            # docker compose up
make down          # 停止
make log           # ログ追跡
```

本番デプロイは `make deploy`（git pull → イメージ pull → compose up）で行います。

## 動作イメージ

```bash
curl http://localhost:8080/api/v1beta/deckcards/{deck_code}/summary
```

デッキコードに対応する 60 枚のカード情報が、種別ごとに集約された JSON で返ります。
