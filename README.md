# 🐱 Cat Breed Identifier

A **pure-Python Android app** built with [Kivy](https://kivy.org/) that uses a
TensorFlow Lite model to identify cat breeds in real-time from the device camera
or from photos selected from the gallery.

---

## Features

| Feature | Description |
|---------|-------------|
| 📷 Camera Detection | Live camera preview — tap **Capture & Identify** to detect breed |
| 🖼 Gallery Upload | Pick any JPG/PNG photo from your phone to analyse |
| 🤖 On-device ML | TFLite inference — works 100 % offline |
| 📊 Confidence Score | Displays breed name and confidence percentage |
| 📜 History | All detections saved to a local SQLite database with timestamps |
| 🗑 Clear History | One-tap history wipe from the History screen |

### Supported Cat Breeds

- Persian
- Siamese
- British Shorthair
- Egyptian Mau
- Bengal

---

## Project Structure

```
cat-breed/
├── main.py               # Kivy app (all screens)
├── model_handler.py      # TFLite model loading & inference
├── image_processor.py    # Image pre-processing (resize, normalise)
├── database.py           # SQLite history CRUD operations
├── buildozer.spec        # Android build configuration
├── .gitignore
├── README.md
└── assets/
    ├── model.tflite      # ← Your Teachable Machine model (add manually)
    └── labels.txt        # Breed class names (one per line)
```

---

## Quick Start (Desktop / Desktop Testing)

### 1 · Install dependencies

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install kivy numpy pillow opencv-python tflite-runtime
# On platforms where tflite-runtime is unavailable, use tensorflow instead:
# pip install tensorflow
```

### 2 · Add your model

Export your [Teachable Machine](https://teachablemachine.withgoogle.com/) model
as **TensorFlow Lite** and copy the files:

```
assets/model.tflite
assets/labels.txt     # already provided – edit if your classes differ
```

### 3 · Run on desktop

```bash
python main.py
```

---

## Building the Android APK

### Prerequisites

- Ubuntu / Debian Linux (or WSL 2 on Windows)
- Python 3.8–3.11
- Java JDK 17

```bash
pip install buildozer cython
sudo apt-get install -y \
    git zip unzip openjdk-17-jdk python3-pip \
    autoconf libtool pkg-config zlib1g-dev \
    libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev
```

### Build

```bash
# One-time setup (downloads Android SDK/NDK – ~5 GB)
buildozer android debug

# The APK will be at:
#   bin/catbreedidentifier-1.0.0-debug.apk
```

### Deploy to Phone

1. Enable **Developer Options** → **USB Debugging** on your Android phone.
2. Connect via USB, then:

```bash
buildozer android debug deploy run
```

Or transfer the APK manually and install it (allow unknown sources).

---

## Training Your Own Model

1. Visit [teachablemachine.withgoogle.com](https://teachablemachine.withgoogle.com/)
2. Create an **Image Project → Standard image model**
3. Add one class per breed, upload 50–100 photos each
4. Click **Train** (1–5 minutes)
5. **Export Model → TensorFlow Lite → Download**
6. Extract the ZIP and copy `model.tflite` → `assets/model.tflite`
7. Update `assets/labels.txt` to match your class names (one per line)

---

## Architecture

```
┌─────────────────────────────────┐
│  Kivy UI (main.py)              │
│  MainScreen / CameraScreen      │
│  GalleryScreen / ResultScreen   │
│  HistoryScreen                  │
└────────────┬────────────────────┘
             │
   ┌─────────▼──────────┐
   │ image_processor.py │  resize + normalise
   └─────────┬──────────┘
             │
   ┌─────────▼──────────┐
   │  model_handler.py  │  TFLite inference
   └─────────┬──────────┘
             │
   ┌─────────▼──────────┐
   │    database.py     │  SQLite history
   └────────────────────┘
```

---

## Permissions (Android)

| Permission | Reason |
|------------|--------|
| `CAMERA` | Live camera preview & capture |
| `READ_EXTERNAL_STORAGE` / `READ_MEDIA_IMAGES` | Gallery image selection |
| `WRITE_EXTERNAL_STORAGE` | Save captured thumbnails |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| *Model file not found* | Make sure `assets/model.tflite` exists |
| *Camera unavailable* | Grant camera permission in device settings |
| *Low accuracy* | Retrain with more images (100+ per breed) |
| *App crashes on start* | Check `buildozer android logcat` output |

---

## License

MIT © 2024 – see [LICENSE](LICENSE) for details.
