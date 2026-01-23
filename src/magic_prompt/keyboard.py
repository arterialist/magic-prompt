"""Keyboard shortcut definitions for Magic Prompt."""

from textual.binding import Binding

# Default bindings
DEFAULT_BINDINGS = [
    Binding("ctrl+q", "quit", "Quit"),
    Binding("ctrl+t", "toggle_realtime", "Real-time"),
    Binding("ctrl+y", "copy_output", "Copy"),
    Binding("ctrl+u", "clear_input", "Clear Input"),
    Binding("ctrl+l", "clear_output", "Clear Output", show=False),
    Binding("ctrl+r", "cycle_retrieval_mode", "Retrieval"),
    Binding("f5", "rescan", "Rescan"),
    Binding("ctrl+s", "settings", "Settings"),
    Binding("ctrl+m", "cycle_mode", "Cycle Mode"),
    Binding("ctrl+b", "cycle_directory", "Cycle Workspace"),
    Binding("ctrl+g", "workspace", "Workspaces"),
]
