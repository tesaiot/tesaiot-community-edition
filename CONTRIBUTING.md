<!--
SPDX-License-Identifier: Apache-2.0
Copyright TESAIoT Platform contributors
-->

# Contributing to TESAIoT Community Edition

First off — thank you for taking the time to contribute! TESAIoT Community Edition
is an Apache-2.0, self-hostable, single-organization IoT security platform, and
it gets better with every issue, idea, and pull request from the community.

This document explains how to report bugs, propose changes, set up a local
development environment, and get your contribution merged.

By participating in this project you agree to abide by our
[Code of Conduct](CODE_OF_CONDUCT.md).

---

## Table of Contents

- [Ways to contribute](#ways-to-contribute)
- [Reporting bugs](#reporting-bugs)
- [Requesting features](#requesting-features)
- [Reporting security issues](#reporting-security-issues)
- [Development setup](#development-setup)
- [Coding standards](#coding-standards)
- [Commit messages](#commit-messages)
- [Licensing & DCO (sign-off)](#licensing--dco-sign-off)
- [Submitting a pull request](#submitting-a-pull-request)
- [Project scope](#project-scope)
- [Getting help](#getting-help)

---

## Ways to contribute

You don't have to write code to make a difference:

- **Report a bug** or unexpected behaviour.
- **Improve the documentation** (typos, clarity, missing steps — all welcome).
- **Triage issues** — reproduce reports, add detail, suggest labels.
- **Review pull requests** from other contributors.
- **Propose a feature** that fits the project [scope](#project-scope).
- **Write code** to fix a bug or implement an accepted feature.

New here? Look for issues labelled
[`good first issue`](https://github.com/tesaiot/tesaiot-community-edition/labels/good%20first%20issue)
and [`help wanted`](https://github.com/tesaiot/tesaiot-community-edition/labels/help%20wanted).

---

## Reporting bugs

Before opening a new issue, please **search existing issues** to avoid
duplicates. If none match, open a
[bug report](.github/ISSUE_TEMPLATE/bug_report.md) and include:

- What you expected to happen vs. what actually happened.
- Exact steps to reproduce.
- Your environment (OS, Docker / Docker Compose version, release tag or commit).
- Relevant logs (`make logs` or `make logs s=<service>`), with secrets redacted.

> Do **not** file security vulnerabilities as public issues. See
> [Reporting security issues](#reporting-security-issues).

---

## Requesting features

Open a [feature request](.github/ISSUE_TEMPLATE/feature_request.md). Describe the
problem you're trying to solve (not just the solution), who it helps, and how it
fits the project [scope](#project-scope). Out-of-scope ideas may still be useful
as a downstream extension — we're happy to discuss.

---

## Reporting security issues

**Never** report a security vulnerability through a public issue, discussion, or
pull request. Follow the coordinated disclosure process in
[SECURITY.md](SECURITY.md).

---

## Development setup

TESAIoT Community Edition runs as a Docker Compose stack. You need:

- Docker Engine 24+ and the Docker Compose v2 plugin
- GNU Make
- `git`, `openssl`, and `bash`

```bash
# 1. Clone your fork
git clone https://github.com/<your-user>/tesaiot-community-edition.git
cd tesaiot-community-edition

# 2. Check host prerequisites (docker, ports, disk, .env)
make preflight

# 3. One-command bootstrap: secrets -> PKI -> DB -> up -> health
make install

# 4. Verify everything is healthy
make health
```

Useful targets while developing (`make help` lists them all):

| Target | Purpose |
|---|---|
| `make up` / `make down` | Start / stop the stack (data kept) |
| `make logs s=api` | Tail logs for a single service |
| `make restart s=api` | Restart a single service |
| `make build` | Rebuild service images |
| `make ps` | Show container status |
| `make clean` | Remove containers, networks **and volumes** (destroys data) |

> **Important:** Always use the `make` targets / `scripts/*` rather than calling
> `docker compose` directly — the wrappers handle ordering, secrets, and health
> checks that raw compose commands skip.

---

## Coding standards

- **Never hardcode values.** Configuration must come from environment variables,
  `config/*`, or be computed from real data. Provide an override path for
  anything operational (TTLs, ports, hosts, validity windows). This is a
  [Twelve-Factor](https://12factor.net/config) discipline and a hard rule for
  this project.
- **Keep it single-organization.** Do not reintroduce multi-tenant /
  multi-organization scoping. Use the single default organization.
- **Stay in scope.** See [Project scope](#project-scope).
- **Backend (Python / FastAPI):** format with `black`, sort imports with
  `isort`, lint with `ruff`. Type hints expected on public functions.
- **Frontend (React):** lint with the project ESLint config; format with
  Prettier.
- **Shell scripts:** must pass `shellcheck`; use `set -euo pipefail`.
- **Tests:** add or update tests for any behavioural change; CI must stay green.

---

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short summary>

<optional body explaining the why>
```

Common types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`,
`build`, `perf`, `security`. Keep the summary in the imperative mood and under
~72 characters. Reference issues in the body (`Fixes #123`).

---

## Licensing & DCO (sign-off)

By contributing, you agree that your contributions are licensed under the
[Apache License 2.0](LICENSE).

This project follows the
[Developer Certificate of Origin (DCO)](https://developercertificate.org/).
Sign off every commit to certify you have the right to submit it:

```bash
git commit -s -m "fix(api): handle missing device serial"
```

This appends a `Signed-off-by:` trailer to your commit.

**File headers (REUSE / SPDX).** New source files should carry a machine-readable
license header so the codebase stays SBOM-friendly:

```python
# SPDX-License-Identifier: Apache-2.0
# Copyright TESAIoT Platform contributors
```

Use the comment syntax appropriate to the file's language. Do **not** add a
personal copyright holder; attribute to *TESAIoT Platform contributors*.

---

## Submitting a pull request

1. **Fork** the repo and create a topic branch off `main`
   (`git checkout -b fix/device-serial`).
2. Make your change with tests and docs updates.
3. Ensure `make build` succeeds and the lint/test suite passes locally.
4. **Sign off** your commits (`-s`).
5. Push and open a PR against `main`, filling in the
   [pull request template](.github/PULL_REQUEST_TEMPLATE.md).
6. Keep PRs focused and reasonably small — easier to review, faster to merge.
7. Be responsive to review feedback. At least one maintainer approval and green
   CI are required before merge.

---

## Project scope

TESAIoT Community Edition deliberately ships **only** these 8 capabilities:

1. User Management
2. Device / Identity Management
3. serverTLS and mTLS authentication modes
4. Basic Certificate Life-cycle Management via HashiCorp Vault PKI
5. APISIX API Gateway
6. EMQX MQTT Broker
7. MongoDB & TimescaleDB
8. IoT Telemetry Dashboard (inside Device Details)

Anything outside this list (multi-tenancy, AI inference, OTA / firmware update,
B2B / WebSocket features, third-party services, analytics, the
Grafana/Prometheus stack) is intentionally **out of scope** for this
distribution.

---

## Getting help

- Usage questions: see [SUPPORT.md](SUPPORT.md).
- Project decisions & roles: see [GOVERNANCE.md](GOVERNANCE.md).
- Documentation: [`docs/en/`](docs/en/) (English) and [`docs/th/`](docs/th/) (Thai).

We're glad you're here. Happy hacking!
