import { fetchAPI } from '../api.js';
import { loadDashboardData } from './dashboard.js';

let currentCalDate = new Date(); // Tracks the currently viewed month

/**
 * Main entry point to load and render the calendar view.
 * Fetches both activity events and macro plan data concurrently for better performance.
 */
export async function loadCalendar() {
    try {
        const grid = document.getElementById('calendar-grid');
        if (!grid) return;

        // 1. Fetch data concurrently
        const [calendarData, macroData] = await Promise.all([
            fetchAPI('/api/calendar'),
            fetchAPI('/api/plan/macro').catch(() => ({ plan: [] })) // Graceful fallback if no plan exists
        ]);

        // 2. Prepare Data Dictionaries for O(1) lookups
        const eventsByDate = groupEventsByDate(calendarData.events || []);
        const macroByDate = groupMacroPlanByDate(macroData.plan || []);

        // 3. Render the Calendar UI
        renderCalendarUI(grid, eventsByDate, macroByDate);

    } catch (err) {
        console.error("Error loading calendar:", err);
    }
}

/* =====================================================================
 * DATA PROCESSING HELPERS
 * ===================================================================== */

function groupEventsByDate(events) {
    const grouped = {};
    events.forEach(ev => {
        if (!grouped[ev.date]) grouped[ev.date] = [];
        grouped[ev.date].push(ev);
    });
    return grouped;
}

function groupMacroPlanByDate(plan) {
    const grouped = {};
    plan.forEach(week => {
        // Map the weekly macro goal to its specific start date
        grouped[week.weekStartDate] = week;
    });
    return grouped;
}

/* =====================================================================
 * RENDERING HELPERS
 * ===================================================================== */

function renderCalendarUI(grid, eventsByDate, macroByDate) {
    grid.innerHTML = ''; // Clear existing grid

    const year = currentCalDate.getFullYear();
    const month = currentCalDate.getMonth();

    updateMonthLabel(year, month);

    const firstDayIndex = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    renderDayHeaders(grid);
    renderBufferSlots(grid, firstDayIndex);
    renderDays(grid, year, month, daysInMonth, eventsByDate, macroByDate);
}

function updateMonthLabel(year, month) {
    const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
    const monthLabel = document.getElementById('calendar-month-label');
    if (monthLabel) monthLabel.textContent = `${monthNames[month]} ${year}`;
}

function renderDayHeaders(grid) {
    const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    days.forEach(day => {
        grid.innerHTML += `<div style="text-align: center; font-weight: bold; border-bottom: 2px solid var(--pico-muted-border-color); padding-bottom: 5px;">${day}</div>`;
    });
}

function renderBufferSlots(grid, count) {
    for (let i = 0; i < count; i++) {
        grid.innerHTML += `<div style="background: transparent; border: none;"></div>`;
    }
}

function renderDays(grid, year, month, daysInMonth, eventsByDate, macroByDate) {
    const todayStr = new Date().toISOString().split('T')[0];

    for (let i = 1; i <= daysInMonth; i++) {
        const mStr = String(month + 1).padStart(2, '0');
        const dStr = String(i).padStart(2, '0');
        const dateStr = `${year}-${mStr}-${dStr}`;

        const isToday = (dateStr === todayStr);
        const borderStyle = isToday ? "2px solid var(--pico-primary)" : "1px solid var(--pico-muted-border-color)";

        let html = `<div style="border: ${borderStyle}; padding: 5px; border-radius: 5px; min-height: 100px; display: flex; flex-direction: column;">`;
        html += `<div style="font-weight: bold; margin-bottom: 5px;">${i}</div>`;

        // 1. Render Macro Plan Goal (if this date is a week start)
        if (macroByDate[dateStr]) {
            html += generateMacroGoalHTML(macroByDate[dateStr]);
        }

        // 2. Render Workouts/Activities
        if (eventsByDate[dateStr]) {
            eventsByDate[dateStr].forEach(ev => {
                html += generateActivityHTML(ev);
            });
        }

        html += `</div>`;
        grid.innerHTML += html;
    }
}

function generateMacroGoalHTML(weekGoal) {
    return `
        <div style="background: var(--pico-contrast-background); color: var(--pico-contrast-inverse); padding: 6px; border-radius: 4px; font-size: 0.7rem; margin-bottom: 8px; text-align: center; border-left: 3px solid var(--pico-primary);">
            <strong style="display: block; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em;">${weekGoal.phase}</strong>
            <span style="font-style: italic;">Focus: ${weekGoal.focus}</span><br>
            <strong>Target TSS: ${weekGoal.targetTss}</strong>
        </div>
    `;
}

