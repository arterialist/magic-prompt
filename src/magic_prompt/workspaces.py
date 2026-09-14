import os
from dataclasses import dataclass, asdict
from typing import Any
from pathlib import Path
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static, Select


@dataclass
class Workspace:
    """Represents a project workspace with its own configuration."""

    name: str
    path: str
    model: str | None = None
    mode: str | None = None
    realtime: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert workspace to a dictionary for JSON storage."""
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> "Workspace":
        """Create a Workspace instance from a dictionary."""
        return cls(
            name=name,
            path=data.get("path", ""),
            model=data.get("model"),
            mode=data.get("mode"),
            realtime=data.get("realtime"),
        )


class WorkspaceModal(ModalScreen[Workspace | None]):
    """Modal for adding or editing a workspace."""

    CSS = """
    WorkspaceModal {
        align: center middle;
    }

    #modal-container {
        width: 60%;
        max-width: 80;
        height: auto;
        padding: 2 4;
        background: $surface;
        border: tall $primary;
    }

    .modal-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 2;
        color: $primary;
    }

    .input-item {
        margin-bottom: 1;
    }

    .modal-buttons {
        margin-top: 2;
        align: center middle;
    }

    .modal-buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, workspace: Workspace | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.workspace = workspace

    def compose(self) -> ComposeResult:
        title = "Edit Workspace" if self.workspace else "Add Workspace"
        name_val = self.workspace.name if self.workspace else ""
        path_val = self.workspace.path if self.workspace else ""

        # Build selects without forcing a value for the "add" case.
        # Newer Textual uses Select.NULL for blank; older used Select.BLANK.
        # Avoid setting a sentinel explicitly to maintain compatibility.
        model_select = Select(
            [
                ("Llama 3.3 70B", "llama-3.3-70b-versatile"),
                ("Llama 3.1 8B", "llama-3.1-8b-instant"),
                ("Mixtral 8x7B", "mixtral-8x7b-32768"),
            ],
            id="ws-model-select",
            allow_blank=True,
        )
        if self.workspace and self.workspace.model:
            model_select.value = self.workspace.model

        mode_select = Select(
            [("Standard", "standard"), ("Pseudocode", "pseudocode")],
            id="ws-mode-select",
            allow_blank=True,
        )
        if self.workspace and self.workspace.mode:
            mode_select.value = self.workspace.mode

        yield Container(
            Static(f"✨ {title}", classes="modal-title"),
            Vertical(
                Label("Workspace Name:"),
                Input(
                    value=name_val, placeholder="e.g., My Project", id="ws-name-input"
                ),
                Label("Directory Path:"),
                Input(
                    value=path_val,
                    placeholder="e.g., /path/to/project",
                    id="ws-path-input",
                ),
                Label("Model (Optional):"),
                model_select,
                Label("Mode (Optional):"),
                mode_select,
                classes="input-item",
            ),
            Horizontal(
                Button("Save", variant="primary", id="modal-save-btn"),
                Button("Cancel", variant="default", id="modal-cancel-btn"),
                classes="modal-buttons",
            ),
            id="modal-container",
        )

    @on(Button.Pressed, "#modal-save-btn")
    def handle_save(self) -> None:
        name = self.query_one("#ws-name-input", Input).value.strip()
        path = self.query_one("#ws-path-input", Input).value.strip()
        model_select = self.query_one("#ws-model-select", Select)
        mode_select = self.query_one("#ws-mode-select", Select)

        if not name or not path:
            return

        expanded_path = str(Path(os.path.expanduser(path)).resolve())

        ws = Workspace(
            name=name,
            path=expanded_path,
            model=(str(model_select.value) if not model_select.is_blank() else None),
            mode=(str(mode_select.value) if not mode_select.is_blank() else None),
            realtime=self.workspace.realtime if self.workspace else None,
        )
        self.dismiss(ws)

    @on(Button.Pressed, "#modal-cancel-btn")
    def handle_cancel(self) -> None:
        self.dismiss(None)
