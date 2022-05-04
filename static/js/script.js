/* ----------------------------------------------------------------------------------------------
CTMS site behaviour: scroll-to-top, flash messages, password reveal, picture cropping, action confirmation and
table column widths.
---------------------------------------------------------------------------------------------- */

(function () {
    'use strict';

    const SCROLL_TRIGGER_OFFSET = 300;
    const VISIBLE_CLASS = 'is-visible';

    const MESSAGE_STACK_CLASS = 'message-stack';
    const AUTO_DISMISS_ATTRIBUTE = 'data-auto-dismiss';
    const AUTO_DISMISS_MILLISECONDS = 9000;
    const ERROR_ALERT_CLASS = 'alert alert-danger alert-dismissible fade show';

    const CONFIRM_ATTRIBUTE = 'data-confirm';
    const CONFIRM_DETAIL_ATTRIBUTE = 'data-confirm-detail';
    const CONFIRM_ACTION_ATTRIBUTE = 'data-confirm-action';
    const CONFIRMED_ATTRIBUTE = 'data-confirmed';
    const CONFIRM_MODAL_SELECTOR = '[data-confirm-modal]';
    const CONFIRM_CONTROL_SELECTOR = 'button:not([disabled])';
    const DEFAULT_CONFIRM_ACTION = 'Confirm';

    const TABLE_NAME_ATTRIBUTE = 'data-table';
    const COLUMN_RESET_ATTRIBUTE = 'data-columns-reset';
    const COLUMN_GRIP_CLASS = 'panel-column-grip';
    const COLUMN_WIDTH_KEY = 'ctms-column-widths-';
    const RESIZING_CLASS = 'is-resizing';
    const WIDE_LAYOUT_QUERY = '(min-width: 992px)';
    const MINIMUM_COLUMN_WIDTH = 72;

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
    function initActionConfirmation() {
        const dialogue = document.querySelector(CONFIRM_MODAL_SELECTOR);
        if (!dialogue || !window.bootstrap) {
            return;
        }

        const modal = new window.bootstrap.Modal(dialogue);
        const title = dialogue.querySelector('[data-confirm-title]');
        const detail = dialogue.querySelector('[' + CONFIRM_DETAIL_ATTRIBUTE + ']');
        const accept = dialogue.querySelector('[data-confirm-accept]');
        let held = null;
        let opener = null;

        document.addEventListener('submit', function (event) {
            const form = event.target;
            const button = form.querySelector('[' + CONFIRM_ATTRIBUTE + ']');

            if (!button || form.hasAttribute(CONFIRMED_ATTRIBUTE)) {
                return;
            }

            event.preventDefault();
            held = form;
            opener = button;

            title.textContent = button.getAttribute(CONFIRM_ATTRIBUTE);
            detail.textContent = button.getAttribute(CONFIRM_DETAIL_ATTRIBUTE) || '';
            detail.hidden = !detail.textContent;
            accept.textContent = button.getAttribute(CONFIRM_ACTION_ATTRIBUTE) || DEFAULT_CONFIRM_ACTION;
            modal.show();
        });

        accept.addEventListener('click', function () {
            const form = held;
            modal.hide();

            if (form) {
                // Marked as answered, so the submission it is about to make passes straight through.
                form.setAttribute(CONFIRMED_ATTRIBUTE, '');
                if (form.requestSubmit) {
                    form.requestSubmit();
                } else {
                    form.submit();
                }
            }
        });

        /* Tabbing past the last control would otherwise land on the page behind for one press, and
        Escape does not reach the dialogue from there. Focus is wrapped between its own controls. */
        dialogue.addEventListener('keydown', function (event) {
            if (event.key !== 'Tab') {
                return;
            }

            const controls = Array.prototype.filter.call(
                dialogue.querySelectorAll(CONFIRM_CONTROL_SELECTOR),
                function (control) { return control.offsetParent !== null; });

            if (!controls.length) {
                return;
            }

            const first = controls[0];
            const last = controls[controls.length - 1];

            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
            }
        });

        /* Closing hands focus back to the control that opened it, so a keyboard carries on from
        where it left off rather than starting again at the top of the page. */
        dialogue.addEventListener('hidden.bs.modal', function () {
            if (opener && document.body.contains(opener)) {
                opener.focus();
            }
            held = null;
            opener = null;
        });
    }

    /* A reCAPTCHA token is single-use and expires two minutes after it is minted, so one is asked for
    at the moment the form is submitted rather than when the page loads. Submitting again after a
    refused password, or after filling the form slowly, therefore carries a token that is still good. */
    function readColumnWidths(name) {
        try {
            return JSON.parse(window.localStorage.getItem(COLUMN_WIDTH_KEY + name));
        } catch (error) {
            return null;
        }
    }

    function writeColumnWidths(name, widths) {
        try {
            if (widths) {
                window.localStorage.setItem(COLUMN_WIDTH_KEY + name, JSON.stringify(widths));
            } else {
                window.localStorage.removeItem(COLUMN_WIDTH_KEY + name);
            }
        } catch (error) {
            // A browser that refuses storage still resizes: only remembering the result is lost.
        }
    }

    /* A heading can be dragged wider, and the widths settled on are kept against the table's own name
    so they are still in place on the next visit. Only while the rows are real table rows: narrower
    than that a row is stacked, where a column has no width to set. */
    function makeColumnsResizable(table, wideLayout) {
        const headings = Array.prototype.slice.call(table.querySelectorAll('thead th'));
        if (headings.length < 2) {
            return;
        }

        const name = table.getAttribute(TABLE_NAME_ATTRIBUTE);
        // One table to a page, so the control that puts its widths back is found on the page.
        const reset = document.querySelector('[' + COLUMN_RESET_ATTRIBUTE + ']');

        function measure() {
            return headings.map(function (heading) {
                return Math.round(heading.getBoundingClientRect().width);
            });
        }

        function hold(widths) {
            table.style.tableLayout = 'fixed';
            headings.forEach(function (heading, index) {
                heading.style.width = widths[index] + 'px';
            });
        }

        function release() {
            table.style.tableLayout = '';
            headings.forEach(function (heading) {
                heading.style.width = '';
            });
        }

        function offerReset(wanted) {
            if (reset) {
                reset.hidden = !wanted;
            }
        }

        function restore() {
            const kept = wideLayout.matches && readColumnWidths(name);
            if (kept && kept.length === headings.length) {
                hold(kept);
                offerReset(true);
            } else {
                release();
                offerReset(false);
            }
        }

        headings.slice(0, -1).forEach(function (heading, index) {
            const grip = document.createElement('span');
            grip.className = COLUMN_GRIP_CLASS;
            grip.setAttribute('aria-hidden', 'true');
            heading.appendChild(grip);

            grip.addEventListener('pointerdown', function (event) {
                if (!wideLayout.matches) {
                    return;
                }
                event.preventDefault();

                // Every column is pinned to what it measures now, so widening one leaves the rest alone.
                const widths = measure();
                const startX = event.clientX;
                const startWidth = widths[index];

                hold(widths);
                grip.classList.add(RESIZING_CLASS);
                table.classList.add(RESIZING_CLASS);
                grip.setPointerCapture(event.pointerId);

                function drag(move) {
                    headings[index].style.width = Math.max(MINIMUM_COLUMN_WIDTH, startWidth + move.clientX - startX) + 'px';
                }

                function settle() {
                    grip.removeEventListener('pointermove', drag);
                    grip.removeEventListener('pointerup', settle);
                    grip.removeEventListener('pointercancel', settle);
                    grip.classList.remove(RESIZING_CLASS);
                    table.classList.remove(RESIZING_CLASS);
                    writeColumnWidths(name, measure());
                    offerReset(true);
                }

                grip.addEventListener('pointermove', drag);
                grip.addEventListener('pointerup', settle);
                grip.addEventListener('pointercancel', settle);
            });
        });

        if (reset) {
            reset.addEventListener('click', function () {
                writeColumnWidths(name, null);
                release();
                offerReset(false);
            });
        }

        wideLayout.addEventListener('change', restore);
        restore();
    }

    function initResizableColumns() {
        const wideLayout = window.matchMedia(WIDE_LAYOUT_QUERY);

        Array.prototype.forEach.call(document.querySelectorAll('[' + TABLE_NAME_ATTRIBUTE + ']'), function (table) {
            makeColumnsResizable(table, wideLayout);
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        initScrollToTop();
        initMessageAutoDismiss();
        initPasswordToggles();
        initPictureCropper();
        initActionConfirmation();
        initResizableColumns();
    });
}());
