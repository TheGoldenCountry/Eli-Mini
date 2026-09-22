#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAVALINK_DIR="$ROOT_DIR/lavalink"
cd "$LAVALINK_DIR"
JAR_PATH="$LAVALINK_DIR/Lavalink.jar"
LOG_PATH="$LAVALINK_DIR/lavalink.log"
PID_PATH="$LAVALINK_DIR/lavalink.pid"

VERSION="${LAVALINK_VERSION:-4.2.2}"
URL="https://github.com/lavalink-devs/Lavalink/releases/download/${VERSION}/Lavalink.jar"

mkdir -p "$LAVALINK_DIR/plugins"

if ! command -v java >/dev/null 2>&1; then
  echo "Java 17+ is required for Lavalink."
  exit 1
fi

if [[ ! -f "$JAR_PATH" ]]; then
  if ! command -v curl >/dev/null 2>&1; then
    echo "curl is required to download Lavalink."
    exit 1
  fi

  echo "Downloading Lavalink ${VERSION}..."
  curl -fL --retry 3 --retry-all-errors "$URL" -o "$JAR_PATH"
fi

if [[ "${1:-}" == "--background" ]]; then
  if [[ -f "$PID_PATH" ]]; then
    old_pid="$(cat "$PID_PATH" 2>/dev/null || true)"
    if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
      echo "Lavalink is already running with PID $old_pid."
      exit 0
    fi
    rm -f "$PID_PATH"
  fi

  echo "Starting Lavalink in the background..."
  nohup java -Xms128M -Xmx512M -jar "$JAR_PATH"     >"$LOG_PATH" 2>&1 < /dev/null &
  echo $! > "$PID_PATH"
  echo "Lavalink PID: $!"
  echo "Lavalink log: $LOG_PATH"
  exit 0
fi

exec java -Xms128M -Xmx512M -jar "$JAR_PATH"
