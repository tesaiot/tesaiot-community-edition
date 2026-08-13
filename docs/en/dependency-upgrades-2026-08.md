<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright TESAIoT Platform contributors -->

# Dependency upgrades — triage, August 2026

Trivy's dependency scan completed for the first time on 2026-08-13. The job had
previously failed while resolving its own action (`trivy-action@0.28.0`, whose
unprefixed upstream tags were deleted), so **nothing in this repository had ever
actually been scanned**. The first successful run reported 83 HIGH/CRITICAL
findings.

This document triages them. It is deliberately not a "run `npm audit fix`" list:
the findings differ by an order of magnitude in real risk, and two of them turned
out to need no upgrade at all.

## The question that changes each answer

**Is the vulnerable code actually called?** A CVE in a library nothing imports
cannot be exploited. "It is in requirements.txt" is not the same as "it is in the
auth path", and treating the two alike wastes an upgrade window on the wrong
package.

---

## Done — no upgrade needed

### `authlib` 1.3.2 — CVE-2026-27962, CRITICAL, authentication bypass via JWK header

**Removed, not upgraded.** One grep hit across the entire repository, and that hit
was the `requirements.txt` line itself. `pip show authlib` in a fully installed
environment reports no reverse dependencies. It looks like a leftover from the
split out of the full platform.

Deleting it closes a CRITICAL finding with zero compatibility risk. JWT handling
in this service is PyJWT (`api/core/auth.py`).

---

## Needs a build and a test run

These cannot be verified on the Droplet — see the no-build rule for that host.
Each needs `make build` plus the API test suite on a machine that can run them.

### `PyJWT` 2.8.0 → 2.12.0 — CVE-2026-32597, HIGH

**Genuinely used**, in `api/core/auth.py` (lines 83, 337, 1129),
`api/services/user_service.py:237` and `api/services/websocket_telemetry.py`.

The CVE is that PyJWT accepts unknown `crit` header extensions, contrary to the
RFC. It matters most when verifying tokens minted by a third party. This service
signs and verifies its own tokens with `algorithms=['HS256']` against its own
`JWT_SECRET`, so an attacker without that secret cannot present a token at all.

**Assessment: upgrade as hygiene, not as an emergency.** Low breakage risk — the
2.x line has kept a stable API.

### `flask` 2.3.2 → 3.1.3, `werkzeug` 2.3.8 → 3.1.6, `flask-cors` 4.0.2 → 6.0.0

95 findings across these three (pip-audit). All are core to the API service.

**These are major bumps and the riskiest item here.** Flask 2 → 3 drops
deprecated APIs; flask-cors 4 → 6 crosses two majors and CORS behaviour is
security-relevant in its own right — a regression here is an outage or a hole,
not a warning. Werkzeug must move with Flask.

**Do these together, on their own branch, with the full suite plus a manual
login/CORS check.** Not bundled with anything else.

### `axios` (admin-ui) — DoS and proxy-inheritance findings, HIGH

Used by the admin UI at runtime. `package-lock.json` already pins 1.19.0, which
is outside the advisory's `1.0.0 - 1.17.0` range, yet CI still reports findings —
the two views disagree and that needs resolving on a machine with Node 20 before
anything is changed. Note `npm audit` on Node 18 / npm 9.2.0 reports **zero**
vulnerabilities against the same lockfile.

### `tar` 7.4.3 / 7.5.16 → 7.5.19 — CVE-2026-59873, CRITICAL, gzip-bomb DoS

Present in both images. Build-time tooling rather than a runtime request path,
which lowers the urgency, but the fix is a patch bump and should be easy.

---

## Suggested order

1. `authlib` — done, no risk.
2. `tar`, `axios` — patch/minor bumps, verify the admin UI still builds.
3. `PyJWT` — small, well-understood.
4. `flask` + `werkzeug` + `flask-cors` — own branch, own test cycle.

## Reproducing the scan

```bash
# What CI runs
pip-audit --strict --requirement services/api/requirements.txt
npm audit --omit=dev --audit-level=high        # from services/admin-ui, Node 20
```

Trivy findings are in the `Trivy filesystem + config scan` job of any CI run on
`main`.
