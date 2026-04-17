"""
image_processor.py - Image preprocessing utilities for TensorFlow Lite inference.

All models exported from Google Teachable Machine expect:
  • Input  : (1, height, width, channels) float32 tensor, values in [0, 1] or [-1, 1]
  • Default resolution: 224 x 224 (RGB)
"""

import os
import numpy as np

try:
    import cv2  # type: ignore
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False

try:
    from PIL import Image  # type: ignore
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


# Teachable Machine models are trained at 224 x 224 RGB
TARGET_SIZE = (224, 224)


def load_image(image_path: str) -> np.ndarray:
    """
    Load an image from *image_path* and return it as an uint8 RGB numpy array
    of shape (H, W, 3).  Raises FileNotFoundError when the path does not exist.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    if _CV2_AVAILABLE:
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"OpenCV could not read: {image_path}")
        # OpenCV loads BGR — convert to RGB
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        return img

    if _PIL_AVAILABLE:
        img = Image.open(image_path).convert("RGB")
        return np.array(img, dtype=np.uint8)

    raise RuntimeError("Neither OpenCV nor Pillow is available for image loading.")


def preprocess_image(image_path: str) -> np.ndarray:
    """
    Load and preprocess an image so it is ready to be fed into the TFLite model.

    Returns a float32 array of shape (1, 224, 224, 3) with values in [0, 1].
    """
    img = load_image(image_path)

    # Resize
    if _CV2_AVAILABLE:
        img = cv2.resize(img, TARGET_SIZE, interpolation=cv2.INTER_LINEAR)
    elif _PIL_AVAILABLE:
        pil_img = Image.fromarray(img).resize(TARGET_SIZE, Image.BILINEAR)
        img = np.array(pil_img, dtype=np.uint8)
    else:
        raise RuntimeError("No image library available for resizing.")

    # Normalise to [0, 1]
    img = img.astype(np.float32) / 255.0

    # Add batch dimension
    img = np.expand_dims(img, axis=0)
    return img


def preprocess_frame(frame: np.ndarray) -> np.ndarray:
    """
    Preprocess a raw camera frame (numpy RGB uint8 array) for model inference.

    Returns a float32 array of shape (1, 224, 224, 3) with values in [0, 1].
    """
    if _CV2_AVAILABLE:
        frame = cv2.resize(frame, TARGET_SIZE, interpolation=cv2.INTER_LINEAR)
    elif _PIL_AVAILABLE:
        pil_img = Image.fromarray(frame).resize(TARGET_SIZE, Image.BILINEAR)
        frame = np.array(pil_img, dtype=np.uint8)
    else:
        # Fallback: simple nearest-neighbour resize using numpy
        h, w = frame.shape[:2]
        th, tw = TARGET_SIZE[1], TARGET_SIZE[0]
        row_idx = (np.arange(th) * h / th).astype(int)
        col_idx = (np.arange(tw) * w / tw).astype(int)
        frame = frame[np.ix_(row_idx, col_idx)]

    frame = frame.astype(np.float32) / 255.0
    return np.expand_dims(frame, axis=0)
