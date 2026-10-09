"""
EventSync Face Verification Service

Provides lightweight offline face verification using:
- OpenCV Haar Cascade face detection
- OpenCV image processing
- NumPy-based normalized image comparison

This is designed for a hackathon/demo workflow.
It is NOT a production-grade biometric authentication system.
"""

from pathlib import Path
from typing import Any
import base64
import re

import cv2
import numpy as np

from utils.helpers import get_absolute_static_path


BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

FACE_MATCH_THRESHOLD = 0.62
MIN_FACE_SIZE = 80


def _get_face_cascade():
    """
    Load OpenCV's built-in Haar Cascade face detector.
    """
    cascade_path = (
        Path(cv2.data.haarcascades)
        / "haarcascade_frontalface_default.xml"
    )

    if not cascade_path.exists():
        raise RuntimeError(
            "OpenCV Haar Cascade file was not found."
        )

    cascade = cv2.CascadeClassifier(str(cascade_path))

    if cascade.empty():
        raise RuntimeError(
            "OpenCV face detector could not be loaded."
        )

    return cascade


def _decode_base64_image(image_data: str) -> np.ndarray:
    """
    Decode a base64 image into an OpenCV BGR image.
    """
    if not image_data:
        raise ValueError("Face image data is required.")

    if not isinstance(image_data, str):
        raise ValueError("Face image data must be a string.")

    image_data = image_data.strip()

    if image_data.startswith("data:"):
        match = re.match(
            r"^data:image/[a-zA-Z0-9.+-]+;base64,(.*)$",
            image_data,
            flags=re.DOTALL,
        )

        if not match:
            raise ValueError("Invalid image data format.")

        image_data = match.group(1)

    try:
        image_bytes = base64.b64decode(
            image_data,
            validate=True,
        )
    except Exception as error:
        raise ValueError(
            "Invalid base64 face image."
        ) from error

    if not image_bytes:
        raise ValueError("Face image is empty.")

    image_array = np.frombuffer(
        image_bytes,
        dtype=np.uint8,
    )

    image = cv2.imdecode(
        image_array,
        cv2.IMREAD_COLOR,
    )

    if image is None:
        raise ValueError(
            "The uploaded image could not be decoded."
        )

    return image


def _load_stored_image(relative_path: str) -> np.ndarray:
    """
    Load a student's stored face image.
    """
    absolute_path = get_absolute_static_path(relative_path)

    if absolute_path is None:
        raise ValueError(
            "No registered face image is available."
        )

    if not absolute_path.exists():
        raise FileNotFoundError(
            "Registered face image could not be found."
        )

    image = cv2.imread(
        str(absolute_path),
        cv2.IMREAD_COLOR,
    )

    if image is None:
        raise ValueError(
            "Registered face image could not be read."
        )

    return image


def detect_faces(image: np.ndarray) -> list[tuple[int, int, int, int]]:
    """
    Detect faces in an OpenCV image.

    Returns:
        List of (x, y, width, height) tuples.
    """
    if image is None:
        return []

    if len(image.shape) == 3:
        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY,
        )
    else:
        gray = image

    cascade = _get_face_cascade()

    faces = cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(MIN_FACE_SIZE, MIN_FACE_SIZE),
    )

    return [
        (
            int(x),
            int(y),
            int(width),
            int(height),
        )
        for x, y, width, height in faces
    ]


def detect_primary_face(
    image: np.ndarray,
) -> tuple[int, int, int, int] | None:
    """
    Return the largest detected face.
    """
    faces = detect_faces(image)

    if not faces:
        return None

    return max(
        faces,
        key=lambda face: face[2] * face[3],
    )


def crop_face(
    image: np.ndarray,
    face_box: tuple[int, int, int, int],
    padding: float = 0.15,
) -> np.ndarray:
    """
    Crop a detected face with a small amount of surrounding context.
    """
    x, y, width, height = face_box

    image_height, image_width = image.shape[:2]

    pad_x = int(width * padding)
    pad_y = int(height * padding)

    left = max(0, x - pad_x)
    top = max(0, y - pad_y)

    right = min(
        image_width,
        x + width + pad_x,
    )

    bottom = min(
        image_height,
        y + height + pad_y,
    )

    cropped = image[top:bottom, left:right]

    if cropped.size == 0:
        raise ValueError("Could not crop the detected face.")

    return cropped


def _prepare_face(face_image: np.ndarray) -> np.ndarray:
    """
    Normalize a face image for comparison.
    """
    if face_image is None or face_image.size == 0:
        raise ValueError("Invalid face image.")

    if len(face_image.shape) == 3:
        gray = cv2.cvtColor(
            face_image,
            cv2.COLOR_BGR2GRAY,
        )
    else:
        gray = face_image

    gray = cv2.equalizeHist(gray)

    resized = cv2.resize(
        gray,
        (160, 160),
        interpolation=cv2.INTER_AREA,
    )

    resized = resized.astype(np.float32) / 255.0

    # Standardize brightness and contrast.
    mean = float(np.mean(resized))
    std = float(np.std(resized))

    if std > 1e-6:
        resized = (resized - mean) / std
    else:
        resized = resized - mean

    return resized


def _normalized_similarity(
    first: np.ndarray,
    second: np.ndarray,
) -> float:
    """
    Calculate normalized similarity between two prepared face images.

    The result is approximately between 0 and 1.
    """
    first_flat = first.flatten()
    second_flat = second.flatten()

    first_norm = np.linalg.norm(first_flat)
    second_norm = np.linalg.norm(second_flat)

    if first_norm == 0 or second_norm == 0:
        return 0.0

    cosine_similarity = float(
        np.dot(first_flat, second_flat)
        / (first_norm * second_norm)
    )

    cosine_similarity = max(
        -1.0,
        min(1.0, cosine_similarity),
    )

    return (cosine_similarity + 1.0) / 2.0


