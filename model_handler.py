"""
model_handler.py - TensorFlow Lite model loading and inference for cat breed detection.
"""

import os
import numpy as np

# ---------------------------------------------------------------------------
# Locate asset files relative to this module
# ---------------------------------------------------------------------------
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MODEL_PATH = os.path.join(_BASE_DIR, "assets", "model.tflite")
DEFAULT_LABELS_PATH = os.path.join(_BASE_DIR, "assets", "labels.txt")


def load_labels(labels_path: str = DEFAULT_LABELS_PATH):
    """
    Read a labels.txt file and return a list of breed name strings.
    Each non-empty line is treated as one label.
    """
    if not os.path.exists(labels_path):
        raise FileNotFoundError(f"Labels file not found: {labels_path}")
    with open(labels_path, "r", encoding="utf-8") as fh:
        labels = [line.strip() for line in fh if line.strip()]
    return labels


class ModelHandler:
    """
    Wraps a TensorFlow Lite interpreter and exposes a simple predict() API.

    Usage
    -----
    handler = ModelHandler()          # uses default asset paths
    breed, confidence = handler.predict(preprocessed_input_array)
    all_probs = handler.predict_all(preprocessed_input_array)
    """

    def __init__(
        self,
        model_path: str = DEFAULT_MODEL_PATH,
        labels_path: str = DEFAULT_LABELS_PATH,
    ):
        self.model_path = model_path
        self.labels = load_labels(labels_path)
        self._interpreter = None
        self._input_details = None
        self._output_details = None
        self._load_model()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_model(self):
        """Load the TFLite model and allocate tensors."""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model file not found: {self.model_path}")

        try:
            import tflite_runtime.interpreter as tflite  # type: ignore
            Interpreter = tflite.Interpreter
        except ImportError:
            try:
                import tensorflow as tf  # type: ignore
                Interpreter = tf.lite.Interpreter
            except ImportError as exc:
                raise ImportError(
                    "Neither tflite_runtime nor tensorflow is installed. "
                    "Install one of them to use ModelHandler."
                ) from exc

        self._interpreter = Interpreter(model_path=self.model_path)
        self._interpreter.allocate_tensors()
        self._input_details = self._interpreter.get_input_details()
        self._output_details = self._interpreter.get_output_details()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def input_shape(self):
        """Return the expected input shape (batch, H, W, C)."""
        return tuple(self._input_details[0]["shape"])

    def predict_all(self, input_data: np.ndarray) -> list:
        """
        Run inference and return a list of (label, probability) tuples,
        sorted from highest to lowest probability.

        *input_data* must be a float32 array matching the model input shape,
        typically (1, 224, 224, 3).
        """
        # Cast to the dtype the model expects
        expected_dtype = self._input_details[0]["dtype"]
        input_data = input_data.astype(expected_dtype)

        self._interpreter.set_tensor(self._input_details[0]["index"], input_data)
        self._interpreter.invoke()

        output_data = self._interpreter.get_tensor(self._output_details[0]["index"])
        probabilities = output_data[0]  # shape: (num_classes,)

        results = sorted(
            zip(self.labels, probabilities),
            key=lambda x: x[1],
            reverse=True,
        )
        return results

    def predict(self, input_data: np.ndarray):
        """
        Run inference and return the top prediction as (breed_name, confidence_float).
        confidence is in the range [0, 1].
        """
        results = self.predict_all(input_data)
        if not results:
            return ("Unknown", 0.0)
        breed, confidence = results[0]
        return (breed, float(confidence))
