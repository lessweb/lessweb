.PHONY: install install-all lint-flake8 lint-mypy test lint test-all pyway-migrate pyway-env

install:
	pip install -e .

install-all:
	pip install -e ".[test]"

lint-flake8:
	flake8 src tests --count --ignore=E501,W293 --show-source --statistics

lint-mypy:
	mypy src shared

test:
	pytest tests --log-cli-level=DEBUG -v

define pyway-env
	@set -a && \
	if [ -n "$$ENV" ]; then \
		ENV_FILE=".env.$$ENV"; \
	else \
		ENV_FILE=".env"; \
	fi && \
	[ -f "$$ENV_FILE" ] && . "./$${ENV_FILE}" && set +a && \
	export PYWAY_DATABASE_HOST=$$MYSQL_HOST && \
	export PYWAY_DATABASE_PORT=$$MYSQL_PORT && \
	export PYWAY_DATABASE_USERNAME=$$MYSQL_USER && \
	export PYWAY_DATABASE_PASSWORD=$$MYSQL_PASSWORD && \
	export PYWAY_DATABASE_NAME=$$MYSQL_DB && \
	echo "Loading env from: $$ENV_FILE" && \
	echo "Connecting to: $$PYWAY_DATABASE_HOST:$$PYWAY_DATABASE_PORT as $$PYWAY_DATABASE_USERNAME"
endef

pyway-migrate:
	$(pyway-env) && \
	pyway migrate

lint: lint-flake8 lint-mypy

test-all: lint test

all: test-all
