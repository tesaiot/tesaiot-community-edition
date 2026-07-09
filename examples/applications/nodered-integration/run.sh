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

# TESAIoT Node-RED helper script
# Tutorial-style helper for macOS/Linux that mirrors the README steps:
#  1. bootstrap → install dependencies
#  2. build     → compile TypeScript nodes
#  3. start     → run Node-RED with TESAIoT profile
#  4. compose   → launch the Docker stack for reproducible demos
# The comments favour beginner/intermediate developers so they understand the
# rationale behind each guard (e.g., Node version check, .env loading).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="tesaiot-nodered"
PACKAGE_MANAGER="npm"

usage() {
  cat <<USAGE
Usage: $(basename "$0") <command>

Commands
  bootstrap          Install Node dependencies (runs "${PACKAGE_MANAGER} install")
  build              Compile TypeScript sources (runs "${PACKAGE_MANAGER} run build")
  start              Start Node-RED locally with current workspace (runs "${PACKAGE_MANAGER} start")
  compose up         Build image and start the Docker service (foreground logs)
  compose down       Stop and remove the Docker service
  compose logs       Tail Docker logs for the service
  clean              Remove node_modules and dist artifacts

Environment
  NODE_VERSION requirement: >= 18.18 (use nvm or Homebrew node@20 on macOS)
  DOCKER_COMPOSE_BIN override the docker compose executable if required
USAGE
}

ensure_command() {
  # Guard against missing tooling so beginners see a clear error message.
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Command '$1' not found. Please install it before continuing." >&2
    exit 1
  fi
}

ensure_node_version() {
  # The FlowFuse dashboard build requires modern Node.js - bail out early if too old.
  ensure_command node
  local version major minor patch
  version="$(node -v | sed 's/^v//')"
  IFS='.' read -r major minor patch <<<"$version"
  if (( major < 18 )) || { (( major == 18 )) && (( minor < 18 )); }; then
    echo "Node version >= 18.18.0 is required. Current: v$version" >&2
    exit 1
  fi
}

load_env_file() {
  # Mirror README instructions: auto-source .env if available so npm scripts pick up API key.
  if [ -f "$SCRIPT_DIR/.env" ]; then
    # shellcheck disable=SC1090
    set -a; source "$SCRIPT_DIR/.env"; set +a
  else
    echo "⚠️  .env not found. Copy .env.example to .env and provide TESAIOT_API_KEY before starting." >&2
  fi
}

npm_exec() {
  # Wrapper so every npm command runs from the project root with version checks applied.
  ensure_node_version
  pushd "$SCRIPT_DIR" >/dev/null
  ${PACKAGE_MANAGER} "$@"
  popd >/dev/null
}

compose_bin() {
  # Resolve docker compose binary name (native plugin preferred, fallback to v1).
  if [ -n "${DOCKER_COMPOSE_BIN:-}" ]; then
    echo "$DOCKER_COMPOSE_BIN"
    return
  fi
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    echo "docker compose"
  elif command -v docker-compose >/dev/null 2>&1; then
    echo "docker-compose"
  else
    echo ""
  fi
}

compose_exec() {
  # Execute docker compose commands in project root while reminding users about .env.
  local bin
  bin="$(compose_bin)"
  if [ -z "$bin" ]; then
    echo "Docker Compose is required. Install Docker Desktop (macOS) or docker compose plugin." >&2
    exit 1
  fi
  pushd "$SCRIPT_DIR" >/dev/null
  if [ ! -f .env ]; then
    echo "⚠️  .env not found. Copy .env.example to .env and provide TESAIOT_API_KEY before running compose." >&2
  fi
  # shellcheck disable=SC2086
  $bin "$@"
  popd >/dev/null
}

check_dependencies() {
  # Ensure npm install has been executed (node_modules exists) otherwise run it.
  if [ ! -d "$SCRIPT_DIR/node_modules" ]; then
    echo "node_modules missing → running ${PACKAGE_MANAGER} install"
    npm_exec install
  fi

  # Guard against git-sourced dashboard packages that do not ship dist/ assets.
  local dashboard_dist="$SCRIPT_DIR/node_modules/@flowfuse/node-red-dashboard/dist/index.html"
  if [ ! -f "$dashboard_dist" ]; then
    cat <<MSG
⚠️  FlowFuse Dashboard assets not found (dist/index.html missing).
    This usually happens if the package was installed directly from GitHub.
    Running ${PACKAGE_MANAGER} install so the published npm release provides
    the pre-built assets.
MSG
    npm_exec install
  fi

  # Apply local dashboard patch (idempotent – skips if already patched).
  npm_exec run patch-dashboard
}

cmd_bootstrap() {
  # Install Node dependencies (npm install) - first step in README quick start.
  npm_exec install
}

cmd_build() {
  # Compile TypeScript custom nodes to dist/ (maps to README build step).
  check_dependencies
  npm_exec run build
}

cmd_start() {
  # Start Node-RED locally after ensuring dependencies and environment are set.
  ensure_node_version
  check_dependencies
  pushd "$SCRIPT_DIR" >/dev/null
  load_env_file
  ${PACKAGE_MANAGER} run build
  ${PACKAGE_MANAGER} start
  popd >/dev/null
}

cmd_compose() {
  # Thin wrapper around docker compose calls so developers can run the containerised demo.
  if [ $# -lt 1 ]; then
    echo "compose requires sub-command: up|down|logs" >&2
    exit 1
  fi
  case "$1" in
    up)
      shift
      compose_exec build --pull
      # shellcheck disable=SC2046
      compose_exec up "$@"
      ;;
    down)
      shift
      compose_exec down "$@"
      ;;
    logs)
      shift
      compose_exec logs -f "$@"
      ;;
    *)
      echo "Unknown compose command: $1" >&2
      exit 1
      ;;
  esac
}

cmd_clean() {
  pushd "$SCRIPT_DIR" >/dev/null
  rm -rf node_modules dist
  echo "Removed node_modules and dist"
  popd >/dev/null
}

if [ $# -lt 1 ]; then
  usage
  exit 1
fi

case "$1" in
  bootstrap)
    shift
    cmd_bootstrap "$@"
    ;;
  build)
    shift
    cmd_build "$@"
    ;;
  start)
    shift
    cmd_start "$@"
    ;;
  compose)
    shift
    cmd_compose "$@"
    ;;
  clean)
    shift
    cmd_clean "$@"
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    echo "Unknown command: $1" >&2
    usage
    exit 1
    ;;
esac
