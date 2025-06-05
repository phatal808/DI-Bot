# DI-Bot

This project provides tools for capturing screenshots from **Diablo Immortal**,
processing them with Tesseract OCR and exposing the results through a Discord
bot. It is split into three parts:

1. **Capture** – automate taking screenshots of the game window.
2. **OCR** – read screenshots using Tesseract and store the text as JSON.
3. **Bot** – a Discord bot with slash commands to query the processed data.

## Setup

1. Install Python 3.10+ and the dependencies:

```bash
pip install -r requirements.txt
```

2. (Optional) Ensure Tesseract is installed on your system so that
`pytesseract` can call it.

3. Set the environment variable `DISCORD_TOKEN` with your bot token.

## Usage

Capture a screenshot of the `Diablo Immortal` window:

```bash
python capture/capture.py
```

Process a screenshot to JSON:

```bash
python ocr/process.py <path_to_image>
```

Run the Discord bot:

```bash
python bot/bot.py
```

The bot exposes a `/stats` slash command that returns the OCR text stored in
`data/output.json`.
