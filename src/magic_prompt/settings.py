"""Settings screen for Magic Prompt."""

from typing import Any
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Switch, Static, Select

from .config import (
    get_debounce_ms,
    get_model,
    get_realtime_mode,
    get_api_key,
    get_enrichment_mode,
    get_copy_toast,
    set_debounce_ms,
    set_model,
    set_realtime_mode,
    set_api_key,
    set_enrichment_mode,
    set_copy_toast,
    get_max_files,
    get_max_depth,
    get_available_models_from_config,
    set_max_files,
    set_max_depth,
    get_retrieval_mode,
    set_retrieval_mode,
    save_workspace,
)
from .workspaces import WorkspaceModal


class SettingsScreen(Screen):
    """Screen for viewing and editing application configuration."""

    CSS = """
    SettingsScreen {
        align: center middle;
    }

    #settings-container {
        width: 60%;
        min-width: 60;
        max-width: 100;
        height: auto;
        padding: 2 4;
        background: $surface;
        border: tall $primary;
    }

    .settings-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 2;
        color: $primary;
    }

    .setting-item {
        margin-bottom: 1;
        height: auto;
    }

    .setting-label {
        width: 20;
        content-align: right middle;
        margin-right: 2;
    }

    #buttons {
        margin-top: 2;
        align: center middle;
    }

    #buttons Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        # Load current settings
        current_model = get_model()
        current_realtime = get_realtime_mode()
        current_debounce = get_debounce_ms()
        current_api_key = get_api_key() or ""
        current_mode = get_enrichment_mode()
        current_mode = get_enrichment_mode()
        current_copy_toast = get_copy_toast()
        current_max_files = get_max_files()
        current_max_files = get_max_files()
        current_max_depth = get_max_depth()
        current_retrieval_mode = get_retrieval_mode()

        yield Container(
            Static("⚙️ Configuration Settings", classes="settings-title"),
            Vertical(
                Horizontal(
                    Label("Groq Model:", classes="setting-label"),
                    Select(
                        [(m, m) for m in get_available_models_from_config()],
                        value=current_model,
                        id="setting-model",
                        allow_blank=False,
                    ),
                    classes="setting-item",
                ),
                Horizontal(
                    Label("API Key:", classes="setting-label"),
                    Input(
                        value=current_api_key,
                        password=True,
                        id="setting-api-key",
                        placeholder="gsk_...",
                    ),
                    classes="setting-item",
                ),
                Horizontal(
                    Label("Enrichment Mode:", classes="setting-label"),
                    Select(
                        [
                            ("Standard", "standard"),
                            ("Pseudocode", "pseudocode"),
                            ("Elaboration", "elaboration"),
                        ],
                        value=current_mode,
                        id="setting-mode",
                    ),
                    classes="setting-item",
                ),
                Horizontal(
                    Label("Real-time Mode:", classes="setting-label"),
                    Switch(value=current_realtime, id="setting-realtime"),
                    classes="setting-item",
                ),
                Horizontal(
                    Label("Debounce (ms):", classes="setting-label"),
                    Input(
                        value=str(current_debounce),
                        id="setting-debounce",
                    ),
                    classes="setting-item",
                ),
                Horizontal(
                    Label("Copy Notification:", classes="setting-label"),
                    Switch(value=current_copy_toast, id="setting-copy-toast"),
                    classes="setting-item",
                ),
                Horizontal(
                    Label("Retrieval Mode:", classes="setting-label"),
                    Select(
                        [
                            ("TF-IDF", "tfidf"),
                            ("Heuristic Only", "heuristic"),
                            ("None (All Files)", "none"),
                        ],
                        value=current_retrieval_mode,
                        id="setting-retrieval-mode",
                    ),
                    classes="setting-item",
                ),
                Horizontal(
                    Label("Max Files:", classes="setting-label"),
                    Input(
                        value=str(current_max_files),
                        id="setting-max-files",
                    ),
                    classes="setting-item",
                ),
                Horizontal(
                    Label("Max Depth:", classes="setting-label"),
                    Input(
                        value=str(current_max_depth),
                        id="setting-max-depth",
                    ),
                    classes="setting-item",
                ),
                id="settings-form",
            ),
            Horizontal(
                Button("Save", variant="primary", id="save-btn"),
                Button("Add Workspace", variant="success", id="add-ws-btn"),
                Button("Workspaces", variant="default", id="workspaces-btn"),
                Button("Cancel", variant="default", id="cancel-btn"),
                id="buttons",
            ),
            id="settings-container",
        )

    @on(Button.Pressed, "#save-btn")
    def handle_save(self) -> None:
        """Save the settings and close the screen."""
        model = self.query_one("#setting-model", Select).value
        api_key = self.query_one("#setting-api-key", Input).value.strip()
        mode = self.query_one("#setting-mode", Select).value
        realtime = self.query_one("#setting-realtime", Switch).value
        copy_toast = self.query_one("#setting-copy-toast", Switch).value
        debounce_str = self.query_one("#setting-debounce", Input).value.strip()
        max_files_str = self.query_one("#setting-max-files", Input).value.strip()
        max_files_str = self.query_one("#setting-max-files", Input).value.strip()
        max_depth_str = self.query_one("#setting-max-depth", Input).value.strip()
        retrieval_mode = self.query_one("#setting-retrieval-mode", Select).value

        try:
            debounce = int(debounce_str)
        except ValueError:
            # Fallback or error handling could be better here
            debounce = get_debounce_ms()

        try:
            max_files = int(max_files_str)
        except ValueError:
            max_files = get_max_files()

        try:
            max_depth = int(max_depth_str)
        except ValueError:
            max_depth = get_max_depth()

        # Update config
        if model:
            set_model(model)
        if api_key:
            set_api_key(api_key)
        if mode:
            set_enrichment_mode(str(mode))
        if mode:
            set_enrichment_mode(str(mode))
        if retrieval_mode:
            set_retrieval_mode(str(retrieval_mode))
        set_realtime_mode(realtime)
        set_copy_toast(copy_toast)
        set_debounce_ms(debounce)
        set_max_files(max_files)
        set_max_depth(max_depth)

        self.dismiss(True)

    @on(Button.Pressed, "#workspaces-btn")
    def handle_workspaces(self) -> None:
        """Close settings and signal to open workspaces."""
        self.dismiss("workspaces")

    @on(Button.Pressed, "#add-ws-btn")
    def handle_add_workspace(self) -> None:
        """Open the add workspace modal without closing settings."""
        self.app.push_screen(WorkspaceModal(), callback=self.handle_add_callback)

    def handle_add_callback(self, workspace_obj: Any | None) -> None:
        """Save the new workspace and notify."""
        if workspace_obj:
            save_workspace(workspace_obj.name, workspace_obj.to_dict())
            self.app.notify(
                f"Workspace '{workspace_obj.name}' added!", severity="information"
            )

    @on(Button.Pressed, "#cancel-btn")
    def handle_cancel(self) -> None:
        """Close the screen without saving."""
        self.dismiss(False)
