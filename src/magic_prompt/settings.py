"""Settings screen for Magic Prompt."""

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
    set_debounce_ms,
    set_model,
    set_realtime_mode,
    set_api_key,
    set_enrichment_mode,
)


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

        yield Container(
            Static("⚙️ Configuration Settings", classes="settings-title"),
            Vertical(
                Horizontal(
                    Label("Groq Model:", classes="setting-label"),
                    Input(value=current_model, id="setting-model"),
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
                        [("Standard", "standard"), ("Pseudocode", "pseudocode")],
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
                id="settings-form",
            ),
            Horizontal(
                Button("Save", variant="primary", id="save-btn"),
                Button("Cancel", variant="default", id="cancel-btn"),
                id="buttons",
            ),
            id="settings-container",
        )

    @on(Button.Pressed, "#save-btn")
    def handle_save(self) -> None:
        """Save the settings and close the screen."""
        model = self.query_one("#setting-model", Input).value.strip()
        api_key = self.query_one("#setting-api-key", Input).value.strip()
        mode = self.query_one("#setting-mode", Select).value
        realtime = self.query_one("#setting-realtime", Switch).value
        debounce_str = self.query_one("#setting-debounce", Input).value.strip()

        try:
            debounce = int(debounce_str)
        except ValueError:
            # Fallback or error handling could be better here
            debounce = get_debounce_ms()

        # Update config
        if model:
            set_model(model)
        if api_key:
            set_api_key(api_key)
        if mode:
            set_enrichment_mode(str(mode))
        set_realtime_mode(realtime)
        set_debounce_ms(debounce)

        self.dismiss(True)

    @on(Button.Pressed, "#cancel-btn")
    def handle_cancel(self) -> None:
        """Close the screen without saving."""
        self.dismiss(False)
