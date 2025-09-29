#!/usr/bin/env bash
# Deploy script for Raspberry Pi (run on the PI as root via sudo)
# - creates a python venv
# - installs requirements
# - attempts to bring up can0 (MCP2515) and load kernel modules
# - installs systemd service units for the hub (pi_zero_2w_hub.py) and web dashboard (simple_webapp.py)

set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "This script must be run with sudo. Example: sudo ./deploy_pi.sh"
  exit 1
fi

# Resolve paths
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="/opt/obd2/venv"
# Default application user to 'bit' for zero-touch preconfigured images. If the
# deploy was invoked via sudo from a different user, honor that user instead.
APP_USER="${SUDO_USER:-bit}"
PYTHON_BIN="/usr/bin/python3"
REQUIREMENTS_FILE="$REPO_DIR/requirements.txt"
CAN_BITRATE=500000
APP_DIR="/opt/obd2/obd2-repo"

echo "Using REPO_DIR=$REPO_DIR"
echo "Using VENV_DIR=$VENV_DIR (owner: $APP_USER)"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "Python3 not found at $PYTHON_BIN. Install python3 first." >&2
  exit 2
fi

# Create venv
if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtualenv at $VENV_DIR"
  $PYTHON_BIN -m venv "$VENV_DIR"
  chown -R "$APP_USER":"$APP_USER" "$VENV_DIR" || true
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


# Ensure python-can and pyserial are present for CAN and serial support
echo "Installing python-can and pyserial into venv"
"${VENV_DIR}/bin/pip" install --no-cache-dir python-can pyserial || true

# Copy repository to APP_DIR so services run from a stable path
echo
echo "Copying repository to $APP_DIR"
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

# Ensure the APP_USER exists on the system (create as unprivileged service account if missing)
if ! id -u "$APP_USER" >/dev/null 2>&1; then
  echo "User $APP_USER does not exist; creating system user $APP_USER"
  # Create a system user with home directory to allow predictable file ownership.
  useradd --system --create-home --shell /bin/bash "$APP_USER" || true
  echo "Created user $APP_USER"
fi

# Write environment overrides for systemd units. Units may include EnvironmentFile=-/etc/default/obd2
mkdir -p /etc/default
cat > /etc/default/obd2 <<EOF
LOG_DIR=$LOG_DIR
PYTHONPATH=/opt/obd2/obd2-repo
EOF
chmod 644 /etc/default/obd2

# Ensure ownerships are correct for venv, app dir and log dir
chown -R "$APP_USER":"$APP_USER" "$VENV_DIR" || true
chown -R "$APP_USER":"$APP_USER" "$APP_DIR" || true
chown -R "$APP_USER":"$APP_USER" "$LOG_DIR" || true

# Copy repository to APP_DIR so services run from a stable path
echo
echo "Copying repository to $APP_DIR"
mkdir -p "$(dirname "$APP_DIR")"
rsync -a --delete "$REPO_DIR/" "$APP_DIR/"
chown -R "$APP_USER":"$APP_USER" "$APP_DIR"


echo
echo "-- Checking/bringing up CAN interface 'can0' --"

echo "Loading CAN kernel modules (can, can_raw, mcp251x, can_dev)"
modprobe can || true
modprobe can_raw || true
modprobe mcp251x || true
modprobe can_dev || true

echo "Trying to bring up can0 with bitrate $CAN_BITRATE"
ip link set can0 down 2>/dev/null || true
if ip link set can0 up type can bitrate $CAN_BITRATE 2>/dev/null; then
  echo "can0 is up"
else
  echo "Failed to bring up can0 automatically."
  echo "If you're using an MCP2515 SPI CAN adapter, ensure the proper dtoverlay is present in /boot/config.txt and reboot."
  echo "Example overlay line to add (on Raspberry Pi OS): dtoverlay=mcp2515-can0,oscillator=16000000,interrupt=25"
  echo "After adding the overlay, reboot and re-run this script. You can also try: sudo ip link set can0 up type can bitrate $CAN_BITRATE"
fi

echo
echo "-- Installing systemd service units --"

SYSTEMD_DIR_SOURCE="$REPO_DIR/systemd"
if [ ! -d "$SYSTEMD_DIR_SOURCE" ]; then
  echo "No systemd unit files found in $SYSTEMD_DIR_SOURCE. Make sure this repo contains systemd/*.service" >&2
else
  for unit in "$SYSTEMD_DIR_SOURCE"/*.service; do
    [ -e "$unit" ] || continue
    echo "Installing $(basename "$unit") to /etc/systemd/system/"
    cp "$unit" /etc/systemd/system/
  done
  systemctl daemon-reload
  echo "Enabling and starting services"
  # Enable known units if present
  for u in obd2_hub.service obd2_web.service obd2_startup.service; do
    if [ -f "/etc/systemd/system/$u" ]; then
      systemctl enable --now "$u"
      echo "Enabled and started $u"
    fi
  done
  # Patch installed unit files to run as APP_USER to support Pi images with user 'bit'
  echo "Patching unit files to run as user: $APP_USER"
  for installed in /etc/systemd/system/*.service; do
    [ -e "$installed" ] || continue
    # Leave the boot oneshot unit alone so it will run as root and can perform kernel/module operations
    if [ "$(basename "$installed")" = "obd2_startup.service" ]; then
      echo "Skipping user/group patch for $(basename "$installed")"
      continue
    fi
    sed -i "s/^User=.*/User=$APP_USER/" "$installed" || true
    sed -i "s/^Group=.*/Group=$APP_USER/" "$installed" || true
    # Ensure Environment=LOG_DIR is present and set to the selected LOG_DIR
    if grep -q '^Environment=LOG_DIR=' "$installed" 2>/dev/null; then
      sed -i "s|^Environment=LOG_DIR=.*|Environment=LOG_DIR=$LOG_DIR|" "$installed" || true
    else
      if grep -q '^Environment=PATH=' "$installed" 2>/dev/null; then
        sed -i "/^Environment=PATH=/a Environment=LOG_DIR=$LOG_DIR" "$installed" || true
      elif grep -q '^WorkingDirectory=' "$installed" 2>/dev/null; then
        sed -i "/^WorkingDirectory=/a Environment=LOG_DIR=$LOG_DIR" "$installed" || true
      else
        sed -i "/^ExecStart=/i Environment=LOG_DIR=$LOG_DIR" "$installed" || true
      fi
    fi
  done
  # Install sudoers rule to allow the webapp user to run network helper without password
  SUDOERS_FILE="/etc/sudoers.d/obd2_network_helper"
  echo "$APP_USER ALL=(ALL) NOPASSWD: /opt/obd2/venv/bin/python /opt/obd2/obd2-repo/scripts/network_helper.py *" > "$SUDOERS_FILE"
  chmod 440 "$SUDOERS_FILE"
  echo "Installed sudoers rule at $SUDOERS_FILE"
  # Reload systemd to apply any unit file changes and restart services so new Environment variables are used
  systemctl daemon-reload || true
  for u in obd2_hub.service obd2_web.service; do
    if [ -f "/etc/systemd/system/$u" ]; then
      systemctl restart "$u" || true
      echo "Restarted $u to pick up LOG_DIR"
    fi
  done
fi

echo
echo "Deploy complete."
echo "Tips:"
echo " - Check service status: sudo systemctl status obd2_hub.service obd2_web.service"
echo " - Check logs: sudo journalctl -u obd2_hub.service -f"
echo " - If can0 isn't present, confirm SPI wiring and /boot/config.txt dtoverlay and reboot."

exit 0
