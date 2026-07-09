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

# generate_csr.sh — Flexible CSR + private key generator for Server-TLS devices.
# Same options as the mTLS version; duplicated here so each tutorial folder is
# self-contained.

die() { echo "[generate_csr] $*" >&2; exit 1; }

DEVICE_ID=""
PROFILE="iot_default"
KEY_TYPE="ecdsa"        # ecdsa|rsa
CURVE="p256"            # p256|p384 (for ecdsa)
RSA_BITS="2048"         # 2048|3072|4096 (for rsa)
COUNTRY="TH"
STATE="Bangkok"
LOCALITY="Bangkok"
ORG="TESA IoT Platform"
OU="Devices"
CN=""
SANS=()
OUT_DIR="$(cd "$(dirname "$0")/.." && pwd)/csr"
FORCE=false

map_curve() { case "$1" in p256|P-256|prime256v1) echo "prime256v1";; p384|P-384|secp384r1) echo "secp384r1";; *) die "Unsupported curve: $1 (use p256|p384)";; esac; }
usage() {
  cat <<USAGE
Usage: $0 --device-id <id> [options]
  --profile <iot_default|medical|industrial>
  --key-type <ecdsa|rsa>   (default: ecdsa)
  --curve <p256|p384>      (ecdsa)
  --rsa-bits <2048|3072|4096>
  --C/--ST/--L/--O/--OU    Subject fields
  --CN <common-name>
  --san "DNS:a,IP:x"       (repeatable)
  --out-dir <dir>          (default: ./csr)
  --force
USAGE
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --device-id) DEVICE_ID="$2"; shift 2 ;;
      --profile) PROFILE="$2"; shift 2 ;;
      --key-type) KEY_TYPE="$2"; shift 2 ;;
      --curve) CURVE="$2"; shift 2 ;;
      --rsa-bits) RSA_BITS="$2"; shift 2 ;;
      --C|--country) COUNTRY="$2"; shift 2 ;;
      --ST|--state) STATE="$2"; shift 2 ;;
      --L|--locality) LOCALITY="$2"; shift 2 ;;
      --O|--org) ORG="$2"; shift 2 ;;
      --OU|--unit) OU="$2"; shift 2 ;;
      --CN|--common-name) CN="$2"; shift 2 ;;
      --san) SANS+=("$2"); shift 2 ;;
      --out-dir) OUT_DIR="$2"; shift 2 ;;
      --force) FORCE=true; shift ;;
      -h|--help) usage; exit 0 ;;
      *) die "Unknown option: $1" ;;
    esac
  done
}

apply_profile() {
  case "$PROFILE" in
    iot_default) : ;;
    medical) ORG="TESA IoT Platform — Medical"; OU="Medical Devices" ;;
    industrial) ORG="TESA IoT Platform — Industrial"; OU="Industrial Devices" ;;
    *) echo "[generate_csr] Unknown profile: $PROFILE (using defaults)" ;;
  esac
}

build_san_list() {
  local list=""
  if [[ ${#SANS[@]} -gt 0 ]]; then list=$(IFS=","; echo "${SANS[*]}"); else
    if [[ -n "$CN" && "$CN" == *.* ]]; then list="DNS:$CN"; else list="DNS:localhost"; fi
  fi
  echo "$list"
}

main(){
  parse_args "$@"; [[ -n "$DEVICE_ID" ]] || die "--device-id is required"; apply_profile
  if [[ -z "$CN" ]]; then CN="$DEVICE_ID"; fi
  local curve_name=""; local alg_label="";
  if [[ "$KEY_TYPE" == "ecdsa" ]]; then curve_name=$(map_curve "$CURVE"); alg_label="ecc-${CURVE}";
  elif [[ "$KEY_TYPE" == "rsa" ]]; then [[ "$RSA_BITS" =~ ^(2048|3072|4096)$ ]] || die "Invalid --rsa-bits"; alg_label="rsa-${RSA_BITS}"; else die "Unsupported --key-type"; fi
  mkdir -p "$OUT_DIR"; local key_file="$OUT_DIR/${DEVICE_ID}-${alg_label}.key.pem"; local csr_file="$OUT_DIR/${DEVICE_ID}.csr.pem"
  if ! $FORCE && { [[ -f "$key_file" ]] || [[ -f "$csr_file" ]]; }; then die "Output exists. Use --force to overwrite."; fi
  if [[ "$KEY_TYPE" == "ecdsa" ]]; then openssl ecparam -name "$curve_name" -genkey -noout -out "$key_file"; else openssl genrsa -out "$key_file" "$RSA_BITS"; fi
  chmod 600 "$key_file"
  local san_list; san_list=$(build_san_list)
  local tmpconf; tmpconf=$(mktemp)
  cat > "$tmpconf" <<CONF
[ req ]
distinguished_name = dn
req_extensions = req_ext
prompt = no

[ dn ]
C = $COUNTRY
ST = $STATE
L = $LOCALITY
O = $ORG
OU = $OU
CN = $CN

[ req_ext ]
subjectAltName = $san_list
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = clientAuth
CONF
  openssl req -new -key "$key_file" -out "$csr_file" -config "$tmpconf" -sha256
  rm -f "$tmpconf"
  echo "[generate_csr] Key: $key_file"; echo "[generate_csr] CSR: $csr_file"; echo "CN=$CN | SAN=$san_list"
}

main "$@"
