import { fetchAPI } from '../api.js';
import { loadDashboardData } from './dashboard.js';

let allRecordsData = {};

export async function loadRecordsData() {
    try {
        const data = await fetchAPI('/api/records');
        allRecordsData = data;

        const sportSelect = document.getElementById('records-sport');
        if (!sportSelect) return;

        sportSelect.innerHTML = '<option value="">-- Select Sport --</option>';
        Object.keys(data).forEach(sport => {
            sportSelect.innerHTML += `<option value="${sport}">${sport}</option>`;
        });

        // Ensure we don't duplicate event listeners
        sportSelect.removeEventListener('change', updateMetricDropdown);
        sportSelect.addEventListener('change', updateMetricDropdown);

        const metricSelect = document.getElementById('records-metric');
        const sortSelect = document.getElementById('records-sort');

        if (metricSelect) {
            metricSelect.removeEventListener('change', renderRecordsTable);
            metricSelect.addEventListener('change', renderRecordsTable);
        }
        if (sortSelect) {
            sortSelect.removeEventListener('change', renderRecordsTable);
            sortSelect.addEventListener('change', renderRecordsTable);
        }

        renderRecordsTable();
    } catch (err) {
        console.error("Error loading records:", err);
    }
}

function updateMetricDropdown() {
    const sport = document.getElementById('records-sport').value;
    const metricSelect = document.getElementById('records-metric');
    metricSelect.innerHTML = '<option value="">-- Select Metric --</option>';

    if (!sport) {
        metricSelect.disabled = true;
        renderRecordsTable();
        return;
    }

    metricSelect.disabled = false;
    Object.keys(allRecordsData[sport]).forEach(metric => {
        metricSelect.innerHTML += `<option value="${metric}">${metric}</option>`;
    });
    renderRecordsTable();
}

function renderRecordsTable() {
    const sport = document.getElementById('records-sport').value;
    const metric = document.getElementById('records-metric').value;
    const sortType = document.getElementById('records-sort').value;
    const tbody = document.getElementById('records-table-body');

    if (!tbody) return;

    if (!sport || !metric) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align: center;">Select a sport and metric to view history.</td></tr>';
        return;
    }

    let efforts = [...allRecordsData[sport][metric]];

    efforts.sort((a, b) => {
        if (sortType === 'date_desc') return new Date(b.date) - new Date(a.date);
        if (sortType === 'date_asc') return new Date(a.date) - new Date(b.date);
        if (sortType === 'perf_best') {
            if (metric.includes("Power")) return b.time - a.time;
            return a.time - b.time;
        }
        return 0;
    });

    tbody.innerHTML = efforts.map(eff => {
        let displayValue;
        if (metric.includes("Power")) {
            displayValue = `${eff.time} W`;
        } else {
            const date = new Date(eff.time * 1000);
            displayValue = eff.time >= 3600 ? date.toISOString().slice(11, 19) : date.toISOString().slice(14, 19);
        }

        return `
            <tr>
                <td><small>${eff.date}</small></td>
                <td>${metric}</td>
                <td style="color: var(--pico-primary);"><strong>${displayValue}</strong></td>
                <td>
                    <a href="#" onclick="window.openPbModal(${eff.id}, ${eff.time}, '${eff.date}', '${eff.activityId || ''}'); return false;">Edit</a> | 
                    <a href="https://www.strava.com/activities/${eff.activityId}" target="_blank">View</a>
                </td>
            </tr>
        `;
    }).join('');
}

export function initRecordsUI() {
    // Expose modal function globally for inline HTML clicks
    window.openPbModal = function (id, time, date, link) {
        document.getElementById('edit-pb-id').value = id;
        document.getElementById('edit-pb-time').value = time;
        document.getElementById('edit-pb-date').value = date;
        document.getElementById('edit-pb-link').value = link || '';
        const modal = document.getElementById('pb-modal');
        if (modal) modal.setAttribute('open', 'true');
    };

    const pbEditForm = document.getElementById('pb-edit-form');
    if (pbEditForm) {
        pbEditForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const pbId = document.getElementById('edit-pb-id').value;
            const payload = {
                timeSeconds: parseInt(document.getElementById('edit-pb-time').value),
                date: document.getElementById('edit-pb-date').value,
                activityId: document.getElementById('edit-pb-link').value
            };

            try {
                await fetchAPI(`/api/pbs/${pbId}`, {
                    method: 'PUT',
                    body: JSON.stringify(payload)
                });
                const modal = document.getElementById('pb-modal');
                if (modal) modal.removeAttribute('open');

                await loadRecordsData();
                await loadDashboardData();
            } catch (err) {
                console.error("Failed to update PB:", err);
            }
        });
    }

    // Refresh if an activity is deleted elsewhere (like the Calendar)
    window.addEventListener('activityDeleted', () => {
        if (document.getElementById('pbs-view').style.display === 'block') {
            loadRecordsData();
        }
    });
}