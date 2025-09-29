document.addEventListener('DOMContentLoaded', (event) => {
    console.log('Analysis page script loaded and DOM is ready.');

    const socket = io();

    socket.on('connect', () => {
        console.log('Successfully connected to Socket.IO server.');
    });

    socket.on('disconnect', () => {
        console.log('Disconnected from Socket.IO server.');
    });

    const fileUpload = document.getElementById('log_file_upload');
    const uploadAndLoadBtn = document.getElementById('upload_and_load_btn');
    const plotDataBtn = document.getElementById('plot_data_btn');
    const logTableBody = document.querySelector('table tbody');

    const pidSelectionContainer = document.getElementById('pid_selection_container');
    const pidCheckboxes = document.getElementById('pid_checkboxes');
    const analysisResultsContainer = document.getElementById('analysis_results_container');
    const plotlyChartContainer = document.getElementById('plotly_chart_container');
    const statsTable = document.getElementById('stats_table');

    let currentLogFile = null;

    // Handle loading from the table of existing logs
    logTableBody.addEventListener('click', (event) => {
        if (event.target.classList.contains('load-btn')) {
            const button = event.target;
            const filename = button.dataset.filename;
            console.log(`Load button clicked for file: ${filename}`);
            if (filename) {
                currentLogFile = filename;
                socket.emit('load_log_file', { filename: filename });
            }
        }
    });

    // Handle uploading a new log file
    uploadAndLoadBtn.addEventListener('click', () => {
        console.log('Upload & Load button clicked.');
        const uploadedFile = fileUpload.files[0];
        if (uploadedFile) {
            currentLogFile = uploadedFile.name;
            const reader = new FileReader();
            reader.onload = function(e) {
                socket.emit('load_log_file', { filename: uploadedFile.name, content: e.target.result });
            };
            reader.readAsText(uploadedFile);
        } else {
            alert('Please select a file to upload first.');
        }
    });

    socket.on('log_file_loaded', (data) => {
        if (data.error) {
            alert('Error loading log file: ' + data.error);
            return;
        }

        // Populate PID checkboxes
        pidCheckboxes.innerHTML = '';
        data.pids.forEach(pid => {
            const div = document.createElement('div');
            div.className = 'flex items-center';
            div.innerHTML = `
                <input type="checkbox" id="pid_${pid}" name="pids_to_plot" value="${pid}"
                       class="form-checkbox h-5 w-5 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500">
                <label for="pid_${pid}" class="ml-3 text-white">${pid}</label>
            `;
            pidCheckboxes.appendChild(div);
        });

        pidSelectionContainer.classList.remove('hidden');
        analysisResultsContainer.classList.add('hidden');
    });

    plotDataBtn.addEventListener('click', () => {
        const selectedPIDs = Array.from(document.querySelectorAll('input[name="pids_to_plot"]:checked')).map(cb => cb.value);
        if (selectedPIDs.length === 0) {
            alert('Please select at least one PID to plot.');
            return;
        }

        socket.emit('get_plot_data', { filename: currentLogFile, pids: selectedPIDs });
    });

    socket.on('plot_data_ready', (data) => {
        if (data.error) {
            alert('Error generating plot data: ' + data.error);
            console.error('Plot data error:', data.error);
            return;
        }

        if (!data.plot_data || !data.plot_data.data || data.plot_data.data.length === 0) {
            alert('No data available for plotting. The log file may be empty or contain no valid numeric data.');
            console.warn('No plot data received:', data);
            return;
        }

        // Render Plotly chart
        const plotData = data.plot_data.data;
        const layout = data.plot_data.layout;
        
        console.log('Rendering plot with', plotData.length, 'data series');
        console.log('Plot data summary:', plotData.map(d => ({name: d.name, points: d.x ? d.x.length : 0})));
        
        Plotly.newPlot(plotlyChartContainer, plotData, layout, {responsive: true});

        // Render stats table
        statsTable.innerHTML = '';
        const table = document.createElement('table');
        table.className = 'min-w-full bg-gray-900 text-white';
        let thead = '<thead><tr>';
        for (const header of data.stats.headers) {
            thead += `<th class="py-2 px-4 border-b border-gray-700">${header}</th>`;
        }
        thead += '</tr></thead>';
        table.innerHTML = thead;

        let tbody = '<tbody>';
        for (const row of data.stats.rows) {
            tbody += '<tr>';
            for (const cell of row) {
                tbody += `<td class="py-2 px-4 border-b border-gray-700 text-center">${cell}</td>`;
            }
            tbody += '</tr>';
        }
        tbody += '</tbody>';
        table.innerHTML += tbody;
        statsTable.appendChild(table);

        analysisResultsContainer.classList.remove('hidden');
    });
});
