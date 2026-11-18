"""The trending-sound step (PLAN section 6.6): TikTok's and Instagram's audio pickers.

The plan calls this the most fragile step, and it is: the audio lists are different in every
version. So the rule is the plan's: **try, and if it fails, post without an added sound** - unless
the caller said the sound is required, in which case the post stops before it is pressed.

Nothing here presses Post. `add_sound` returns True only when a sound was actually added and the
screen is back at the editor, so the caller can log honestly ("posted without a sound").
"""

from __future__ import annotations

import logging
import time

from .ui import Element, Screen, Signature, find, find_exact

log = logging.getLogger("robotapp")

# The audio panel, whichever app: a list of sounds and a way to close it.
AUDIO_PANEL = Signature("audio panel", any_of=("Sounds", "Trending", "Add sound", "Search sounds", "Use"))
VOLUME_PANEL = Signature("volume panel", any_of=("Original sound", "Volume", "Music volume", "Sound volume"))
TIKTOK_EDITOR = Signature("tiktok editor", any_of=("Next", "Add sound", "Edit", "Sound"))
IG_EDITOR = Signature("instagram editor", any_of=("Next", "Edit", "Audio", "Audio mixer"))


def _first_sound(elements: list[Element]) -> Element | None:
    """The first sound in the trending list: a row that is clickable and says something."""
    for element in elements:
        if not (element.clickable and element.enabled):
            continue
        label = (element.text or element.desc or "").strip()
        if not label or label.lower() in ("search", "cancel", "back", "done", "next", "use"):
            continue
        # A sound row is usually "name · original sound" or "&#9834; name".
        if "sound" in label.lower() or "\u266a" in label or "\u266b" in label or "\u2669" in label:
            return element
    return None


def _tap_any(screen: Screen, labels: tuple[str, ...]) -> bool:
    for label in labels:
        button = find_exact(screen.elements(), label)
        if button is not None:
            screen.tap(button)
            time.sleep(1.0)
            return True
    return False


def add_sound(screen: Screen, platform: str) -> bool:
    """TikTok: editor -> Add sound -> a trending one -> Use. Instagram: Audio -> Trending -> pick.

    Returns True only when the picker closed again with a sound chosen (the editor is back). The
    caller decides what a False means: post without a sound, or stop if it is required.
    """
    width, height = screen.size()
    elements = screen.elements()
    opened = _tap_any(screen, ("Add sound", "Sounds", "Audio", "Music"))
    if not opened:
        # No label: the sound chip on TikTok's editor sits at the top, centre-right.
        screen.tap(Element(text="", bounds=(int(width * 0.45), int(height * 0.09),
                                           int(width * 0.62), int(height * 0.14))))
    time.sleep(2.5)
    elements = screen.elements()
    if not AUDIO_PANEL.matches(elements):
        log.info("%s: no sound panel appeared", platform)
        return False

    # A trending tab first; the list is already trending-first in both apps.
    _tap_any(screen, ("Trending", "Suggested", "For you"))
    time.sleep(2.0)
    elements = screen.elements()
    sound = _first_sound(elements)
    if sound is None:
        log.info("%s: no sound row to pick", platform)
        _close(screen)
        return False
    screen.tap(sound)
    time.sleep(2.5)

    # TikTok's picker has a "Use" / check button; Instagram applies on tap.
    _tap_any(screen, ("Use", "Next", "Done", "Add"))
    time.sleep(1.5)

    # Back at the editor with a sound: the plan's volume mix (original high, added low).
    try:
        elements = screen.elements()
        if VOLUME_PANEL.matches(elements):
            _lower_music(screen, elements)
    except Exception:  # noqa: BLE001 - the volume panel is optional
        log.debug("%s: no volume panel", platform)

    back = TIKTOK_EDITOR.matches(screen.elements()) or IG_EDITOR.matches(screen.elements())
    if not back:
        log.info("%s: the picker did not close on the editor", platform)
        _close(screen)
        return False
    return True


def _lower_music(screen: Screen, elements: list[Element]) -> None:
    """Drag the music/added-sound slider down and the original up, roughly (section 6.6)."""
    row = next((e for e in elements if "music" in (e.text or "").lower()
                or "added" in (e.text or "").lower()), None)
    if row is None:
        return
    x1, y1, x2, y2 = row.bounds
    # Slide the handle to about a fifth of the track: quiet under the clip's own audio.
    screen.tap(Element(text="", bounds=(x1, y1, x1 + max(20, (x2 - x1) // 5), y2)))
    time.sleep(1.0)


def _close(screen: Screen) -> None:
    """Leave the picker without a sound: the editor must be usable again."""
    for label in ("Cancel", "Close", "Back", "Done", "X"):
        button = find_exact(screen.elements(), label)
        if button is not None:
            screen.tap(button)
            time.sleep(1.0)
            return
    screen.press_back()
    time.sleep(1.0)
