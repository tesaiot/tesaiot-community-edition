#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
Secure-element mTLS client — a host simulation of an OPTIGA Trust M / PSE84 device.

It reproduces the exact enrollment + telemetry contract those hardware examples use
against TESAIoT Community Edition, and is verified end-to-end (telemetry lands in the
device_telemetry hypertable):

  1. Generate an EC P-256 keypair locally (the secure element does this on-chip; the
     private key never leaves the chip on real hardware).
  2. Build a CSR (CN = device_id) and have Community Edition sign it via
     POST /api/v1/certificates/devices/{id}/certificate/sign-csr, then download the
     issued client certificate.
  3. Connect to the EMQX mTLS listener (:8883) with the client cert + key, verifying the
     broker against the CE Vault-PKI CA chain, and publish device/<id>/telemetry.

CE auth note: EMQX runs a password_based webhook authenticator, so the mTLS client must
also send MQTT username=device_id and a non-empty password (its device API key). The
webhook then authorises by the client-certificate CN.

Env:
  BASE_URL (https://localhost) ADMIN_JWT (or ADMIN_EMAIL/ADMIN_PASSWORD via CE .env)
  DEVICE_ID  API_KEY  CA_CERT (CE ca-bundle.pem)
  MQTT_HOST (localhost)  MQTT_PORT (8883)  COUNT (4)  INTERVAL (3)
Stdlib + paho-mqtt + openssl CLI.
"""
import json, os, ssl, subprocess, sys, time, datetime, urllib.request, urllib.error
import paho.mqtt.client as mqtt

BASE = os.getenv("BASE_URL", "https://localhost")
DID = os.environ["DEVICE_ID"]
API_KEY = os.environ["API_KEY"]
CA = os.environ["CA_CERT"]
MQTT_HOST = os.getenv("MQTT_HOST", "localhost"); MQTT_PORT = int(os.getenv("MQTT_PORT", "8883"))
COUNT = int(os.getenv("COUNT", "4")); IVL = float(os.getenv("INTERVAL", "3"))
WORK = os.getenv("WORKDIR", "./se_certs")
os.makedirs(WORK, exist_ok=True)
_SSL = ssl.create_default_context(); _SSL.check_hostname = False; _SSL.verify_mode = ssl.CERT_NONE


def _http(method, url, token=None, body=None):
    h = {"Content-Type": "application/json"} if body is not None else {}
    if token: h["Authorization"] = "Bearer " + token
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, context=_SSL, timeout=30) as r:
            return r.status, r.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")


def _admin_jwt():
    tok = os.getenv("ADMIN_JWT")
    if tok: return tok
    email, pw = os.getenv("ADMIN_EMAIL"), os.getenv("ADMIN_PASSWORD")
    if not (email and pw):
        sys.exit("Set ADMIN_JWT, or ADMIN_EMAIL/ADMIN_PASSWORD, to sign the CSR.")
    c, t = _http("POST", BASE + "/api/v1/auth/login", body={"email": email, "password": pw})
    if c != 200: sys.exit(f"login failed {c}")
    return json.loads(t)["token"]


def enroll():
    key = f"{WORK}/client_key.pem"; csr = f"{WORK}/device.csr"; crt = f"{WORK}/client_cert.pem"
    # 1. on-chip keygen (simulated) + CSR
    subprocess.run(["openssl", "ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", key], check=True)
    subprocess.run(["openssl", "req", "-new", "-key", key, "-out", csr,
                    "-subj", f"/CN={DID}/O=TESAIoT Community Edition"], check=True)
    tok = _admin_jwt()
    # 2. CE signs the CSR (issues + binds the cert), then download the device cert
    c, t = _http("POST", f"{BASE}/api/v1/certificates/devices/{DID}/certificate/sign-csr",
                 token=tok, body={"csr": open(csr).read(), "validity_days": 365})
    if c != 200: sys.exit(f"sign-csr failed {c}: {t[:200]}")
    c, t = _http("GET", f"{BASE}/api/v1/certificates/devices/{DID}/certificate/download/device-cert", token=tok)
    if c != 200: sys.exit(f"cert download failed {c}")
    pem = t
    if t.lstrip().startswith("{"):
        def find(o):
            if isinstance(o, str) and "BEGIN CERTIFICATE" in o: return o
            if isinstance(o, dict):
                for v in o.values():
                    r = find(v)
                    if r: return r
            return None
        pem = find(json.loads(t))
    open(crt, "w").write(pem)
    print(f"[se] enrolled: cert CN={DID} issued by CE Vault PKI")
    return crt, key


def publish(crt, key):
    c = mqtt.Client(client_id=DID)
    c.username_pw_set(DID, API_KEY)  # CE: engages the password_based auth webhook
    c.tls_set(ca_certs=CA, certfile=crt, keyfile=key,
              cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS)
    c.tls_insecure_set(False)
    c.connect(MQTT_HOST, MQTT_PORT, 30); c.loop_start(); time.sleep(1)
    topic = f"device/{DID}/telemetry"
    for i in range(COUNT):
        payload = {"device_id": DID,
                   "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   "data": {"temperature": round(26 + i * 0.5, 2), "battery": 95 - i}}
        c.publish(topic, json.dumps(payload), qos=1).wait_for_publish(5)
        print(f"[se] published {topic}: {payload['data']}")
        time.sleep(IVL)
    c.loop_stop(); c.disconnect()


if __name__ == "__main__":
    crt, key = enroll()
    publish(crt, key)
    print("[se] done")
