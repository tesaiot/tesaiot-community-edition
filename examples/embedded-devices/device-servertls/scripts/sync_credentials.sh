#!/usr/bin/env bash

# Copyright (c) 2025 TESAIoT Platform (TESA)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -euo pipefail

# Tutorial note: reshape the Server-TLS bundles (HTTPS + MQTT) into the layout
# expected by the example binaries.  Mirrors the "import credentials" section
# from README.md.
# Usage:
#   ./scripts/sync_credentials.sh --device-dir ../download

die() { echo "[sync] $*" >&2; exit 1; }

script_dir=$(cd "$(dirname "$0")" && pwd)
example_dir=$(cd "$script_dir/.." && pwd)
dest_dir="$example_dir/certs_credentials"

device_dir=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --device-dir) device_dir="$2"; shift 2 ;;
    --dest-dir)   dest_dir="$2"; shift 2 ;;
    *) die "Unknown arg: $1" ;;
  esac
done

[[ -n "$device_dir" ]] || die "--device-dir is required"
[[ -d "$device_dir" ]] || die "Device dir not found: $device_dir"

mkdir -p "$dest_dir"

shopt -s nullglob

# HTTPS Server‑TLS bundle
stls_https=("$device_dir"/*-servertls-https-bundle*/)
if [[ ${#stls_https[@]} -gt 0 ]]; then
  src_dir="${stls_https[0]}"
  echo "[sync] Copying HTTPS Server‑TLS bundle: $src_dir"
  # CA chain
  if [[ -f "$src_dir/ca-chain.pem" ]]; then cp -f "$src_dir/ca-chain.pem" "$dest_dir/ca-chain.pem"; fi
  chain_candidate=$(ls "$src_dir"/*-ca-chain.pem 2>/dev/null | head -n1 || true)
  [[ -n "$chain_candidate" ]] && cp -f "$chain_candidate" "$dest_dir/ca-chain.pem"
  # endpoints
  [[ -f "$src_dir/endpoints.json" ]] && cp -f "$src_dir/endpoints.json" "$dest_dir/endpoints.json"
  # API key, device id
  cred_file=$(ls "$device_dir"/*-servertls-https-bundle*/https-api-credentials.txt 2>/dev/null | head -n1 || true)
  if [[ -f "$cred_file" ]]; then
    awk -F': ' '/^API Key:/ {print $2}' "$cred_file" > "$dest_dir/api_key.txt"
    awk -F': ' '/^Device ID:/ {print $2}' "$cred_file" > "$dest_dir/device_id.txt"
  fi
fi

# MQTT Server‑TLS bundle: extract mqtt_username/password into files
stls_mqtt=("$device_dir"/*-servertls-mqtt-bundle*/)
if [[ ${#stls_mqtt[@]} -gt 0 ]]; then
  src_mqtt="${stls_mqtt[0]}"
  echo "[sync] Copying MQTT Server‑TLS bundle: $src_mqtt"
  [[ -f "$src_mqtt/endpoints.json" ]] && cp -f "$src_mqtt/endpoints.json" "$dest_dir/endpoints.json"
  [[ -f "$src_mqtt/ca-chain.pem" ]] && cp -f "$src_mqtt/ca-chain.pem" "$dest_dir/ca-chain.pem"
  if [[ -f "$src_mqtt/mqtt-credentials.txt" ]]; then
    user=$(awk -F': ' '/^Device ID/ {print $2}' "$src_mqtt/mqtt-credentials.txt" | tr -d '\r')
    pass=$(awk -F': ' '/^Password/ {print $2}' "$src_mqtt/mqtt-credentials.txt" | tr -d '\r')
    [[ -n "$user" ]] && printf "%s\n" "$user" > "$dest_dir/mqtt_username.txt"
    [[ -n "$pass" ]] && printf "%s\n" "$pass" > "$dest_dir/mqtt_password.txt"
    # Also set device_id.txt if missing
    if [[ ! -f "$dest_dir/device_id.txt" && -n "$user" ]]; then printf "%s\n" "$user" > "$dest_dir/device_id.txt"; fi
    echo "[sync] Wrote mqtt_username.txt and mqtt_password.txt"
  fi
fi

echo "[sync] Done. Files in $dest_dir:" && ls -la "$dest_dir"