def compare_faces(
    registered_face: np.ndarray,
    live_face: np.ndarray,
) -> dict[str, Any]:
    """
    Compare two already-cropped face images.
    """
    registered_prepared = _prepare_face(
        registered_face
    )

    live_prepared = _prepare_face(
        live_face
    )

    similarity = _normalized_similarity(
        registered_prepared,
        live_prepared,
    )

    verified = similarity >= FACE_MATCH_THRESHOLD

    return {
        "verified": verified,
        "confidence": round(similarity, 4),
        "confidence_percent": round(
            similarity * 100,
            2,
        ),
        "threshold": FACE_MATCH_THRESHOLD,
    }


def verify_face_from_base64(
    registered_face_path: str,
    live_image_data: str,
) -> dict[str, Any]:
    """
    Verify a live base64 image against a registered face image.

    Workflow:
    1. Load registered image.
    2. Decode live image.
    3. Detect a face in both images.
    4. Crop the primary face.
    5. Compare normalized face images.
    """
    try:
        registered_image = _load_stored_image(
            registered_face_path
        )
    except (ValueError, FileNotFoundError) as error:
        return {
            "verified": False,
            "confidence": 0.0,
            "confidence_percent": 0.0,
            "reason": str(error),
            "registered_face_detected": False,
            "live_face_detected": False,
        }

    try:
        live_image = _decode_base64_image(
            live_image_data
        )
    except ValueError as error:
        return {
            "verified": False,
            "confidence": 0.0,
            "confidence_percent": 0.0,
            "reason": str(error),
            "registered_face_detected": False,
            "live_face_detected": False,
        }

    try:
        registered_box = detect_primary_face(
            registered_image
        )
    except RuntimeError as error:
        return {
            "verified": False,
            "confidence": 0.0,
            "confidence_percent": 0.0,
            "reason": str(error),
            "registered_face_detected": False,
            "live_face_detected": False,
        }

    try:
        live_box = detect_primary_face(
            live_image
        )
    except RuntimeError as error:
        return {
            "verified": False,
            "confidence": 0.0,
            "confidence_percent": 0.0,
            "reason": str(error),
            "registered_face_detected": False,
            "live_face_detected": False,
        }

    if registered_box is None:
        return {
            "verified": False,
            "confidence": 0.0,
            "confidence_percent": 0.0,
            "reason": (
                "No face was detected in the registered "
                "student image."
            ),
            "registered_face_detected": False,
            "live_face_detected": live_box is not None,
        }

    if live_box is None:
        return {
            "verified": False,
            "confidence": 0.0,
            "confidence_percent": 0.0,
            "reason": (
                "No face was detected in the live camera image."
            ),
            "registered_face_detected": True,
            "live_face_detected": False,
        }

    try:
        registered_face = crop_face(
            registered_image,
            registered_box,
        )

        live_face = crop_face(
            live_image,
            live_box,
        )

        comparison = compare_faces(
            registered_face,
            live_face,
        )
    except ValueError as error:
        return {
            "verified": False,
            "confidence": 0.0,
            "confidence_percent": 0.0,
            "reason": str(error),
            "registered_face_detected": True,
            "live_face_detected": True,
        }

    comparison.update(
        {
            "reason": (
                "Face verified successfully."
                if comparison["verified"]
                else "Face does not sufficiently match the registered image."
            ),
            "registered_face_detected": True,
            "live_face_detected": True,
        }
    )

    return comparison


def verify_face_from_image_bytes(
    registered_face_path: str,
    image_bytes: bytes,
) -> dict[str, Any]:
    """
    Verify a registered face against raw image bytes.
    """
    if not image_bytes:
        return {
            "verified": False,
            "confidence": 0.0,
            "confidence_percent": 0.0,
            "reason": "Live image data is empty.",
        }

    encoded = base64.b64encode(image_bytes).decode(
        "ascii"
    )

    return verify_face_from_base64(
        registered_face_path=registered_face_path,
        live_image_data=encoded,
    )


def validate_face_image(
    image_data: str,
) -> dict[str, Any]:
    """
    Validate that an image contains a detectable face.

    Used during student registration.
    """
    try:
        image = _decode_base64_image(image_data)
    except ValueError as error:
        return {
            "valid": False,
            "reason": str(error),
            "face_detected": False,
            "face_count": 0,
        }

    try:
        faces = detect_faces(image)
    except RuntimeError as error:
        return {
            "valid": False,
            "reason": str(error),
            "face_detected": False,
            "face_count": 0,
        }

    face_count = len(faces)

    if face_count == 0:
        return {
            "valid": False,
            "reason": "No face detected in the image.",
            "face_detected": False,
            "face_count": 0,
        }

    if face_count > 1:
        return {
            "valid": False,
            "reason": (
                "Multiple faces detected. "
                "Please capture only the student's face."
            ),
            "face_detected": True,
            "face_count": face_count,
        }

    x, y, width, height = faces[0]

    return {
        "valid": True,
        "reason": "Face detected successfully.",
        "face_detected": True,
        "face_count": 1,
        "face_box": {
            "x": x,
            "y": y,
            "width": width,
            "height": height,
        },
    }


def get_face_match_threshold() -> float:
    """
    Return the configured face verification threshold.
    """
    return FACE_MATCH_THRESHOLD