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

# Tutorial note: normalise the bundle downloaded from Admin UI so the sample
# app can run without manual file renaming.  Treat this as the "import
# credentials" step outlined in the README.
# Usage:
#   ./scripts/sync_credentials.sh --device-dir ../../../download/device01 [--client-key /path/to/key.pem]

die() { echo "[sync] $*" >&2; exit 1; }

script_dir=$(cd "$(dirname "$0")" && pwd)
example_dir=$(cd "$script_dir/.." && pwd)
dest_dir="$example_dir/certs_credentials"

device_dir=""
client_key_opt=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --device-dir) device_dir="$2"; shift 2 ;;
    --client-key) client_key_opt="$2"; shift 2 ;;
    --dest-dir)   dest_dir="$2"; shift 2 ;;
    *) die "Unknown arg: $1" ;;
  esac
done

[[ -n "$device_dir" ]] || die "--device-dir is required"
[[ -d "$device_dir" ]] || die "Device dir not found: $device_dir"

mkdir -p "$dest_dir"

shopt -s nullglob
mtls_https=("$device_dir"/*-https-mtls-bundle*/)

if [[ ${#mtls_https[@]} -gt 0 ]]; then
  src_dir="${mtls_https[0]}"
  echo "[sync] Copying HTTPS mTLS bundle: $src_dir"
  cp -f "$src_dir"/*-certificate.pem "$dest_dir/client_cert.pem" 2>/dev/null || true
  # candidate names for CA chain
  if [[ -f "$src_dir/ca-chain.pem" ]]; then cp -f "$src_dir/ca-chain.pem" "$dest_dir/ca-chain.pem"; fi
  chain_candidate=$(ls "$src_dir"/*-ca-chain.pem 2>/dev/null | head -n1 || true)
  [[ -n "$chain_candidate" ]] && cp -f "$chain_candidate" "$dest_dir/ca-chain.pem"
  # device id from file name
  cert_candidate=$(ls "$src_dir"/*-certificate.pem 2>/dev/null | head -n1 || true)
  if [[ -n "$cert_candidate" ]]; then
    base=$(basename "$cert_candidate"); dev_id=${base%-certificate.pem}; echo "$dev_id" > "$dest_dir/device_id.txt"
  fi
  [[ -f "$src_dir/endpoints.json" ]] && cp -f "$src_dir/endpoints.json" "$dest_dir/endpoints.json"
else
  echo "[sync] No HTTPS mTLS bundle directory found; continuing"
fi

if [[ -n "$client_key_opt" ]]; then
  [[ -f "$client_key_opt" ]] || die "Client key not found: $client_key_opt"
  cp -f "$client_key_opt" "$dest_dir/client_key.pem"
  chmod 600 "$dest_dir/client_key.pem"
  echo "[sync] Installed client_key.pem"
fi

echo "[sync] Done. Files in $dest_dir:" && ls -la "$dest_dir"
