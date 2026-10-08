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

import os

import pytest

# The package validates its config at import time of trend_signals.main only; tests import the
# modules directly, but the model library wants a project when a client is built.
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "test-project")
os.environ.setdefault("FRONTEND_DIST", os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))


@pytest.fixture
def user():
    """A fresh user key per test, so canvas state never leaks between tests."""
    import uuid

    return f"test-{uuid.uuid4().hex[:8]}"


class Ctx:
    """The slice of ADK's ToolContext the tools read."""

    def __init__(self, user: str) -> None:
        from trend_signals.kit import identity

        self.state = {identity.SESSION_KEY: user}


@pytest.fixture
def ctx(user):
    return Ctx(user)
