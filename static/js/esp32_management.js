// ESP32 Sensor Management JavaScript

class ESP32Manager {
    constructor() {
        this.initializeEventListeners();
        this.loadConfiguredSensors();
        this.loadNetworkInfo();
    }

    initializeEventListeners() {
        document.getElementById('scan-network').addEventListener('click', () => this.scanNetwork());
        document.getElementById('add-manual').addEventListener('click', () => this.addManualSensor());
        document.getElementById('refresh-clients').addEventListener('click', () => this.loadNetworkInfo());
        document.getElementById('reboot-network').addEventListener('click', () => this.rebootNetwork());
        document.getElementById('close-modal').addEventListener('click', () => this.closeModal());
        document.getElementById('save-sensor').addEventListener('click', () => this.saveSensorConfig());
        const closeMon = document.getElementById('close-monitor');
        if (closeMon) closeMon.addEventListener('click', () => this.stopMonitor());
    }

    async scanNetwork() {
        const statusEl = document.getElementById('scan-status');
        const scanBtn = document.getElementById('scan-network');
        
        statusEl.textContent = 'Scanning network...';
        scanBtn.disabled = true;
        
        try {
            const response = await fetch('/api/esp32/scan', { method: 'POST' });
            const data = await response.json();
            
            if (data.success) {
                this.displayDiscoveredDevices(data.devices);
                statusEl.textContent = `Found ${data.devices.length} devices`;
            } else {
                statusEl.textContent = `Scan failed: ${data.error}`;
            }
        } catch (error) {
            statusEl.textContent = `Scan error: ${error.message}`;
        } finally {
            scanBtn.disabled = false;
            setTimeout(() => statusEl.textContent = '', 3000);
        }
    }

