import { fetchAPI } from '../api.js';
import { loadDashboardData } from './dashboard.js';

let currentCalDate = new Date(); // Tracks the currently viewed month

/**
 * Fetches calendar data and renders the monthly grid.
 */
export async function loadCalendar() {
    try {
        const data = await fetchAPI('/api/calendar');
        const grid = document.getElementById('calendar-grid');
        if (!grid) return;
        grid.innerHTML = '';

        const year = currentCalDate.getFullYear();
        const month = currentCalDate.getMonth();

        const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
        const monthLabel = document.getElementById('calendar-month-label');
        if (monthLabel) monthLabel.textContent = `${monthNames[month]} ${year}`;

        const eventsByDate = {};
        data.events.forEach(ev => {
            if (!eventsByDate[ev.date]) eventsByDate[ev.date] = [];
            eventsByDate[ev.date].push(ev);
        });

        const firstDayIndex = new Date(year, month, 1).getDay();
        const daysInMonth = new Date(year, month + 1, 0).getDate();

        // Render Day Headers
        ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].forEach(day => {
            grid.innerHTML += `<div style="text-align: center; font-weight: bold; border-bottom: 2px solid var(--pico-muted-border-color); padding-bottom: 5px;">${day}</div>`;
        });

        // Render Empty Buffer Slots
        for (let i = 0; i < firstDayIndex; i++) {
            grid.innerHTML += `<div style="background: transparent; border: none;"></div>`;
        }

        // Render Actual Days
        for (let i = 1; i <= daysInMonth; i++) {
            const m = String(month + 1).padStart(2, '0');
            const d = String(i).padStart(2, '0');
            const dateStr = `${year}-${m}-${d}`;

            const isToday = (dateStr === new Date().toISOString().split('T')[0]);
            const borderStyle = isToday ? "2px solid var(--pico-primary)" : "1px solid var(--pico-muted-border-color)";

            let html = `<div style="border: ${borderStyle}; padding: 5px; border-radius: 5px; min-height: 100px;">`;
            html += `<div style="font-weight: bold; margin-bottom: 5px;">${i}</div>`;

            if (eventsByDate[dateStr]) {
                eventsByDate[dateStr].forEach(ev => {
                    let color = ev.isHistorical ? 'var(--pico-primary-background)' : 'var(--pico-secondary-background)';
                    if (ev.type === 'Strength') color = '#e67e22';
                    if (ev.type === 'Mobility') color = '#8e44ad';

                    if (ev.isHistorical) {
                        html += `
                            <div style="background: ${color}; color: white; padding: 4px; border-radius: 3px; font-size: 0.75rem; margin-bottom: 4px; line-height: 1.2;">
                                <strong>${ev.type}</strong>: ${ev.title}<br>
                                ${ev.distance ? ev.distance + 'km | ' : ''} TSS: ${ev.tss != null ? ev.tss : '--'}
                                <div style="text-align: right; margin-top: 2px;">
                                    <a href="#" style="color: #ffcccc;" onclick="window.deleteActivity(${ev.id}); return false;">Del</a>
                                </div>
                            </div>
                        `;
                    } else {
                        // Escaping the description for the onclick handler
                        const safeDesc = (ev.description || "").replace(/'/g, "&#39;").replace(/"/g, "&quot;").replace(/\n/g, "\\n");
                        html += `
                            <div style="background: ${color}; color: white; padding: 4px; border-radius: 3px; font-size: 0.75rem; margin-bottom: 4px; line-height: 1.2; cursor: pointer;" 
                                 onclick="window.openWorkoutModal(${ev.id}, '${ev.type}', '${ev.title.replace(/'/g, "\\'")}', ${ev.duration || "''"}, ${ev.tss || "''"}, '${safeDesc}')">
                                <strong>${ev.type}</strong>: ${ev.title}<br>
                                ${ev.distance ? ev.distance + 'km | ' : (ev.duration ? ev.duration + 'm | ' : '')} TSS: ${ev.tss != null ? ev.tss : '--'}
                            </div>
                        `;
                    }
                });
            }
            html += `</div>`;
            grid.innerHTML += html;
        }
    } catch (err) {
        console.error("Error loading calendar:", err);
    }
}

/**
 * Initializes all Calendar-related event listeners
 */
