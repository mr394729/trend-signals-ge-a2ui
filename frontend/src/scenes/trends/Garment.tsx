/**
 * Copyright 2026 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     https://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

// Flat garment silhouettes drawn in SVG — product "imagery" with no external assets
// (the srcdoc cannot load images). Color comes from the SKU or the trend's lead swatch.

const PATHS: Record<string, string> = {
  tee: "M30 16 L42 10 Q50 19 58 10 L70 16 L92 34 L82 47 L71 40 L71 90 L29 90 L29 40 L18 47 L8 34 Z",
  hoodie: "M30 14 L42 8 Q50 18 58 8 L70 14 L95 72 L83 77 L71 46 L71 92 L29 92 L29 46 L17 77 L5 72 Z",
  trousers: "M30 8 L70 8 L75 92 L55 92 L50 38 L45 92 L25 92 Z",
  jacket: "M27 12 L41 7 L50 20 L59 7 L73 12 L95 68 L83 73 L73 42 L73 92 L27 92 L27 42 L17 73 L5 68 Z",
  dress: "M36 8 L44 8 Q50 20 56 8 L64 8 L66 34 L80 92 L20 92 L34 34 Z",
  skirt: "M31 26 L69 26 L84 90 L16 90 Z",
};

export function Garment({ shape, color, size = 64, label }: {
  shape: string; color: string; size?: number; label?: string;
}) {
  const d = PATHS[shape] ?? PATHS.tee;
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" role="img" aria-label={label ?? shape}>
      <path d={d} fill={color} stroke="rgba(11,29,54,.28)" strokeWidth="1.6" strokeLinejoin="round" />
      {shape === "jacket" && <path d="M50 20 L50 92" stroke="rgba(255,255,255,.35)" strokeWidth="1.6" />}
      {shape === "skirt" && <rect x="31" y="22" width="38" height="5" rx="1.5" fill="rgba(255,255,255,.28)" />}
      {shape === "trousers" && <path d="M50 38 L50 8" stroke="rgba(255,255,255,.3)" strokeWidth="1.4" />}
    </svg>
  );
}
