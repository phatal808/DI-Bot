import os
import time
from datetime import datetime
from pathlib import Path

try:
    import pyautogui
    import pygetwindow
except Exception as e:
    print("Warning: screenshot libraries not available -", e)
    pyautogui = None
    pygetwindow = None

def capture_window(window_name: str, save_dir: str = "capture/images") -> str:
    """Capture a screenshot of the given window.

    Returns the path to the saved image.
    """
    if pyautogui is None or pygetwindow is None:
        raise RuntimeError("Required libraries not installed")

    windows = pygetwindow.getWindowsWithTitle(window_name)
    if not windows:
        raise RuntimeError(f"Window '{window_name}' not found")

    win = windows[0]
    win.activate()
    time.sleep(0.2)

    bbox = (win.left, win.top, win.width, win.height)
    screenshot = pyautogui.screenshot(region=bbox)

    Path(save_dir).mkdir(parents=True, exist_ok=True)
    file_name = datetime.now().strftime("%Y%m%d_%H%M%S.png")
    path = os.path.join(save_dir, file_name)
    screenshot.save(path)
    return path

def main():
    path = capture_window("Diablo Immortal")
    print("Saved screenshot to", path)

if __name__ == "__main__":
    main()
