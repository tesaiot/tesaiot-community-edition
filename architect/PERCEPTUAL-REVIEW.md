<!--
SPDX-License-Identifier: Apache-2.0
Copyright TESAIoT Platform contributors
-->

# Perceptual Review — TESAIoT Community Edition Architecture Diagram

## Scope

This review covers the delivered interactive architecture diagram at
[`tesaiot-architecture.html`](tesaiot-architecture.html), generated from
[`tesaiot-architecture.json`](tesaiot-architecture.json) with the Archify skill
at `quality_profile: showcase`.

Artifact identity at review time:

| Item | Value |
|------|-------|
| Specification SHA-256 | `de08922c097baaec3b789d5a89e3c1afd67c7335dd90bed9840dcf4b68981071` |
| Artifact SHA-256 | `697bdf4d9d16a90ea1651bb17e61b6ce64713449f95a90c15bda6b7bc6cc3740` |
| Artifact size | 818,017 bytes |

The diagram records the single-organization, 11-container Docker Compose stack
described by `README.md`, `docker-compose.yml`, and `docs/en/architecture.md`.

## Method

Three independent evidence layers were collected, per the Archify delivery
contract. They are reported separately and must not be conflated.

1. **Deterministic artifact checks** — `archify deliver`. Result: pass, 9 of 9
   showcase composition checks, 0 errors, 0 warnings.
2. **Automated browser evidence** — `archify visual-check` on the frozen
   artifact. Checked 1440x900, 1600x1000, 1920x1080, and 2048x1320, each in
   light and dark (screenshots at 1440x900 and 2048x1320, both themes).
3. **Perceptual review** — human/visual inspection of the delivered render.

## Automated browser evidence

`visual-check` reported `status: pass` for containment, readability, viewer
chrome, and captures across every checked viewport.

- No horizontal or vertical overflow at any viewport
  (`scrollWidth <= innerWidth`, `scrollHeight <= innerHeight`).
- The smallest projected node text measured 9 px against a 6 px floor.
- The navigation dock clears the diagram stage (`dockStageGap` 10.2 px against a
  10 px minimum) with no intersection.
- Both the light and dark themes resolved and captured cleanly.

## Perceptual findings

Reviewed at full resolution in light and dark.

- **Composition and balance** — the diagram uses three vertical tiers: edge and
  ingress on the left, application tier in the centre, and state plus PKI on the
  right. The `tesa-api` node anchors the middle, so the eye follows one main
  path from devices through the proxies and broker to the data stores. No
  conspicuous empty band and no crowding.
- **Readability** — labels are legible at the target viewports. Relationship
  labels (`/api proxy`, `mTLS :9444`, `auth / ACL webhook`, `registry`,
  `telemetry`, `cache`, `PKI sign`) sit clear of nodes and of unrelated routes.
- **Semantics** — network boundaries (`tesa-external (LAN edge)`,
  `tesa-internal (backend only)`) and the hosting region are drawn as nested
  containers, matching the compose file. Variants distinguish security crossings
  (`PKI sign`, `mTLS :9444`) and the asynchronous webhook path.
- **Theme parity** — light and dark renders preserve geometry, colour roles, and
  contrast; switching theme does not alter the topology.
- **No defects found** — no clipped nodes, no two-route overlap, no label
  masking another route, and no misleading crossing.

## Result

Perceptual review: **pass**. The diagram is accurate to the repository, readable
across the checked desktop viewports, and balanced without filler.

## Notes and limitations

- The review covers static rendering only. Interactive viewer capabilities
  (pan/zoom, search, focus, relationship tracing, presentation, exports) are
  present in the artifact but were exercised only to the extent the browser
  evidence required.
- Node positions and route controls in the specification are hand-authored and
  validated by the Archify showcase checks; re-validating after any edit to the
  specification is required.
