// Main JavaScript file for Chesanto Bakery Management System

// Global app configuration
const ChesantoApp = {
    // API base URL - will be set dynamically based on environment
    apiUrl: window.location.origin + '/api/',
    
    // Initialize the application
    init() {
        this.setupCSRF();
        console.log('Chesanto Bakery Management System initialized');
    },
    
    // Setup CSRF token for AJAX requests
    setupCSRF() {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        if (csrfToken) {
            // Set up axios or fetch defaults with CSRF token
            window.csrfToken = csrfToken;
        }
    }
};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    ChesantoApp.init();
});