export function initCalendarUI() {
    // --- Global Window Expose for Inline HTML Onclicks ---
    window.deleteActivity = async function (activityId) {
        if (!confirm("Delete this activity? This will recalculate your fitness metrics.")) return;
        try {
            await fetchAPI(`/api/activities/${activityId}`, { method: 'DELETE' });
            loadCalendar();
            loadDashboardData();
            // We dispatch an event so the records page knows to refresh if it's open
            window.dispatchEvent(new CustomEvent('activityDeleted'));
        } catch (err) {
            console.error("Failed to delete activity:", err);
        }
    };

    window.openWorkoutModal = function (id, type, title, duration, tss, description) {
        document.getElementById('edit-wo-id').value = id;
        document.getElementById('edit-wo-type').value = type;
        document.getElementById('edit-wo-title').value = title;
        document.getElementById('edit-wo-duration').value = duration;
        document.getElementById('edit-wo-tss').value = tss;
        document.getElementById('edit-wo-desc').value = description;
        const modal = document.getElementById('workout-modal');
        if (modal) modal.setAttribute('open', 'true');
    };

    // --- Navigation ---
    const prevMonthBtn = document.getElementById('prev-month');
    if (prevMonthBtn) {
        prevMonthBtn.addEventListener('click', () => {
            currentCalDate.setMonth(currentCalDate.getMonth() - 1);
            loadCalendar();
        });
    }

    const nextMonthBtn = document.getElementById('next-month');
    if (nextMonthBtn) {
        nextMonthBtn.addEventListener('click', () => {
            currentCalDate.setMonth(currentCalDate.getMonth() + 1);
            loadCalendar();
        });
    }

    // --- AI Micro Planner ---
    const genWeekBtn = document.getElementById('generate-week-btn');
    if (genWeekBtn) {
        genWeekBtn.addEventListener('click', async () => {
            const startDate = document.getElementById('micro-week-start').value;
            if (!startDate) {
                alert("Please select a date first!");
                return;
            }

            genWeekBtn.setAttribute('aria-busy', 'true');
            genWeekBtn.textContent = "Drafting Workouts...";

            try {
                await fetchAPI('/api/plan/micro', {
                    method: 'POST',
                    body: JSON.stringify({ weekStartDate: startDate })
                });
                genWeekBtn.setAttribute('aria-busy', 'false');
                genWeekBtn.textContent = "Workouts Synced! ✨";
                loadCalendar();
                setTimeout(() => { genWeekBtn.innerHTML = "✨ Generate Week"; }, 3000);
            } catch (err) {
                console.error(err);
                genWeekBtn.setAttribute('aria-busy', 'false');
                genWeekBtn.textContent = "Error Generation Failed";
                setTimeout(() => { genWeekBtn.innerHTML = "✨ Generate Week"; }, 3000);
            }
        });
    }

    // --- Manual Workout Scheduling ---
    const scheduleForm = document.getElementById('schedule-form');
    if (scheduleForm) {
        scheduleForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const wDuration = document.getElementById('w-duration').value;
            const wTss = document.getElementById('w-tss').value;

            const payload = {
                date: document.getElementById('w-date').value,
                type: document.getElementById('w-type').value,
                title: document.getElementById('w-title').value,
                duration: wDuration ? parseInt(wDuration) : null,
                trainingLoad: wTss ? parseFloat(wTss) : null,
                description: document.getElementById('w-desc').value
            };

            try {
                await fetchAPI('/api/workouts', {
                    method: 'POST',
                    body: JSON.stringify(payload)
                });
                alert("Workout Scheduled and pushed to Intervals.icu!");
                scheduleForm.reset();
                loadCalendar();
            } catch (err) {
                console.error("Scheduling failed:", err);
            }
        });
    }

    // --- Workout Edit / Delete Modal ---
    const woEditForm = document.getElementById('workout-edit-form');
    if (woEditForm) {
        woEditForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const woId = document.getElementById('edit-wo-id').value;
            const payload = {
                type: document.getElementById('edit-wo-type').value,
                title: document.getElementById('edit-wo-title').value,
                duration: parseInt(document.getElementById('edit-wo-duration').value) || null,
                trainingLoad: parseFloat(document.getElementById('edit-wo-tss').value) || null,
                description: document.getElementById('edit-wo-desc').value
            };

            try {
                await fetchAPI(`/api/workouts/${woId}`, {
                    method: 'PUT',
                    body: JSON.stringify(payload)
                });
                const modal = document.getElementById('workout-modal');
                if (modal) modal.removeAttribute('open');
                loadCalendar();
            } catch (err) {
                console.error("Update failed:", err);
            }
        });
    }

    const delWoBtn = document.getElementById('delete-wo-btn');
    if (delWoBtn) {
        delWoBtn.addEventListener('click', async () => {
            if (!confirm("Delete this planned workout?")) return;
            const woId = document.getElementById('edit-wo-id').value;
            try {
                await fetchAPI(`/api/workouts/${woId}`, { method: 'DELETE' });
                const modal = document.getElementById('workout-modal');
                if (modal) modal.removeAttribute('open');
                loadCalendar();
            } catch (err) {
                console.error("Delete failed:", err);
            }
        });
    }
}