function generateActivityHTML(ev) {
    let color = ev.isHistorical ? 'var(--pico-primary-background)' : 'var(--pico-secondary-background)';
    if (ev.type === 'Strength') color = '#e67e22';
    if (ev.type === 'Mobility') color = '#8e44ad';

    if (ev.isHistorical) {
        return `
            <div style="background: ${color}; color: white; padding: 4px; border-radius: 3px; font-size: 0.75rem; margin-bottom: 4px; line-height: 1.2;">
                <strong>${ev.type}</strong>: ${ev.title}<br>
                ${ev.distance ? ev.distance + 'km | ' : ''} TSS: ${ev.tss != null ? ev.tss : '--'}
                <div style="text-align: right; margin-top: 2px;">
                    <a href="#" style="color: #ffcccc;" onclick="window.deleteActivity(${ev.id}); return false;">Del</a>
                </div>
            </div>
        `;
    } else {
        const safeDesc = (ev.description || "").replace(/'/g, "&#39;").replace(/"/g, "&quot;").replace(/\n/g, "\\n");
        return `
            <div style="background: ${color}; color: white; padding: 4px; border-radius: 3px; font-size: 0.75rem; margin-bottom: 4px; line-height: 1.2; cursor: pointer;" 
                 onclick="window.openWorkoutModal(${ev.id}, '${ev.type}', '${ev.title.replace(/'/g, "\\'")}', ${ev.duration || "''"}, ${ev.tss || "''"}, '${safeDesc}')">
                <strong>${ev.type}</strong>: ${ev.title}<br>
                ${ev.distance ? ev.distance + 'km | ' : (ev.duration ? ev.duration + 'm | ' : '')} TSS: ${ev.tss != null ? ev.tss : '--'}
            </div>
        `;
    }
}

/* =====================================================================
 * INITIALIZATION & EVENT LISTENERS
 * ===================================================================== */

export function initCalendarUI() {
    // --- Global Window Expose for Inline HTML Onclicks ---
    window.deleteActivity = async function (activityId) {
        if (!confirm("Delete this activity? This will recalculate your fitness metrics.")) return;
        try {
            await fetchAPI(`/api/activities/${activityId}`, { method: 'DELETE' });
            loadCalendar();
            loadDashboardData();
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
    document.getElementById('prev-month')?.addEventListener('click', () => {
        currentCalDate.setMonth(currentCalDate.getMonth() - 1);
        loadCalendar();
    });

    document.getElementById('next-month')?.addEventListener('click', () => {
        currentCalDate.setMonth(currentCalDate.getMonth() + 1);
        loadCalendar();
    });

    // --- AI Micro Planner ---
    const genWeekBtn = document.getElementById('generate-week-btn');
    if (genWeekBtn) {
        genWeekBtn.addEventListener('click', async () => {
            const startDate = document.getElementById('micro-week-start').value;
            if (!startDate) return alert("Please select a date first!");

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
    document.getElementById('schedule-form')?.addEventListener('submit', async (e) => {
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
            await fetchAPI('/api/workouts', { method: 'POST', body: JSON.stringify(payload) });
            alert("Workout Scheduled and pushed to Intervals.icu!");
            e.target.reset();
            loadCalendar();
        } catch (err) {
            console.error("Scheduling failed:", err);
        }
    });

    // --- Workout Edit / Delete Modal ---
    document.getElementById('workout-edit-form')?.addEventListener('submit', async (e) => {
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
            await fetchAPI(`/api/workouts/${woId}`, { method: 'PUT', body: JSON.stringify(payload) });
            document.getElementById('workout-modal')?.removeAttribute('open');
            loadCalendar();
        } catch (err) {
            console.error("Update failed:", err);
        }
    });

    document.getElementById('delete-wo-btn')?.addEventListener('click', async () => {
        if (!confirm("Delete this planned workout?")) return;
        const woId = document.getElementById('edit-wo-id').value;
        try {
            await fetchAPI(`/api/workouts/${woId}`, { method: 'DELETE' });
            document.getElementById('workout-modal')?.removeAttribute('open');
            loadCalendar();
        } catch (err) {
            console.error("Delete failed:", err);
        }
    });
}