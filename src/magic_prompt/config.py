"""Configuration persistence for Magic Prompt."""

import json
import os
from pathlib import Path
from typing import Any


# Default settings
DEFAULT_DEBOUNCE_MS = 800
DEFAULT_REALTIME_MODE = False
DEFAULT_MODEL = "llama-3.3-70b-versatile"


def get_config_dir() -> Path:
    """Get the configuration directory, creating it if needed."""
    # Use XDG config dir on Linux/macOS, or fall back to ~/.config
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        config_dir = Path(xdg_config) / "magic-prompt"
    else:
        config_dir = Path.home() / ".config" / "magic-prompt"

    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_path() -> Path:
    """Get the path to the config file."""
    return get_config_dir() / "config.json"


def load_config() -> dict[str, Any]:
    """Load configuration from disk."""
    config_path = get_config_path()
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_config(config: dict[str, Any]) -> None:
    """Save configuration to disk."""
    config_path = get_config_path()
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def get_saved_directory() -> str | None:
    """Get the saved working directory from config."""
    config = load_config()
    directory = config.get("working_directory")
    if directory and Path(directory).is_dir():
        return directory
    return None


def save_directory(directory: str) -> None:
    """Save the working directory to config."""
    config = load_config()
    config["working_directory"] = str(Path(directory).resolve())
    save_config(config)


def clear_directory() -> None:
    """Clear the saved working directory."""
    config = load_config()
    config.pop("working_directory", None)
    save_config(config)


def get_debounce_ms() -> int:
    """Get the debounce time in milliseconds."""
    config = load_config()
    return config.get("debounce_ms", DEFAULT_DEBOUNCE_MS)


def set_debounce_ms(ms: int) -> None:
    """Set the debounce time in milliseconds."""
    config = load_config()
    config["debounce_ms"] = max(100, min(5000, ms))  # Clamp between 100-5000ms
    save_config(config)


def get_realtime_mode() -> bool:
    """Get whether real-time mode is enabled by default."""
    config = load_config()
    return config.get("realtime_mode", DEFAULT_REALTIME_MODE)


def set_realtime_mode(enabled: bool) -> None:
    """Set whether real-time mode is enabled by default."""
    config = load_config()
    config["realtime_mode"] = enabled
    save_config(config)


def get_model() -> str:
    """Get the Groq model to use."""
    config = load_config()
    return config.get("model", DEFAULT_MODEL)


def set_model(model: str) -> None:
    """Set the Groq model to use."""
    config = load_config()
    config["model"] = model
    save_config(config)