    displayDiscoveredDevices(devices) {
        const container = document.getElementById('discovered-devices');
        container.innerHTML = '';

        devices.forEach(device => {
            const deviceCard = document.createElement('div');
            deviceCard.className = 'bg-gray-700 p-4 rounded';
            deviceCard.innerHTML = `
                <div class="text-white font-semibold">${device.ip}</div>
                <div class="text-gray-300 text-sm mb-2">Type: ${device.type || 'Unknown'}</div>
                <div class="text-gray-300 text-xs mb-3">
                    Sample: <code class="bg-gray-600 px-1 rounded">${JSON.stringify(device.sample).slice(0, 50)}...</code>
                </div>
                <div class="flex space-x-2">
                    <button onclick="esp32Manager.configureSensor('${device.ip}', ${JSON.stringify(device).replace(/"/g, '&quot;')})" 
                            class="bg-blue-500 hover:bg-blue-700 text-white text-sm px-3 py-1 rounded">
                        Configure
                    </button>
                    <button onclick="esp32Manager.testSensor('${device.url || (`http://${device.ip}/data`)}')" 
                            class="bg-green-500 hover:bg-green-700 text-white text-sm px-3 py-1 rounded">
                        Test
                    </button>
                    <button onclick="esp32Manager.startMonitor('${device.url || (`http://${device.ip}/data`)}')"
                            class="bg-purple-500 hover:bg-purple-700 text-white text-sm px-3 py-1 rounded">
                        Live
                    </button>
                </div>
            `;
            container.appendChild(deviceCard);
        });
    }

    async loadConfiguredSensors() {
        try {
            const response = await fetch('/api/esp32/configured');
            const data = await response.json();
            
            if (data.success) {
                this.displayConfiguredSensors(data.sensors);
            }
        } catch (error) {
            console.error('Failed to load configured sensors:', error);
        }
    }

    displayConfiguredSensors(sensors) {
        const container = document.getElementById('configured-sensors');
        container.innerHTML = '';

        if (sensors.length === 0) {
            container.innerHTML = '<div class="text-gray-400">No sensors configured</div>';
            return;
        }

        sensors.forEach((sensor, index) => {
            const sensorCard = document.createElement('div');
            sensorCard.className = 'bg-gray-700 p-4 rounded flex justify-between items-center';
            sensorCard.innerHTML = `
                <div>
                    <div class="text-white font-semibold">${sensor.name}</div>
                    <div class="text-gray-300 text-sm">${sensor.url}</div>
                    <div class="text-gray-400 text-xs">PID: ${sensor.pid_name || 'Auto'} | Type: ${sensor.data_type || 'Auto'}</div>
                </div>
                <div class="flex space-x-2">
                    <button onclick="esp32Manager.editSensor(${index})" 
                            class="bg-yellow-500 hover:bg-yellow-700 text-white text-sm px-3 py-1 rounded">
                        Edit
                    </button>
                    <button onclick="esp32Manager.testSensor('${sensor.url}')" 
                            class="bg-green-500 hover:bg-green-700 text-white text-sm px-3 py-1 rounded">
                        Test
                    </button>
                    <button onclick="esp32Manager.startMonitor('${sensor.url}')"
                            class="bg-purple-500 hover:bg-purple-700 text-white text-sm px-3 py-1 rounded">
                        Live
                    </button>
                    <button onclick="esp32Manager.removeSensor(${index})" 
                            class="bg-red-500 hover:bg-red-700 text-white text-sm px-3 py-1 rounded">
                        Remove
                    </button>
                </div>
            `;
            container.appendChild(sensorCard);
        });
    }

    async loadNetworkInfo() {
        try {
            const response = await fetch('/api/network/status');
            const data = await response.json();
            
            if (data.success) {
                document.getElementById('wifi-mode').textContent = data.mode;
                document.getElementById('wifi-ssid').textContent = data.ssid;
                document.getElementById('wifi-ip').textContent = data.ip;
                document.getElementById('client-count').textContent = data.clients.length;
                
                this.displayConnectedClients(data.clients);
            }
        } catch (error) {
            console.error('Failed to load network info:', error);
        }
    }

    displayConnectedClients(clients) {
        const container = document.getElementById('connected-clients');
        container.innerHTML = '';

        if (clients.length === 0) {
            container.innerHTML = '<div class="text-gray-400">No connected clients</div>';
            return;
        }

        clients.forEach(client => {
            const clientDiv = document.createElement('div');
            clientDiv.className = 'border-b border-gray-600 pb-2 mb-2 last:border-b-0';
            clientDiv.innerHTML = `
                <div class="text-white text-sm">${client.ip}</div>
                <div class="text-gray-300 text-xs">MAC: ${client.mac || 'Unknown'}</div>
                <div class="text-gray-400 text-xs">
                    ${client.providing_data ? '📡 Providing sensor data' : '💻 Client only'}
                </div>
                ${client.last_data ? `<div class="text-gray-500 text-xs">Last: ${new Date(client.last_data).toLocaleTimeString()}</div>` : ''}
            `;
            container.appendChild(clientDiv);
        });
    }

    configureSensor(ip, deviceData) {
        const device = typeof deviceData === 'string' ? JSON.parse(deviceData) : deviceData;
        
        const modalContent = document.getElementById('modal-content');
        modalContent.innerHTML = `
            <div class="space-y-4">
                <div>
                    <label class="block text-gray-300 text-sm mb-1">Sensor Name</label>
                    <input type="text" id="config-name" value="${device.suggested_name || ip}" 
                           class="w-full px-3 py-2 bg-gray-600 text-white rounded">
                </div>
                <div>
                    <label class="block text-gray-300 text-sm mb-1">URL</label>
                    <input type="text" id="config-url" value="http://${ip}/data" 
                           class="w-full px-3 py-2 bg-gray-600 text-white rounded">
                </div>
                <div>
                    <label class="block text-gray-300 text-sm mb-1">PID Name (for CSV logging)</label>
                    <input type="text" id="config-pid" value="${device.suggested_pid || ip.replace(/\./g, '_')}" 
                           class="w-full px-3 py-2 bg-gray-600 text-white rounded">
                </div>
                <div>
                    <label class="block text-gray-300 text-sm mb-1">Data Type</label>
                    <select id="config-type" class="w-full px-3 py-2 bg-gray-600 text-white rounded">
                        <option value="pressure">Pressure (PSI)</option>
                        <option value="temperature">Temperature (°F)</option>
                        <option value="voltage">Voltage (V)</option>
                        <option value="raw">Raw JSON</option>
                    </select>
                </div>
                <div>
                    <label class="block text-gray-300 text-sm mb-1">Sample Data</label>
                    <pre class="bg-gray-600 p-2 rounded text-xs text-gray-300 overflow-auto max-h-20">
${JSON.stringify(device.sample, null, 2)}
                    </pre>
                </div>
            </div>
        `;
        
        this.currentConfigDevice = device;
        document.getElementById('sensor-modal').classList.remove('hidden');
        document.getElementById('sensor-modal').classList.add('flex');
    }

    async addManualSensor() {
        const name = document.getElementById('manual-name').value;
        const url = document.getElementById('manual-url').value;
        const type = document.getElementById('manual-type').value;
        
        if (!name || !url) {
            alert('Please fill in sensor name and URL');
            return;
        }
        
        try {
            const response = await fetch('/api/esp32/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, url, data_type: type })
            });
            
            const data = await response.json();
            if (data.success) {
                this.loadConfiguredSensors();
                // Clear form
                document.getElementById('manual-name').value = '';
                document.getElementById('manual-url').value = '';
            } else {
                alert(`Failed to add sensor: ${data.error}`);
            }
        } catch (error) {
            alert(`Error adding sensor: ${error.message}`);
        }
    }

    async testSensor(url) {
        // Normalize bare IPs/hosts to a full URL with scheme and default path
        try {
            if (url && !/^https?:\/\//i.test(url)) {
                // If no slash in the value (host only), default to /data
                url = url.includes('/') ? `http://${url}` : `http://${url}/data`;
            }
        } catch (e) { /* best-effort normalization */ }
        try {
            const response = await fetch('/api/esp32/test', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });
            
            const data = await response.json();
            if (data.success) {
                alert(`Sensor test successful!\nResponse: ${JSON.stringify(data.response, null, 2)}`);
            } else {
                alert(`Sensor test failed: ${data.error}`);
            }
        } catch (error) {
            alert(`Test error: ${error.message}`);
        }
    }

    // Live Monitor
    startMonitor(url) {
        try {
            if (url && !/^https?:\/\//i.test(url)) {
                url = url.includes('/') ? `http://${url}` : `http://${url}/data`;
            }
        } catch (e) {}
        this.monitorUrl = url;
        const modal = document.getElementById('monitor-modal');
        if (!modal) { this.testSensor(url); return; }
        document.getElementById('monitor-url').textContent = url;
        modal.classList.remove('hidden');
        modal.classList.add('flex');
        this.monitorTimer = setInterval(() => this.pollMonitor(), 750);
    }

    async pollMonitor() {
        if (!this.monitorUrl) return;
        try {
            const resp = await fetch('/api/esp32/test', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: this.monitorUrl })
            });
            const data = await resp.json();
            const jsonEl = document.getElementById('monitor-json');
            const valsEl = document.getElementById('monitor-values');
            if (!data.success) {
                jsonEl.textContent = `Error: ${data.error}`;
                valsEl.innerHTML = '';
            } else {
                const payload = data.response;
                jsonEl.textContent = JSON.stringify(payload, null, 2);
                // Simple parse: list numeric-looking keys and values
                const items = [];
                Object.entries(payload).forEach(([k,v]) => {
                    if (typeof v === 'number' || (!isNaN(parseFloat(v)) && isFinite(v))) {
                        items.push(`<div><span class="text-gray-400">${k}:</span> <span class="text-white">${v}</span></div>`);
                    }
                });
                valsEl.innerHTML = items.join('') || '<div class="text-gray-400">No numeric keys detected</div>';
                document.getElementById('monitor-updated').textContent = new Date().toLocaleTimeString();
            }
        } catch (e) {
            const jsonEl = document.getElementById('monitor-json');
            if (jsonEl) jsonEl.textContent = `Fetch error: ${e.message}`;
        }
    }

    stopMonitor() {
        const modal = document.getElementById('monitor-modal');
        if (modal) {
            modal.classList.add('hidden');
            modal.classList.remove('flex');
        }
        if (this.monitorTimer) { clearInterval(this.monitorTimer); this.monitorTimer = null; }
        this.monitorUrl = null;
    }

    async rebootNetwork() {
        if (!confirm('Are you sure you want to restart the network service? This may disconnect all clients temporarily.')) {
            return;
        }
        
        try {
            const response = await fetch('/api/network/reboot', { method: 'POST' });
            const data = await response.json();
            
            if (data.success) {
                alert('Network service restart initiated. Please wait a moment and refresh the page.');
            } else {
                alert(`Reboot failed: ${data.error}`);
            }
        } catch (error) {
            alert(`Reboot error: ${error.message}`);
        }
    }

    closeModal() {
        document.getElementById('sensor-modal').classList.add('hidden');
        document.getElementById('sensor-modal').classList.remove('flex');
    }

    async saveSensorConfig() {
        const name = document.getElementById('config-name').value;
        const url = document.getElementById('config-url').value;
        const pid = document.getElementById('config-pid').value;
        const type = document.getElementById('config-type').value;
        
        try {
            const response = await fetch('/api/esp32/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    name, 
                    url, 
                    pid_name: pid, 
                    data_type: type 
                })
            });
            
            const data = await response.json();
            if (data.success) {
                this.closeModal();
                this.loadConfiguredSensors();
            } else {
                alert(`Failed to save sensor: ${data.error}`);
            }
        } catch (error) {
            alert(`Save error: ${error.message}`);
        }
    }

    async removeSensor(index) {
        if (!confirm('Are you sure you want to remove this sensor?')) {
            return;
        }
        
        try {
            const response = await fetch('/api/esp32/remove', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ index })
            });
            
            const data = await response.json();
            if (data.success) {
                this.loadConfiguredSensors();
            } else {
                alert(`Failed to remove sensor: ${data.error}`);
            }
        } catch (error) {
            alert(`Remove error: ${error.message}`);
        }
    }
}

// Initialize when page loads
let esp32Manager;
document.addEventListener('DOMContentLoaded', () => {
    esp32Manager = new ESP32Manager();
});