from pathlib import Path
from typing import Any
from textual import events, on, work
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from .config import (
    list_workspaces,
    save_workspace,
    delete_workspace,
)
from .workspaces import WorkspaceModal


class WorkspaceScreen(ModalScreen):
    """Screen for managing workspaces."""

    def __init__(self, current_path: str | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_path = current_path

    CSS = """
    WorkspaceScreen {
        align: center middle;
    }

    #workspace-container {
        width: 80%;
        max-width: 100;
        height: 85%;
        padding: 2 4;
        background: $surface;
        border: tall $primary;
    }

    .workspace-item.active-workspace {
        border: tall $secondary;
        background: $secondary-darken-3;
    }

    .active-tag {
        color: $secondary;
        text-style: bold;
        margin-right: 1;
    }

    .workspace-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 2;
        color: $primary;
    }

    #workspace-list {
        height: 1fr;
        border: round $accent;
        margin-bottom: 1;
        overflow-y: scroll;
    }

    .workspace-item {
        height: auto;
        padding: 0 2;
        margin: 0 1 1 1;
        background: $surface;
        border: solid $primary;
        color: $text;
    }

    .workspace-item:hover {
        background: $primary-darken-3;
        border: solid $accent;
    }

    .workspace-name {
        text-style: bold;
        color: $primary;
    }

    .workspace-path {
        color: $text-muted;
        text-style: italic;
    }

    #workspace-buttons {
        margin-top: 1;
        align: center middle;
    }

    #workspace-buttons Button {
        margin: 0 1;
    }

    /* Selection Styling */
    /* Selection Styling */
    .workspace-item:focus {
        background: $primary-darken-2;
        border: solid $accent-lighten-1;
    }

    .ws-header-row {
        height: auto;
        align: left middle;
        margin-bottom: 0;
    }

    .ws-header-row Button {
        height: 1;
        min-width: 5;
        padding: 0 1;
        margin-left: 2;
        background: transparent;
        border: none;
        color: $error;
    }

    .ws-header-row Button:hover {
        background: $error;
        color: $text;
    }
    """

    def compose(self) -> ComposeResult:
        yield Container(
            Static("📁 Workspace Management", classes="workspace-title"),
            VerticalScroll(id="workspace-list"),
            Horizontal(
                Button("Add Workspace", variant="primary", id="add-ws-btn"),
                Button("Close", variant="default", id="close-ws-btn"),
                id="workspace-buttons",
            ),
            id="workspace-container",
        )

    @work
    async def on_mount(self) -> None:
        await self.refresh_list()

    async def refresh_list(self) -> None:
        """Refresh the list of workspaces."""
        list_container = self.query_one("#workspace-list")

        # Safer cleanup using query and remove
        await list_container.query("*").remove()

        workspaces = list_workspaces()
        if not workspaces:
            await list_container.mount(
                Static(
                    "No workspaces saved. Add one to get started!",
                    classes="workspace-path",
                )
            )
            return

        for name, data in workspaces.items():
            path = data.get("path", "")
            model = data.get("model", "Default")
            mode = data.get("mode", "Standard")

            is_active = False
            if self.current_path:
                try:
                    is_active = (
                        Path(path).resolve() == Path(self.current_path).resolve()
                    )
                except Exception:
                    pass

            # Create detail string
            details = f"[dim]Path: {path}[/]"
            if model or mode:
                details += f"\n[dim]Model: {model} | Mode: {mode.capitalize()}[/]"

            classes = "workspace-item"
            if is_active:
                classes += " active-workspace"

            # Create 3-line detail items
            ws_item = Vertical(
                Horizontal(
                    Static(
                        "⭐ " if is_active else "📁 ",
                        classes="active-tag" if is_active else "workspace-name",
                    ),
                    Static(f"{name}", classes="workspace-name"),
                    Static("  ", expand=True),
                    Button(
                        "✕", variant="default", id=f"del-{name}", classes="delete-btn"
                    ),
                    classes="ws-header-row",
                ),
                Static(f"Path: {path}", classes="workspace-path"),
                Static(
                    f"Config: {model or 'Default'} | Mode: {mode.capitalize()}",
                    classes="workspace-path",
                ),
                classes=classes,
                id=f"ws-item-{name}",
            )

            # Make the item focusable for keyboard navigation
            ws_item.can_focus = True
            await list_container.mount(ws_item)

    @on(events.Click, ".workspace-item")
    def handle_click(self, event: events.Click) -> None:
        """Handle clicking the workspace item to activate."""
        # Check if we clicked a button - get the specific widget at coordinates
        widgets = self.get_widget_at(event.screen_x, event.screen_y)
        if not widgets:
            return

        widget = widgets[0]

        # If clicked button (or child of button), let button handler take care of it
        current = widget
        while current:
            if isinstance(current, Button):
                return
            if current.id and current.id.startswith("ws-item-"):
                # Reached the item container without hitting a button
                break
            current = current.parent

        # Find workspace item ancestor
        item = widget
        while item and not (item.id and item.id.startswith("ws-item-")):
            item = item.parent

        if item and item.id:
            name = item.id[8:]
            self.dismiss(name)

    def on_key(self, event: events.Key) -> None:
        """Handle Enter key to activate focused workspace."""
        if event.key == "enter":
            focused = self.focused
            if focused and focused.id and focused.id.startswith("ws-item-"):
                name = focused.id[8:]
                self.dismiss(name)

    @on(Button.Pressed)
    def handle_button(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if not button_id:
            return

        if button_id == "close-ws-btn":
            self.dismiss()
        elif button_id == "add-ws-btn":
            self.app.push_screen(WorkspaceModal(), callback=self.handle_add_callback)
        elif button_id.startswith("act-"):
            name = button_id[4:]
            self.dismiss(name)
        elif button_id.startswith("del-"):
            name = button_id[4:]
            delete_workspace(name)
            self.run_worker(self.refresh_list())

    def handle_add_callback(self, workspace_obj: Any | None) -> None:
        """Callback from WorkspaceModal when adding a workspace."""
        if workspace_obj:
            save_workspace(workspace_obj.name, workspace_obj.to_dict())
            self.run_worker(self.refresh_list())
