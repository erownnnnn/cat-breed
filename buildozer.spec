[app]

# ─── Application metadata ───────────────────────────────────────────────────
title           = Cat Breed Identifier
package.name    = catbreedidentifier
package.domain  = com.catbreed

source.dir      = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,tflite,txt,json

version         = 1.0.0

# ─── Entry point ────────────────────────────────────────────────────────────
source.main      = main.py

# ─── Python dependencies ────────────────────────────────────────────────────
requirements = python3,kivy==2.3.0,numpy,pillow,tflite_runtime,opencv

# ─── Asset / data directories ───────────────────────────────────────────────
source.include_patterns = assets/*

# ─── UI / Icon ──────────────────────────────────────────────────────────────
# Place a 512x512 PNG at assets/icon.png for a custom launcher icon
# presplash.filename  = %(source.dir)s/assets/presplash.png
# icon.filename       = %(source.dir)s/assets/icon.png

orientation         = portrait
fullscreen          = 0

# ─── Android configuration ──────────────────────────────────────────────────
[buildozer]

log_level           = 2
warn_on_root        = 1

android.permissions = CAMERA,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,READ_MEDIA_IMAGES

# Minimum SDK must be ≥ 21 for modern OpenCV & TFLite
android.minapi      = 21
android.api         = 33
android.ndk         = 25b
android.sdk         = 33

android.archs       = arm64-v8a, armeabi-v7a

# Enable hardware-accelerated OpenGL
android.enable_androidx = True

# Accept Android SDK licences automatically during build
android.accept_sdk_license = True

# ─── iOS (optional – leave commented out) ───────────────────────────────────
# [buildozer:ios]
# ios.kivy_ios_url    = https://github.com/kivy/kivy-ios
# ios.kivy_ios_branch = master
