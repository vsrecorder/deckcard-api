SHELL := /bin/bash

.PHONY: docker-build-and-push
docker-build-and-push:
	docker build -t vsrecorder/deckcard-api:latest . && docker push vsrecorder/deckcard-api:latest

.PHONY: source
source:
	fish -C "source .venv/bin/activate.fish"

.PHONY: run
run:
	fish -C "source .venv/bin/activate.fish; uvicorn main:app --host 0.0.0.0 --port 8080"


.PHONY: deploy
deploy:
	docker compose pull && docker compose down && docker compose up -d

.PHONY: restart
restart:
	docker compose down && docker compose up -d

.PHONY: up
up:
	docker compose up -d

.PHONY: down
down:
	docker compose down
