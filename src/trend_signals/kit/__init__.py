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

"""The generic A2UI / Gemini Enterprise plumbing: nothing here knows about trends.

Copy this package into any agent that renders A2UI v0.9 in Gemini Enterprise:
wire builders validated against the composite catalog (v09, sdk), part assembly
(emit), click normalization (actions, click_bridge), the closing-event card
attachment (final_panel), identity, and srcdoc state injection.
"""
