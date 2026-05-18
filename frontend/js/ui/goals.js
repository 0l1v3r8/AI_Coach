import { fetchAPI } from '../api.js';

export async function loadMacroPlan() {
    try {
        const data = await fetchAPI('/api/plan/macro');
        const tbody = document.getElementById('macro-plan-body');
        if (!tbody) return;

        if (data.plan && data.plan.length > 0) {
            tbody.innerHTML = data.plan.map(week => `
                <tr>
                    <td><strong>${week.weekStartDate}</strong></td>
                    <td>${week.phase}</td>
                    <td>${week.focus}</td>
                    <td>${week.targetTss}</td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align: center;">No plan generated yet.</td></tr>';
        }
    } catch (err) {
        console.error("Error loading macro plan:", err);
    }
}

export function initGoalsUI() {
    // --- Auto-Fill Today's Date for Macro Start ---
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    const todayFormatted = `${yyyy}-${mm}-${dd}`;

    const macroStart = document.getElementById('macro-start');
    if (macroStart) macroStart.value = todayFormatted;

    const goalsForm = document.getElementById('goals-form');
    if (goalsForm) {
        goalsForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const payload = {
                aRace: document.getElementById('goal-arace').value.trim(),
                trainingPriorities: document.getElementById('goal-priorities').value.trim()
            };

            try {
                await fetchAPI('/api/users/goals', {
                    method: 'PUT',
                    body: JSON.stringify(payload)
                });

                const status = document.getElementById('goals-save-status');
                if (status) {
                    status.innerHTML = "<strong>✅ Saved!</strong>";
                    setTimeout(() => { status.innerHTML = ""; }, 3000);
                }

                const goalsBadge = document.getElementById('goals-status-badge');
                const macroBadge = document.getElementById('macro-status-badge');
                if (goalsBadge) goalsBadge.style.display = 'inline-block';
                if (macroBadge) macroBadge.style.display = 'inline-block';
            } catch (err) {
                console.error("Failed to save goals:", err);
            }
        });
    }

    const macroForm = document.getElementById('macro-plan-form');
    if (macroForm) {
        macroForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = document.getElementById('macro-btn');
            btn.setAttribute('aria-busy', 'true');
            btn.textContent = "Gemini is building your plan...";

            const payload = {
                startDate: document.getElementById('macro-start').value,
                targetDate: document.getElementById('macro-target').value
            };

            try {
                await fetchAPI('/api/plan/macro', {
                    method: 'POST',
                    body: JSON.stringify(payload)
                });
                btn.setAttribute('aria-busy', 'false');
                btn.textContent = "Plan Generated!";
                await loadMacroPlan();
                setTimeout(() => { btn.textContent = "Generate AI Macro Plan"; }, 3000);
            } catch (err) {
                alert(`Error: ${err.message}`);
                btn.setAttribute('aria-busy', 'false');
                btn.textContent = "Generate AI Macro Plan";
            }
        });
    }
}