// List of all main section IDs in your HTML
export const VIEWS = [
    'login-view', 'dashboard-view', 'settings-view',
    'pbs-view', 'analytics-view', 'calendar-view', 'goals-view'
];

/**
 * Hides all views and displays the requested one.
 */
export function showView(viewId) {
    VIEWS.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    });

    const target = document.getElementById(viewId);
    if (target) target.style.display = 'block';

    // We dispatch a custom event so other modules know the view changed.
    // This removes the need for router.js to "know" about data fetching!
    window.dispatchEvent(new CustomEvent('viewChanged', { detail: { viewId } }));
}

/**
 * Builds the top navigation bar based on authentication status.
 */
export function buildNav(isLoggedIn) {
    const nav = document.getElementById('nav-menu');
    if (!nav) return;

    if (isLoggedIn) {
        nav.innerHTML = `
            <li><a href="#" data-action="dashboard">🏠 Dashboard</a></li>
            <li><a href="#" data-action="calendar">📅 Calendar</a></li>
            <li><a href="#" data-action="analytics">📈 Analytics</a></li>
            <li><a href="#" data-action="pbs">🏆 Records</a></li> 
            <li><a href="#" data-action="goals">🎯 Goals</a></li> 
            <li><a href="#" data-action="settings">⚙️ Settings</a></li>
            <li><a href="#" data-action="logout" class="secondary outline" style="padding: 0.5rem 1rem; border-radius: 20px;">Logout</a></li>
        `;
    } else {
        nav.innerHTML = `
            <li><a href="/api/auth/google/login" role="button">Login</a></li>
        `;
    }
}