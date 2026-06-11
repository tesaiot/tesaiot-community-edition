<!--
SPDX-License-Identifier: Apache-2.0
Copyright TESAIoT Platform contributors
-->

# User Management

TESAIoT Community Edition manages human users (operators / admins) in MongoDB, with
JWT-based authentication, bcrypt password hashing, and optional email/OTP flows.
This is a **single-organization** deployment: every user belongs to the one
default organization.

---

## 1. The bootstrap admin

On first boot the API seeds a single administrator from `.env`:

| Variable | Default | Meaning |
|----------|---------|---------|
| `ADMIN_EMAIL` | `admin@localhost` | Login email. |
| `ADMIN_USERNAME` | `admin` | Username. |
| `ADMIN_PASSWORD` | *(random, set by `generate-secrets.sh`)* | Initial password. |
| `ADMIN_BYPASS_RATE_LIMIT` | `true` | Allows this account to bypass per-IP login rate limiting. |

Find the generated password in `.env` after install, log in at
`https://<domain>/`, and **change it immediately** from the UI.

---

## 2. Authentication model

- **JWT (HS256)** signed with `JWT_SECRET`. Access + refresh tokens.
- **Passwords** hashed with bcrypt; cost factor from `BCRYPT_LOG_ROUNDS`
  (default 12 — never hardcoded).
- **Login rate limiting** is per-IP in the API (backed by Redis). If a user is
  locked out, the limit clears with time or an API restart; the bootstrap admin
  bypasses it when `ADMIN_BYPASS_RATE_LIMIT=true`.

### Auth API (prefix `/api/v1/auth`)

| Method & path | Purpose |
|---------------|---------|
| `POST /api/v1/auth/login` | Log in, returns access + refresh tokens. |
| `POST /api/v1/auth/refresh` | Exchange a refresh token for a new access token. |
| `POST /api/v1/auth/logout` | Invalidate the session. |
| `GET  /api/v1/auth/verify` | Validate the current token. |
| `POST /api/v1/auth/validate-token` | Validate an arbitrary token. |
| `GET  /api/v1/auth/user/me` | Current user profile. |
| `POST /api/v1/auth/change-password` | Change own password. |
| `GET\|PUT /api/v1/auth/profile` | Read / update own profile. |
| `POST /api/v1/auth/forgot-password` / `reset-password` | Password reset (needs email). |
| OTP endpoints under `/api/v1/auth/otp/*` | OTP login / verification (needs email). |

Example login:

```bash
curl -k -X POST https://localhost/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@localhost","password":"<ADMIN_PASSWORD>"}'
```

Use the returned `access_token` as `Authorization: Bearer <token>` on subsequent
calls.

---

## 3. Managing users

Via the Admin UI (**Users** section) or the API (prefix `/api/v1/users`,
requires an admin JWT):

| Method & path | Purpose |
|---------------|---------|
| `GET  /api/v1/users/` (or `/list`) | List users. |
| `POST /api/v1/users/` | Create a user. |
| `POST /api/v1/users/create-with-otp` | Create a user and send an OTP invite (needs email). |
| `PUT  /api/v1/users/<id>` | Update a user. |
| `DELETE /api/v1/users/<id>` | Delete a user. |
| `POST /api/v1/users/<id>/activate` / `deactivate` | Enable / disable a user. |
| `POST /api/v1/users/<id>/reset-password` | Admin-reset a user's password. |
| `GET  /api/v1/users/<id>/activity` | User activity log. |
| `GET\|PUT /api/v1/users/me` | Own profile. |
| `POST /api/v1/users/me/change-password` | Change own password. |
| `GET\|PUT /api/v1/users/me/preferences` | Own preferences. |

Create a user:

```bash
TOKEN=<admin access_token>
curl -k -X POST https://localhost/api/v1/users/ \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"email":"op1@example.com","username":"op1","password":"<strong>","role":"operator"}'
```

> Users are stored in the MongoDB `users` collection with a unique index on
> `email`.

---

## 4. Email & OTP (optional)

User invites, password resets, and OTP login require SMTP. Configure in `.env`:

```ini
EMAIL_ENABLED=true
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_USER=...
EMAIL_PASSWORD=...
EMAIL_FROM_ADDRESS=noreply@example.com
# OTP policy
OTP_LENGTH=6
OTP_EXPIRE_MINUTES=15
OTP_MAX_ATTEMPTS=3
OTP_COOLDOWN_SECONDS=30
```

Then `docker compose restart api`. With `EMAIL_ENABLED=false`, mail is logged to
stdout instead of sent (useful for testing) — view it with `make logs s=api`.

---

## 5. Security notes

- Rotate `ADMIN_PASSWORD` after first login; consider creating a personal admin
  account and disabling the shared bootstrap one.
- `JWT_SECRET` and `SECRET_KEY` must stay secret and stable — rotating them
  invalidates all active sessions.
- All user actions can be recorded in the `activity_logs` / `audit_logs` tables
  (see [architecture.md](architecture.md)).
