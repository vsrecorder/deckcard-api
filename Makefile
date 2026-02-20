SHELL := /bin/bash

.PHONY: source
source:
	fish -C "source .venv/bin/activate.fish; pip install -r requirements.txt"

.PHONY: run
run:
	fish -C "source .venv/bin/activate.fish; pip install -r requirements.txt; uvicorn main:app --host 0.0.0.0 --port 8080"



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
	docker compose up -d

.PHONY: down
down:
	docker compose down

.PHONY: log
log:
	docker logs -f deckcard-api-deckcard-api-1
