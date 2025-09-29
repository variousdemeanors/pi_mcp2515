document.addEventListener('DOMContentLoaded', (event) => {
    const socket = io();
    const metricsContainer = document.getElementById('metrics-container');
    const statusElement = document.getElementById('connection-status');
    const startBtn = document.getElementById('start-btn');
    const stopBtn = document.getElementById('stop-btn');
    let liveChart;
    const MAX_DATA_POINTS = 50;

    // Datasets now include the key name to look up in the incoming payload
    const chartDatasets = [
        { label: 'RPM', key: 'RPM', data: [], borderColor: 'rgb(255, 99, 132)', tension: 0.1, fill: false },
        { label: 'Intercooler', key: 'Intercooler_Pressure', data: [], borderColor: 'rgb(54, 162, 235)', tension: 0.1, fill: false },
        { label: 'WMI Pre', key: 'WMI Pre_solenoid', data: [], borderColor: 'rgb(75, 192, 192)', tension: 0.1, fill: false },
        { label: 'WMI Post', key: 'WMI post_solenoid', data: [], borderColor: 'rgb(255, 159, 64)', tension: 0.1, fill: false },
        { label: 'Fuel Flow (GPH)', key: 'fuel_flow_gph', data: [], borderColor: 'rgb(255, 205, 86)', tension: 0.1, fill: false },
        { label: 'Injector Duty %', key: 'injector_duty_cycle', data: [], borderColor: 'rgb(255, 159, 243)', tension: 0.1, fill: false },
        { label: 'AFR', key: 'measured_afr', data: [], borderColor: 'rgb(128, 255, 128)', tension: 0.1, fill: false }
    ];

    function initChart() {
        const ctx = document.getElementById('live-chart').getContext('2d');
        liveChart = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: chartDatasets
            },
            options: {
                animation: false,
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        type: 'time',
                        time: { unit: 'second' },
                        title: { display: true, text: 'Time' },
                        ticks: { maxTicksLimit: 10 }
                    },
                    y: { title: { display: true, text: 'Value' } }
                }
            }
        });
    }

    socket.on('connect', () => {
        console.log('Connected to server');
    });

    // If socket fails to connect, fall back to polling the /alldata endpoint
    let fallbackInterval = null;
    let fallbackStarted = false;
    const startFallback = () => {
        if (fallbackStarted) return;
        console.warn('Starting HTTP polling fallback to /alldata');
        fallbackStarted = true;
        fallbackInterval = setInterval(async () => {
            try {
                const resp = await fetch('/alldata', {cache: 'no-store'});
                if (!resp.ok) {
                    console.warn('Fallback /alldata HTTP error', resp.status);
                    return;
                }
                const data = await resp.json();
                handleIncomingData(data);
            } catch (e) {
                console.warn('Fallback fetch error', e);
            }
        }, 200); // 200ms polling; adjust as needed
    };

    // If socket connection error occurs, start HTTP fallback
    socket.io && socket.io.on('connect_error', (err) => {
        console.warn('Socket.IO connect_error', err);
        startFallback();
    });

    // Also start fallback if socket does not connect within 2s
    setTimeout(() => {
        if (!socket.connected) startFallback();
    }, 2000);

    socket.on('status_update', (data) => {
        statusElement.textContent = data.status;
        
        // Handle connection status
        if (data.status.includes('Connected')) {
            statusElement.classList.remove('text-yellow-500', 'text-red-500');
            statusElement.classList.add('text-green-500');
        } else if (data.status.includes('Error') || data.status.includes('failed')) {
            statusElement.classList.remove('text-yellow-500', 'text-green-500');
            statusElement.classList.add('text-red-500');
        } else {
            statusElement.classList.remove('text-green-500', 'text-red-500');
            statusElement.classList.add('text-yellow-500');
        }
        
        // Handle logging status updates
        if (data.hasOwnProperty('log_status')) {
            const startBtn = document.getElementById('start-log');
            const stopBtn = document.getElementById('stop-log');
            
            if (data.log_status) {
                // Logging is active
                if (startBtn) {
                    startBtn.disabled = true;
                    startBtn.textContent = 'Logging Active';
                    startBtn.classList.add('bg-green-600');
                    startBtn.classList.remove('bg-blue-600');
                }
                if (stopBtn) {
                    stopBtn.disabled = false;
                }
            } else {
                // Logging is not active
                if (startBtn) {
                    startBtn.disabled = false;
                    startBtn.textContent = 'Start Logging';
                    startBtn.classList.remove('bg-green-600');
                    startBtn.classList.add('bg-blue-600');
                }
                if (stopBtn) {
                    stopBtn.disabled = true;
                }
            }
        }
        
        // Show any messages
        if (data.message) {
            console.log('Status message:', data.message);
        }
        
        // Show any errors
        if (data.error) {
            console.error('Status error:', data.error);
        }
    });

    socket.on('current_data', (data) => {
        handleIncomingData(data);
    });

    function handleIncomingData(data) {
        // Update live metrics display
        metricsContainer.innerHTML = '';
        for (const [key, value] of Object.entries(data)) {
            if (['connection_status','log_active','last_stop_time','log_file_name'].includes(key)) continue;
            const div = document.createElement('div');
            div.className = "p-2 bg-gray-700 rounded-lg";
            div.innerHTML = `<p class="font-bold text-sm text-gray-400">${key.replace(/_/g, ' ')}</p><p class="text-lg font-semibold">${value}</p>`;
            metricsContainer.appendChild(div);
        }

        // Initialize chart on first data receipt
        if (!liveChart) {
            initChart();
        }

        const now = Date.now();

        // Update chart data using dataset.key mapping
        liveChart.data.datasets.forEach(dataset => {
            const lookupKey = dataset.key || dataset.label.replace(/ /g, '_');
            let raw = data[lookupKey];
            // Some payloads may use lowercase or different casing
            if (raw === undefined && lookupKey.toLowerCase && data[lookupKey.toLowerCase()]) raw = data[lookupKey.toLowerCase()];
            const value = parseFloat(raw);
            if (!isNaN(value)) {
                dataset.data.push({ x: now, y: value });
            }

            // Limit the number of data points
            if (dataset.data.length > MAX_DATA_POINTS) {
                dataset.data.shift();
            }
        });

        liveChart.update('quiet');
    }

    startBtn.addEventListener('click', () => {
        socket.emit('start_log');
        console.log('Start log event emitted');
    });

    stopBtn.addEventListener('click', () => {
        socket.emit('stop_log');
        console.log('Stop log event emitted');
    });
});
