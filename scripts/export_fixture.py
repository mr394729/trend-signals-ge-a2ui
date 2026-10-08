#!/usr/bin/env python3
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

"""Write the gallery fixture (frontend/src/dev/fixture.json) from the Python dataset.

`npm run dev` renders the workspace from this file when no agent injected a state, so the page
can be designed without running the agent. It is the same dict the agent injects in production.
"""

from __future__ import annotations

import json
from pathlib import Path

from trend_signals import state

OUT = Path(__file__).resolve().parents[1] / "frontend" / "src" / "dev" / "fixture.json"

if __name__ == "__main__":
    OUT.write_text(json.dumps(state.build("fixture"), separators=(",", ":")) + "\n")
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB)")
