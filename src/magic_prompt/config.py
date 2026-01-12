"""Configuration persistence for Magic Prompt."""

import json
import os
from pathlib import Path
from typing import Any


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
