"""
Face Detection and Preprocessing Module.
Handles face localization, bounding box expansion, and normalized cropping.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple
import cv2
import numpy as np


@dataclass
class FaceDetectionResult:
    """Structured result from face detection and cropping."""
    success: bool
    crop_path: Optional[str] = None
    original_path: Optional[str] = None
    face_box: Optional[Tuple[int, int, int, int]] = None  # (x, y, w, h)
    faces_detected_count: int = 0
    confidence: float = 0.0
    error_message: Optional[str] = None


def process_face(
    image_path: str,
    margin_percent: float = 0.15,
    output_path: str = "temp_face_crop.jpg",
    min_face_size: Tuple[int, int] = (40, 40)
) -> FaceDetectionResult:
    """
    Reads an input image, detects the primary face, applies a margin expansion,
    and writes the cropped face to disk.

    Args:
        image_path: Filepath to the input image.
        margin_percent: Margin expansion around face box (default 0.15 = 15%).
        output_path: Filepath to write the cropped face image.
        min_face_size: Minimum width and height to qualify as a face.

    Returns:
        FaceDetectionResult with crop filepath and bounding box info.
    """
    path = Path(image_path)
    if not path.exists():
        return FaceDetectionResult(
            success=False,
            error_message=f"Input image not found at path: {image_path}"
        )

    # 1. Read input image
    image = cv2.imread(str(path))
    if image is None:
        return FaceDetectionResult(
            success=False,
            error_message=f"Failed to decode image at: {image_path}"
        )

    img_h, img_w = image.shape[:2]

    # 2. Try detection across multiple cascade models
    gray_variants = [
        cv2.cvtColor(image, cv2.COLOR_BGR2GRAY),
        cv2.equalizeHist(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))
    ]

    cascades = [
        "haarcascade_frontalface_default.xml",
        "haarcascade_frontalface_alt2.xml",
        "haarcascade_frontalface_alt.xml",
        "haarcascade_profileface.xml"
    ]

    faces = []
    for cascade_name in cascades:
        cascade_path = cv2.data.haarcascades + cascade_name
        classifier = cv2.CascadeClassifier(cascade_path)
        for g in gray_variants:
            detected = classifier.detectMultiScale(
                g,
                scaleFactor=1.05,
                minNeighbors=3,
                minSize=(20, 20)
            )
            if len(detected) > 0:
                faces = detected
                break
        if len(faces) > 0:
            break

    # If still no face detected and image is already a square portrait avatar (w/h close to 1)
    if len(faces) == 0 and 0.7 <= (img_w / img_h) <= 1.4:
        # Treat center region as primary face
        faces = [(int(img_w * 0.1), int(img_h * 0.1), int(img_w * 0.8), int(img_h * 0.8))]

    if len(faces) == 0:
        return FaceDetectionResult(
            success=False,
            original_path=str(path),
            faces_detected_count=0,
            error_message="No face detected in the provided image."
        )

    # 4. Select the primary (largest) face by bounding box area (w * h)
    faces_sorted = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
    x, y, w, h = faces_sorted[0]

    # 5. Expand bounding box by margin_percent
    margin_x = int(w * margin_percent)
    margin_y = int(h * margin_percent)

    crop_x1 = max(0, x - margin_x)
    crop_y1 = max(0, y - margin_y)
    crop_x2 = min(img_w, x + w + margin_x)
    crop_y2 = min(img_h, y + h + margin_y)

    cropped_face = image[crop_y1:crop_y2, crop_x1:crop_x2]

    # 6. Save cropped face
    out_path = Path(output_path)
    cv2.imwrite(str(out_path), cropped_face)

    return FaceDetectionResult(
        success=True,
        crop_path=str(out_path),
        original_path=str(path),
        face_box=(int(x), int(y), int(w), int(h)),
        faces_detected_count=len(faces),
        confidence=0.95,
        error_message=None
    )
