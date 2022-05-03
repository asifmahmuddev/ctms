/* ----------------------------------------------------------------------------------------------
CTMS site behaviour: scroll-to-top, flash messages, password reveal and picture cropping.
---------------------------------------------------------------------------------------------- */

(function () {
    'use strict';

    const SCROLL_TRIGGER_OFFSET = 300;
    const VISIBLE_CLASS = 'is-visible';

    const MESSAGE_STACK_CLASS = 'message-stack';
    const AUTO_DISMISS_ATTRIBUTE = 'data-auto-dismiss';
    const AUTO_DISMISS_MILLISECONDS = 9000;
    const ERROR_ALERT_CLASS = 'alert alert-danger alert-dismissible fade show';

    const PASSWORD_TARGET_ATTRIBUTE = 'data-password-target';
    const PASSWORD_HIDDEN_ICON = 'fa-eye';
    const PASSWORD_VISIBLE_ICON = 'fa-eye-slash';

    const PICTURE_FORM_SELECTOR = '[data-picture-form]';
    const PICTURE_PREVIEW_SELECTOR = '[data-picture-preview]';
    const UNSUPPORTED_PICTURE_MESSAGE = 'Choose a PNG or JPEG picture.';
    const OVERSIZED_PICTURE_MESSAGE = 'Choose a picture smaller than {limit} MB.';
    const BYTES_PER_MEGABYTE = 1024 * 1024;
    const CROP_ASPECT_RATIO = 1;
    const CROP_VIEW_MODE = 1;
    const CROP_MIN_BOX_PIXELS = 96;

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

    // Messages join the server's fixed stack, created here when the page carries none.
    function showErrorAlert(message) {
        let stack = document.querySelector('.' + MESSAGE_STACK_CLASS);
        const alert = document.createElement('div');
        const close = document.createElement('button');

        if (!stack) {
            stack = document.createElement('div');
            stack.className = MESSAGE_STACK_CLASS;
            document.body.insertBefore(stack, document.body.firstChild);
        }

        close.type = 'button';
        close.className = 'btn-close';
        close.setAttribute('data-bs-dismiss', 'alert');
        close.setAttribute('aria-label', 'Close');

        alert.className = ERROR_ALERT_CLASS;
        alert.setAttribute('role', 'alert');
        alert.textContent = message;
        alert.appendChild(close);

        stack.appendChild(alert);
        armAutoDismiss(alert);
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

    function initPictureCropper() {
        const form = document.querySelector(PICTURE_FORM_SELECTOR);
        if (!form || !window.Cropper || !window.bootstrap) {
            return;
        }

        const fileInput = form.querySelector('input[type="file"]');
        const preview = form.querySelector(PICTURE_PREVIEW_SELECTOR);
        const dialog = form.querySelector('.modal');
        const modal = window.bootstrap.Modal.getOrCreateInstance(dialog);
        let cropper = null;

        // Looked up once, because the crop event fires continuously while the selection is dragged.
        const selectionFields = {};
        ['x', 'y', 'width', 'height'].forEach(function (key) {
            selectionFields[key] = form.querySelector('[name="crop_' + key + '"]');
        });

        // Both limits are read from the control itself, so the browser applies the server's own rules.
        function pictureProblem(file) {
            const maxBytes = parseInt(fileInput.getAttribute('data-max-bytes'), 10);
            const accepted = fileInput.accept.split(',').some(function (type) {
                return type.trim() === file.type;
            });

            if (!accepted) {
                return UNSUPPORTED_PICTURE_MESSAGE;
            }
            if (maxBytes && file.size > maxBytes) {
                return OVERSIZED_PICTURE_MESSAGE.replace('{limit}', Math.floor(maxBytes / BYTES_PER_MEGABYTE));
            }
            return '';
        }

        function recordSelection(detail) {
            Object.keys(selectionFields).forEach(function (key) {
                if (selectionFields[key]) {
                    selectionFields[key].value = Math.round(detail[key]);
                }
            });
        }

        fileInput.addEventListener('change', function () {
            if (!fileInput.files.length) {
                return;
            }

            const problem = pictureProblem(fileInput.files[0]);

            if (problem) {
                showErrorAlert(problem);
                fileInput.value = '';
                return;
            }

            const reader = new FileReader();
            reader.onload = function (event) {
                preview.src = event.target.result;
                modal.show();
            };
            reader.readAsDataURL(fileInput.files[0]);
        });

        // Cropper measures the image, so it can only start once the dialog has finished opening.
        dialog.addEventListener('shown.bs.modal', function () {
            cropper = new window.Cropper(preview, {
                aspectRatio: CROP_ASPECT_RATIO,
                viewMode: CROP_VIEW_MODE,
                autoCropArea: 1,
                minCropBoxWidth: CROP_MIN_BOX_PIXELS,
                minCropBoxHeight: CROP_MIN_BOX_PIXELS,
                crop: function (event) {
                    recordSelection(event.detail);
                }
            });
        });

        // Abandoning the dialog also drops the chosen file, so a later save cannot submit it unseen.
        dialog.addEventListener('hidden.bs.modal', function () {
            if (cropper) {
                cropper.destroy();
                cropper = null;
            }
            fileInput.value = '';
        });
    }

    /* An action that cannot be taken back asks first, in the site's own dialogue rather than the
    browser's box. The submission is held, the dialogue takes its wording from the control that
    raised it, and only accepting lets the form through. */
    document.addEventListener('DOMContentLoaded', function () {
        initScrollToTop();
        initMessageAutoDismiss();
        initPasswordToggles();
        initPictureCropper();
    });
}());
