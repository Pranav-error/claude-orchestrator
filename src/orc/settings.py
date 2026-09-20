"""User-customizable display preferences — the same idea as Claude Code's
own settings.json (theme, spinnerVerbs, outputStyle): a small local JSON
file of preferences that change how things are *shown*, not what data
exists. Machine-local like identity, since terminal capabilities and taste
are a per-machine thing."""

import json
from pathlib import Path

SETTINGS_FILE_NAME = ".claude-orchestrator-settings.json"
SETTINGS_FILE = Path.home() / SETTINGS_FILE_NAME

DEFAULTS = {
    "theme": "amber",
    "icons": True,
    "usage_days": 14,
    "color": "auto",  # auto | always | never
}

THEMES = {
    "amber": {
        "prompt": "\033[36m",       # cyan
        "gradient": [222, 216, 214, 208, 202, 166],  # pale amber -> deep orange
        "good": "\033[32m",
        "bad": "\033[31m",
        "warn": "\033[33m",
    },
    "ocean": {
        "prompt": "\033[38;5;45m",
        "gradient": [159, 123, 87, 51, 39, 33],  # pale cyan -> deep blue
        "good": "\033[38;5;41m",
        "bad": "\033[38;5;203m",
        "warn": "\033[38;5;221m",
    },
    "sunset": {
        "prompt": "\033[38;5;213m",
        "gradient": [224, 217, 210, 209, 203, 197],  # pale pink -> magenta/red
        "good": "\033[38;5;114m",
        "bad": "\033[38;5;196m",
        "warn": "\033[38;5;215m",
    },
    "mono": {
        "prompt": "",
        "gradient": ["" for _ in range(6)],
        "good": "",
        "bad": "",
        "warn": "",
    },
}


def load() -> dict:
    if not SETTINGS_FILE.exists():
        return dict(DEFAULTS)
    try:
        data = json.loads(SETTINGS_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULTS)
    merged = dict(DEFAULTS)
    merged.update({k: v for k, v in data.items() if k in DEFAULTS})
    return merged


def save(settings: dict) -> None:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2, sort_keys=True) + "\n")


def get(key: str):
    return load().get(key, DEFAULTS.get(key))


def set_value(key: str, value):
    if key not in DEFAULTS:
        raise ValueError(f"unknown setting {key!r} — valid keys: {', '.join(DEFAULTS)}")
    if key == "theme" and value not in THEMES:
        raise ValueError(f"unknown theme {value!r} — valid themes: {', '.join(THEMES)}")
    if key == "color" and value not in ("auto", "always", "never"):
        raise ValueError("color must be one of: auto, always, never")
    if key == "icons":
        value = value if isinstance(value, bool) else str(value).lower() in ("1", "true", "yes", "on")
    if key == "usage_days":
        value = int(value)

    settings = load()
    settings[key] = value
    save(settings)
    return settings


def theme(name: str = None) -> dict:
    return THEMES.get(name or get("theme"), THEMES["amber"])
