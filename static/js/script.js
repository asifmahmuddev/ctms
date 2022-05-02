/* ----------------------------------------------------------------------------------------------
CTMS site behaviour: scroll-to-top, flash messages and password reveal.
---------------------------------------------------------------------------------------------- */

(function () {
    'use strict';

    const SCROLL_TRIGGER_OFFSET = 300;
    const VISIBLE_CLASS = 'is-visible';

    const AUTO_DISMISS_ATTRIBUTE = 'data-auto-dismiss';
    const AUTO_DISMISS_MILLISECONDS = 9000;
    const PASSWORD_TARGET_ATTRIBUTE = 'data-password-target';
    const PASSWORD_HIDDEN_ICON = 'fa-eye';
    const PASSWORD_VISIBLE_ICON = 'fa-eye-slash';

    function initScrollToTop() {
        const control = document.querySelector('.scroll-to-top');
        if (!control) {
            return;
        }

        function syncVisibility() {
            control.classList.toggle(VISIBLE_CLASS, window.pageYOffset > SCROLL_TRIGGER_OFFSET);
        }

        // passive:true tells the browser the handler never blocks the scroll, keeping it smooth.
        window.addEventListener('scroll', syncVisibility, { passive: true });
        syncVisibility();

        control.addEventListener('click', function (event) {
            event.preventDefault();
            const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
            window.scrollTo({ top: 0, behavior: prefersReducedMotion ? 'auto' : 'smooth' });
        });
    }

    function armAutoDismiss(message) {
        window.setTimeout(function () {
            const alert = window.bootstrap && window.bootstrap.Alert.getOrCreateInstance(message);
            if (alert) {
                alert.close();
            }
        }, AUTO_DISMISS_MILLISECONDS);
    }

    function initMessageAutoDismiss() {
        Array.prototype.forEach.call(document.querySelectorAll('[' + AUTO_DISMISS_ATTRIBUTE + ']'), armAutoDismiss);
    }

    function initPasswordToggles() {
        const toggles = document.querySelectorAll('[' + PASSWORD_TARGET_ATTRIBUTE + ']');

        Array.prototype.forEach.call(toggles, function (toggle) {
            const field = document.getElementById(toggle.getAttribute(PASSWORD_TARGET_ATTRIBUTE));
            const icon = toggle.querySelector('i');
            if (!field || !icon) {
                return;
            }

            toggle.addEventListener('click', function () {
                const wasRevealed = field.type === 'text';

                field.type = wasRevealed ? 'password' : 'text';
                toggle.setAttribute('aria-label', wasRevealed ? 'Show password' : 'Hide password');
                icon.classList.toggle(PASSWORD_HIDDEN_ICON, wasRevealed);
                icon.classList.toggle(PASSWORD_VISIBLE_ICON, !wasRevealed);
            });
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        initScrollToTop();
        initMessageAutoDismiss();
        initPasswordToggles();
    });
}());
