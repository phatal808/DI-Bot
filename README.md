# DI-Bot
Capture and process images from the game Diablo Immortal for players stats.

## Requirements

```
pip install pyautogui pygetwindow Pillow pytesseract opencv-python
```

## Usage

Run the automation script while the game is running. Press **F8** to pause/resume
and **F9** to stop whenever supported:

```
python main.py
```

The script captures character information and statistics and stores them in
`players.json`.
