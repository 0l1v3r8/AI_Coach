import { getToken, setToken, logout, fetchAPI } from './api.js';
import { showView, buildNav } from './router.js';
import { initDashboardUI, loadDashboardData, loadAnalyticsChart } from './ui/dashboard.js';
import { initCalendarUI, loadCalendar } from './ui/calendar.js';
import { initRecordsUI, loadRecordsData } from './ui/records.js';
import { initGoalsUI, loadMacroPlan } from './ui/goals.js';

document.addEventListener("DOMContentLoaded", async () => {
    // --- 1. INITIALIZATION & URL PARSING ---
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');

    if (token) {
        setToken(token);
        window.history.replaceState({}, document.title, "/");
        window.location.reload();
        return;
    }

    let targetView = 'dashboard-view';

    if (urlParams.get('success') === 'strava_connected') {
        const connStatus = document.getElementById('connection-status');
        if (connStatus) connStatus.innerHTML = "<strong>✅ Strava Connected Successfully!</strong>";
        window.history.replaceState({}, document.title, "/");
        targetView = 'settings-view';
    }

    
    // --- 2. INITIALIZE ALL UI LISTENERS ---
    initDashboardUI();
    initRecordsUI();
    initGoalsUI();
    initCalendarUI();

    // --- 3. AUTHENTICATION & DATA LOADING ---
    const savedToken = getToken();

    if (savedToken) {
        try {
            const user = await fetchAPI('/api/users/me');

            const userProfile = document.getElementById('user-profile');
            if (userProfile) userProfile.textContent = `${user.name} (${user.email})`;


            // Populate Settings
            const baselineInput = document.getElementById('settings-baseline-weeks');
            if (baselineInput && user.baselineLookbackWeeks) {
                baselineInput.value = user.baselineLookbackWeeks;
                baselineInput.defaultValue = user.baselineLookbackWeeks; // Sets the baseline for the fallback
            }

            // Populate Goals
            const goalARace = document.getElementById('goal-arace');
            const goalPriorities = document.getElementById('goal-priorities');
            if (goalARace) goalARace.value = user.aRace || '';
            if (goalPriorities) goalPriorities.value = user.trainingPriorities || '';

            if (user.aRace) {
                const goalsBadge = document.getElementById('goals-status-badge');
                const macroBadge = document.getElementById('macro-status-badge');
                if (goalsBadge) goalsBadge.style.display = 'inline-block';
                if (macroBadge) macroBadge.style.display = 'inline-block';
            }

            const stravaUnconnected = document.getElementById('strava-unconnected');
            const stravaConnected = document.getElementById('strava-connected');
            if (stravaUnconnected && stravaConnected) {
                stravaUnconnected.style.display = user.stravaConnected ? 'none' : 'block';
                stravaConnected.style.display = user.stravaConnected ? 'block' : 'none';
            }

            const intervalsUnconnected = document.getElementById('intervals-unconnected');
            const intervalsConnected = document.getElementById('intervals-connected');
            if (intervalsUnconnected && intervalsConnected) {
                intervalsUnconnected.style.display = user.intervalsConnected ? 'none' : 'block';
                intervalsConnected.style.display = user.intervalsConnected ? 'block' : 'none';
            }

            buildNav(true);
            showView(targetView);
            await loadDashboardData();

        } catch (err) {
            console.error("Auth failed:", err);
            // The api.js fetchAPI wrapper auto-logs out on 401, but just in case:
            logout();
        }

        // Health Check
        fetch('/api/health')
            .then(res => res.json())
            .then(() => {
                const apiStatus = document.getElementById('api-status');
                if (apiStatus) {
                    apiStatus.textContent = "Online 🟢";
                    apiStatus.style.color = "green";
                }
            }).catch(() => {
                const apiStatus = document.getElementById('api-status');
                if (apiStatus) apiStatus.textContent = "Offline 🔴";
            });

    } else {
        buildNav(false);
        showView('login-view');
    }

    // --- 4. NAVIGATION LISTENERS ---
    const navMenu = document.getElementById('nav-menu');
    if (navMenu) {
        navMenu.addEventListener('click', (e) => {
            const anchor = e.target.closest('a');
            if (anchor) {
                const action = anchor.getAttribute('data-action');
                if (action === 'dashboard') showView('dashboard-view');
                if (action === 'calendar') showView('calendar-view');
                if (action === 'analytics') showView('analytics-view');
                if (action === 'pbs') showView('pbs-view');
                if (action === 'goals') showView('goals-view');
                if (action === 'settings') showView('settings-view');
                if (action === 'logout') logout();
            }
        });
    }

    // Listen for the custom event fired by router.js to load view-specific data
    window.addEventListener('viewChanged', async (e) => {
        const viewId = e.detail.viewId;
        if (viewId === 'analytics-view') await loadAnalyticsChart();
        if (viewId === 'calendar-view') await loadCalendar();
        if (viewId === 'pbs-view') await loadRecordsData();
        if (viewId === 'goals-view') await loadMacroPlan();
    });
});