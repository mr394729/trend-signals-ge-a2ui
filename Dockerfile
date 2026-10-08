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

# ---- Stage 1: the workspace page (single-file Vite build) ---------------------
FROM node:20-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci || npm install
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: the agent service ------------------------------------------------
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.11.14 /uv /uvx /bin/
WORKDIR /code

COPY pyproject.toml uv.lock ./
COPY src/ src/
RUN uv sync --frozen --no-dev

COPY --from=frontend-build /frontend/dist /code/frontend_dist

ENV FRONTEND_DIST=/code/frontend_dist \
    GOOGLE_CLOUD_LOCATION=global \
    PYTHONUNBUFFERED=1

EXPOSE 8080
CMD ["uv", "run", "--no-sync", "uvicorn", "trend_signals.main:app", "--host", "0.0.0.0", "--port", "8080"]
