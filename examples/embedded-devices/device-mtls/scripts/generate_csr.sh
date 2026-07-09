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

# generate_csr.sh — Flexible CSR + private key generator for IoT devices.
# This script mirrors the tutorial narrative: pick a profile, pick an
# algorithm, and it emits ready-to-upload artifacts.
#
# Usage examples:
#   ./scripts/generate_csr.sh --device-id 1ba7-...-a083 \
#     --key-type ecdsa --curve p256 \
#     --san DNS:device01.localhost \
#     --profile iot_default
#
#   ./scripts/generate_csr.sh --device-id device02 \
#     --key-type rsa --rsa-bits 3072 --profile industrial --out-dir ./csr
#
# Outputs:
#   <out_dir>/<device_id>-<alg>.key.pem
#   <out_dir>/<device_id>.csr.pem
#
# Notes:
# - ECDSA curves: p256 (=prime256v1), p384 (=secp384r1)
# - RSA sizes: 2048, 3072, 4096
# - SANs support: comma-separated (e.g., "DNS:foo,IP:1.2.3.4") or multiple --san flags

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

map_curve() {
  case "$1" in
    p256|P-256|prime256v1) echo "prime256v1" ;;
    p384|P-384|secp384r1)  echo "secp384r1" ;;
    *) die "Unsupported curve: $1 (use p256|p384)" ;;
  esac
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

usage() {
  cat <<USAGE
Usage: $0 --device-id <id> [options]
Options:
  --profile <name>         iot_default (default) | medical | industrial
  --key-type <ecdsa|rsa>   Key algorithm (default: ecdsa)
  --curve <p256|p384>      ECDSA curve (default: p256)
  --rsa-bits <n>           RSA bits: 2048|3072|4096 (default: 2048)
  --C/--ST/--L/--O/--OU    Subject fields (country/state/locality/org/unit)
  --CN <common-name>       Subject CN (default: <device_id>)
  --san "DNS:a,IP:x"       SubjectAltName list (repeatable)
  --out-dir <dir>          Output directory (default: ./csr)
  --force                  Overwrite existing files
  -h, --help               Show help
USAGE
}

apply_profile() {
  case "$PROFILE" in
    iot_default)
      : # keep defaults
      ;;
    medical)
      ORG="TESA IoT Platform — Medical"
      OU="Medical Devices"
      ;;
    industrial)
      ORG="TESA IoT Platform — Industrial"
      OU="Industrial Devices"
      ;;
    *)
      echo "[generate_csr] Unknown profile: $PROFILE (using defaults)"
      ;;
  esac
}

build_san_list() {
  local list=""
  if [[ ${#SANS[@]} -gt 0 ]]; then
    # Join with commas; if user passed comma-separated all at once, it's still fine
    list=$(IFS=","; echo "${SANS[*]}")
  else
    # Default: include CN as DNS if CN looks like hostname; and wildcard domain
    if [[ -n "$CN" && "$CN" == *.* ]]; then
      list="DNS:$CN"
    else
      list="DNS:localhost"
    fi
  fi
  echo "$list"
}

main() {
  parse_args "$@"
  [[ -n "$DEVICE_ID" ]] || die "--device-id is required"
  apply_profile

  # Subject defaults
  if [[ -z "$CN" ]]; then CN="$DEVICE_ID"; fi
  local curve_name=""; local alg_label="";
  if [[ "$KEY_TYPE" == "ecdsa" ]]; then
    curve_name=$(map_curve "$CURVE")
    alg_label="ecc-${CURVE}"
  elif [[ "$KEY_TYPE" == "rsa" ]]; then
    [[ "$RSA_BITS" =~ ^(2048|3072|4096)$ ]] || die "Invalid --rsa-bits: $RSA_BITS"
    alg_label="rsa-${RSA_BITS}"
  else
    die "Unsupported --key-type: $KEY_TYPE"
  fi

  mkdir -p "$OUT_DIR"
  local key_file="$OUT_DIR/${DEVICE_ID}-${alg_label}.key.pem"
  local csr_file="$OUT_DIR/${DEVICE_ID}.csr.pem"

  if ! $FORCE && { [[ -f "$key_file" ]] || [[ -f "$csr_file" ]]; }; then
    die "Output exists. Use --force to overwrite: $key_file or $csr_file"
  fi

  # Generate key
  if [[ "$KEY_TYPE" == "ecdsa" ]]; then
    openssl ecparam -name "$curve_name" -genkey -noout -out "$key_file"
  else
    openssl genrsa -out "$key_file" "$RSA_BITS"
  fi
  chmod 600 "$key_file"

  # Build OpenSSL req config (with SAN)
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

  # Generate CSR (SHA-256)
  openssl req -new -key "$key_file" -out "$csr_file" -config "$tmpconf" -sha256
  rm -f "$tmpconf"

  echo "[generate_csr] CSR and key generated:" 
  echo "  Key: $key_file"
  echo "  CSR: $csr_file"
  echo "\n[Subject] CN=$CN, O=$ORG, OU=$OU, C=$COUNTRY"
  echo "[SAN]    $san_list"
  echo "\nVerify CSR (human-readable):"
  echo "  openssl req -in '$csr_file' -noout -text | sed -n '1,200p'"
}

main "$@"
