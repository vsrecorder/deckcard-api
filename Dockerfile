#
# 3.11 系はセキュリティ修正だけが出る期間に入っているため、パッチ版はすべてセキュリティリリース。
# 3.11.14 のまま据え置くと、その後の修正(3.11.15〜)が入らない。
#
FROM python:3.15.0-slim

RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry

WORKDIR /app

COPY pyproject.toml poetry.lock* ./

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --without dev

COPY . .

#
# 待ち受けはループバックに限定する。
#
# docker-compose.yml は network_mode: host で動かすため、compose の ports は効かず、
# ここで決めたアドレスがそのままホストの待ち受けになる。以前の 0.0.0.0 では、クラウド側の
# パケットフィルタの設定ひとつで nginx の流量制限・fail2ban・アクセスログを通らずに外から
# 直接叩ける状態だった(2026-10-31 の精査で指摘)。nginx は 127.0.0.1:8080 へ proxy_pass し、
# healthcheck も 127.0.0.1 を叩くので、ループバックだけで足りる。
#
CMD ["gunicorn", "main:app", \
    "-k", "uvicorn.workers.UvicornWorker", \
    "-w", "2", \
    "-b", "127.0.0.1:8080", \
    "--timeout", "60"]