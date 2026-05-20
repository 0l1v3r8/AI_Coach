import { fetchAPI } from '../api.js';

let fitnessChartInstance = null;

/**
 * Fetches and populates the main dashboard numbers (CTL, ATL, TSB, FTP, LTHR)
 */
export async function loadDashboardData() {
    try {
        const data = await fetchAPI('/api/dashboard/data');

        if (data.fitness_data && data.fitness_data.length > 0) {
            const today = data.fitness_data[data.fitness_data.length - 1];

            const ctlNode = document.getElementById('current-ctl');
            const atlNode = document.getElementById('current-atl');
            const tsbSpan = document.getElementById('current-tsb');

            if (ctlNode) ctlNode.textContent = today.fitness;
            if (atlNode) atlNode.textContent = today.fatigue;
            if (tsbSpan) {
                tsbSpan.textContent = today.form;
                tsbSpan.style.color = today.form > 0 ? "green" : "red";
            }
        }

        if (data.baseline) {
            const ftpNode = document.getElementById('current-ftp');
            const lthrNode = document.getElementById('current-lthr');
            const maxHrNode = document.getElementById('current-maxhr'); // <-- ADD THIS

            if (ftpNode) ftpNode.textContent = data.baseline.ftp ? `${data.baseline.ftp} W` : '-- W';
            if (lthrNode) lthrNode.textContent = data.baseline.lthr ? `${data.baseline.lthr} bpm` : '-- bpm';
            if (maxHrNode) maxHrNode.textContent = data.baseline.maxHr ? `${data.baseline.maxHr} bpm` : '-- bpm'; //
        }
    } catch (err) {
        console.error("Error loading dashboard numbers:", err);
    }
}

/**
 * Fetches timeseries data and renders the Chart.js graph
 */
let curveChartInstance = null;
let curveData = null; // Cache to prevent re-fetching

export async function loadAnalyticsChart() {
    // Render Fitness chart by default
    document.getElementById('chart-type-selector').value = "fitness";
    toggleChartVisibility("fitness");
    
    try {
        const data = await fetchAPI('/api/analytics/timeseries');
        const ctx = document.getElementById('fitnessChart');
        if (!ctx) return;

        if (fitnessChartInstance) fitnessChartInstance.destroy();
        fitnessChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.dates,
                datasets: [
                    { label: 'Fitness (CTL)', data: data.fitness, borderColor: 'blue', tension: 0.4, fill: false },
                    { label: 'Fatigue (ATL)', data: data.fatigue, borderColor: 'red', tension: 0.4, borderDash: [5, 5], fill: false },
                    { label: 'Form (TSB)', data: data.form, backgroundColor: 'rgba(0, 200, 0, 0.2)', type: 'bar' }
                ]
            },
            options: { responsive: true }
        });
        
        // Setup dropdown listener (prevent multiple bindings)
        const selector = document.getElementById('chart-type-selector');
        selector.removeEventListener('change', handleChartChange);
        selector.addEventListener('change', handleChartChange);
        
    } catch (err) {
        console.error("Error loading analytics:", err);
    }
}

async function handleChartChange(e) {
    const type = e.target.value;
    toggleChartVisibility(type);

    if (type === 'fitness') return; // Already rendered
    
    // Fetch curve data once and cache it
    if (!curveData) {
        curveData = await fetchAPI('/api/analytics/curves');
    }
    
    renderCurveChart(type);
}

function toggleChartVisibility(type) {
    document.getElementById('fitnessChart').style.display = (type === 'fitness') ? 'block' : 'none';
    document.getElementById('curveChart').style.display = (type !== 'fitness') ? 'block' : 'none';
    
    const desc = document.getElementById('analytics-desc');
    if (type === 'fitness') desc.textContent = "Your 6-month training load time-series.";
    else desc.textContent = "Your peak efforts over your defined Baseline Lookback Period.";
}

function renderCurveChart(type) {
    const ctx = document.getElementById('curveChart');
    if (curveChartInstance) curveChartInstance.destroy();

    let chartLabels, chartValues, chartTitle, color;
    
    if (type === 'power-ride') {
        chartLabels = curveData.power.labels;
        chartValues = curveData.power.data;
        chartTitle = 'Peak Power Output (Watts)';
        color = 'purple';
    } else if (type === 'hr-run') {
        chartLabels = curveData.hr_run.labels;
        chartValues = curveData.hr_run.data;
        chartTitle = 'Peak HR - Run (BPM)';
        color = '#e67e22';
    } else if (type === 'hr-ride') {
        chartLabels = curveData.hr_ride.labels;
        chartValues = curveData.hr_ride.data;
        chartTitle = 'Peak HR - Ride (BPM)';
        color = '#3498db';
    }

    curveChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: chartLabels,
            datasets: [{
                label: chartTitle,
                data: chartValues,
                borderColor: color,
                backgroundColor: color,
                tension: 0.3,
                fill: false,
                spanGaps: true // Connects line if some durations are missing
            }]
        },
        options: {
            responsive: true,
            scales: { y: { beginAtZero: false } }
        }
    });
}

