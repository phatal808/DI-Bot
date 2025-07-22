import json
import re
import time
from datetime import datetime

import pyautogui
import pygetwindow as gw
import pytesseract
import cv2
import numpy as np

from lists import CLASS_OPTIONS, STAT_NAMES_PAGE1, STAT_NAMES_PAGE2


WINDOW_TITLE = "Diablo Immortal"


def bring_window_to_foreground(title: str):
    windows = gw.getWindowsWithTitle(title)
    if not windows:
        raise RuntimeError(f"Window titled '{title}' not found")
    window = windows[0]
    if window.isMinimized:
        window.restore()
    window.activate()
    return window


def ocr_region(window, left, top, width, height):
    x = window.left + left
    y = window.top + top
    screenshot = pyautogui.screenshot(region=(x, y, width, height))
    img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    text = pytesseract.image_to_string(gray)
    return text.replace("\u00e9", "?")




def parse_player_info(text: str):
    """Return ``(name, level, paragon)`` or ``(None, None, None)`` if unreadable."""

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None, None, None

    raw_name = lines[0].replace("\u00e9", "?")
    name = re.sub(r"[^A-Za-z0-9-]", "", raw_name)
    if not name:
        name = None

    level = None
    paragon = None
    if len(lines) >= 2:
        match = re.search(r"Level:\s*(\d+)\((\d+)\)", lines[1])
        if match:
            level = int(match.group(1))
            paragon = int(match.group(2))

    return name, level, paragon


def detect_class(text: str):
    """Return the class name based on skill text."""
    cleaned = re.sub(r"[^a-z]", "", text.lower())
    for cls, phrases in CLASS_OPTIONS.items():
        for phrase in phrases:
            p_clean = re.sub(r"[^a-z]", "", phrase.lower())
            if p_clean in cleaned:
                return cls
    return None


def levenshtein(a: str, b: str) -> int:
    """Compute Levenshtein distance between two short strings."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, c1 in enumerate(a, 1):
        cur = [i]
        for j, c2 in enumerate(b, 1):
            cost = 0 if c1 == c2 else 1
            cur.append(min(cur[j-1] + 1, prev[j] + 1, prev[j-1] + cost))
        prev = cur
    return prev[-1]


def update_player_json(name, level, paragon, stats, **extra):
    """Update players.json while preserving field order."""
    if name is None:
        print("Player name unreadable; skipping JSON update")
        return

    try:
        with open("players.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}

    def norm(s: str) -> str:
        return re.sub(r"[^a-z0-9]", "", s.lower())

    for existing in data:
        if levenshtein(norm(existing), norm(name)) <= 1:
            name = existing
            break

    old = data.get(name, {})

    # Build an ordered dict with priority fields first
    player = {}

    # Clan and Warband come right after the player name
    clan_val = extra.get("clan", old.get("Clan"))
    if clan_val is not None:
        player["Clan"] = clan_val

    warband_val = extra.get("warband", old.get("Warband"))
    if warband_val is not None:
        player["Warband"] = warband_val

    # Priority fields
    rank_val = extra.get("rank", old.get("Rank"))
    if rank_val is not None:
        player["Rank"] = rank_val

    last_online_val = extra.get("last_online", old.get("Last Online"))
    if last_online_val is not None:
        player["Last Online"] = last_online_val

    paragon_val = paragon if paragon is not None else old.get("Paragon")
    if paragon_val is not None:
        player["Paragon"] = paragon_val

    class_val = extra.get("player_class", old.get("Class"))
    if class_val is not None:
        player["Class"] = class_val

    cr_val = stats.get("Combat Rating") if stats else None
    if cr_val is None:
        cr_val = old.get("Combat Rating")
    if cr_val is not None:
        player["Combat Rating"] = cr_val

    res_val = stats.get("Resonance") if stats else None
    if res_val is None:
        res_val = old.get("Resonance")
    if res_val is not None:
        player["Resonance"] = res_val

    lvl_val = level if level is not None else old.get("Level")
    if lvl_val is not None:
        player["Level"] = lvl_val

    # Other stats in fixed order, skipping ones already added
    if stats:
        for key in STAT_NAMES_PAGE1 + STAT_NAMES_PAGE2:
            if key in {"Combat Rating", "Resonance"}:
                continue
            if key in stats:
                player[key] = stats[key]
            elif key in old:
                player.setdefault(key, old[key])
    else:
        for key in STAT_NAMES_PAGE1 + STAT_NAMES_PAGE2:
            if key in {"Combat Rating", "Resonance"}:
                continue
            if key in old:
                player[key] = old[key]

    # Preserve any unknown fields from old data except last_seen
    for k, v in old.items():
        if k not in player and k != "last_seen":
            player[k] = v

    # last_seen must be last; record timestamp in 12-hour format
    now = datetime.now()
    player["last_seen"] = now.strftime("%I:%M%p %m/%d/%y")

    data[name] = player

    with open("players.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)




def parse_stats(text: str, wanted_names):
    """Return a mapping of ``wanted_names`` to their OCR'd values.

    The OCR may miss the stat label on the left, so we simply
    capture numbers in order and map them sequentially to the
    provided ``wanted_names`` list.
    """

    values = []
    for line in text.splitlines():
        match = re.search(r"([0-9][0-9,]*\.?[0-9]*%?)", line)
        if match:
            val = match.group(1).strip()
            values.append(val.replace("\u00e9", "?"))
        if len(values) >= len(wanted_names):
            break

    stats = {}
    for i, stat in enumerate(wanted_names):
        if i < len(values):
            stats[stat] = values[i]

    return stats
