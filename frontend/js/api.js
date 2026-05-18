// Centralized token management
const TOKEN_KEY = 'tri_coach_token';

export function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
    localStorage.setItem(TOKEN_KEY, token);
}

export function logout() {
    localStorage.removeItem(TOKEN_KEY);
    window.location.href = "/";
}

/**
 * A generic wrapper around the native fetch API that automatically 
 * injects the Authorization header and handles JSON parsing.
 */
export async function fetchAPI(endpoint, options = {}) {
    const token = getToken();

    // Set up default headers, injecting the auth token if it exists
    const headers = {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        ...(options.headers || {})
    };

    const response = await fetch(endpoint, {
        ...options,
        headers
    });

    // If the token is expired or invalid, auto-logout
    if (response.status === 401) {
        logout();
        return;
    }

    if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `API request failed: ${response.statusText}`);
    }

    return response.json();
}