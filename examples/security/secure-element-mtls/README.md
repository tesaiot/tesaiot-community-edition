<!--
SPDX-License-Identifier: Apache-2.0
Copyright TESAIoT Platform contributors
-->

# Secure-element mTLS (OPTIGA Trust M / PSE84) — reference + host simulation

`se_mtls_client.py` is a **host simulation** of a hardware secure element that reproduces
the exact enrollment + telemetry contract the OPTIGA Trust M and PSE84 firmware use, and
is **verified end-to-end against a live CE install** (telemetry lands in the
`device_telemetry` hypertable).

Flow:
1. **On-chip keygen (simulated):** generate an EC P-256 keypair — on real silicon the
   private key is created inside the chip and never exported.
2. **Enrollment:** build a CSR (CN = device_id) and have CE sign it via
   `POST /api/v1/certificates/devices/{id}/certificate/sign-csr` (Vault PKI, `csr-signing`
   role), then download the issued client certificate.
3. **mTLS telemetry:** connect to EMQX `:8883` with the client cert + key, verify the
   broker against the CE CA chain, and publish `device/<id>/telemetry`.

## Run

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
export DEVICE_ID=my-device API_KEY=tesa_dak_... CA_CERT=../../../config/tls/ca-bundle.pem
export ADMIN_EMAIL=... ADMIN_PASSWORD=...     # to sign the CSR
./.venv/bin/python se_mtls_client.py
```

## Community Edition notes & limitations

- **mTLS auth requires a password.** EMQX runs a `password_based` webhook authenticator,
  so the client sends `username=device_id` + `password=<device API key>`; the webhook then
  authorises by the client-certificate **CN**. A cert-only connection is rejected before
  the webhook runs. (This is why the PSE84 firmware sets `MQTT_PASSWORD = API_KEY`.)
- **EMQX `:8883` is container-internal** in the default compose. On real hardware/edge the
  device dials `:8883` directly; for a local host test, forward it (e.g.
  `docker run --rm --network tesa-int0 -p 18883:8883 alpine/socat TCP-LISTEN:8883,fork TCP:tesa-emqx:8883`)
  and set `MQTT_PORT=18883`.
- **Excluded from CE:** the hardware examples' **CSR-over-MQTT enrollment** and
  **Protected Update (OTA)** paths have no server-side answer in stock CE (the mqtt-bridge
  is telemetry-only). Enroll over the HTTP `sign-csr` API instead (as this client does).

## Real hardware firmware

The full firmware lives in the developer hub under `security/pse84_tesaiot_client`
(Infineon PSE84 secure element) and `security/rpi_tesaiot_client` (Raspberry Pi + OPTIGA
Trust M). They implement the identical mTLS publish contract verified here; flashing them
exercises the same CE path. Requires the physical hardware (and, for PSE84, a valid
TESAIoT license / `libtesaiot`).
