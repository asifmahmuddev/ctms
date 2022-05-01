/* ----------------------------------------------------------------------------------------------
CTMS site behaviour: scroll-to-top and flash messages.
---------------------------------------------------------------------------------------------- */

(function () {
    'use strict';

    const SCROLL_TRIGGER_OFFSET = 300;
    const VISIBLE_CLASS = 'is-visible';

    const AUTO_DISMISS_ATTRIBUTE = 'data-auto-dismiss';
    const AUTO_DISMISS_MILLISECONDS = 9000;

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

    document.addEventListener('DOMContentLoaded', function () {
        initScrollToTop();
        initMessageAutoDismiss();
    });
}());
