/* =========================================================
   EventSync - QR Verification JavaScript
   Handles:
   - QR token input
   - Camera QR scanning when available
   - Server-side QR validation
   - QR countdown / status
   - Copy token
   ========================================================= */

(function () {
    "use strict";

    const EventSyncQR = {
        scanner: null,
        scanning: false,
        timer: null,

        config: {
            tokenInput: "qr_token",
            video: "qr-video",
            scannerContainer: "qr-scanner-container",
            status: "qr-status",
            result: "qr-result",
            countdown: "qr-countdown",
            checkUrl: null,
            verifyUrl: null
        },

        init(options = {}) {
            this.config = {
                ...this.config,
                ...options
            };

            this.cacheElements();
            this.bindEvents();
            this.updateTokenState();

            return this;
        },

        cacheElements() {
            this.tokenInput = document.getElementById(this.config.tokenInput);
            this.video = document.getElementById(this.config.video);
            this.scannerContainer = document.getElementById(
                this.config.scannerContainer
            );
            this.statusElement = document.getElementById(this.config.status);
            this.resultElement = document.getElementById(this.config.result);
            this.countdownElement = document.getElementById(
                this.config.countdown
            );

            this.scanButton = document.getElementById("start-qr-scanner");
            this.stopButton = document.getElementById("stop-qr-scanner");
            this.checkButton = document.getElementById("check-qr-button");
            this.copyButton = document.getElementById("copy-qr-token");
        },

        bindEvents() {
            if (this.tokenInput) {
                this.tokenInput.addEventListener("input", () => {
                    this.updateTokenState();
                });

                this.tokenInput.addEventListener("change", () => {
                    this.updateTokenState();
                });
            }

            if (this.scanButton) {
                this.scanButton.addEventListener("click", () => {
                    this.startScanner();
                });
            }

            if (this.stopButton) {
                this.stopButton.addEventListener("click", () => {
                    this.stopScanner();
                });
            }

            if (this.checkButton) {
                this.checkButton.addEventListener("click", () => {
                    this.checkToken();
                });
            }

            if (this.copyButton) {
                this.copyButton.addEventListener("click", () => {
                    this.copyToken();
                });
            }

            window.addEventListener("beforeunload", () => {
                this.stopScanner();
                this.stopCountdown();
            });
        },

        normalizeToken(token) {
            if (!token) {
                return "";
            }

            // Tokens are case-sensitive; preserve their original case.
            return token
                .trim()
                .replace(/\s+/g, "");
        },

        updateTokenState() {
            if (!this.tokenInput) {
                return;
            }

            const token = this.normalizeToken(this.tokenInput.value);

            this.tokenInput.value = token;

            if (token) {
                this.setStatus("QR token entered. Ready to validate.", "info");
            } else {
                this.setStatus("Scan or enter the event QR token.", "muted");
            }
        },

        setStatus(message, type = "info") {
            if (!this.statusElement) {
                return;
            }

            this.statusElement.textContent = message;

            this.statusElement.classList.remove(
                "is-success",
                "is-error",
                "is-warning",
                "is-info",
                "is-muted"
            );

            this.statusElement.classList.add(`is-${type}`);
        },

        showResult(message, success = true) {
            if (!this.resultElement) {
                return;
            }

            this.resultElement.textContent = message;

            this.resultElement.classList.remove(
                "is-success",
                "is-error"
            );

            this.resultElement.classList.add(
                success ? "is-success" : "is-error"
            );
        },

        async checkToken() {
            if (!this.tokenInput) {
                return;
            }

            const token = this.normalizeToken(this.tokenInput.value);

            if (!token) {
                this.setStatus("Please enter or scan a QR token.", "warning");
                this.showResult("QR token is required.", false);
                return;
            }

            if (!this.config.checkUrl) {
                this.setStatus(
                    "QR validation endpoint is not configured.",
                    "error"
                );
                return;
            }

            this.setStatus("Validating QR token...", "info");

            if (this.checkButton) {
                this.checkButton.disabled = true;
            }

            try {
                const response = await fetch(this.config.checkUrl, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-Requested-With": "XMLHttpRequest"
                    },
                    body: JSON.stringify({
                        token: token
                    })
                });

                const data = await this.parseResponse(response);

                if (!response.ok || !data.success) {
                    throw new Error(
                        data.message || "QR token validation failed."
                    );
                }

                this.setStatus(
                    data.message || "QR token is valid.",
                    "success"
                );

                this.showResult(
                    data.message || "QR token verified successfully.",
                    true
                );

                if (data.expires_at) {
                    this.startCountdown(data.expires_at);
                }

                this.dispatchEvent("qrValidated", data);
            } catch (error) {
                console.error("QR validation error:", error);

                this.setStatus(
                    error.message || "Unable to validate QR token.",
                    "error"
                );

                this.showResult(
                    error.message || "QR validation failed.",
                    false
                );

                this.dispatchEvent("qrValidationFailed", {
                    message: error.message
                });
            } finally {
                if (this.checkButton) {
                    this.checkButton.disabled = false;
                }
            }
        },

        async parseResponse(response) {
            const contentType =
                response.headers.get("content-type") || "";

            if (contentType.includes("application/json")) {
                return await response.json();
            }

            const text = await response.text();

            return {
                success: response.ok,
                message: text
            };
        },

        async copyToken() {
            if (!this.tokenInput || !this.tokenInput.value) {
                this.setStatus("No QR token available to copy.", "warning");
                return;
            }

            const token = this.normalizeToken(this.tokenInput.value);

            try {
                await navigator.clipboard.writeText(token);

                this.setStatus("QR token copied.", "success");

                if (window.EventSync && EventSync.showToast) {
                    EventSync.showToast("QR token copied.", "success");
                }
            } catch (error) {
                console.error("Copy failed:", error);

                this.tokenInput.select();

                try {
                    document.execCommand("copy");
                    this.setStatus("QR token copied.", "success");
                } catch (fallbackError) {
                    this.setStatus(
                        "Unable to copy token automatically.",
                        "warning"
                    );
                }
            }
        },

        async startScanner() {
            if (this.scanning) {
                return;
            }

            if (!this.video) {
                this.setStatus(
                    "QR camera element is not available.",
                    "error"
                );
                return;
            }

            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                this.setStatus(
                    "Camera access is not supported by this browser.",
                    "error"
                );
                return;
            }

            this.setStatus(
                "Starting camera scanner...",
                "info"
            );

            try {
                if (
                    typeof window.Html5Qrcode !== "undefined" &&
                    this.scannerContainer
                ) {
                    await this.startHtml5Scanner();
                    return;
                }

                await this.startNativeCamera();
            } catch (error) {
                console.error("QR scanner error:", error);

                this.setStatus(
                    "Unable to start QR scanner. Check camera permission.",
                    "error"
                );

                this.stopScanner();
            }
        },

        async startHtml5Scanner() {
            const containerId = this.config.scannerContainer;

            this.scanner = new Html5Qrcode(containerId);

            this.scanning = true;

            this.updateScannerButtons();

            await this.scanner.start(
                {
                    facingMode: "environment"
                },
                {
                    fps: 10,
                    qrbox: {
                        width: 250,
                        height: 250
                    }
                },
                (decodedText) => {
                    this.handleScannedToken(decodedText);
                },
                () => {
                    // Ignore individual scan failures.
                }
            );

            this.setStatus(
                "Camera scanner active. Point it at the EventSync QR.",
                "info"
            );
        },

        async startNativeCamera() {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: {
                        ideal: "environment"
                    }
                },
                audio: false
            });

            this.video.srcObject = stream;

            this.video.setAttribute("playsinline", "true");

            await this.video.play();

            this.nativeStream = stream;
            this.scanning = true;

            this.updateScannerButtons();

            this.setStatus(
                "Camera active. QR decoding library is not available; enter the scanned token manually.",
                "warning"
            );
        },

        handleScannedToken(decodedText) {
            if (!decodedText) {
                return;
            }

            let token = decodedText.trim();

            /*
             * EventSync QR values may be:
             *
             * EVENTSYNC:<token>
             *
             * or a direct token.
             */
            if (token.startsWith("EVENTSYNC:")) {
                token = token.substring("EVENTSYNC:".length);
            }

            token = this.normalizeToken(token);

            if (!token) {
                return;
            }

            if (this.tokenInput) {
                this.tokenInput.value = token;
            }

            this.stopScanner();

            this.setStatus(
                "QR scanned successfully. Validating...",
                "success"
            );

            this.checkToken();

            this.dispatchEvent("qrScanned", {
                token: token,
                raw: decodedText
            });
        },

        stopScanner() {
            if (
                this.scanner &&
                typeof this.scanner.stop === "function"
            ) {
                this.scanner
                    .stop()
                    .catch(() => {})
                    .finally(() => {
                        if (
                            typeof this.scanner.clear === "function"
                        ) {
                            try {
                                this.scanner.clear();
                            } catch (error) {
                                // Ignore cleanup errors.
                            }
                        }

                        this.scanner = null;
                    });
            }

            if (this.nativeStream) {
                this.nativeStream
                    .getTracks()
                    .forEach((track) => track.stop());

                this.nativeStream = null;
            }

            if (this.video) {
                this.video.pause();
                this.video.srcObject = null;
            }

            this.scanning = false;

            this.updateScannerButtons();

            this.setStatus(
                "QR scanner stopped.",
                "muted"
            );
        },

        updateScannerButtons() {
            if (this.scanButton) {
                this.scanButton.disabled = this.scanning;
            }

            if (this.stopButton) {
                this.stopButton.disabled = !this.scanning;
            }
        },

        startCountdown(expiresAt) {
            this.stopCountdown();

            if (!this.countdownElement) {
                return;
            }

            const expiry = this.parseDate(expiresAt);

            if (!expiry) {
                return;
            }

            const update = () => {
                const remaining =
                    expiry.getTime() - Date.now();

                if (remaining <= 0) {
                    this.countdownElement.textContent =
                        "QR expired";

                    this.countdownElement.classList.add(
                        "is-expired"
                    );

                    this.stopCountdown();

                    this.setStatus(
                        "QR token has expired. Please scan the latest QR.",
                        "warning"
                    );

                    this.dispatchEvent("qrExpired", {
                        expiresAt: expiresAt
                    });

                    return;
                }

                const seconds = Math.ceil(
                    remaining / 1000
                );

                this.countdownElement.textContent =
                    `${seconds}s remaining`;

                this.countdownElement.classList.remove(
                    "is-expired"
                );
            };

            update();

            this.timer = setInterval(
                update,
                1000
            );
        },

        stopCountdown() {
            if (this.timer) {
                clearInterval(this.timer);
                this.timer = null;
            }
        },

        parseDate(value) {
            if (!value) {
                return null;
            }

            const date = new Date(value);

            if (Number.isNaN(date.getTime())) {
                return null;
            }

            return date;
        },

        dispatchEvent(name, detail = {}) {
            document.dispatchEvent(
                new CustomEvent(
                    `eventsync:${name}`,
                    {
                        detail: detail
                    }
                )
            );
        }
    };

    window.EventSyncQR = EventSyncQR;

    /*
     * Auto-initialize when QR configuration is supplied
     * through data attributes on the page.
     */
    document.addEventListener("DOMContentLoaded", () => {
        const qrRoot =
            document.querySelector("[data-eventsync-qr]");

        if (!qrRoot) {
            return;
        }

        EventSyncQR.init({
            tokenInput:
                qrRoot.dataset.tokenInput ||
                "qr_token",

            video:
                qrRoot.dataset.video ||
                "qr-video",

            scannerContainer:
                qrRoot.dataset.scannerContainer ||
                "qr-scanner-container",

            status:
                qrRoot.dataset.status ||
                "qr-status",

            result:
                qrRoot.dataset.result ||
                "qr-result",

            countdown:
                qrRoot.dataset.countdown ||
                "qr-countdown",

            checkUrl:
                qrRoot.dataset.checkUrl ||
                null,

            verifyUrl:
                qrRoot.dataset.verifyUrl ||
                null
        });
    });
})();