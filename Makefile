# MIT License

project_name := vrt-bridge
project_version := $(shell git describe --tags --always)

image_url := $(project_name)
dev_image_url := $(image_url)-dev

working_directory := /workspace/app

image: ## Build production image
	docker build \
		--build-arg="USER_UID=$(shell id -u)" \
		--build-arg="USER_GID=$(shell id -g)" \
		--target=prod \
		--tag=$(image_url):$(project_version) \
		--tag=$(image_url) \
		.
.PHONY: image

dev-image: ## Build development image
	docker build \
		--build-arg="USER_UID=$(shell id -u)" \
		--build-arg="USER_GID=$(shell id -g)" \
		--target=dev \
		--tag=$(dev_image_url):$(project_version) \
		--tag=$(dev_image_url) \
		.
.PHONY: dev-image

run: image ## Run container
	docker run \
		--name=$(project_name) \
		-it \
		--rm \
		$(image_url):$(project_version)
.PHONY: run

dev: dev-image ## Run development environment
	docker run \
		--name=$(project_name)-dev \
		-it \
		--rm \
		--publish=8080:8080 \
		--volume="$(CURDIR):/workspace" \
		--workdir="$(working_directory)" \
		$(dev_image_url):$(project_version) \
		/bin/zsh
.PHONY: dev

test: dev-image ## Run tests
	docker run \
		--name=$(project_name) \
		-it \
		--rm \
		--volume="$(CURDIR):/workspace" \
		--workdir="$(working_directory)" \
		$(dev_image_url):$(project_version) \
		/bin/bash -c "python -m pytest -vx --cov=."
.PHONY: test

clean: ## Clean repository
	find . -type f -name ".coverage" -exec rm -rf {} +
	find . -type d -name "dist" -exec rm -rf {} +
	find . -type d -name "build" -exec rm -rf {} +
	find . -type d -name "venv" -exec rm -rf {} +
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
.PHONY: clean

reset: ## Reset repository
	git clean -xdf || true
.PHONY: reset

help: ## Show help
	@grep -E '^[0-9a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
.PHONY: help

.EXPORT_ALL_VARIABLES:
DOCKER_BUILDKIT = 1
COMPOSE_DOCKER_CLI_BUILD = 1

.DEFAULT_GOAL := help
