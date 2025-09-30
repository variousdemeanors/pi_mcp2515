#!/usr/bin/env bash
# Non-interactive setup script for Raspberry Pi (MCP2515 preconfigured)
# Usage: sudo ./scripts/setup_pi_mcp2515.sh

set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "This script must be run with sudo. Example: sudo ./scripts/setup_pi_mcp2515.sh"
  exit 1
fi

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="/opt/obd2/venv"
APP_USER="${SUDO_USER:-pi}"
PYTHON_BIN="/usr/bin/python3"
REQUIREMENTS_FILE="$REPO_DIR/requirements.txt"
CAN_BITRATE=500000
APP_DIR="/opt/obd2/obd2-repo"
PRECONFIG="$REPO_DIR/config.preconfigured_mcp2515.json"

echo "Preparing Pi for MCP2515 CAN (REPO_DIR=$REPO_DIR, APP_DIR=$APP_DIR)"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "Python3 not found at $PYTHON_BIN. Install python3 first." >&2
  exit 2
fi

# Create venv
if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtualenv at $VENV_DIR"
  $PYTHON_BIN -m venv "$VENV_DIR"
  chown -R "$APP_USER":"$APP_USER" "$VENV_DIR"
fi

echo "Installing/Upgrading pip in venv"
"$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel

if [ -f "$REQUIREMENTS_FILE" ]; then
  echo "Installing requirements from $REQUIREMENTS_FILE"
  "$VENV_DIR/bin/pip" install -r "$REQUIREMENTS_FILE"
else
  echo "Requirements file not found at $REQUIREMENTS_FILE — skipping pip install"
fi

# Ensure python-can and pyserial are present for CAN and serial support
echo "Installing python-can and pyserial into venv"
"${VENV_DIR}/bin/pip" install --no-cache-dir python-can pyserial || true

# Ensure log directory
mkdir -p /var/log/obd2
chown -R "$APP_USER":"$APP_USER" /var/log/obd2

echo
echo "-- Copying repository to $APP_DIR --"
mkdir -p "$(dirname "$APP_DIR")"
rsync -a --delete "$REPO_DIR/" "$APP_DIR/"
chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

# Determine log directory from deployed config.json (if present) and ensure ownership
LOG_DIR_DEFAULT="/var/log/obd2"
LOG_DIR="$LOG_DIR_DEFAULT"
if [ -f "$APP_DIR/config.json" ]; then
  LOG_FROM_CFG=$(python3 - <<PY
import json,sys
try:
    cfg=json.load(open(r"$APP_DIR/config.json"))
    print(cfg.get('datalogging',{}).get('output_path',''))
except Exception:
    pass
PY
)
  if [ -n "$LOG_FROM_CFG" ]; then
    LOG_DIR="$LOG_FROM_CFG"
  fi
fi
mkdir -p "$LOG_DIR" || true
chown -R "$APP_USER":"$APP_USER" "$LOG_DIR" || true
echo "Log directory set to $LOG_DIR (owner: $APP_USER)"

echo
echo "-- Installing MCP2515 dtoverlay into /boot/config.txt (idempotent) --"
DT_LINE='dtoverlay=mcp2515-can0,oscillator=16000000,interrupt=25'
SPI_LINE='dtparam=spi=on'
if [ -f "/boot/firmware/config.txt" ]; then
  CONFIG_TXT="/boot/firmware/config.txt"
elif [ -f "/boot/firmware/config" ]; then
  CONFIG_TXT="/boot/firmware/config"
else
  CONFIG_TXT="/boot/config.txt"
fi
# Enable SPI if not already enabled
if ! grep -Fq "$SPI_LINE" "$CONFIG_TXT" 2>/dev/null; then
  echo "$SPI_LINE" >> "$CONFIG_TXT"
  echo "Enabled SPI in $CONFIG_TXT"
else
  echo "SPI already enabled in $CONFIG_TXT"
fi
# Add MCP2515 dtoverlay
if ! grep -Fq "$DT_LINE" "$CONFIG_TXT" 2>/dev/null; then
  echo "$DT_LINE" >> "$CONFIG_TXT"
  echo "Added dtoverlay to $CONFIG_TXT (requires reboot to take full effect)."
