import os
import getpass
import subprocess

SERVICE_NAME = "datalogger.service"
SERVICE_FILE_PATH = f"/etc/systemd/system/{SERVICE_NAME}"

def get_service_template(working_dir, python_executable):
    """
    Returns the systemd service file content as a string template.
    """
    user = getpass.getuser()
    return f"""[Unit]
Description=OBD-II Datalogger and Web Dashboard Service
After=network.target

[Service]
User={user}
WorkingDirectory={working_dir}
ExecStart={python_executable} {os.path.join(working_dir, 'main.py')} --start-service
Restart=always

[Install]
WantedBy=multi-user.target
"""

def generate_service_file():
    """
    Generates the systemd service file content.
    """
    working_dir = os.getcwd()
    # This is a bit of a guess, but usually correct on Debian-based systems like RPi OS
    python_executable = '/usr/bin/python3'
    return get_service_template(working_dir, python_executable)

def install_service():
    """
    Generates and installs the systemd service file.
    This function requires sudo privileges to run.
    """
    print("--- Installing Systemd Service ---")
    print(f"This will create a service named '{SERVICE_NAME}'.")
    print("You may be prompted for your password to grant sudo permissions.")

    service_content = generate_service_file()

    try:
        # Write the service file using sudo
        write_cmd = f"echo '{service_content}' | sudo tee {SERVICE_FILE_PATH}"
        subprocess.run(write_cmd, shell=True, check=True, capture_output=True)
        print(f"Service file written to {SERVICE_FILE_PATH}")

        # Reload the systemd daemon
        print("Reloading systemd daemon...")
        subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)

        # Enable the service to start on boot
        print(f"Enabling service '{SERVICE_NAME}' to start on boot...")
        subprocess.run(["sudo", "systemctl", "enable", SERVICE_NAME], check=True)

        print("\n--- Service Installation Complete ---")
        print("You can now manage the service with commands like:")
        print(f"  sudo systemctl start {SERVICE_NAME}")
        print(f"  sudo systemctl stop {SERVICE_NAME}")
        print(f"  sudo systemctl status {SERVICE_NAME}")
        return True

    except subprocess.CalledProcessError as e:
        print("\n--- ERROR: Service installation failed. ---")
        print(f"Command '{e.cmd}' returned non-zero exit status {e.returncode}.")
        if e.stderr:
            print(f"Error output: {e.stderr.decode('utf-8')}")
        return False
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        return False
