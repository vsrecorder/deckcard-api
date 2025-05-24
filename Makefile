.PHONY: docker-build
docker-build-and-push:
	sudo docker build --no-cache -t vsrecorder/deckcard-api:latest . && sudo docker push vsrecorder/deckcard-api:latest

.PHONY: deploy
deploy:
	docker compose pull && docker compose down && docker compose up -d
