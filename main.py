import time
import pyautogui
from helpers import (
    WINDOW_TITLE,
    bring_window_to_foreground,
    ocr_region,
    parse_player_info,
    detect_class,
    parse_stats,
    update_player_json,
)
from lists import STAT_NAMES_PAGE1, STAT_NAMES_PAGE2


def main(**extra):
    window = bring_window_to_foreground(WINDOW_TITLE)

    info_text = ocr_region(window, 1920, 110, 410, 160)
    name, level, paragon = parse_player_info(info_text)
    if name is None:
        print("Unable to read player information")
        return None

    # Determine class from the skills list
    pyautogui.click(window.left + 2055, window.top + 515)
    time.sleep(1)
    skills_text = ocr_region(window, 1805, 390, 315, 50)
    player_class = detect_class(skills_text)
    # Return to the main Attributes screen via the back arrow
    pyautogui.click(window.left + 1556, window.top + 196)
    time.sleep(1)

    pyautogui.click(window.left + 1760, window.top + 510)
    time.sleep(1)

    stats_text = ocr_region(window, 1660, 310, 800, 840)
    stats = parse_stats(stats_text, STAT_NAMES_PAGE1)

    # Capture secondary stats
    pyautogui.click(window.left + 2050, window.top + 1195)
    time.sleep(1)

    # Position mouse in the stats area so subsequent scrolls happen within
    # the region. Move slightly up and left to avoid covering Movement Speed.
    pyautogui.moveTo(
        window.left + 1660 + 400 - 20,
        window.top + 310 + 420 - 20,
    )

    second_stats = {}
    text = ocr_region(window, 1660, 310, 800, 870)
    second_stats.update(parse_stats(text, STAT_NAMES_PAGE2[:5]))

    for _ in range(10):
        pyautogui.scroll(-500)
        time.sleep(0.05)

    text = ocr_region(window, 1660, 310, 800, 870)
    second_stats.update(parse_stats(text, STAT_NAMES_PAGE2[5:12]))

    for _ in range(10):
        pyautogui.scroll(-500)
        time.sleep(0.05)

    text = ocr_region(window, 1660, 310, 800, 870)
    second_stats.update(parse_stats(text, STAT_NAMES_PAGE2[12:18]))

    for _ in range(8):
        pyautogui.scroll(-500)
        time.sleep(0.05)

    text = ocr_region(window, 1660, 930, 800, 280)
    second_stats.update(parse_stats(text, STAT_NAMES_PAGE2[18:]))

    stats.update(second_stats)
    extra["player_class"] = player_class
    update_player_json(name, level, paragon, stats, **extra)

    pyautogui.click(window.left + 2470, window.top + 60)

    return name


if __name__ == "__main__":
    main()
