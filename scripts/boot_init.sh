#!/usr/bin/env bash
# Boot initialization for OBD2 system
# - loads CAN kernel modules
# - tries to bring up can0
# - ensures python venv exists and then starts systemd services

set -e

LOGFILE=/var/log/obd2/boot_init.log
mkdir -p /var/log/obd2
echo "$(date -Is) - Boot init starting" >> "$LOGFILE"

modprobe can || true
modprobe can_raw || true
modprobe mcp251x || true
modprobe can_dev || true

# Try to bring up can0; ignore errors and log guidance
if ip link show can0 >/dev/null 2>&1; then
  echo "$(date -Is) - Probing CAN bitrates for can0" >> "$LOGFILE"
  if ip link set can0 up type can bitrate 500000 2>/dev/null; then
    echo "$(date -Is) - can0 up at 500000" >> "$LOGFILE"
    DETECTED=500000
  elif ip link set can0 up type can bitrate 250000 2>/dev/null; then
    echo "$(date -Is) - can0 up at 250000" >> "$LOGFILE"
    DETECTED=250000
  else
    echo "$(date -Is) - Failed to bring up can0 at common bitrates" >> "$LOGFILE"
    DETECTED=0
  fi

  # If we detected a bitrate and config exists, patch it
  if [ "$DETECTED" -ne 0 ] && [ -f "/opt/obd2/obd2-repo/config.json" ]; then
    python3 - <<PY >> "$LOGFILE" 2>&1
import json
p='/opt/obd2/obd2-repo/config.json'
with open(p,'r') as f:
    cfg=json.load(f)
cfg.setdefault('network',{}).setdefault('obd_connection',{})['bitrate']= $DETECTED
with open(p,'w') as f:
    json.dump(cfg,f,indent=2)
print('Patched bitrate into',p)
PY
  fi
else
  echo "$(date -Is) - can0 not present (check dtoverlay/mcp2515)" >> "$LOGFILE"
fi

# Ensure venv path exists (deployed via deploy_pi.sh)
if [ -d "/opt/obd2/venv" ]; then
  echo "$(date -Is) - venv exists" >> "$LOGFILE"
else
  echo "$(date -Is) - venv missing at /opt/obd2/venv" >> "$LOGFILE"
fi
echo "$(date -Is) - Boot init complete" >> "$LOGFILE"

exit 0
