.PHONY: docker-build
docker-build:
	sudo docker build --no-cache -t vsrecorder/deckcard-api:latest .

.PHONY: docker-push
docker-push:
	sudo docker push vsrecorder/deckcard-api:latest

.PHONY: deploy
deploy:
	docker compose pull && docker compose down && docker compose up -d
