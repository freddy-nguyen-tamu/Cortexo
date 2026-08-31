SHELL := /bin/bash

.PHONY: tree core-db research-db python-install python-api java-run web-vue web-run check-dirs clean

tree:
	python3 scripts/create_tree.py

core-db:
	docker compose -f docker-compose.core.yml up -d

research-db:
	docker compose -f docker-compose.research.yml up -d

python-install:
	cd ml && python -m venv .venv && . .venv/bin/activate && pip install --upgrade pip && pip install -e . && pip install -r requirements.txt

python-api:
	cd ml && .venv/bin/uvicorn cortexo_ml.api.main:app --reload --port 8000

java-run:
	cd apps/api-spring && ./mvnw spring-boot:run

web-vue:
	cd apps/web-vue && npm install && npm run dev

check-dirs:
	python3 scripts/create_tree.py

clean:
	rm -rf ml/.venv ml/.pytest_cache apps/web-vue/node_modules apps/web-vue/dist apps/api-spring/target