# Flappy Bird Clone (Kivy)

A Flappy Bird clone built with [Kivy](https://kivy.org), using the classic
`sourabhv/FlappyBirdAssets` sprite and sound set (included under `assets/`).

## Project layout

```
flappybird/
├── main.py            # game code
├── buildozer.spec      # Android build config
├── assets/
│   ├── sprites/        # png sprites (bird, pipes, background, digits, etc.)
│   └── audio/           # wav sound effects
└── README.md
```

## Run it on your desktop first (recommended)

```bash
python3 -m pip install kivy
cd flappybird
python3 main.py
```

Tap/click anywhere (or press Space) to flap.

## Build the Android APK

Building an APK requires downloading the Android SDK/NDK (~1-2 GB) and a
Java toolchain, so it must be done on a machine with internet access — it
can't be done inside this sandbox. Easiest path is **Linux (native or WSL)**
or **Google Colab**.

### Option A — Linux machine (native, WSL2, or a VM)

```bash
sudo apt update
sudo apt install -y python3-pip build-essential git zip unzip openjdk-17-jdk \
    autoconf libtool pkg-config zlib1g-dev libncurses5-dev cmake

python3 -m pip install --upgrade buildozer cython==0.29.36

cd flappybird
buildozer -v android debug
```

The first build downloads the Android SDK/NDK automatically (per the
`android.ndk = 25b` / `android.api = 34` settings in `buildozer.spec`) and
will take a while. When it finishes, the APK is at:

```
bin/flappybirdclone-1.0-arm64-v8a_armeabi-v7a-debug.apk
```

Install on a connected device/emulator with:

```bash
buildozer android deploy run
```

### Option B — Google Colab (no Linux machine needed)

1. Upload the `flappybird` project folder (zipped) to Colab.
2. In a cell:
   ```python
   !unzip flappybird.zip -d /content/
   !apt update && apt install -y openjdk-17-jdk
   !pip install buildozer cython==0.29.36
   %cd /content/flappybird
   !buildozer -v android debug
   ```
3. Download `bin/*.apk` from the Colab file browser once it finishes.

### Notes / tuning

- `buildozer.spec` targets `android.api = 34`, `android.minapi = 21`,
  and builds for `arm64-v8a` + `armeabi-v7a`. Trim the `android.archs`
  list to a single ABI to speed up the first build.
- For a signed **release** APK (for the Play Store), use
  `buildozer android release` and follow buildozer's signing docs to
  create/apply a keystore.
- If the build fails on missing system packages, buildozer's error
  message usually names the missing `apt` package directly.

## Gameplay notes

- Tap/click/space to flap.
- Score increments as you pass each pipe pair.
- Game over screen shows; tap again to restart.
- All assets are the original `FlappyBirdAssets` sprites/sounds (see
  `assets/` — license info was in the original asset package, not
  redistributed here beyond the files needed to run the game).
