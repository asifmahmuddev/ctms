/* ----------------------------------------------------------------------------------------------
CTMS site behaviour: the scroll-to-top control and flash message auto-dismiss.
---------------------------------------------------------------------------------------------- */

(function () {
    'use strict';

    var SCROLL_TRIGGER_OFFSET = 300;
    var VISIBLE_CLASS = 'is-visible';

    function initScrollToTop() {
        var control = document.querySelector('.scroll-to-top');
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
            var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
            window.scrollTo({ top: 0, behavior: prefersReducedMotion ? 'auto' : 'smooth' });
        });
    }

    function initMessageAutoDismiss() {
        var messages = document.querySelectorAll('[data-auto-dismiss]');

        Array.prototype.forEach.call(messages, function (message) {
            var delay = parseInt(message.getAttribute('data-auto-dismiss'), 10);
            if (!delay) {
                return;
            }

            window.setTimeout(function () {
                var alert = window.bootstrap && window.bootstrap.Alert.getOrCreateInstance(message);
                if (alert) {
                    alert.close();
                }
            }, delay);
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        initScrollToTop();
        initMessageAutoDismiss();
    });
}());
