"""Configuration persistence for Magic Prompt."""

import json
import os
from pathlib import Path
from typing import Any, Dict


# Default settings
DEFAULT_DEBOUNCE_MS = 800
DEFAULT_REALTIME_MODE = False
DEFAULT_MODEL = "llama-3.3-70b-versatile"
DEFAULT_ENRICHMENT_MODE = "standard"
DEFAULT_COPY_TOAST = True
DEFAULT_MAX_FILES = 5000
DEFAULT_MAX_DEPTH = 10
# Retrieval mode: "tfidf" (TF-IDF similarity), "heuristic" (keyword+recency only), "none" (include all)
DEFAULT_RETRIEVAL_MODE = "tfidf"
DEFAULT_TOP_K_FILES = 100
DEFAULT_AVAILABLE_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "llama3-70b-8192",
    "llama3-8b-8192",
    "gemma2-9b-it",
    "mixtral-8x7b-32768",
]


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


def save_directory(directory: str, label: str | None = None) -> None:
    """Save the working directory (wrapper for save_workspace)."""
    # If no label provided, use the directory name
    if not label:
        label = Path(directory).name or "default"

    save_workspace(label, {"path": str(Path(directory).resolve())})

    # Also update last used
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


# --- Workspace Management ---


def list_workspaces() -> Dict[str, Dict[str, Any]]:
    """List all saved workspaces, performing migration if needed."""
    config = load_config()
    workspaces = config.get("workspaces", {})

    # Migration: Convert saved_directories to workspaces
    saved_dirs = config.get("saved_directories", {})
    if saved_dirs and not workspaces:
        for label, path in saved_dirs.items():
            workspaces[label] = {"path": path}
        config["workspaces"] = workspaces
        # Clear old key after migration
        config.pop("saved_directories", None)
        save_config(config)

    return workspaces


def get_workspace(name: str) -> Dict[str, Any] | None:
    """Get a specific workspace configuration."""
    return list_workspaces().get(name)


def save_workspace(name: str, workspace_data: Dict[str, Any]) -> None:
    """Save or update a workspace configuration."""
    config = load_config()
    workspaces = config.get("workspaces", {})

    # Handle if data is a Workspace object (converted elsewhere or here)
    if hasattr(workspace_data, "to_dict"):
        data = workspace_data.to_dict()
    else:
        data = workspace_data

    workspaces[name] = data
    config["workspaces"] = workspaces
    save_config(config)


def delete_workspace(name: str) -> None:
    """Delete a workspace configuration."""
    config = load_config()
    workspaces = config.get("workspaces", {})
    if name in workspaces:
        del workspaces[name]
        config["workspaces"] = workspaces
        save_config(config)


def get_directory_by_label(label: str) -> str | None:
    """Get a saved directory path by its label (now workspace name)."""
    ws = get_workspace(label)
    if ws:
        path = ws.get("path")
        if path and Path(path).is_dir():
            return path
    return None


def get_next_directory(current_path: str) -> tuple[str, str] | None:
    """Get the next saved workspace (name, path) for cycling."""
    workspaces = list_workspaces()
    if not workspaces:
        return None

    names = list(workspaces.keys())
    paths = [ws.get("path") for ws in workspaces.values()]

    try:
        current_index = paths.index(str(Path(current_path).resolve()))
    except ValueError:
        return names[0], paths[0]

    next_index = (current_index + 1) % len(names)
    return names[next_index], paths[next_index]


def get_model() -> str:
    """Get the Groq model to use."""
    config = load_config()
    return config.get("model", DEFAULT_MODEL)


def set_model(model: str) -> None:
    """Set the Groq model to use."""
    config = load_config()
    config["model"] = model
    save_config(config)


def get_api_key() -> str | None:
    """Get the Groq API key from config or environment."""
    config = load_config()
    return config.get("api_key") or os.getenv("GROQ_API_KEY")


def set_api_key(api_key: str) -> None:
    """Set the Groq API key."""
    config = load_config()
    config["api_key"] = api_key
    save_config(config)


def get_enrichment_mode() -> str:
    """Get the current enrichment mode."""
    config = load_config()
    return config.get("enrichment_mode", DEFAULT_ENRICHMENT_MODE)


def set_enrichment_mode(mode: str) -> None:
    """Set the current enrichment mode."""
    config = load_config()
    config["enrichment_mode"] = mode
    save_config(config)


def get_copy_toast() -> bool:
    """Get whether copy toast notifications are enabled."""
    config = load_config()
    return config.get("copy_toast", DEFAULT_COPY_TOAST)


def set_copy_toast(enabled: bool) -> None:
    """Set whether copy toast notifications are enabled."""
    config = load_config()
    config["copy_toast"] = enabled
    save_config(config)


def get_max_files() -> int:
    """Get the maximum number of files to scan."""
    config = load_config()
    return config.get("max_files", DEFAULT_MAX_FILES)


def set_max_files(limit: int) -> None:
    """Set the maximum number of files to scan."""
    config = load_config()
    config["max_files"] = max(100, min(10000, limit))
    save_config(config)


def get_max_depth() -> int:
    """Get the maximum directory depth to scan."""
    config = load_config()
    return config.get("max_depth", DEFAULT_MAX_DEPTH)


def set_max_depth(depth: int) -> None:
    """Set the maximum directory depth to scan."""
    config = load_config()
    config["max_depth"] = max(1, min(20, depth))
    save_config(config)


def get_available_models_from_config() -> list[str]:
    """Get the list of available models from config."""
    config = load_config()
    return config.get("available_models", DEFAULT_AVAILABLE_MODELS)


def update_available_models() -> list[str]:
    """Fetch and update available models from Groq API."""
    from .groq_client import GroqClient

    api_key = get_api_key()
    if not api_key:
        return get_available_models_from_config()

    try:
        client = GroqClient(api_key=api_key)
        models = client.get_available_models()
        if models:
            config = load_config()
            config["available_models"] = models
            save_config(config)
            return models
    except Exception:
        pass

    return get_available_models_from_config()


def get_retrieval_mode() -> str:
    """Get the retrieval mode (tfidf, heuristic, or none)."""
    config = load_config()
    return config.get("retrieval_mode", DEFAULT_RETRIEVAL_MODE)


def set_retrieval_mode(mode: str) -> None:
    """Set the retrieval mode (tfidf, heuristic, or none)."""
    valid_modes = {"tfidf", "heuristic", "none"}
    if mode not in valid_modes:
        mode = DEFAULT_RETRIEVAL_MODE
    config = load_config()
    config["retrieval_mode"] = mode
    save_config(config)


def get_top_k_files() -> int:
    """Get the number of top files to include after retrieval."""
    config = load_config()
    return config.get("top_k_files", DEFAULT_TOP_K_FILES)


def set_top_k_files(k: int) -> None:
    """Set the number of top files to include after retrieval."""
    config = load_config()
    config["top_k_files"] = max(5, min(100, k))
    save_config(config)
