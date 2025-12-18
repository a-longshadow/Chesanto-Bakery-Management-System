# Base Template System & Design Schema

## Overview

The Chesanto Bakery Management System uses a professional, minimal design system inspired by Apple's design principles. The template system is built with accessibility, performance, and maintainability in mind.

## Design Principles

### 1. **Seamless Design, Effortless Flow**
- Clean, uncluttered interfaces that prioritize content
- Minimal visual noise with purposeful design elements
- Intuitive navigation that guides users naturally
- Consistent spacing and typography throughout

### 2. **Professional & Minimal**
- Apple-inspired aesthetic with clean lines
- Sophisticated color palette focused on grays, whites, and subtle blues
- No purple gradients or flashy colors
- Emphasis on whitespace and breathing room

### 3. **Accessibility First**
- WCAG 2.1 AA compliant
- Keyboard navigation support
- Screen reader optimized
- Focus indicators and semantic HTML

### 4. **Performance Optimized**
- Minimal CSS and JavaScript
- Critical CSS inlined
- Lazy loading for images
- Optimized font loading

## Color Palette

### Neutral Colors
```css
--color-white: #ffffff;
--color-gray-50: #f9fafb;   /* Light backgrounds */
--color-gray-100: #f3f4f6;  /* Subtle backgrounds */
--color-gray-200: #e5e7eb;  /* Borders */
--color-gray-300: #d1d5db;  /* Input borders */
--color-gray-400: #9ca3af;  /* Placeholder text */
--color-gray-500: #6b7280;  /* Secondary text */
--color-gray-600: #4b5563;  /* Body text */
--color-gray-700: #374151;  /* Headings */
--color-gray-800: #1f2937;  /* Dark headings */
--color-gray-900: #111827;  /* Primary text */
--color-black: #000000;
```

### Accent Colors
```css
--color-primary: #2563eb;        /* Primary blue */
--color-primary-hover: #1d4ed8;  /* Hover state */
--color-primary-light: #dbeafe;  /* Light backgrounds */
--color-success: #059669;        /* Success states */
--color-warning: #d97706;        /* Warning states */
--color-error: #dc2626;          /* Error states */
--color-info: #0891b2;           /* Info states */
```

## Typography

### Font Stack
- **Primary**: Inter (Google Fonts)
- **Fallback**: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif
- **Monospace**: 'SF Mono', Monaco, 'Cascadia Code', Consolas, monospace

### Scale
```css
--font-size-xs: 0.75rem;    /* 12px - Small labels */
--font-size-sm: 0.875rem;   /* 14px - Body text, buttons */
--font-size-base: 1rem;     /* 16px - Default body */
--font-size-lg: 1.125rem;   /* 18px - Large body */
--font-size-xl: 1.25rem;    /* 20px - Small headings */
--font-size-2xl: 1.5rem;    /* 24px - Section headings */
--font-size-3xl: 1.875rem;  /* 30px - Page headings */
--font-size-4xl: 2.25rem;   /* 36px - Hero headings */
```

### Weights
```css
--font-weight-light: 300;    /* Light text */
--font-weight-normal: 400;   /* Body text */
--font-weight-medium: 500;   /* Emphasized text */
--font-weight-semibold: 600; /* Headings */
--font-weight-bold: 700;     /* Strong emphasis */
```

## Spacing System

### Scale (rem units)
```css
--spacing-1: 0.25rem;   /* 4px  - Tight spacing */
--spacing-2: 0.5rem;    /* 8px  - Small gaps */
--spacing-3: 0.75rem;   /* 12px - Default gaps */
--spacing-4: 1rem;      /* 16px - Standard spacing */
--spacing-5: 1.25rem;   /* 20px - Medium spacing */
--spacing-6: 1.5rem;    /* 24px - Section spacing */
--spacing-8: 2rem;      /* 32px - Large spacing */
--spacing-10: 2.5rem;   /* 40px - Extra large */
--spacing-12: 3rem;     /* 48px - Section breaks */
--spacing-16: 4rem;     /* 64px - Major sections */
--spacing-20: 5rem;     /* 80px - Page sections */
```

## Component Library

### 1. Navigation Bar
- **Fixed positioning** with backdrop blur effect
- **Responsive design** with mobile hamburger menu
- **Dropdown menus** with smooth animations
- **User menu** with avatar and profile options

### 2. Buttons
```css
.btn                 /* Base button styles */
.btn--primary       /* Primary action buttons */
.btn--secondary     /* Secondary buttons */
.btn--ghost         /* Minimal buttons */
.btn--sm           /* Small buttons */
.btn--lg           /* Large buttons */
```

### 3. Cards
```css
.card              /* Base card container */
.card__header      /* Card header section */
.card__content     /* Main card content */
.card__footer      /* Card footer section */
```

