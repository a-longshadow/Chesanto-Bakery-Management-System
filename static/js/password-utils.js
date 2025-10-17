/**
 * Password Utilities
 * - Password strength meter
 * - Password visibility toggle
 */

// Password Strength Checker
const PasswordStrength = {
    /**
     * Calculate password strength score (0-4)
     * @param {string} password - Password to evaluate
     * @returns {Object} - {score: number, label: string, color: string}
     */
    evaluate(password) {
        if (!password) {
            return { score: 0, label: 'Enter a password', color: '#ccc', percentage: 0 };
        }

        let score = 0;
        
        // Length criteria
        if (password.length >= 8) score++;
        if (password.length >= 12) score++;
        
        // Character variety criteria
        if (/[a-z]/.test(password)) score++; // lowercase
        if (/[A-Z]/.test(password)) score++; // uppercase
        if (/[0-9]/.test(password)) score++; // numbers
        if (/[^a-zA-Z0-9]/.test(password)) score++; // special chars
        
        // Cap at 4
        score = Math.min(score, 4);
        
        // Map score to labels and colors
        const levels = {
            0: { label: 'Too weak', color: '#ef4444', percentage: 0 },
            1: { label: 'Weak', color: '#f97316', percentage: 25 },
            2: { label: 'Fair', color: '#eab308', percentage: 50 },
            3: { label: 'Good', color: '#22c55e', percentage: 75 },
            4: { label: 'Strong', color: '#16a34a', percentage: 100 }
        };
        
        return { score, ...levels[score] };
    },

    /**
     * Initialize strength meter on password input
     * @param {string} inputId - ID of password input field
     */
    init(inputId) {
        const input = document.getElementById(inputId);
        if (!input) return;

        // Create strength meter HTML
        const meterId = `${inputId}-strength-meter`;
        const meterHTML = `
            <div id="${meterId}" class="password-strength-meter" style="margin-top: 0.5rem;">
                <div class="password-strength-meter__bar" style="
                    height: 4px;
                    background: #e5e7eb;
                    border-radius: 2px;
                    overflow: hidden;
                ">
                    <div class="password-strength-meter__progress" style="
                        height: 100%;
                        width: 0%;
                        background: #ccc;
                        transition: all 0.3s ease;
                    "></div>
                </div>
                <div class="password-strength-meter__label" style="
                    font-size: 0.875rem;
                    margin-top: 0.25rem;
                    color: #6b7280;
                "></div>
            </div>
        `;

        // Insert meter after input
        input.insertAdjacentHTML('afterend', meterHTML);

        // Update on input
        input.addEventListener('input', (e) => {
            const result = this.evaluate(e.target.value);
            const meter = document.getElementById(meterId);
            const progress = meter.querySelector('.password-strength-meter__progress');
            const label = meter.querySelector('.password-strength-meter__label');

            progress.style.width = `${result.percentage}%`;
            progress.style.background = result.color;
            label.textContent = result.label;
            label.style.color = result.color;
        });
    }
};

// Password Visibility Toggle
const PasswordToggle = {
    /**
     * Create SVG icon for eye (show)
     */
    eyeIcon: `
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
            <circle cx="12" cy="12" r="3"></circle>
        </svg>
    `,

    /**
     * Create SVG icon for eye-off (hide)
     */
    eyeOffIcon: `
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
            <line x1="1" y1="1" x2="23" y2="23"></line>
        </svg>
    `,

    /**
     * Initialize toggle on password input
     * @param {string} inputId - ID of password input field
     */
    init(inputId) {
        const input = document.getElementById(inputId);
        if (!input) return;

        // Wrap input in container if not already wrapped
        if (!input.parentElement.classList.contains('password-toggle-wrapper')) {
            const wrapper = document.createElement('div');
            wrapper.className = 'password-toggle-wrapper';
            wrapper.style.position = 'relative';
            input.parentNode.insertBefore(wrapper, input);
            wrapper.appendChild(input);
        }

        const wrapper = input.parentElement;

        // Create toggle button
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'password-toggle-btn';
        button.setAttribute('aria-label', 'Toggle password visibility');
        button.innerHTML = this.eyeIcon;
        
        // Style button
        Object.assign(button.style, {
            position: 'absolute',
            right: '0.75rem',
            top: '50%',
            transform: 'translateY(-50%)',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            padding: '0.25rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#6b7280',
            transition: 'color 0.2s'
        });

        // Add hover effect
        button.addEventListener('mouseenter', () => {
            button.style.color = '#111827';
        });
        button.addEventListener('mouseleave', () => {
            button.style.color = '#6b7280';
        });

        // Add click handler
        button.addEventListener('click', () => {
            const isPassword = input.type === 'password';
            input.type = isPassword ? 'text' : 'password';
            button.innerHTML = isPassword ? this.eyeOffIcon : this.eyeIcon;
            button.setAttribute('aria-label', 
                isPassword ? 'Hide password' : 'Show password'
            );
        });

        // Add padding to input for button
        input.style.paddingRight = '3rem';

        wrapper.appendChild(button);
    },

    /**
     * Initialize toggle on multiple password fields
     * @param {string[]} inputIds - Array of password input IDs
     */
    initMultiple(inputIds) {
        inputIds.forEach(id => this.init(id));
    }
};

// Auto-initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
    // Find all password inputs with data-strength attribute
    document.querySelectorAll('input[type="password"][data-strength]').forEach(input => {
        PasswordStrength.init(input.id);
    });

    // Find all password inputs with data-toggle attribute
    document.querySelectorAll('input[type="password"][data-toggle]').forEach(input => {
        PasswordToggle.init(input.id);
    });
});

// Export for manual initialization
window.PasswordStrength = PasswordStrength;
window.PasswordToggle = PasswordToggle;
