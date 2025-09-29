Deploy scripts for Raspberry Pi

deploy_pi.sh
- Run as root (sudo) from the Raspberry Pi to install the application into /opt/obd2,
  create a Python virtualenv, install requirements, attempt to bring up can0 (MCP2515),
  and install systemd unit files found in the repository's systemd/ directory.

Usage:
  sudo ./deploy_pi.sh

Notes:
- Ensure SPI and the mcp2515 dtoverlay are configured in /boot/config.txt if using MCP2515.
- This script copies the repo into /opt/obd2/obd2-repo — systemd units reference that path.
