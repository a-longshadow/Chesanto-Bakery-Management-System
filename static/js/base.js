/**
 * Base JavaScript for Chesanto Bakery Management System
 * Apple-inspired, minimal, and professional interactions
 */

(function() {
    'use strict';

    // =============================================================================
    // UTILITIES
    // =============================================================================

    /**
     * Debounce function to limit function calls
     */
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    /**
     * Throttle function to limit function calls
     */
    function throttle(func, limit) {
        let lastFunc;
        let lastRan;
        return function(...args) {
            if (!lastRan) {
                func(...args);
                lastRan = Date.now();
            } else {
                clearTimeout(lastFunc);
                lastFunc = setTimeout(() => {
                    if ((Date.now() - lastRan) >= limit) {
                        func(...args);
                        lastRan = Date.now();
                    }
                }, limit - (Date.now() - lastRan));
            }
        };
    }

    /**
     * Element selection helper
     */
    function $(selector, context = document) {
        return context.querySelector(selector);
    }

    function $$(selector, context = document) {
        return Array.from(context.querySelectorAll(selector));
    }

    // =============================================================================
    // NAVIGATION COMPONENT
    // =============================================================================

    class Navigation {
        constructor() {
            this.navbar = $('.navbar');
            this.toggle = $('.navbar__toggle');
            this.menu = $('.navbar__menu');
            this.dropdowns = $$('.navbar__item--dropdown');
            this.userMenu = $('.navbar__user-menu');
            
            this.init();
        }

        init() {
            if (!this.navbar) return;

            // Mobile menu toggle
            if (this.toggle && this.menu) {
                this.toggle.addEventListener('click', () => this.toggleMobileMenu());
            }

            // Dropdown menus
            this.dropdowns.forEach(dropdown => this.initDropdown(dropdown));

            // User menu
            if (this.userMenu) {
                this.initUserMenu();
            }

            // Close dropdowns when clicking outside
            document.addEventListener('click', (e) => this.handleOutsideClick(e));

            // Handle escape key
            document.addEventListener('keydown', (e) => this.handleEscapeKey(e));

            // Navbar scroll effect
            this.initScrollEffect();
        }

        toggleMobileMenu() {
            const isExpanded = this.toggle.getAttribute('aria-expanded') === 'true';
            this.toggle.setAttribute('aria-expanded', !isExpanded);
            this.menu.setAttribute('aria-expanded', !isExpanded);
            
            // Prevent body scroll when menu is open
            document.body.style.overflow = isExpanded ? '' : 'hidden';
        }

        initDropdown(dropdown) {
            const trigger = dropdown.querySelector('.navbar__link--dropdown');
            const menu = dropdown.querySelector('.navbar__dropdown');
            
            if (!trigger || !menu) return;

            // Mouse events
            dropdown.addEventListener('mouseenter', () => {
                this.showDropdown(trigger, menu);
            });

            dropdown.addEventListener('mouseleave', () => {
                this.hideDropdown(trigger, menu);
            });

            // Keyboard events
            trigger.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.toggleDropdown(trigger, menu);
                }
            });
        }

        initUserMenu() {
            const trigger = this.userMenu.querySelector('.navbar__user-toggle');
            const menu = this.userMenu.querySelector('.navbar__dropdown');
            
            if (!trigger || !menu) return;

            trigger.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleDropdown(trigger, menu);
            });
        }

        showDropdown(trigger, menu) {
            trigger.setAttribute('aria-expanded', 'true');
            menu.style.opacity = '1';
            menu.style.visibility = 'visible';
            menu.style.transform = 'translateY(0)';
        }

        hideDropdown(trigger, menu) {
            trigger.setAttribute('aria-expanded', 'false');
            menu.style.opacity = '0';
            menu.style.visibility = 'hidden';
            menu.style.transform = 'translateY(-8px)';
        }

        toggleDropdown(trigger, menu) {
            const isExpanded = trigger.getAttribute('aria-expanded') === 'true';
            if (isExpanded) {
                this.hideDropdown(trigger, menu);
            } else {
                this.showDropdown(trigger, menu);
            }
        }

        handleOutsideClick(e) {
            // Close dropdowns when clicking outside
            this.dropdowns.forEach(dropdown => {
                if (!dropdown.contains(e.target)) {
                    const trigger = dropdown.querySelector('.navbar__link--dropdown');
                    const menu = dropdown.querySelector('.navbar__dropdown');
                    if (trigger && menu) {
                        this.hideDropdown(trigger, menu);
                    }
                }
            });

            // Close user menu when clicking outside
            if (this.userMenu && !this.userMenu.contains(e.target)) {
                const trigger = this.userMenu.querySelector('.navbar__user-toggle');
                const menu = this.userMenu.querySelector('.navbar__dropdown');
                if (trigger && menu) {
                    this.hideDropdown(trigger, menu);
                }
            }
        }

        handleEscapeKey(e) {
            if (e.key === 'Escape') {
                // Close mobile menu
                if (this.toggle && this.toggle.getAttribute('aria-expanded') === 'true') {
                    this.toggleMobileMenu();
                }

                // Close all dropdowns
                this.dropdowns.forEach(dropdown => {
                    const trigger = dropdown.querySelector('.navbar__link--dropdown');
                    const menu = dropdown.querySelector('.navbar__dropdown');
                    if (trigger && menu) {
                        this.hideDropdown(trigger, menu);
                    }
                });
            }
        }

        initScrollEffect() {
            let lastScrollY = window.scrollY;
            
            const handleScroll = throttle(() => {
                const currentScrollY = window.scrollY;
                
                if (currentScrollY > 50) {
                    this.navbar.style.backgroundColor = 'rgba(0, 0, 0, 0.95)';
                    this.navbar.style.backdropFilter = 'saturate(180%) blur(20px)';
                } else {
                    this.navbar.style.backgroundColor = 'rgba(0, 0, 0, 0.8)';
                    this.navbar.style.backdropFilter = 'saturate(180%) blur(20px)';
                }

                lastScrollY = currentScrollY;
            }, 10);

            window.addEventListener('scroll', handleScroll);
        }
    }

    // =============================================================================
    // NOTIFICATIONS COMPONENT
    // =============================================================================

    class NotificationManager {
        constructor() {
            this.container = $('.notification-container');
            this.init();
        }

        init() {
            if (!this.container) return;

            // Auto-dismiss notifications
            $$('.notification').forEach(notification => {
                this.initNotification(notification);
            });
        }

        initNotification(notification) {
            const closeBtn = notification.querySelector('.notification__close');
            
            if (closeBtn) {
                closeBtn.addEventListener('click', () => {
                    this.dismissNotification(notification);
                });
            }

            // Auto-dismiss after 5 seconds (except for error notifications)
            if (!notification.classList.contains('notification--error')) {
                setTimeout(() => {
                    this.dismissNotification(notification);
                }, 5000);
            }
        }

        dismissNotification(notification) {
            notification.style.transform = 'translateX(100%)';
            notification.style.opacity = '0';
            
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }

        // Method to programmatically add notifications
        show(message, type = 'info') {
            if (!this.container) {
                this.createContainer();
            }

            const notification = this.createNotification(message, type);
            this.container.appendChild(notification);
            this.initNotification(notification);

            // Trigger animation
            requestAnimationFrame(() => {
                notification.style.transform = 'translateX(0)';
                notification.style.opacity = '1';
            });
        }

        createContainer() {
            this.container = document.createElement('div');
            this.container.className = 'notification-container';
            document.body.appendChild(this.container);
        }

        createNotification(message, type) {
            const notification = document.createElement('div');
            notification.className = `notification notification--${type}`;
            notification.style.transform = 'translateX(100%)';
            notification.style.opacity = '0';
            
            notification.innerHTML = `
                <div class="notification__content">${message}</div>
                <button class="notification__close" aria-label="Dismiss notification">
                    <svg width="14" height="14" viewBox="0 0 14 14">
                        <path d="M14 1.41L12.59 0 7 5.59 1.41 0 0 1.41 5.59 7 0 12.59 1.41 14 7 8.41 12.59 14 14 12.59 8.41 7z"/>
                    </svg>
                </button>
            `;
            
            return notification;
        }
    }

    // =============================================================================
    // FORM ENHANCEMENTS
    // =============================================================================

    class FormEnhancer {
        constructor() {
            this.forms = $$('form');
            this.init();
        }

        init() {
            this.forms.forEach(form => this.enhanceForm(form));
        }

        enhanceForm(form) {
            const inputs = form.querySelectorAll('.form-control');
            
            inputs.forEach(input => {
                // Add floating label effect
                this.addFloatingLabel(input);
                
                // Add validation feedback
                this.addValidationFeedback(input);
            });
        }

        addFloatingLabel(input) {
            if (!input.id) return;
            const label = document.querySelector(`label[for="${input.id}"]`);
            if (!label) return;

            const updateLabel = () => {
                if (input.value || input === document.activeElement) {
                    label.classList.add('form-label--floating');
                } else {
                    label.classList.remove('form-label--floating');
                }
            };

            input.addEventListener('focus', updateLabel);
            input.addEventListener('blur', updateLabel);
            input.addEventListener('input', updateLabel);
            
            // Initial state
            updateLabel();
        }

        addValidationFeedback(input) {
            input.addEventListener('invalid', (e) => {
                e.preventDefault();
                this.showValidationError(input, input.validationMessage);
            });

            input.addEventListener('input', () => {
                if (input.validity.valid) {
                    this.clearValidationError(input);
                }
            });
        }

        showValidationError(input, message) {
            this.clearValidationError(input);
            
            const errorElement = document.createElement('div');
            errorElement.className = 'form-error';
            errorElement.textContent = message;
            
            input.parentNode.appendChild(errorElement);
            input.classList.add('form-control--error');
        }

        clearValidationError(input) {
            const errorElement = input.parentNode.querySelector('.form-error');
            if (errorElement) {
                errorElement.remove();
            }
            input.classList.remove('form-control--error');
        }
    }

    // =============================================================================
    // SMOOTH SCROLLING
    // =============================================================================

    function initSmoothScrolling() {
        $$('a[href^="#"]').forEach(link => {
            link.addEventListener('click', (e) => {
                const targetId = link.getAttribute('href');
                if (targetId === '#') return;
                
                const target = $(targetId);
                if (!target) return;
                
                e.preventDefault();
                
                const navbarHeight = $('.navbar')?.offsetHeight || 0;
                const targetPosition = target.offsetTop - navbarHeight - 20;
                
                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
            });
        });
    }

    // =============================================================================
    // KEYBOARD NAVIGATION
    // =============================================================================

    function initKeyboardNavigation() {
        // Tab trap for modals (when we add them)
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                // Focus management will be handled by individual components
            }
        });
    }

    // =============================================================================
    // PERFORMANCE OPTIMIZATIONS
    // =============================================================================

    function initPerformanceOptimizations() {
        // Lazy load images when we add them
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src;
                        img.classList.remove('lazy');
                        observer.unobserve(img);
                    }
                });
            });

            $$('img[data-src]').forEach(img => {
                imageObserver.observe(img);
            });
        }
    }

    // =============================================================================
    // INITIALIZATION
    // =============================================================================

    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Shared notification manager instance
    let notificationManager;

    function init() {
        // Initialize components
        new Navigation();
        notificationManager = new NotificationManager();
        new FormEnhancer();
        
        // Initialize features
        initSmoothScrolling();
        initKeyboardNavigation();
        initPerformanceOptimizations();
        
        // Add global event listeners
        window.addEventListener('resize', debounce(() => {
            // Handle resize events
        }, 250));
        
        // Add loading states
        document.body.classList.add('loaded');
    }

    // =============================================================================
    // GLOBAL API
    // =============================================================================

    // Expose some utilities globally
    window.ChesantoUI = {
        get notification() { return notificationManager; },
        debounce,
        throttle,
        $,
        $$
    };

})();
