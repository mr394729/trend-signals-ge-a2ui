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

import { useId } from "react";

type Kind = "twill" | "rib" | "weave" | "boucle";

/** The textile a fabric name suggests, drawn as a repeating SVG pattern. */
export function kindFor(fabrics: string[]): Kind {
  const f = fabrics.join(" ").toLowerCase();
  if (/denim|twill|canvas|corduroy|ripstop|shell|waxed/.test(f)) return "twill";
  if (/knit|rib|jersey|seamless/.test(f)) return "rib";
  if (/bouclé|boucle|fleece|sherpa|tweed|suede|wool|shearling/.test(f)) return "boucle";
  return "weave";
}

/** A fabric-texture overlay for a colored block. Draws in currentColor; the parent sets the color. */
export function Texture({ kind, opacity = 0.16 }: { kind: Kind; opacity?: number }) {
  const id = useId().replace(/:/g, "");
  return (
    <svg aria-hidden="true" className="pointer-events-none absolute inset-0 size-full" style={{ opacity }}>
      <defs>
        {kind === "twill" && (
          <pattern id={id} width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(32)">
            <line x1="0" y1="0" x2="0" y2="6" stroke="currentColor" strokeWidth="1.6" />
          </pattern>
        )}
        {kind === "rib" && (
          <pattern id={id} width="7" height="7" patternUnits="userSpaceOnUse">
            <line x1="3" y1="0" x2="3" y2="7" stroke="currentColor" strokeWidth="2.4" />
          </pattern>
        )}
        {kind === "weave" && (
          <pattern id={id} width="8" height="8" patternUnits="userSpaceOnUse">
            <path d="M0 4H8M4 0V8" stroke="currentColor" strokeWidth="1" />
            <path d="M0 0H4V4H0zM4 4H8V8H4z" fill="currentColor" opacity=".35" />
          </pattern>
        )}
        {kind === "boucle" && (
          <pattern id={id} width="11" height="11" patternUnits="userSpaceOnUse">
            <circle cx="3" cy="3" r="2.1" fill="currentColor" />
            <circle cx="8.5" cy="7.5" r="1.7" fill="currentColor" />
            <circle cx="9" cy="1.5" r="1" fill="currentColor" />
          </pattern>
        )}
      </defs>
      <rect width="100%" height="100%" fill={`url(#${id})`} />
    </svg>
  );
}
