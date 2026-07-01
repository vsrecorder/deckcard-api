SHELL := /bin/bash

.PHONY: install
install:
	poetry install

.PHONY: run
run: install
	poetry run gunicorn main:app \
	-k uvicorn.workers.UvicornWorker \
	-w 1 \
	-b 0.0.0.0:8080 \
	--timeout 60

.PHONY: image
image:
	docker build -t vsrecorder/deckcard-api:latest .
	docker push     vsrecorder/deckcard-api:latest

.PHONY: deploy
deploy:
	git pull
	docker compose pull
	docker compose up -d --no-deps --wait deckcard-api

.PHONY: restart
restart:
	docker compose down && docker compose up -d

.PHONY: up
up:
	docker compose up

.PHONY: down
down:
	docker compose down

.PHONY: log
log:
	docker logs -f deckcard-api-deckcard-api-1
