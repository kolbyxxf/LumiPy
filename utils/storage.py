import json

SETTINGS_FILE = "settings.json"
AFK_FILE = "afk.json"
WELCOME_FILE = "welcome.json"
GOODBYE_FILE = "goodbye.json"
AUTOROLE_FILE = "autorole.json"
REACTION_ROLE_FILE = "reaction_roles.json"
DROPDOWN_ROLE_FILE = "dropdown_roles.json"
CLEANUP_FILE = "cleanup.json"


def _load(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)


# ── settings (mod log channels) ──
def load_settings() -> dict:
    return _load(SETTINGS_FILE)

def save_settings(data: dict) -> None:
    _save(SETTINGS_FILE, data)


# ── afk ──
def load_afk() -> dict[str, str]:
    return _load(AFK_FILE)

def save_afk(data: dict) -> None:
    _save(AFK_FILE, data)


# ── welcome / goodbye ──
def load_welcome() -> dict:
    return _load(WELCOME_FILE)

def save_welcome(data: dict) -> None:
    _save(WELCOME_FILE, data)

def load_goodbye() -> dict:
    return _load(GOODBYE_FILE)

def save_goodbye(data: dict) -> None:
    _save(GOODBYE_FILE, data)


# ── autoroles ──
def load_autorole() -> dict:
    return _load(AUTOROLE_FILE)

def save_autorole(data: dict) -> None:
    _save(AUTOROLE_FILE, data)


# ── reaction roles ──
def load_reaction_roles() -> dict:
    return _load(REACTION_ROLE_FILE)

def save_reaction_roles(data: dict) -> None:
    _save(REACTION_ROLE_FILE, data)


# ── dropdown roles ──
def load_dropdown_roles() -> dict:
    return _load(DROPDOWN_ROLE_FILE)

def save_dropdown_roles(data: dict) -> None:
    _save(DROPDOWN_ROLE_FILE, data)


# ── cleanup ──
def load_cleanup() -> dict:
    return _load(CLEANUP_FILE)

def save_cleanup(data: dict) -> None:
    _save(CLEANUP_FILE, data)

# ── Generic Helpers ──
def load_data(filename: str) -> dict:
    return _load(filename)

def save_data(filename: str, data: dict) -> None:
    _save(filename, data)