/**
 * Initializes button listeners for the Dashboard and Settings views
 */
export function initDashboardUI() {
    const syncStravaBtn = document.getElementById('sync-strava-btn');
    if (syncStravaBtn) {
        syncStravaBtn.addEventListener('click', async (e) => {
            const btn = e.target;
            const originalText = btn.textContent;
            btn.setAttribute('aria-busy', 'true');
            btn.textContent = "Syncing 12 months of history (this takes a moment)...";

            try {
                const data = await fetchAPI('/api/strava/sync', { method: 'POST' });
                btn.setAttribute('aria-busy', 'false');
                btn.textContent = `Sync Complete! Imported ${data.imported || 0} new activities.`;
                await loadDashboardData();
                setTimeout(() => { btn.textContent = originalText; }, 3000);
            } catch (err) {
                console.error(err);
                btn.setAttribute('aria-busy', 'false');
                btn.textContent = "Sync Failed. Try Again";
                setTimeout(() => { btn.textContent = originalText; }, 3000);
            }
        });
    }

    const disconnectStravaBtn = document.getElementById('disconnect-strava-btn');
    if (disconnectStravaBtn) {
        disconnectStravaBtn.addEventListener('click', async () => {
            await fetchAPI('/api/users/strava/disconnect', { method: 'POST' });
            window.location.reload();
        });
    }

    const disconnectIntervalsBtn = document.getElementById('disconnect-intervals-btn');
    if (disconnectIntervalsBtn) {
        disconnectIntervalsBtn.addEventListener('click', async () => {
            await fetchAPI('/api/users/intervals/disconnect', { method: 'POST' });
            window.location.reload();
        });
    }

    const intervalsForm = document.getElementById('intervals-form');
    if (intervalsForm) {
        intervalsForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const keyInput = document.getElementById('intervals-key');
            const key = keyInput ? keyInput.value.trim() : '';

            try {
                const data = await fetchAPI('/api/auth/intervals', {
                    method: 'POST',
                    body: JSON.stringify({ api_key: key })
                });
                if (data.success) {
                    const connStatus = document.getElementById('connection-status');
                    if (connStatus) connStatus.innerHTML = "<strong>✅ Intervals.icu Saved!</strong>";
                    if (keyInput) keyInput.value = '';
                    setTimeout(() => window.location.reload(), 1000);
                }
            } catch (err) {
                console.error("Intervals saving failed:", err);
            }
        });
    }

    const userSettingsForm = document.getElementById('user-settings-form');
    if (userSettingsForm) {
        userSettingsForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const btn = e.target.querySelector('button[type="submit"]');
            btn.setAttribute('aria-busy', 'true');
            btn.textContent = "Saving...";

            // Grab the value from the new input
            // Default value is the users current saved value
            const payload = {
                baselineLookbackWeeks: parseInt(document.getElementById('settings-baseline-weeks').value) || 12
            };

            try {
                // Send the PUT request to the backend route we made earlier
                await fetchAPI('/api/users/settings', {
                    method: 'PUT',
                    body: JSON.stringify(payload)
                });

                // Show a success message
                const status = document.getElementById('settings-save-status');
                if (status) {
                    status.innerHTML = "<strong>✅ Saved!</strong>";
                    setTimeout(() => { status.innerHTML = ""; }, 3000);
                }

                // Reload the dashboard numbers in the background to reflect the new timeframe immediately
                await loadDashboardData();
            } catch (err) {
                console.error("Failed to save settings:", err);
                alert("Failed to save settings. Please ensure your backend is running.");
            } finally {
                btn.setAttribute('aria-busy', 'false');
                btn.textContent = "Save Settings";
            }
        });
    }

    const chatForm = document.getElementById('chat-form');
    if (chatForm) {
        chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const input = document.getElementById('chat-input');
            if (!input || !input.value.trim()) return;

            const text = input.value.trim();
            const chatBox = document.getElementById('chat-box');
            if (chatBox) {
                const msgRow = document.createElement('p');
                msgRow.className = "chat-message user-msg";
                const label = document.createElement('strong');
                label.textContent = "You: ";
                const textNode = document.createTextNode(text);

                msgRow.appendChild(label);
                msgRow.appendChild(textNode);
                chatBox.appendChild(msgRow);

                input.value = '';
                chatBox.scrollTop = chatBox.scrollHeight;
            }
        });
    }
}