### 4. Forms
```css
.form-group        /* Form field wrapper */
.form-label        /* Field labels */
.form-control      /* Input fields */
.form-help         /* Help text */
.form-error        /* Error messages */
```

### 5. Notifications
```css
.notification              /* Base notification */
.notification--success     /* Success notifications */
.notification--warning     /* Warning notifications */
.notification--error       /* Error notifications */
.notification--info        /* Info notifications */
```

## Template Structure

### Base Template (`base.html`)
```
<!DOCTYPE html>
├── <head>
│   ├── Meta tags (charset, viewport, description)
│   ├── Title block
│   ├── Google Fonts (Inter)
│   ├── CSS files (base.css, components.css)
│   ├── Page-specific CSS block
│   └── Favicon
├── <body>
│   ├── Skip link (accessibility)
│   ├── Global notifications
│   ├── Navigation (include)
│   ├── Page wrapper
│   │   ├── Sidebar block (optional)
│   │   └── Main content
│   │       ├── Page header block
│   │       ├── Breadcrumbs block
│   │       └── Content block
│   ├── Footer (include)
│   ├── Base JavaScript
│   └── Page-specific JS block
```

### Component Templates
- `components/navigation.html` - Main navigation bar
- `components/footer.html` - Site footer
- `components/breadcrumbs.html` - Breadcrumb navigation
- `components/sidebar.html` - Sidebar navigation

## Layout Templates

### 1. Dashboard Layout
```html
{% extends 'base.html' %}
<!-- Full-width dashboard with cards -->
```

### 2. Content Layout
```html
{% extends 'base.html' %}
<!-- Standard content layout with sidebar -->
```

### 3. Auth Layout
```html
{% extends 'base.html' %}
<!-- Minimal layout for login/register -->
```

## Responsive Breakpoints

```css
/* Mobile First Approach */
/* Base styles: 320px+ */

@media (min-width: 640px) {
    /* sm: Small devices */
}

@media (min-width: 768px) {
    /* md: Medium devices */
}

@media (min-width: 1024px) {
    /* lg: Large devices */
}

@media (min-width: 1280px) {
    /* xl: Extra large devices */
}
```

## JavaScript Architecture

### Core Features
- **Navigation management** - Mobile menu, dropdowns
- **Notification system** - Toast notifications
- **Form enhancements** - Validation, floating labels
- **Accessibility** - Keyboard navigation, focus management
- **Performance** - Lazy loading, debouncing

### Global API
```javascript
window.ChesantoUI = {
    notification: NotificationManager,
    debounce: debounce,
    throttle: throttle,
    $: querySelector,
    $$: querySelectorAll
}
```

## Usage Examples

### Creating a New Page
```html
{% extends 'base.html' %}
{% load static %}

{% block title %}Page Title - Chesanto Bakery{% endblock %}
{% block meta_description %}Page description{% endblock %}

{% block extra_css %}
<link rel="stylesheet" href="{% static 'css/page-specific.css' %}">
{% endblock %}

{% block content %}
<div class="container">
    <h1>Page Content</h1>
</div>
{% endblock %}

{% block extra_js %}
<script src="{% static 'js/page-specific.js' %}"></script>
{% endblock %}
```

### Adding Notifications
```javascript
// Success notification
ChesantoUI.notification.show('Operation completed successfully!', 'success');

// Error notification
ChesantoUI.notification.show('An error occurred.', 'error');
```

### Creating Cards
```html
<div class="card">
    <div class="card__header">
        <h3 class="card__title">Card Title</h3>
        <p class="card__subtitle">Subtitle</p>
    </div>
    <div class="card__content">
        <p>Card content goes here.</p>
    </div>
    <div class="card__footer">
        <button class="btn btn--primary">Action</button>
    </div>
</div>
```

## Performance Guidelines

### CSS
- Use CSS custom properties for theming
- Minimize specificity conflicts
- Use efficient selectors
- Leverage CSS containment where possible

### JavaScript
- Use event delegation for dynamic content
- Debounce/throttle expensive operations
- Lazy load non-critical scripts
- Use modern ES6+ features

### Images
- Use SVG for icons and logos
- Implement lazy loading
- Provide multiple formats (WebP, etc.)
- Include proper alt texts

## Accessibility Checklist

- [ ] Semantic HTML elements
- [ ] Proper heading hierarchy
- [ ] Alt text for images
- [ ] Keyboard navigation
- [ ] Focus indicators
- [ ] ARIA labels where needed
- [ ] Color contrast compliance
- [ ] Screen reader testing

## Browser Support

### Supported Browsers
- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+

### Progressive Enhancement
- Core functionality works in all browsers
- Enhanced features use feature detection
- Graceful degradation for older browsers

This template system provides a solid foundation for the Chesanto Bakery Management System with professional, accessible, and maintainable code.
