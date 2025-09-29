#!/usr/bin/env bash
# Script to be copied to the Raspberry Pi and executed there.
# It will clone/update the repo, switch to the preconfigured branch,
# run the non-interactive Pi setup for MCP2515, and report helpful status.

set -euo pipefail

REPO_URL='https://github.com/variousdemeanors/Rpi4-OBD2-datalogger-custom-sensors.git'
REPO_DIR="$HOME/Rpi4-OBD2-datalogger-custom-sensors"
BRANCH='preconfigured/pi-zero-mcp2515'

echo "[remote-script] Running on $(hostname) as $(whoami)"

if [ -d "$REPO_DIR/.git" ]; then
  echo "[remote-script] Repo exists at $REPO_DIR — fetching updates"
  cd "$REPO_DIR"
  git fetch origin || true
  git checkout "$BRANCH" || git checkout -b "$BRANCH" "origin/$BRANCH"
  git pull origin "$BRANCH" || true
else
  echo "[remote-script] Cloning repo to $REPO_DIR"
  git clone "$REPO_URL" "$REPO_DIR"
  cd "$REPO_DIR"
  git checkout "$BRANCH"
fi

echo "[remote-script] Running one-shot setup (may prompt for sudo password)"
sudo bash ./scripts/setup_pi_mcp2515.sh || {
  echo "[remote-script] setup script failed — inspect logs or rerun manually" >&2
  exit 2
}

echo "[remote-script] Setup finished. Checking can0 and service status"
ip link show can0 || true
echo "-- config.json network.obd_connection section (grep) --"
grep -n "bitrate" config.json || true

echo "[remote-script] System service statuses (last 5 lines each)"
sudo systemctl status obd2_hub.service --no-pager -n 5 || true
sudo systemctl status obd2_web.service --no-pager -n 5 || true

echo "[remote-script] Done. If a dtoverlay was added, please reboot: sudo reboot"
