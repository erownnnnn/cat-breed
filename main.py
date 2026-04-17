"""
main.py - Cat Breed Identifier Android App built with Kivy.

Screens:
    MainScreen    - Entry point with Camera / Gallery / History buttons.
    CameraScreen  - Live camera preview with capture button.
    ResultScreen  - Shows the detected breed and confidence score.
    HistoryScreen - Scrollable list of past detections.

Dependencies:
    kivy, tflite_runtime (or tensorflow), opencv-python, pillow
"""

import os
import threading

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics.texture import Texture
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.camera import Camera
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.image import Image as KivyImage
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager, SlideTransition
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner

import database
import image_processor
import model_handler as mh

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
BG_COLOR = (0.12, 0.12, 0.18, 1)
ACCENT = (0.25, 0.55, 0.95, 1)
ACCENT_DARK = (0.18, 0.38, 0.72, 1)
SUCCESS = (0.2, 0.75, 0.45, 1)
DANGER = (0.85, 0.25, 0.25, 1)
TEXT_LIGHT = (0.95, 0.95, 0.95, 1)
TEXT_MUTED = (0.65, 0.65, 0.72, 1)

# ---------------------------------------------------------------------------
# Shared model handler (loaded once at startup)
# ---------------------------------------------------------------------------
_model: mh.ModelHandler | None = None
_model_error: str = ""


def _load_model_background():
    global _model, _model_error
    try:
        _model = mh.ModelHandler()
    except FileNotFoundError as exc:
        _model_error = f"Missing file – {exc}"
    except ImportError as exc:
        _model_error = f"Dependency not installed – {exc}"
    except Exception as exc:  # noqa: BLE001
        _model_error = str(exc)


# ---------------------------------------------------------------------------
# Helper widgets
# ---------------------------------------------------------------------------

def make_button(text, bg_color=ACCENT, **kwargs):
    """Return a rounded Button with consistent styling."""
    btn = Button(
        text=text,
        background_normal="",
        background_color=bg_color,
        color=TEXT_LIGHT,
        font_size="18sp",
        bold=True,
        **kwargs,
    )
    return btn


def make_label(text, font_size="16sp", color=TEXT_LIGHT, **kwargs):
    return Label(text=text, font_size=font_size, color=color, **kwargs)


# ---------------------------------------------------------------------------
# Main screen
# ---------------------------------------------------------------------------

class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = BoxLayout(orientation="vertical", padding=30, spacing=20)
        root.canvas.before.clear()
        with root.canvas.before:
            from kivy.graphics import Color, Rectangle
            Color(*BG_COLOR)
            self._bg_rect = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=self._update_bg, size=self._update_bg)

        # Title
        root.add_widget(make_label(
            "🐱 Cat Breed Identifier",
            font_size="28sp",
            bold=True,
            size_hint_y=0.18,
            halign="center",
        ))

        root.add_widget(make_label(
            "Point your camera at a cat or upload a photo\nto identify the breed instantly.",
            font_size="14sp",
            color=TEXT_MUTED,
            size_hint_y=0.12,
            halign="center",
        ))

        # Status label (model loading feedback)
        self.status_lbl = make_label("Loading model…", font_size="13sp", color=TEXT_MUTED)
        root.add_widget(self.status_lbl)

        # Buttons
        btn_camera = make_button("📷  Open Camera", size_hint_y=0.14)
        btn_camera.bind(on_release=self.go_camera)
        root.add_widget(btn_camera)

        btn_gallery = make_button("🖼  Upload from Gallery", bg_color=ACCENT_DARK, size_hint_y=0.14)
        btn_gallery.bind(on_release=self.go_gallery)
        root.add_widget(btn_gallery)

        btn_history = make_button("📜  View History", bg_color=(0.3, 0.3, 0.38, 1), size_hint_y=0.12)
        btn_history.bind(on_release=self.go_history)
        root.add_widget(btn_history)

        root.add_widget(make_label(
            "Detects: Persian · Siamese · British Shorthair\nEgyptian Mau · Bengal",
            font_size="13sp",
            color=TEXT_MUTED,
            halign="center",
            size_hint_y=0.15,
        ))

        self.add_widget(root)
        Clock.schedule_once(self._check_model_loaded, 1)

    def _update_bg(self, instance, value):
        self._bg_rect.pos = instance.pos
        self._bg_rect.size = instance.size

    def _check_model_loaded(self, dt):
        if _model is not None:
            self.status_lbl.text = "✅ Model ready"
            self.status_lbl.color = SUCCESS
        elif _model_error:
            self.status_lbl.text = f"⚠️ Model error: {_model_error}"
            self.status_lbl.color = DANGER
        else:
            Clock.schedule_once(self._check_model_loaded, 1)

    def go_camera(self, *_):
        self.manager.transition = SlideTransition(direction="left")
        self.manager.current = "camera"

    def go_gallery(self, *_):
        self.manager.transition = SlideTransition(direction="left")
        self.manager.current = "gallery"

    def go_history(self, *_):
        self.manager.transition = SlideTransition(direction="left")
        hist_screen = self.manager.get_screen("history")
        hist_screen.refresh()
        self.manager.current = "history"


