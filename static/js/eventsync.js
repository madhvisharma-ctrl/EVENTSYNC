/*
 * EventSync — Global JavaScript
 * Handles:
 * - mobile navigation
 * - flash messages
 * - confirmations
 * - forms
 * - live clocks/countdowns
 * - status refresh helpers
 * - common UI utilities
 */

(function () {
    "use strict";

    /* =====================================================
       DOM Helpers
       ===================================================== */

    function $(selector, root) {
        return (root || document).querySelector(selector);
    }

    function $$(selector, root) {
        return Array.from((root || document).querySelectorAll(selector));
    }

    function show(element) {
        if (element) {
            element.classList.remove("hidden");
            element.removeAttribute("hidden");
        }
    }

    function hide(element) {
        if (element) {
            element.classList.add("hidden");
            element.setAttribute("hidden", "hidden");
        }
    }

    function setText(element, value) {
        if (element) {
            element.textContent = value;
        }
    }

    /* =====================================================
       Mobile Navigation
       ===================================================== */

    function initMobileNavigation() {
        const toggle = $("[data-mobile-menu-toggle]");
        const menu = $("[data-mobile-menu]");

        if (!toggle || !menu) {
            return;
        }

        toggle.addEventListener("click", function () {
            const isOpen = menu.classList.toggle("is-open");

            toggle.setAttribute(
                "aria-expanded",
                isOpen ? "true" : "false"
            );
        });

        $$(".mobile-menu a", menu).forEach(function (link) {
            link.addEventListener("click", function () {
                menu.classList.remove("is-open");
                toggle.setAttribute("aria-expanded", "false");
            });
        });
    }

    /* =====================================================
       Auto-hide Flash Messages
       ===================================================== */

    function initFlashMessages() {
        const flashes = $$(".flash[data-auto-dismiss]");

        flashes.forEach(function (flash) {
            const delay = Number(
                flash.dataset.autoDismiss || 5000
            );

            window.setTimeout(function () {
                flash.style.opacity = "0";
                flash.style.transform = "translateY(-5px)";

                window.setTimeout(function () {
                    flash.remove();
                }, 250);
            }, delay);
        });
    }

    /* =====================================================
       Confirmation Dialogs
       ===================================================== */

    function initConfirmations() {
        $$("[data-confirm]").forEach(function (element) {
            element.addEventListener("click", function (event) {
                const message =
                    element.dataset.confirm ||
                    "Are you sure you want to continue?";

                if (!window.confirm(message)) {
                    event.preventDefault();
                }
            });
        });

        $$("form[data-confirm]").forEach(function (form) {
            form.addEventListener("submit", function (event) {
                const message =
                    form.dataset.confirm ||
                    "Are you sure you want to continue?";

                if (!window.confirm(message)) {
                    event.preventDefault();
                }
            });
        });
    }

    /* =====================================================
       Form Double-submit Protection
       ===================================================== */

    function initFormProtection() {
        $$("form[data-prevent-double-submit]").forEach(function (form) {
            form.addEventListener("submit", function () {
                if (form.dataset.submitted === "true") {
                    return;
                }

                form.dataset.submitted = "true";

                const submitButtons = form.querySelectorAll(
                    'button[type="submit"], input[type="submit"]'
                );

                submitButtons.forEach(function (button) {
                    button.disabled = true;

                    if (button.tagName.toLowerCase() === "button") {
                        button.dataset.originalText = button.textContent;
                        button.textContent = "Processing...";
                    }
                });
            });
        });
    }

    /* =====================================================
       Password Visibility
       ===================================================== */

    function initPasswordToggles() {
        $$("[data-password-toggle]").forEach(function (toggle) {
            const targetId = toggle.dataset.passwordToggle;
            const input = document.getElementById(targetId);

            if (!input) {
                return;
            }

            toggle.addEventListener("click", function () {
                const isPassword =
                    input.getAttribute("type") === "password";

                input.setAttribute(
                    "type",
                    isPassword ? "text" : "password"
                );

                toggle.textContent =
                    isPassword ? "Hide" : "Show";
            });
        });
    }

    /* =====================================================
       Search Filtering
       ===================================================== */

    function initClientSearch() {
        $$("[data-table-search]").forEach(function (input) {
            const targetSelector = input.dataset.tableSearch;
            const target = $(targetSelector);

            if (!target) {
                return;
            }

            input.addEventListener("input", function () {
                const query = input.value.trim().toLowerCase();

                const rows = $$("tbody tr", target);

                rows.forEach(function (row) {
                    const text = row.textContent.toLowerCase();

                    row.style.display =
                        !query || text.includes(query)
                            ? ""
                            : "none";
                });
            });
        });
    }

    /* =====================================================
       Date / Time Helpers
       ===================================================== */

    function parseDateTime(value) {
        if (!value) {
            return null;
        }

        const date = new Date(value);

        if (Number.isNaN(date.getTime())) {
            return null;
        }

        return date;
    }

    function formatCountdown(milliseconds) {
        if (milliseconds <= 0) {
            return "00:00:00";
        }

        const totalSeconds = Math.floor(milliseconds / 1000);

        const days = Math.floor(totalSeconds / 86400);
        const hours = Math.floor(
            (totalSeconds % 86400) / 3600
        );
        const minutes = Math.floor(
            (totalSeconds % 3600) / 60
        );
        const seconds = totalSeconds % 60;

        const hh = String(hours).padStart(2, "0");
        const mm = String(minutes).padStart(2, "0");
        const ss = String(seconds).padStart(2, "0");

        if (days > 0) {
            return (
                String(days).padStart(2, "0") +
                "d " +
                hh +
                ":" +
                mm +
                ":" +
                ss
            );
        }

        return `${hh}:${mm}:${ss}`;
    }

    function initCountdowns() {
        $$("[data-countdown]").forEach(function (element) {
            const targetValue = element.dataset.countdown;
            const target = parseDateTime(targetValue);

            if (!target) {
                setText(element, "--:--:--");
                return;
            }

            function update() {
                const remaining =
                    target.getTime() - Date.now();

                setText(
                    element,
                    formatCountdown(remaining)
                );

                if (remaining <= 0) {
                    element.classList.add("countdown-expired");

                    if (
                        element.dataset.reloadOnExpire === "true"
                    ) {
                        window.setTimeout(function () {
                            window.location.reload();
                        }, 1000);
                    }
                }
            }

            update();

            window.setInterval(update, 1000);
        });
    }

    /* =====================================================
       Live Clock
       ===================================================== */

    function initClocks() {
        $$("[data-live-clock]").forEach(function (element) {
            const includeSeconds =
                element.dataset.liveClockSeconds !== "false";

            function update() {
                const now = new Date();

                setText(
                    element,
                    now.toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                        second: includeSeconds
                            ? "2-digit"
                            : undefined
                    })
                );
            }

            update();
            window.setInterval(update, 1000);
        });
    }

    /* =====================================================
       Character Counters
       ===================================================== */

    function initCharacterCounters() {
        $$("[data-character-counter]").forEach(function (counter) {
            const targetId =
                counter.dataset.characterCounter;

            const input = document.getElementById(targetId);

            if (!input) {
                return;
            }

            function update() {
                setText(
                    counter,
                    `${input.value.length} / ${
                        input.maxLength > 0
                            ? input.maxLength
                            : "∞"
                    }`
                );
            }

            input.addEventListener("input", update);
            update();
        });
    }

    /* =====================================================
       Copy to Clipboard
       ===================================================== */

    function initCopyButtons() {
        $$("[data-copy-target]").forEach(function (button) {
            button.addEventListener("click", async function () {
                const targetId =
                    button.dataset.copyTarget;

                const target = document.getElementById(
                    targetId
                );

                if (!target) {
                    return;
                }

                const value =
                    "value" in target
                        ? target.value
                        : target.textContent;

                try {
                    await navigator.clipboard.writeText(
                        value.trim()
                    );

                    const original =
                        button.textContent;

                    button.textContent = "Copied!";

                    window.setTimeout(function () {
                        button.textContent = original;
                    }, 1500);
                } catch (error) {
                    console.error(
                        "Clipboard copy failed:",
                        error
                    );
                }
            });
        });
    }

    /* =====================================================
       Modal
       ===================================================== */

    function initModals() {
        $$("[data-modal-open]").forEach(function (button) {
            button.addEventListener("click", function () {
                const modalId =
                    button.dataset.modalOpen;

                const modal =
                    document.getElementById(modalId);

                if (!modal) {
                    return;
                }

                show(modal);
                document.body.classList.add("modal-open");
            });
        });

        $$("[data-modal-close]").forEach(function (button) {
            button.addEventListener("click", function () {
                const modal =
                    button.closest("[data-modal]");

                if (!modal) {
                    return;
                }

                hide(modal);
                document.body.classList.remove(
                    "modal-open"
                );
            });
        });

        $$("[data-modal]").forEach(function (modal) {
            modal.addEventListener("click", function (event) {
                if (event.target === modal) {
                    hide(modal);
                    document.body.classList.remove(
                        "modal-open"
                    );
                }
            });
        });

        document.addEventListener("keydown", function (event) {
            if (event.key !== "Escape") {
                return;
            }

            const openModals = $$(
                '[data-modal]:not([hidden])'
            );

            openModals.forEach(function (modal) {
                hide(modal);
            });

            document.body.classList.remove(
                "modal-open"
            );
        });
    }

    /* =====================================================
       Smooth Anchor Scrolling
       ===================================================== */

    function initSmoothScrolling() {
        $$('a[href^="#"]').forEach(function (link) {
            link.addEventListener("click", function (event) {
                const id = link.getAttribute("href");

                if (!id || id === "#") {
                    return;
                }

                const target = document.querySelector(id);

                if (!target) {
                    return;
                }

                event.preventDefault();

                target.scrollIntoView({
                    behavior: "smooth",
                    block: "start"
                });
            });
        });
    }

    /* =====================================================
       Dynamic Status Refresh
       ===================================================== */

    function initStatusRefresh() {
        $$("[data-status-url]").forEach(function (element) {
            const url = element.dataset.statusUrl;

            if (!url) {
                return;
            }

            const interval = Number(
                element.dataset.statusInterval || 10000
            );

            async function refresh() {
                try {
                    const response =
                        await fetch(url, {
                            headers: {
                                "X-Requested-With":
                                    "XMLHttpRequest"
                            }
                        });

                    if (!response.ok) {
                        return;
                    }

                    const data =
                        await response.json();

                    if (
                        data.status !== undefined
                    ) {
                        setText(
                            element,
                            data.status
                        );
                    }

                    element.dataset.statusValue =
                        JSON.stringify(data);
                } catch (error) {
                    console.warn(
                        "Status refresh failed:",
                        error
                    );
                }
            }

            refresh();
            window.setInterval(
                refresh,
                interval
            );
        });
    }

    /* =====================================================
       Prevent Empty Search Submission
       ===================================================== */

    function initSearchForms() {
        $$("form[data-search-form]").forEach(function (form) {
            form.addEventListener("submit", function () {
                $$(
                    "input, select",
                    form
                ).forEach(function (field) {
                    if (
                        field.name &&
                        field.value.trim &&
                        !field.value.trim()
                    ) {
                        field.disabled = true;
                    }
                });
            });
        });
    }

    /* =====================================================
       Scroll-to-top
       ===================================================== */

    function initScrollTop() {
        const button = $("[data-scroll-top]");

        if (!button) {
            return;
        }

        function update() {
            if (window.scrollY > 400) {
                show(button);
            } else {
                hide(button);
            }
        }

        window.addEventListener(
            "scroll",
            update,
            { passive: true }
        );

        button.addEventListener(
            "click",
            function () {
                window.scrollTo({
                    top: 0,
                    behavior: "smooth"
                });
            }
        );

        update();
    }

    /* =====================================================
       Global Initialization
       ===================================================== */

    function init() {
        initMobileNavigation();
        initFlashMessages();
        initConfirmations();
        initFormProtection();
        initPasswordToggles();
        initClientSearch();
        initCountdowns();
        initClocks();
        initCharacterCounters();
        initCopyButtons();
        initModals();
        initSmoothScrolling();
        initStatusRefresh();
        initSearchForms();
        initScrollTop();
    }

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            init
        );
    } else {
        init();
    }

    /* =====================================================
       Public API
       ===================================================== */

    window.EventSync = {
        show: show,
        hide: hide,
        setText: setText,
        formatCountdown: formatCountdown,
        parseDateTime: parseDateTime
    };

})();