else
  echo "dtoverlay already present in $CONFIG_TXT"
fi

echo
echo "-- Loading CAN kernel modules --"
modprobe can || true
modprobe can_raw || true
modprobe mcp251x || true
modprobe can_dev || true

echo "Probing CAN bitrates (trying 500000 then 250000)"
ip link set can0 down 2>/dev/null || true
DETECTED_BITRATE=0
if ip link set can0 up type can bitrate 500000 2>/dev/null; then
  DETECTED_BITRATE=500000
  echo "can0 is up at 500000"
elif ip link set can0 up type can bitrate 250000 2>/dev/null; then
  DETECTED_BITRATE=250000
  echo "can0 is up at 250000"
else
  echo "Failed to bring up can0 automatically at common bitrates. It may require a reboot for the dtoverlay to take effect."
fi

echo "Detected CAN bitrate: ${DETECTED_BITRATE:-0}"

echo
echo "-- Installing systemd service units --"
SYSTEMD_DIR_SOURCE="$REPO_DIR/systemd"
if [ -d "$SYSTEMD_DIR_SOURCE" ]; then
  for unit in "$SYSTEMD_DIR_SOURCE"/*.service; do
    [ -e "$unit" ] || continue
    echo "Installing $(basename "$unit") to /etc/systemd/system/"
    cp "$unit" /etc/systemd/system/
  done
  # Ensure the installed unit files run as the intended application user
  echo "Patching installed systemd unit user/group to '$APP_USER'"
  for installed in /etc/systemd/system/*.service; do
    [ -e "$installed" ] || continue
    # Do NOT override the boot-initialization oneshot unit; it must run as root
    if [ "$(basename "$installed")" = "obd2_startup.service" ]; then
      echo "Skipping user/group patch for $(basename "$installed") (must run as root)"
      continue
    fi
    sed -i "s/^User=.*/User=$APP_USER/" "$installed" || true
    sed -i "s/^Group=.*/Group=$APP_USER/" "$installed" || true
  done
  # Install sudoers rule to allow the webapp user to run network helper without password
  SUDOERS_FILE="/etc/sudoers.d/obd2_network_helper"
  echo "$APP_USER ALL=(ALL) NOPASSWD: /opt/obd2/venv/bin/python /opt/obd2/obd2-repo/scripts/network_helper.py *" > "$SUDOERS_FILE"
  chmod 440 "$SUDOERS_FILE"
  echo "Installed sudoers rule at $SUDOERS_FILE"
  systemctl daemon-reload
  echo "Enabling and starting services"
  for u in obd2_startup.service obd2_hub.service obd2_web.service; do
    if [ -f "/etc/systemd/system/$u" ]; then
      systemctl enable --now "$u" || true
      echo "Enabled and attempted to start $u"
    fi
  done
else
  echo "No systemd unit files found in $SYSTEMD_DIR_SOURCE"
fi

echo
echo "-- Applying preconfigured config (MCP2515) --"
if [ -f "$PRECONFIG" ]; then
  cp "$PRECONFIG" "$APP_DIR/config.json"
  chown "$APP_USER":"$APP_USER" "$APP_DIR/config.json"
  echo "Installed preconfigured config to $APP_DIR/config.json"
  # If we detected a bitrate, update the copied config.json accordingly
  if [ "$DETECTED_BITRATE" -ne 0 ]; then
    echo "Patching config.json with detected bitrate $DETECTED_BITRATE"
    python3 - <<PY
import json
p='''$APP_DIR/config.json'''
with open(p,'r') as f:
    cfg=json.load(f)
cfg.setdefault('network',{}).setdefault('obd_connection',{})['bitrate'] = $DETECTED_BITRATE
with open(p,'w') as f:
    json.dump(cfg,f,indent=2)
print('Patched bitrate into',p)
PY
  else
    echo "No bitrate detected; config.json left unchanged."
  fi
else
  echo "Preconfigured config not found at $PRECONFIG — skipping"
fi

echo
echo "Setup complete. Notes:"
echo " - If you added the dtoverlay, reboot is recommended: sudo reboot"
echo " - Check can interface: ip link show can0 || true"
echo " - Check service status: sudo systemctl status obd2_hub.service obd2_web.service"

exit 0
