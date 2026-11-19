#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright TESAIoT Platform contributors
#
# Fail the build when the code calls a pydantic API from a major the image does
# not install.
#
# WHY THIS EXISTS
# ---------------
# services/api/requirements.txt pinned pydantic 1.10.13 while two model files
# called model_dump(), which exists only in pydantic 2. Both files even declare
# their target in a comment — "Pydantic v1 compatibility" — seventeen and thirty
# lines above the call. The result was an AttributeError on a live path (CSR
# workflow tracking and enhanced device logging) that no test, lint or type check
# could see, because nothing in CI installs requirements.txt or imports the models.
#
# The check reads the pin and derives what is legal from it, so it keeps working
# when the pin moves: on pydantic 1 it rejects v2-only spellings, and on pydantic 2
# it rejects the v1 ones. A migration flips the check by editing one line —
# requirements.txt — which is the point.
set -euo pipefail

cd "$(dirname "$0")/.."

REQ="services/api/requirements.txt"
TARGETS="services/api services/mqtt-bridge"

pin="$(grep -E '^pydantic==' "$REQ" | head -1 | cut -d= -f3)"
[ -n "$pin" ] || { echo "::error file=$REQ::no 'pydantic==' pin found"; exit 1; }
major="${pin%%.*}"
echo "pydantic pinned at $pin (major $major) in $REQ"

fail=0
report() {  # report <label> <pattern> [file:line exemptions...]
  # Comment lines are not code and are skipped. A hit whose code also matches
  # $EXCLUDE (when set) is skipped too.
  local label="$1" pattern="$2"; shift 2
  local hits
  hits="$(grep -rnE --include='*.py' -- "$pattern" $TARGETS || true)"
  [ -n "$hits" ] || return 0
  while IFS= read -r hit; do
    local loc="${hit%%:*}"; local rest="${hit#*:}"; loc="$loc:${rest%%:*}"
    local code="${rest#*:}"
    if [[ "$code" =~ ^[[:space:]]*# ]]; then continue; fi
    if [ -n "${EXCLUDE:-}" ] && grep -qE -- "$EXCLUDE" <<< "$code"; then continue; fi
    for allowed in "$@"; do
      if [ "$loc" = "$allowed" ]; then continue 2; fi
    done
    echo "::error file=${loc%%:*},line=${loc##*:}::pydantic $major is pinned, but this is $label: ${hit#*:*:}"
    fail=1
  done <<< "$hits"
}

if [ "$major" = "1" ]; then
  # v2-only APIs. Calling any of these under a v1 pin raises at runtime, or —
  # worse — is silently ignored, which is what model_config does here.
  report "a pydantic v2 API"      '\.model_dump\(|\.model_dump_json\(|\.model_validate\(|\.model_copy\('
  report "a pydantic v2 validator" '@field_validator|@model_validator'
  # KNOWN AND ACCEPTED, for now: nine model_config = ConfigDict(validate_assignment=True)
  # declarations in performance_models.py. Under the v1 pin they are inert — the
  # validation the author asked for does not happen. Converting them to
  # `class Config` would switch that validation ON, which is a behaviour change on
  # nine model classes and needs its own decision and its own verification, so it
  # is a separate work package. The exemption is listed line by line, deliberately:
  # a tenth one cannot be added without editing this file.
  PM="services/api/api/modules/device_management/models/performance_models.py"
  report "a pydantic v2 config"   'model_config *=|ConfigDict' \
    "$PM:18" "$PM:89" "$PM:113" "$PM:139" "$PM:162" "$PM:184" \
    "$PM:208" "$PM:233" "$PM:265" "$PM:286"
else
  # The mirror image, for after the migration.
  report "a pydantic v1 API" \
    '\.dict\(|\.parse_obj\(|\.parse_raw\(|\.parse_file\(|\.from_orm\(|\.copy\(update=|\.__fields__|\.schema\(\)|\.schema_json\(|\.update_forward_refs\(|@validator\(|@root_validator'
  report "a pydantic v1 config key" \
    'allow_population_by_field_name|orm_mode *=|allow_mutation *=|(^|[^_[:alnum:]])schema_extra *='
  report "a v1-only field argument" \
    '(Field|constr|conlist|conset|confrozenset)\([^)]*(regex|min_items|max_items|const)='
  # .json() on a model is pydantic 1. The one other .json() in this tree is
  # requests' Response.json(), always on a variable named response/resp/res/r,
  # so those receivers are excluded rather than whole files.
  EXCLUDE='(^|[^_[:alnum:]])(response|resp|res|r)\.json\(' \
    report "a pydantic v1 API" '\.json\('
  # A nested `class Config:` is a pydantic 1 model config. The Flask settings
  # classes in this tree are module-level, which is why the indentation decides.
  report "a pydantic v1 config" '^[[:space:]]+class Config:'
  # Not covered: a Field( whose v1-only argument sits on a later line.
fi

if [ "$fail" -eq 0 ]; then
  echo "no pydantic-major violations"
else
  echo "pydantic-major violations found — fix the call sites, or move the pin and re-run"
fi
exit "$fail"
