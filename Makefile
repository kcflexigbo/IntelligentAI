SHELL := /bin/bash

.PHONY: docker-up
docker-up:
	@echo "Building and starting containers..."
	docker compose up --build -d --wait
	@echo "Services are up and running."

.PHONY: docker-down
docker-down:
	@echo "Stopping and cleaning up containers..."
	docker compose down -v
	@echo "Cleanup complete."

.PHONY: logs
logs:
	docker compose logs -f

.PHONY: help
help:
	@echo "Makefile commands:"
	@echo "  docker-up     - Build and start Docker containers"
	@echo "  docker-down   - Stop and clean up Docker containers"
	@echo "  help          - Show this help message"