# ---------------------------------------------------------------------------
# Camera screen
# ---------------------------------------------------------------------------

class CameraScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._camera = None
        root = BoxLayout(orientation="vertical")
        with root.canvas.before:
            from kivy.graphics import Color, Rectangle
            Color(*BG_COLOR)
            self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda i, v: setattr(self._bg, "pos", v),
                  size=lambda i, v: setattr(self._bg, "size", v))

        # Top bar
        top_bar = BoxLayout(size_hint_y=0.08, padding=5)
        btn_back = make_button("← Back", bg_color=(0.3, 0.3, 0.38, 1), size_hint_x=0.3)
        btn_back.bind(on_release=self.go_back)
        top_bar.add_widget(btn_back)
        top_bar.add_widget(make_label("Camera Detection", font_size="18sp", halign="center"))
        root.add_widget(top_bar)

        # Camera widget placeholder
        self.cam_container = BoxLayout(size_hint_y=0.72)
        root.add_widget(self.cam_container)

        # Status
        self.status_lbl = make_label("Tap 'Capture & Identify' to detect breed", font_size="14sp",
                                     color=TEXT_MUTED, size_hint_y=0.08, halign="center")
        root.add_widget(self.status_lbl)

        # Capture button
        btn_capture = make_button("📸  Capture & Identify", size_hint_y=0.12)
        btn_capture.bind(on_release=self.capture)
        root.add_widget(btn_capture)

        self.add_widget(root)

    def on_enter(self, *args):
        """Start the camera when the screen becomes active."""
        if self._camera is None:
            try:
                self._camera = Camera(play=True, resolution=(640, 480), size_hint=(1, 1))
                self.cam_container.add_widget(self._camera)
            except PermissionError as exc:
                self.cam_container.add_widget(
                    make_label(f"Camera permission denied.\nGrant camera access in Settings.\n({exc})",
                               color=DANGER, halign="center")
                )
            except Exception as exc:  # noqa: BLE001
                msg = str(exc)
                if "permission" in msg.lower():
                    hint = "Grant camera access in Settings."
                elif "not found" in msg.lower() or "unavailable" in msg.lower():
                    hint = "No camera hardware detected."
                else:
                    hint = "Check that no other app is using the camera."
                self.cam_container.add_widget(
                    make_label(f"Camera error: {hint}\n({exc})", color=DANGER, halign="center")
                )
        else:
            self._camera.play = True

    def on_leave(self, *args):
        """Stop camera to save battery."""
        if self._camera:
            self._camera.play = False

    def capture(self, *_):
        if _model is None:
            self.status_lbl.text = "⏳ Model not loaded yet…"
            return
        if self._camera is None:
            self.status_lbl.text = "⚠️ Camera not available"
            return

        self.status_lbl.text = "Analysing…"
        # Export texture to a temp file
        try:
            import tempfile
            tmp_path = os.path.join(tempfile.gettempdir(), "cat_capture.png")
            self._camera.export_to_png(tmp_path)
            self._run_inference(tmp_path)
        except Exception as exc:  # noqa: BLE001
            self.status_lbl.text = f"Error: {exc}"

    def _run_inference(self, image_path: str):
        def _task():
            try:
                tensor = image_processor.preprocess_image(image_path)
                breed, conf = _model.predict(tensor)
                database.save_detection(breed, conf, image_path)
                Clock.schedule_once(lambda dt: self._show_result(breed, conf, image_path))
            except Exception as exc:  # noqa: BLE001
                Clock.schedule_once(lambda dt: setattr(self.status_lbl, "text", f"Error: {exc}"))

        threading.Thread(target=_task, daemon=True).start()

    def _show_result(self, breed, conf, image_path):
        result_screen = self.manager.get_screen("result")
        result_screen.update(breed, conf, image_path)
        self.manager.transition = SlideTransition(direction="left")
        self.manager.current = "result"

    def go_back(self, *_):
        if self._camera:
            self._camera.play = False
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "main"


# ---------------------------------------------------------------------------
# Gallery screen (file chooser)
# ---------------------------------------------------------------------------

class GalleryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = BoxLayout(orientation="vertical")
        with root.canvas.before:
            from kivy.graphics import Color, Rectangle
            Color(*BG_COLOR)
            self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda i, v: setattr(self._bg, "pos", v),
                  size=lambda i, v: setattr(self._bg, "size", v))

        # Top bar
        top_bar = BoxLayout(size_hint_y=0.08, padding=5)
        btn_back = make_button("← Back", bg_color=(0.3, 0.3, 0.38, 1), size_hint_x=0.3)
        btn_back.bind(on_release=self.go_back)
        top_bar.add_widget(btn_back)
        top_bar.add_widget(make_label("Select a Cat Photo", font_size="18sp", halign="center"))
        root.add_widget(top_bar)

        # File chooser
        self.chooser = FileChooserIconView(
            filters=["*.png", "*.jpg", "*.jpeg", "*.webp", "*.bmp"],
            size_hint_y=0.80,
        )
        root.add_widget(self.chooser)

        # Status
        self.status_lbl = make_label("Select an image then tap Identify",
                                     font_size="14sp", color=TEXT_MUTED,
                                     size_hint_y=0.06, halign="center")
        root.add_widget(self.status_lbl)

        btn_identify = make_button("🔍  Identify Breed", size_hint_y=0.11)
        btn_identify.bind(on_release=self.identify)
        root.add_widget(btn_identify)

        self.add_widget(root)

    def identify(self, *_):
        if _model is None:
            self.status_lbl.text = "⏳ Model not loaded yet…"
            return
        selection = self.chooser.selection
        if not selection:
            self.status_lbl.text = "⚠️ Please select an image first"
            return
        image_path = selection[0]
        self.status_lbl.text = "Analysing…"
        self._run_inference(image_path)

    def _run_inference(self, image_path: str):
        def _task():
            try:
                tensor = image_processor.preprocess_image(image_path)
                breed, conf = _model.predict(tensor)
                database.save_detection(breed, conf, image_path)
                Clock.schedule_once(lambda dt: self._show_result(breed, conf, image_path))
            except Exception as exc:  # noqa: BLE001
                Clock.schedule_once(lambda dt: setattr(self.status_lbl, "text", f"Error: {exc}"))

        threading.Thread(target=_task, daemon=True).start()

    def _show_result(self, breed, conf, image_path):
        result_screen = self.manager.get_screen("result")
        result_screen.update(breed, conf, image_path)
        self.manager.transition = SlideTransition(direction="left")
        self.manager.current = "result"

    def go_back(self, *_):
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "main"


# ---------------------------------------------------------------------------
# Result screen
# ---------------------------------------------------------------------------

class ResultScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._image_path = ""

        root = BoxLayout(orientation="vertical", padding=25, spacing=15)
        with root.canvas.before:
            from kivy.graphics import Color, Rectangle
            Color(*BG_COLOR)
            self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda i, v: setattr(self._bg, "pos", v),
                  size=lambda i, v: setattr(self._bg, "size", v))

        root.add_widget(make_label("Detection Result", font_size="22sp",
                                   bold=True, size_hint_y=0.1, halign="center"))

        # Thumbnail
        self.thumb = KivyImage(size_hint_y=0.38, allow_stretch=True, keep_ratio=True)
        root.add_widget(self.thumb)

        # Breed name
        self.breed_lbl = make_label("Breed: —", font_size="24sp", bold=True,
                                    size_hint_y=0.12, halign="center")
        root.add_widget(self.breed_lbl)

        # Confidence bar area
        conf_box = BoxLayout(orientation="vertical", size_hint_y=0.12, spacing=5)
        self.conf_lbl = make_label("Confidence: —", font_size="16sp",
                                   color=TEXT_MUTED, halign="center")
        conf_box.add_widget(self.conf_lbl)

        from kivy.uix.progressbar import ProgressBar
        self.conf_bar = ProgressBar(max=100, value=0, size_hint_y=0.5)
        conf_box.add_widget(self.conf_bar)
        root.add_widget(conf_box)

        # All breed probabilities label
        self.all_lbl = make_label("", font_size="13sp", color=TEXT_MUTED,
                                  size_hint_y=0.18, halign="center")
        root.add_widget(self.all_lbl)

        # Action buttons
        btn_row = BoxLayout(size_hint_y=0.1, spacing=10)
        btn_again = make_button("🔄  Try Again", bg_color=ACCENT_DARK)
        btn_again.bind(on_release=self.try_again)
        btn_history = make_button("📜  History", bg_color=(0.3, 0.3, 0.38, 1))
        btn_history.bind(on_release=self.go_history)
        btn_row.add_widget(btn_again)
        btn_row.add_widget(btn_history)
        root.add_widget(btn_row)

        self.add_widget(root)

    def update(self, breed: str, confidence: float, image_path: str = ""):
        """Populate the result screen with detection data."""
        self._image_path = image_path
        self.breed_lbl.text = f"🐱 {breed}"

        pct = round(confidence * 100, 1)
        self.conf_lbl.text = f"Confidence: {pct}%"
        self.conf_bar.value = pct

        if image_path and os.path.exists(image_path):
            self.thumb.source = image_path
        else:
            self.thumb.source = ""

        # Show all breed probabilities if model is available
        if _model and os.path.exists(image_path):
            try:
                tensor = image_processor.preprocess_image(image_path)
                all_results = _model.predict_all(tensor)
                lines = "\n".join(
                    f"{b}: {round(c * 100, 1)}%" for b, c in all_results
                )
                self.all_lbl.text = lines
            except Exception:  # noqa: BLE001
                self.all_lbl.text = ""

    def try_again(self, *_):
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "main"

    def go_history(self, *_):
        hist = self.manager.get_screen("history")
        hist.refresh()
        self.manager.transition = SlideTransition(direction="left")
        self.manager.current = "history"


