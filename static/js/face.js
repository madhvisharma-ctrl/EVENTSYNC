/* =========================================================
   EventSync - Face Verification JavaScript
   Handles:
   - Camera access
   - Live video preview
   - Face image capture
   - Base64 conversion
   - Capture / retake
   - Camera cleanup
   ========================================================= */

(function () {
    "use strict";

    const EventSyncFace = {
        stream: null,
        video: null,
        canvas: null,
        capturedImage: null,
        initialized: false,

        config: {
            videoId: "face-video",
            canvasId: "face-canvas",
            previewId: "face-preview",
            imageInputId: "face_image",
            startButtonId: "start-face-camera",
            captureButtonId: "capture-face",
            retakeButtonId: "retake-face",
            stopButtonId: "stop-face-camera",
            statusId: "face-status",
            width: 640,
            height: 480,
            imageQuality: 0.88
        },

        init(options = {}) {
            this.config = {
                ...this.config,
                ...options
            };

            this.cacheElements();
            this.bindEvents();

            this.initialized = true;

            return this;
        },

        cacheElements() {
            this.video = document.getElementById(
                this.config.videoId
            );

            this.canvas = document.getElementById(
                this.config.canvasId
            );

            this.preview = document.getElementById(
                this.config.previewId
            );

            this.imageInput = document.getElementById(
                this.config.imageInputId
            );

            this.startButton = document.getElementById(
                this.config.startButtonId
            );

            this.captureButton = document.getElementById(
                this.config.captureButtonId
            );

            this.retakeButton = document.getElementById(
                this.config.retakeButtonId
            );

            this.stopButton = document.getElementById(
                this.config.stopButtonId
            );

            this.statusElement = document.getElementById(
                this.config.statusId
            );
        },

        bindEvents() {
            if (this.startButton) {
                this.startButton.addEventListener(
                    "click",
                    () => this.startCamera()
                );
            }

            if (this.captureButton) {
                this.captureButton.addEventListener(
                    "click",
                    () => this.capture()
                );
            }

            if (this.retakeButton) {
                this.retakeButton.addEventListener(
                    "click",
                    () => this.retake()
                );
            }

            if (this.stopButton) {
                this.stopButton.addEventListener(
                    "click",
                    () => this.stopCamera()
                );
            }

            window.addEventListener(
                "beforeunload",
                () => this.stopCamera()
            );
        },

        isSupported() {
            return Boolean(
                navigator.mediaDevices &&
                navigator.mediaDevices.getUserMedia
            );
        },

        async startCamera() {
            if (!this.video) {
                this.setStatus(
                    "Camera preview is not available.",
                    "error"
                );

                return false;
            }

            if (!this.isSupported()) {
                this.setStatus(
                    "Camera access is not supported by this browser.",
                    "error"
                );

                return false;
            }

            if (this.stream) {
                return true;
            }

            this.setStatus(
                "Requesting camera permission...",
                "info"
            );

            try {
                this.stream =
                    await navigator.mediaDevices.getUserMedia({
                        video: {
                            facingMode: {
                                ideal: "user"
                            },
                            width: {
                                ideal: this.config.width
                            },
                            height: {
                                ideal: this.config.height
                            }
                        },
                        audio: false
                    });

                this.video.srcObject = this.stream;
                this.video.setAttribute(
                    "playsinline",
                    "true"
                );

                await this.video.play();

                this.setCameraState(true);

                this.setStatus(
                    "Camera ready. Position your face inside the frame.",
                    "success"
                );

                this.dispatchEvent(
                    "cameraStarted"
                );

                return true;
            } catch (error) {
                console.error(
                    "Face camera error:",
                    error
                );

                let message =
                    "Unable to access camera.";

                if (
                    error &&
                    error.name === "NotAllowedError"
                ) {
                    message =
                        "Camera permission was denied. Please allow camera access.";
                } else if (
                    error &&
                    error.name === "NotFoundError"
                ) {
                    message =
                        "No camera was found on this device.";
                } else if (
                    error &&
                    error.name === "NotReadableError"
                ) {
                    message =
                        "Camera is already being used by another application.";
                }

                this.setStatus(
                    message,
                    "error"
                );

                this.dispatchEvent(
                    "cameraError",
                    {
                        error: error
                    }
                );

                return false;
            }
        },

        capture() {
            if (!this.video) {
                this.setStatus(
                    "Camera preview is unavailable.",
                    "error"
                );

                return null;
            }

            if (
                !this.stream ||
                this.video.readyState < 2
            ) {
                this.setStatus(
                    "Start the camera before capturing.",
                    "warning"
                );

                return null;
            }

            if (!this.canvas) {
                this.setStatus(
                    "Capture canvas is unavailable.",
                    "error"
                );

                return null;
            }

            const width =
                this.video.videoWidth ||
                this.config.width;

            const height =
                this.video.videoHeight ||
                this.config.height;

            this.canvas.width = width;
            this.canvas.height = height;

            const context =
                this.canvas.getContext("2d");

            if (!context) {
                this.setStatus(
                    "Unable to prepare image capture.",
                    "error"
                );

                return null;
            }

            /*
             * Mirror correction for front camera.
             * If CSS mirrors the video, the captured image
             * should remain natural rather than reversed.
             */
            context.save();

            context.translate(
                width,
                0
            );

            context.scale(
                -1,
                1
            );

            context.drawImage(
                this.video,
                0,
                0,
                width,
                height
            );

            context.restore();

            const imageData =
                this.canvas.toDataURL(
                    "image/jpeg",
                    this.config.imageQuality
                );

            this.capturedImage = imageData;

            if (this.imageInput) {
                this.imageInput.value =
                    imageData;
            }

            if (this.preview) {
                this.preview.src =
                    imageData;

                this.preview.style.display =
                    "block";
            }

            this.setStatus(
                "Face image captured. You can retake it if needed.",
                "success"
            );

            this.setCaptureState(true);

            this.dispatchEvent(
                "faceCaptured",
                {
                    image: imageData
                }
            );

            return imageData;
        },

        retake() {
            this.capturedImage = null;

            if (this.imageInput) {
                this.imageInput.value = "";
            }

            if (this.preview) {
                this.preview.removeAttribute(
                    "src"
                );

                this.preview.style.display =
                    "none";
            }

            this.setCaptureState(false);

            this.setStatus(
                "Ready to capture a new face image.",
                "info"
            );

            if (!this.stream) {
                this.startCamera();
            }

            this.dispatchEvent(
                "faceRetake"
            );
        },

        clearCapture() {
            this.capturedImage = null;

            if (this.imageInput) {
                this.imageInput.value = "";
            }

            if (this.preview) {
                this.preview.removeAttribute(
                    "src"
                );

                this.preview.style.display =
                    "none";
            }

            this.setCaptureState(false);
        },

        stopCamera() {
            if (this.stream) {
                this.stream
                    .getTracks()
                    .forEach(
                        (track) => track.stop()
                    );

                this.stream = null;
            }

            if (this.video) {
                this.video.pause();
                this.video.srcObject = null;
            }

            this.setCameraState(false);

            this.dispatchEvent(
                "cameraStopped"
            );
        },

        setCameraState(active) {
            if (this.startButton) {
                this.startButton.disabled =
                    active;

                this.startButton.style.display =
                    active ? "none" : "";
            }

            if (this.captureButton) {
                this.captureButton.disabled =
                    !active ||
                    Boolean(this.capturedImage);
            }

            if (this.stopButton) {
                this.stopButton.disabled =
                    !active;

                this.stopButton.style.display =
                    active ? "" : "";
            }
        },

        setCaptureState(captured) {
            if (this.captureButton) {
                this.captureButton.disabled =
                    captured ||
                    !Boolean(this.stream);
            }

            if (this.retakeButton) {
                this.retakeButton.disabled =
                    !captured;

                this.retakeButton.style.display =
                    captured ? "" : "none";
            }
        },

        setStatus(message, type = "info") {
            if (!this.statusElement) {
                return;
            }

            this.statusElement.textContent =
                message;

            this.statusElement.classList.remove(
                "is-success",
                "is-error",
                "is-warning",
                "is-info",
                "is-muted"
            );

            this.statusElement.classList.add(
                `is-${type}`
            );
        },

        getCapturedImage() {
            return this.capturedImage;
        },

        hasCapture() {
            return Boolean(
                this.capturedImage
            );
        },

        validateCapture() {
            if (!this.capturedImage) {
                this.setStatus(
                    "Please capture your face before submitting.",
                    "warning"
                );

                return false;
            }

            if (
                !this.capturedImage.startsWith(
                    "data:image/"
                )
            ) {
                this.setStatus(
                    "Captured image format is invalid.",
                    "error"
                );

                return false;
            }

            return true;
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

    window.EventSyncFace =
        EventSyncFace;

    /*
     * Auto initialization.
     *
     * A page can provide:
     *
     * <div
     *   data-eventsync-face
     *   data-video-id="face-video"
     *   data-canvas-id="face-canvas"
     * >
     * </div>
     */
    document.addEventListener(
        "DOMContentLoaded",
        () => {
            const root =
                document.querySelector(
                    "[data-eventsync-face]"
                );

            if (!root) {
                return;
            }

            EventSyncFace.init({
                videoId:
                    root.dataset.videoId ||
                    "face-video",

                canvasId:
                    root.dataset.canvasId ||
                    "face-canvas",

                previewId:
                    root.dataset.previewId ||
                    "face-preview",

                imageInputId:
                    root.dataset.imageInputId ||
                    "face_image",

                startButtonId:
                    root.dataset.startButtonId ||
                    "start-face-camera",

                captureButtonId:
                    root.dataset.captureButtonId ||
                    "capture-face",

                retakeButtonId:
                    root.dataset.retakeButtonId ||
                    "retake-face",

                stopButtonId:
                    root.dataset.stopButtonId ||
                    "stop-face-camera",

                statusId:
                    root.dataset.statusId ||
                    "face-status"
            });
        }
    );
})();