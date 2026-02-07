SHELL := /bin/bash

.PHONY: docker-build-and-push
docker-build-and-push:
	docker build -t vsrecorder/deckcard-api:latest . && docker push vsrecorder/deckcard-api:latest

.PHONY: deploy
deploy:
	docker compose pull && docker compose down && docker compose up -d

.PHONY: restart
restart:
	docker compose down && docker compose up -d

.PHONY: source
source:
	fish -C "source .venv/bin/activate.fish"

.PHONY: run
run:
	uvicorn main:app --host 0.0.0.0 --port 8080

