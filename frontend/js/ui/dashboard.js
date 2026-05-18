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
            if (ftpNode) ftpNode.textContent = data.baseline.ftp ? `${data.baseline.ftp} W` : '-- W';
            if (lthrNode) lthrNode.textContent = data.baseline.lthr ? `${data.baseline.lthr} bpm` : '-- bpm';
        }
    } catch (err) {
        console.error("Error loading dashboard numbers:", err);
    }
}

/**
 * Fetches timeseries data and renders the Chart.js graph
 */
export async function loadAnalyticsChart() {
    try {
        const data = await fetchAPI('/api/analytics/timeseries');
        const ctx = document.getElementById('fitnessChart');
        if (!ctx) return;

        if (fitnessChartInstance) fitnessChartInstance.destroy();

        // Chart is loaded globally via CDN in index.html
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
            options: {
                responsive: true,
                scales: { y: { beginAtZero: true } }
            }
        });
    } catch (err) {
        console.error("Error loading analytics:", err);
    }
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