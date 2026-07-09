# Community Edition notes

C (Mongoose) **mTLS** client — verified end-to-end against a live CE install (mTLS
publish landed in the `device_telemetry` hypertable).

## CE adaptations applied
- `config.h`: `DEFAULT_MQTT_HOST` → `localhost`, `DEFAULT_API_BASE_URL` → `https://localhost:9444`.
- **CA-trust fix** (`main.c`): both the MQTTS and HTTPS branches previously set
  `tls.ca_chain = NULL` (public OS trust). They now load `certs_credentials/ca-chain.pem`
  (the CE Vault-PKI chain) with `verify_peer` on.
- **mTLS auth fix** (`main.c`): the client now sends `username = device_id` and
  `password = <device API key>` (from `certs_credentials/api_key.txt`). CE's EMQX runs a
  `password_based` webhook authenticator, so a certificate-only CONNECT with an empty
  password is rejected *before* the webhook validates the client-cert CN. With the
  username+API-key present, the webhook authorises by CN.

## Provision & run
Register an mTLS device, then in `certs_credentials/`:
- `client_key.pem` — generate on the device (EC P-256): `openssl ecparam -name prime256v1 -genkey -noout -out client_key.pem`
- `client_cert.pem` — CSR signed by CE: `POST /api/v1/certificates/devices/{id}/certificate/sign-csr`, then download `.../certificate/download/device-cert`
- `ca-chain.pem` — `cp ../../../config/tls/ca-bundle.pem ca-chain.pem`
- `device_id.txt`, `api_key.txt` (from `regenerate-api-key`)

```bash
make all
COMM_MODE=MQTTS MQTT_HOST=localhost MQTT_PORT=8883 CERTS_DIR=$PWD/certs_credentials ./device_client
```

> The EMQX mTLS listener (`:8883`) is container-internal in the default compose. To reach
> it from the host, either expose the port or forward it (e.g. a `socat` container on the
> `tesa` network). On real hardware/edge the device connects to `:8883` directly.

## Snapshot (real data from a live CE run)

![device-mtls Vault-issued certificate](../../images/screenshots/device-mtls-certificate.png)
