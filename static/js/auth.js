/**
 * Interactive Sliding Authentication Script
 * Controls mode toggling, URL history synchronization, password visibility,
 * and dynamic actions.
 */

const container = document.getElementById('container');

// Global URLs provided via data attributes or window.AUTH_CONFIG
const config = window.AUTH_CONFIG || {
    loginUrl: '/account/login/',
    signupUrl: '/account/signup/',
    siteName: 'GoTrip'
};

/**
 * Toggle between sign-in and sign-up states
 * @param {string} [targetMode] Optional: 'sign-in' or 'sign-up'
 */
function toggle(targetMode) {
    if (!container) return;

    let newMode;
    if (targetMode === 'sign-up') {
        container.classList.remove('sign-in');
        container.classList.add('sign-up');
        newMode = 'sign-up';
    } else if (targetMode === 'sign-in') {
        container.classList.remove('sign-up');
        container.classList.add('sign-in');
        newMode = 'sign-in';
    } else {
        const isSignIn = container.classList.contains('sign-in');
        newMode = isSignIn ? 'sign-up' : 'sign-in';
        container.classList.toggle('sign-in');
        container.classList.toggle('sign-up');
    }

    // Keep URL and history synchronized
    const urlParams = new URLSearchParams(window.location.search);
    const nextVal = urlParams.get('next');
    const queryString = nextVal ? `?next=${encodeURIComponent(nextVal)}` : '';
    const destinationUrl = newMode === 'sign-up' ? (config.signupUrl + queryString) : (config.loginUrl + queryString);

    if (window.history && window.history.pushState && window.location.pathname !== (newMode === 'sign-up' ? config.signupUrl : config.loginUrl)) {
        window.history.pushState({ mode: newMode }, '', destinationUrl);
    }

    document.title = (newMode === 'sign-up' ? 'Sign up' : 'Sign in') + ' · ' + config.siteName;
}

// Support global toggle invocation
window.toggle = toggle;

/**
 * Toggle password field visibility
 * @param {string} inputId ID of the password input
 * @param {HTMLElement} iconElement The clicked icon
 */
function togglePassword(inputId, iconElement) {
    const input = document.getElementById(inputId);
    if (!input) return;

    if (input.type === 'password') {
        input.type = 'text';
        iconElement.classList.remove('bx-hide', 'bxs-lock-alt');
        iconElement.classList.add('bx-show');
        iconElement.setAttribute('title', 'Hide password');
    } else {
        input.type = 'password';
        iconElement.classList.remove('bx-show');
        iconElement.classList.add('bx-hide');
        iconElement.setAttribute('title', 'Show password');
    }
}
window.togglePassword = togglePassword;

/**
 * Modal handlers for Forgot Password
 */
function openForgotPassword(event) {
    if (event) event.preventDefault();
    const modal = document.getElementById('forgotModal');
    if (modal) {
        modal.classList.add('active');
        const emailInput = document.getElementById('forgotEmailInput');
        if (emailInput) setTimeout(() => emailInput.focus(), 150);
    }
}
window.openForgotPassword = openForgotPassword;

function closeForgotPassword() {
    const modal = document.getElementById('forgotModal');
    if (modal) modal.classList.remove('active');
}
window.closeForgotPassword = closeForgotPassword;

/**
 * Toast notification system
 * @param {string} message Text message
 * @param {string} icon Boxicon class
 */
function showToast(message, icon = 'bx-info-circle') {
    let toast = document.getElementById('authToast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'authToast';
        toast.className = 'auth-toast';
        document.body.appendChild(toast);
    }

    toast.innerHTML = `<i class='bx ${icon}'></i> <span>${message}</span>`;
    toast.classList.add('show');

    clearTimeout(window._toastTimeout);
    window._toastTimeout = setTimeout(() => {
        toast.classList.remove('show');
    }, 3500);
}
window.showToast = showToast;

/**
 * Social Auth feedback
 * @param {string} provider Name of social provider
 */
function socialAuthNotice(provider) {
    showToast(`Connecting with ${provider}... Social login is available in production.`, 'bxl-' + provider.toLowerCase());
}
window.socialAuthNotice = socialAuthNotice;

// Listen for browser navigation (Back / Forward buttons)
window.addEventListener('popstate', (event) => {
    if (!container) return;
    if (event.state && event.state.mode) {
        toggle(event.state.mode);
    } else {
        const isSignUpPage = window.location.pathname.includes('signup');
        toggle(isSignUpPage ? 'sign-up' : 'sign-in');
    }
});

// Close modal when clicking outside or pressing Escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeForgotPassword();
});

document.addEventListener('click', (e) => {
    const modal = document.getElementById('forgotModal');
    if (modal && modal.classList.contains('active') && e.target === modal) {
        closeForgotPassword();
    }
});

// Initialize active mode based on page configuration
document.addEventListener('DOMContentLoaded', () => {
    if (!container) return;

    const initialMode = container.getAttribute('data-initial-mode') || 'sign-in';

    setTimeout(() => {
        if (initialMode === 'sign-up') {
            container.classList.remove('sign-in');
            container.classList.add('sign-up');
        } else {
            container.classList.remove('sign-up');
            container.classList.add('sign-in');
        }
        container.classList.add('is-ready');
    }, 80);

    // Form button loading states on submit
    const signInForm = document.getElementById('signInForm');
    if (signInForm) {
        signInForm.addEventListener('submit', () => {
            const btn = signInForm.querySelector('button[type="submit"]');
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = `<i class='bx bx-loader-alt bx-spin'></i> Signing in...`;
            }
        });
    }

    const signUpForm = document.getElementById('signUpForm');
    if (signUpForm) {
        signUpForm.addEventListener('submit', () => {
            const btn = signUpForm.querySelector('button[type="submit"]');
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = `<i class='bx bx-loader-alt bx-spin'></i> Creating account...`;
            }
        });
    }
});
