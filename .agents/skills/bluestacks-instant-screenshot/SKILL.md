---
name: bluestacks-instant-screenshot
description: Instantly capture high-resolution, sub-second screenshots of the BlueStacks emulator or running Android app in ~300-450ms directly to disk or memory via raw ADB socket protocol. Eliminates ADB banner noise, PowerShell UTF-16 redirection corruption, and device-side file I/O lag. Use whenever inspecting live screen state, capturing visual artifacts, verifying UI navigation, checking combat status, or grabbing frames for RL observation.
---

# BlueStacks Instant Screenshot

A high-performance screenshot skill designed to capture the exact Android framebuffer from BlueStacks 5 (or any Android device) in **sub-second time (~300–450ms)** without device-side disk writes, ADB banner pollution, or Windows PowerShell encoding corruption.

---

## When to Use

- **Visual State Inspection**: Checking the live screen to determine if the game is on Splash, Loader, Map, or Fight Arena.
- **Combat & Animation Verification**: Confirming player movements, hit animations, health bars, and round timers.
- **Fast Feedback Loops**: Grabbing screenshots during agent evaluation turns without blocking execution or triggering slow 5–10s ADB file transfer dialogues.
- **Reinforcement Learning Harness**: Grabbing frame observations directly into Python memory for RL state encoding (`PIL.Image` or NumPy arrays).

---

## Why Standard Methods Fail

| Method | Latency | Problem / Failure Mode |
| :--- | :--- | :--- |
| `adb shell screencap -p > screen.png` in PowerShell | ~5,000ms | **Corrupted File**: PowerShell's `>` redirection operator encodes binary stdout as UTF-16LE text, rendering the PNG unreadable by image viewers and tools. |
| `adb shell screencap /sdcard/s.png` + `adb pull` | ~6,000–10,000ms | **Slow Disk I/O & Progress Spam**: Writes to device storage, then transfers across ADB while generating hundreds of progress log lines (`[ 2%] ... [100%]`). |
| Standard `HD-Adb.exe exec-out screencap -p` | ~5,000ms (uncached) | **Banner Text Pollution**: BlueStacks's `HD-Adb.exe` automatically restarts the daemon if idle, prepending `* daemon not running... *` strings into binary stdout and breaking standard PNG decoders. |
| **Direct ADB Socket (`screenshot.py`)** | **~300–450ms** | **Zero I/O, Pure Memory Stream**: Talks directly to the persistent ADB daemon over TCP `127.0.0.1:5037`, streams raw bytes directly to disk/RAM, and strips any transient headers automatically. |

---

## Quick Start & Usage

The bundled Python script is located at:
`.agents/skills/bluestacks-instant-screenshot/scripts/screenshot.py`

### 1. Save Directly as an Agent Artifact (Recommended)
This writes the screenshot directly into the active Antigravity conversation artifact directory, ready for immediate `view_file` inspection:

```powershell
& "c:\Users\Ishan\Personal\Porfolio\Shadow Fight 2\.venv\Scripts\python.exe" .agents\skills\bluestacks-instant-screenshot\scripts\screenshot.py --artifact current_screen
```

### 2. Save to a Specific File Path
```powershell
& "c:\Users\Ishan\Personal\Porfolio\Shadow Fight 2\.venv\Scripts\python.exe" .agents\skills\bluestacks-instant-screenshot\scripts\screenshot.py "bluestacks/screenshots/fight_state.png"
```

### 3. Crop Specific UI Elements (e.g. Health Bars / Timer)
The 1920x1080 Shadow Fight 2 viewport layout:
- **Round Timer (Center)**: `(900, 20, 1020, 110)`
- **Shadow Health Bar (Left)**: `(270, 100, 900, 150)`
- **Opponent Health Bar (Right)**: `(1020, 100, 1650, 150)`

```powershell
& "c:\Users\Ishan\Personal\Porfolio\Shadow Fight 2\.venv\Scripts\python.exe" .agents\skills\bluestacks-instant-screenshot\scripts\screenshot.py --artifact timer_crop --crop 900,20,1020,110
```

---

## Python API (In-Memory / RL Harness)

To capture frames in Python without touching the disk:

```python
import io
from PIL import Image
from scripts.screenshot import capture_screenshot_bytes

# 1. Grab raw PNG bytes in ~400ms
png_bytes, elapsed = capture_screenshot_bytes(serial="emulator-5554")
print(f"Captured in {elapsed * 1000:.1f}ms")

# 2. Convert directly to PIL Image
image = Image.open(io.BytesIO(png_bytes))

# 3. Access pixels or convert to NumPy array for RL observation
import numpy as np

frame_array = np.array(image.convert("RGB"))  # Shape: (1080, 1920, 3)
```

---

## Script Options Reference

| Argument | Description | Default |
| :--- | :--- | :--- |
| `output` | Target PNG file path | `<artifact_dir>/current_screen.png` |
| `--artifact <name>` | Save directly to current agent artifact directory with given name | None |
| `-s, --serial` | ADB device serial to capture | `emulator-5554` (auto-detected) |
| `--crop <x1,y1,x2,y2>` | Crop bounding box | None (full frame) |
| `-q, --quiet` | Suppress status output to stdout | False |

---

## Technical Architecture

```text
[screenshot.py]
      │
      │ 1. Connect TCP (127.0.0.1:5037)
      ▼
[ADB Daemon] (Persistent background process: HD-Adb server nodaemon)
      │
      │ 2. "host:transport:emulator-5554" -> OKAY
      │ 3. "exec:screencap -p"            -> OKAY
      ▼
[BlueStacks Framebuffer] (/dev/graphics/fb0 or SurfaceFlinger)
      │
      │ 4. Stream raw PNG binary chunks (~800KB)
      ▼
[screenshot.py]
      │
      │ 5. Slice at '\x89PNG\r\n\x1a\n' (strips banners)
      ▼
[Target PNG File / Memory Buffer] (< 450ms total)
```
