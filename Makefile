# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Trend Signals: install, test, run locally, deploy, register.
# Offline targets need no cloud access. Cloud targets read .env (copy .env.example).

SHELL := /bin/bash
-include .env
export

REGION ?= us-central1
PROJECT_ID := $(GOOGLE_CLOUD_PROJECT)
GC = gcloud --project $(PROJECT_ID)

.PHONY: help install frontend-build fixture lint test check gallery run screenshots \
        require-project enable-apis deploy register register-dry list-ge url smoke

help:
	@echo "Offline:  install  frontend-build  lint  test  check  gallery  run  screenshots"
	@echo "Cloud:    enable-apis  deploy  register-dry  register  list-ge  url  smoke"

# ---- offline -------------------------------------------------------------------------
install:
	uv sync
	cd frontend && npm ci

frontend/dist/index.html: $(shell find frontend/src -type f) frontend/index.html frontend/package.json
	cd frontend && npm run build

frontend-build: frontend/dist/index.html

fixture:                     ## regenerate the gallery fixture from the Python dataset
	uv run python scripts/export_fixture.py

lint:
	uv run ruff check . --select F,E9

test: frontend-build
	uv run pytest -q

check: lint test

gallery:                     ## the workspace page on :5173 with the illustrative data, no agent needed
	cd frontend && npm run dev

# Local A2A server on :8080 (needs GOOGLE_CLOUD_PROJECT and your ADC for the Gemini calls).
run: frontend-build require-project
	uv run uvicorn trend_signals.main:app --port 8080 --reload

screenshots: frontend-build  ## render the workspace views to docs/images/ (Playwright)
	uv run python scripts/screenshots.py

# ---- cloud -----------------------------------------------------------------------------
require-project:
	@if [[ -z "$(PROJECT_ID)" || "$(PROJECT_ID)" == "your-project-id" ]]; then \
	  echo "GOOGLE_CLOUD_PROJECT is not set: cp .env.example .env and fill it in"; exit 1; fi

enable-apis: require-project
	$(GC) services enable run.googleapis.com cloudbuild.googleapis.com \
	  artifactregistry.googleapis.com aiplatform.googleapis.com discoveryengine.googleapis.com iam.googleapis.com

deploy: require-project
	./deploy/deploy_cloud_run.sh

# Gemini Enterprise keeps a static copy of the agent card: re-run after ANY card change.
register: require-project
	uv run python registration/register_ge.py register

register-dry: require-project
	uv run python registration/register_ge.py register --dry-run

list-ge: require-project
	uv run python registration/register_ge.py list

SERVICE ?= trend-signals-agent
# Only for `url` and `smoke`. Never exported: deploy_cloud_run.sh reads SERVICE from the environment.
unexport SERVICE

url: require-project         ## stable URL of the deployed service
	uv run python scripts/cloud_run_url.py $(SERVICE)

smoke: require-project       ## agent card + one turn against the deployed service
	uv run python scripts/smoke_remote.py $(SERVICE)
