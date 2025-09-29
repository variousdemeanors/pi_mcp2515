# **RaspberryPi 4 OBD-II Datalogger & Web Dashboard**

This project is a comprehensive, configurable OBD-II datalogger and web dashboard designed for the Raspberry Pi 4\. It has been refactored from a simple script into a full-featured application with a command-line interface for setup and a web-based UI for real-time monitoring, configuration, and data analysis.

This tool is perfect for car enthusiasts, mechanics, or anyone interested in monitoring their vehicle's performance and health in a highly customizable way.

## **🚀 Quick Start (Automated Setup)**

For the fastest setup experience with wireless CAN (Acebott ESP32), use the automated setup:

### **Windows:**
```bash
# Double-click or run:
quick_start.bat
```

### **Linux/Raspberry Pi:**
```bash
# Make executable and run:
chmod +x quick_start.sh
./quick_start.sh

# Or run directly:
python3 quick_start.py
```

The automated setup will:
1. ✅ Install required dependencies
2. 🔍 Auto-detect wireless CAN transceivers
3. ⚙️ Configure connection settings
4. 🚀 Launch the datalogger

### **Manual Automated Setup Options:**
```bash
# Auto-detect and setup wireless CAN only:
python3 auto_setup.py --wireless-only

# Full automated setup (tries all connection types):
python3 auto_setup.py

# Traditional manual setup:
python3 setup.py
```

## **Features**

* **Dual Interface**: Configure the application via a powerful command-line menu or through a secure, modern web dashboard.  
* **Flexible Network Setup**: Operate in Wi-Fi Access Point (AP) mode (acting as its own hotspot) or Client mode (connecting to an existing network).  
* **Advanced Datalogging**:  
  * Customize log file names and output directories.  
  * Choose between creating a new log file for every session or appending to a single static file.  
* **Dynamic PID Management**:  
  * Automatically discover all PIDs supported by your vehicle.  
  * Interactively select which PIDs to log from the discovered list via the CLI or web UI.  
* **Performance Benchmarking**: Run a benchmark test to determine the optimal data logging speed your hardware and vehicle can support, measuring PIDs per second and error rates.  
* **Secure Web Dashboard**:  
  * A password-protected web interface for all features.  
  * View real-time data with a live-updating chart and metrics display.  
  * Modify all application settings directly from your browser.  
* **Powerful Log Analysis**:  
  * Select from previously created log files or upload your own.  
  * Generate interactive, zoomable charts with Plotly.js to visualize your data.  
  * View a table of key statistics (min, max, mean, etc.) for all logged parameters.  
* **Systemd Service**: Install a systemd service to automatically start the datalogger or web dashboard on boot for headless operation.
* **External Sensor Integration**: Log data from multiple external microcontrollers (like ESP32s) alongside your OBD-II data. Simply add your devices' URLs to the config file, and their JSON data will be automatically fetched, synchronized, and added as new columns in the CSV log.

### **External Sensor Integration (ESP32 and others)**

This application can fetch data from any number of external devices that expose a simple JSON API endpoint. This is ideal for logging custom sensors (like boost pressure, methanol injection PSI, etc.) alongside the standard OBD-II data.

**Configuration (`config.json`)**

To use this feature, first enable it in the `setup.py` script. Then, edit the `esp32` section of your `config.json` file. It should contain a list of `devices`, where each device is an object with a `name` and a `url`.

```json
"esp32": {
  "enabled": true,
  "devices": [
    {
      "name": "BoostController",
      "url": "http://192.168.1.100/data"
    },
    {
      "name": "MethanolController",
      "url": "http://192.168.1.101/data"
    }
  ]
}
```

**ESP32 JSON Format**

Each device's URL should return a JSON object where the keys are the sensor names (which will become the column headers in the CSV) and the values are the sensor readings.

*Example response from `http://192.168.1.100/data`*:
```json
{
  "Boost_PSI": 14.7,
  "Wastegate_Duty": 30.5
}
```

*Example response from `http://192.168.1.101/data`*:
```json
{
  "Methanol_PSI": 150.2
}
```

The datalogger will fetch data from each URL in the list during every logging cycle and add all the key-value pairs to the data store. These will then appear as new columns in your CSV file, synchronized with the OBD-II data for that timestamp.

## **Requirements**

*   Python 3.x
*   An ELM327-compatible OBD-II **USB or Bluetooth** adapter.
*   All Python libraries listed in `requirements.txt`.

## **Installation and Setup**

This project includes an interactive setup script that will guide you through the installation and configuration process.

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_name>
    ```

2.  **Create a Python virtual environment (Recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Run the Interactive Setup Script:**
    ```bash
    python3 setup.py
    ```
    This script is mandatory on first run. It will:
    *   Ask you to choose your OBD-II adapter type (USB or Bluetooth).
    *   If you select Bluetooth on a Linux system, it will offer to automatically install the required system dependencies.
    *   Install all the necessary Python libraries from `requirements.txt`.
    *   Create a `config.json` file with your connection preferences.

## **How to Use**

After running the setup script, all further configuration is handled through the main application.

### **First-Time Setup**

1. **Run the application:**  
   python3 main.py

2. **Follow the CLI Menu**: On first run, you should go through the menus in order:  
   * **Network Setup**: Choose whether the device should create its own Wi-Fi network (AP Mode) or connect to an existing one (Client Mode).  
   * **Web Dashboard Security**: Set the username and password for the web dashboard. This is required to access the web UI.  
   * **PID Management**:  
     * Run "Discover and Save Supported PIDs" to connect to your vehicle and see what data is available.  
     * Run "Select PIDs to Log" to choose which of the discovered PIDs you want to record.  
   * **System Service (Optional)**: If you want the application to run automatically on boot, use this menu to install the systemd service and configure what should autostart (e.g., the web dashboard).

### **Running the Application**

* **To run the CLI menu**: python3 main.py  
* **To start the Datalogger directly**: Choose this option from the CLI menu.  
* **To start the Web Dashboard**: Choose this option from the CLI menu. If you configured the device in AP mode, the URL will be http://192.168.4.1:5000 (or as configured). If in Client mode, you will need to find the Raspberry Pi's IP address on your network.

## **Future Development Goals**

### **WMI (Water-Methanol Injection) Integration**

A primary long-term goal for this project is to merge it with the "WMI Control Dashboard" project. The vision is to create a single, comprehensive system that not only handles vehicle datalogging but also provides full control and monitoring of a water-methanol injection system.

**Current Status & Challenges:**

The dashboard.py script in the original version of this project contained non-functional code intended to fetch data from an ESP32. This was an early attempt at this integration.

The ESP32 integration has been preserved but made optional and configurable. The core/datalogger.py module can be enabled to fetch data from a configured URL, allowing custom data sources to be logged alongside OBD-II parameters.

The main challenge is designing a robust communication protocol between the Raspberry Pi and the WMI controller (presumably the ESP32) and creating a seamless UI that combines control, configuration, and data visualization for both systems.

This will likely involve expanding the web dashboard significantly with new pages for WMI control and configuration.

This section will be updated as the integration plan develops.