# ---------------------------------------------------------------------------
# History screen
# ---------------------------------------------------------------------------

class HistoryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        root = BoxLayout(orientation="vertical")
        with root.canvas.before:
            from kivy.graphics import Color, Rectangle
            Color(*BG_COLOR)
            self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda i, v: setattr(self._bg, "pos", v),
                  size=lambda i, v: setattr(self._bg, "size", v))

        # Top bar
        top_bar = BoxLayout(size_hint_y=0.08, padding=5)
        btn_back = make_button("← Back", bg_color=(0.3, 0.3, 0.38, 1), size_hint_x=0.3)
        btn_back.bind(on_release=self.go_back)
        top_bar.add_widget(btn_back)
        top_bar.add_widget(make_label("Detection History", font_size="18sp", halign="center"))
        btn_clear = make_button("🗑 Clear", bg_color=DANGER, size_hint_x=0.25)
        btn_clear.bind(on_release=self.clear_history)
        top_bar.add_widget(btn_clear)
        root.add_widget(top_bar)

        # Scrollable list
        scroll = ScrollView(size_hint_y=0.92)
        self.list_layout = BoxLayout(
            orientation="vertical",
            spacing=5,
            padding=[10, 5],
            size_hint_y=None,
        )
        self.list_layout.bind(minimum_height=self.list_layout.setter("height"))
        scroll.add_widget(self.list_layout)
        root.add_widget(scroll)

        self.add_widget(root)

    def refresh(self):
        """Reload history from SQLite and rebuild the list."""
        self.list_layout.clear_widgets()
        rows = database.get_all_history()
        if not rows:
            self.list_layout.add_widget(
                make_label("No detections yet.", color=TEXT_MUTED,
                           halign="center", size_hint_y=None, height=60)
            )
            return
        for row in rows:
            _, breed, conf, _img, timestamp = row
            pct = round(conf * 100, 1)
            entry = BoxLayout(size_hint_y=None, height=60, spacing=10, padding=5)
            with entry.canvas.before:
                from kivy.graphics import Color, RoundedRectangle
                Color(0.2, 0.2, 0.28, 1)
                RoundedRectangle(pos=entry.pos, size=entry.size, radius=[8])
            entry.bind(
                pos=lambda w, v: setattr(w.canvas.before.children[-1], "pos", v),
                size=lambda w, v: setattr(w.canvas.before.children[-1], "size", v),
            )
            entry.add_widget(make_label(f"🐱 {breed}", font_size="15sp",
                                        bold=True, size_hint_x=0.45))
            entry.add_widget(make_label(f"{pct}%", font_size="14sp",
                                        color=SUCCESS, size_hint_x=0.2))
            entry.add_widget(make_label(timestamp, font_size="11sp",
                                        color=TEXT_MUTED, size_hint_x=0.35))
            self.list_layout.add_widget(entry)

    def clear_history(self, *_):
        database.delete_all_history()
        self.refresh()

    def go_back(self, *_):
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "main"


# ---------------------------------------------------------------------------
# App entry point
# ---------------------------------------------------------------------------

class CatBreedApp(App):
    title = "Cat Breed Identifier"

    def build(self):
        Window.clearcolor = BG_COLOR

        sm = ScreenManager()
        sm.add_widget(MainScreen(name="main"))
        sm.add_widget(CameraScreen(name="camera"))
        sm.add_widget(GalleryScreen(name="gallery"))
        sm.add_widget(ResultScreen(name="result"))
        sm.add_widget(HistoryScreen(name="history"))

        # Initialise the database
        database.init_db()

        # Load model in background so the UI remains responsive
        threading.Thread(target=_load_model_background, daemon=True).start()

        return sm


if __name__ == "__main__":
    CatBreedApp().run()
