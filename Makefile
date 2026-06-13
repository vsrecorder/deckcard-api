SHELL := /bin/bash

.PHONY: install
install:
	poetry install

.PHONY: run
run: install
	poetry run python main.py

.PHONY: image
image:
	docker build -t vsrecorder/deckcard-api:latest . && docker push vsrecorder/deckcard-api:latest

.PHONY: deploy
deploy:
	docker compose pull && docker compose down && docker compose up -d

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