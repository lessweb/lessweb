.PHONY: lint-flake8 lint-mypy test lint test-all pyway-init pyway-migrate dump-openapi

lint-flake8:
	flake8 src shared tests main.py --count --show-source --statistics --extend-ignore=E501,W293

lint-mypy:
	mypy src shared main.py

test:
	pytest tests --log-cli-level=DEBUG -v

pyway-init:
	python main.py pyway-init $(SCHEMA_FILE)

pyway-migrate:
	python main.py pyway-migrate

dump-openapi:
	python main.py dump-openapi

lint: lint-flake8 lint-mypy

test-all: lint test

clear-log:
	rm -f logs/*.log
	rm -f logs/*.log.*

all: test-all
