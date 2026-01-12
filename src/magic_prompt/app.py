"""Textual TUI application for Magic Prompt."""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import (
    Footer,
    Header,
    Input,
    Label,
    RichLog,
    Static,
    TextArea,
)

from .config import (
    get_debounce_ms,
    get_realtime_mode,
    get_saved_directory,
    save_directory,
    set_realtime_mode,
)
from .enricher import PromptEnricher
from .groq_client import GroqClient
from .scanner import ProjectContext, scan_project


class DirectoryScreen(Screen):
    """Initial screen for selecting project directory."""

    CSS = """
    DirectoryScreen {
        align: center middle;
    }

    #dir-container {
        width: 80%;
        max-width: 100;
        height: auto;
        padding: 2 4;
        background: $surface;
        border: tall $primary;
    }

    #dir-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
        color: $text;
    }

    #dir-subtitle {
        text-align: center;
        color: $text-muted;
        margin-bottom: 2;
    }

    #dir-input {
        margin-bottom: 1;
    }

    #dir-error {
        color: $error;
        text-align: center;
        height: 1;
    }
    """

    def compose(self) -> ComposeResult:
        # Pre-fill with saved directory if available
        saved_dir = get_saved_directory() or ""
        yield Container(
            Static("🪄 Magic Prompt", id="dir-title"),
            Static("Enter the project root directory to analyze", id="dir-subtitle"),
            Input(
                value=saved_dir,
                placeholder="e.g., /Users/you/projects/myapp",
                id="dir-input",
            ),
            Static("", id="dir-error"),
            id="dir-container",
        )

    def on_mount(self) -> None:
        self.query_one("#dir-input", Input).focus()

    @on(Input.Submitted, "#dir-input")
    def handle_dir_submit(self, event: Input.Submitted) -> None:
        path = event.value.strip()
        if not path:
            self.query_one("#dir-error", Static).update("Please enter a directory path")
            return

        expanded = os.path.expanduser(path)
        if not Path(expanded).exists():
            self.query_one("#dir-error", Static).update(
                f"Directory does not exist: {path}"
            )
            return

        if not Path(expanded).is_dir():
            self.query_one("#dir-error", Static).update(f"Not a directory: {path}")
            return

        # Save directory for future runs
        save_directory(expanded)
        self.app.switch_to_main(expanded)


class APIKeyScreen(Screen):
    """Screen for entering Groq API key."""

    CSS = """
    APIKeyScreen {
        align: center middle;
    }

    #key-container {
        width: 80%;
        max-width: 100;
        height: auto;
        padding: 2 4;
        background: $surface;
        border: tall $warning;
    }

    #key-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
        color: $warning;
    }

    #key-subtitle {
        text-align: center;
        color: $text-muted;
        margin-bottom: 2;
    }

    #key-input {
        margin-bottom: 1;
    }

    #key-error {
        color: $error;
        text-align: center;
        height: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Container(
            Static("🔑 Groq API Key Required", id="key-title"),
            Static("Get your key at https://console.groq.com/keys", id="key-subtitle"),
            Input(
                placeholder="gsk_...",
                password=True,
                id="key-input",
            ),
            Static("", id="key-error"),
            id="key-container",
        )

    def on_mount(self) -> None:
        self.query_one("#key-input", Input).focus()

    @on(Input.Submitted, "#key-input")
    def handle_key_submit(self, event: Input.Submitted) -> None:
        key = event.value.strip()
        if not key:
            self.query_one("#key-error", Static).update(
                "API key is required to proceed"
            )
            return

        if not key.startswith("gsk_"):
            self.query_one("#key-error", Static).update(
                "Invalid key format (should start with gsk_)"
            )
            return

        self.app.set_api_key(key)


class MainScreen(Screen):
    """Main enrichment screen with log, output, and input panels."""

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+t", "toggle_realtime", "Real-time"),
        Binding("ctrl+y", "copy_output", "Copy"),
        Binding("ctrl+l", "clear_output", "Clear"),
        Binding("ctrl+r", "rescan", "Rescan"),
    ]

    # Reactive attribute for real-time mode
    realtime_mode = reactive(False)

    CSS = """
    MainScreen {
        layout: grid;
        grid-size: 1 4;
        grid-rows: 6 4 3fr 3;
    }

    #log-panel {
        border: round $primary-darken-2;
        height: 100%;
        overflow-y: auto;
    }

    #log-panel RichLog {
        scrollbar-gutter: stable;
    }

    #original-panel {
        border: round $warning-darken-2;
        height: 100%;
        overflow-y: auto;
    }

    #original-prompt {
        height: 100%;
        padding: 0 1;
    }

    #output-panel {
        border: round $success-darken-2;
        height: 100%;
    }

    #output-panel TextArea {
        height: 100%;
    }

    #input-container {
        height: 3;
        padding: 0 1;
    }

    #prompt-input {
        width: 100%;
    }

    .panel-label {
        dock: top;
        padding: 0 1;
        background: $surface;
        color: $text-muted;
    }
    """

    def __init__(
        self,
        project_path: str,
        api_key: str,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.project_path = project_path
        self.api_key = api_key
        self.project_context: ProjectContext | None = None
        self.enricher: PromptEnricher | None = None
        self.groq_client: GroqClient | None = None
        self.is_enriching = False
        self.realtime_mode = get_realtime_mode()
        self._debounce_task: asyncio.Task | None = None
        self._debounce_ms = get_debounce_ms()
        self._last_input = ""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Label("📋 Logs", classes="panel-label"),
            TextArea(read_only=True, id="log", show_line_numbers=False),
            id="log-panel",
        )
        yield Container(
            Label("📝 Original Prompt", classes="panel-label"),
            Static("", id="original-prompt"),
            id="original-panel",
        )
        yield Container(
            Label("✨ Enriched Prompt", classes="panel-label"),
            TextArea(read_only=True, id="output", show_line_numbers=False),
            id="output-panel",
        )
        yield Container(
            Input(
                placeholder="Type your prompt and press Enter...",
                id="prompt-input",
            ),
            id="input-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#prompt-input", Input).focus()
        self._update_mode_indicator()
        self.scan_project()

    def _update_mode_indicator(self) -> None:
        """Update the input placeholder to show current mode."""
        input_widget = self.query_one("#prompt-input", Input)
        if self.realtime_mode:
            input_widget.placeholder = f"⚡ Real-time mode (debounce: {self._debounce_ms}ms) - type to enrich..."
        else:
            input_widget.placeholder = "Type your prompt and press Enter..."

    def add_log(self, message: str) -> None:
        """Add message to the log panel."""
        import re

        # Strip rich markup for plain text display
        plain_message = re.sub(r"\[/?[^\]]+\]", "", message)
        log_widget = self.query_one("#log", TextArea)
        current = log_widget.text
        if current:
            log_widget.text = current + "\n" + plain_message
        else:
            log_widget.text = plain_message
        # Scroll to bottom
        log_widget.scroll_end(animate=False)

    @work(thread=True)
    def scan_project(self) -> None:
        """Scan the project directory in a background thread."""
        self.add_log(f"[bold blue]Scanning project:[/] {self.project_path}")

        try:
            self.project_context = scan_project(
                self.project_path,
                log_callback=lambda msg: self.app.call_from_thread(
                    self.add_log, f"[dim]{msg}[/dim]"
                ),
            )
            self.add_log(
                f"[bold green]✓ Scan complete:[/] "
                f"{self.project_context.total_files} files, "
                f"{self.project_context.total_dirs} dirs, "
                f"{len(self.project_context.signatures)} signatures"
            )

            # Initialize enricher
            try:
                self.groq_client = GroqClient(api_key=self.api_key)
                self.enricher = PromptEnricher(self.groq_client, self.project_context)
                mode_str = "⚡ Real-time" if self.realtime_mode else "Enter to submit"
                self.add_log(f"[bold green]✓ Ready![/] ({mode_str})")
            except ValueError as e:
                self.add_log(f"[bold red]API Error:[/] {e}")

        except Exception as e:
            self.add_log(f"[bold red]Scan error:[/] {e}")

    @on(Input.Submitted, "#prompt-input")
    async def handle_prompt_submit(self, event: Input.Submitted) -> None:
        """Handle Enter key - always enriches in non-real-time mode."""
        prompt = event.value.strip()
        if not prompt:
            return

        # Cancel any pending debounce
        if self._debounce_task:
            self._debounce_task.cancel()
            self._debounce_task = None

        await self._do_enrich(prompt, clear_input=True)

    @on(Input.Changed, "#prompt-input")
    async def handle_input_changed(self, event: Input.Changed) -> None:
        """Handle real-time input with debouncing."""
        if not self.realtime_mode:
            return

        prompt = event.value.strip()
        if not prompt or prompt == self._last_input:
            return

        # Cancel existing debounce task
        if self._debounce_task:
            self._debounce_task.cancel()

        # Start new debounce timer
        self._debounce_task = asyncio.create_task(self._debounced_enrich(prompt))

    async def _debounced_enrich(self, prompt: str) -> None:
        """Wait for debounce period then enrich."""
        try:
            await asyncio.sleep(self._debounce_ms / 1000.0)
            if prompt and prompt != self._last_input:
                await self._do_enrich(prompt, clear_input=False)
        except asyncio.CancelledError:
            pass  # Debounce was cancelled by new input

    async def _do_enrich(self, prompt: str, clear_input: bool = True) -> None:
        """Perform the actual enrichment."""
        if self.is_enriching:
            return

        if not self.enricher:
            self.add_log(
                "[red]Enricher not ready. Wait for project scan to complete.[/]"
            )
            return

        self._last_input = prompt

        if clear_input:
            input_widget = self.query_one("#prompt-input", Input)
            input_widget.value = ""

        # Show original prompt
        original_widget = self.query_one("#original-prompt", Static)
        original_widget.update(prompt)

        output = self.query_one("#output", TextArea)
        output.clear()

        self.enrich_prompt(prompt)

    @work(exclusive=True)
    async def enrich_prompt(self, prompt: str) -> None:
        """Enrich the prompt using Groq API with streaming."""
        self.is_enriching = True
        output = self.query_one("#output", TextArea)

        try:
            self.add_log(f"[bold blue]Enriching:[/] {prompt[:50]}...")

            full_response = ""
            async for chunk in self.enricher.enrich(
                prompt,
                log_callback=lambda msg: self.add_log(f"[dim]{msg}[/dim]"),
            ):
                full_response += chunk
                output.text = full_response

            self.add_log("[bold green]✓ Enrichment complete[/]")

            # Show token usage if available
            if self.groq_client and self.groq_client.last_usage:
                usage = self.groq_client.last_usage
                self.add_log(
                    f"[dim]Tokens: {usage.total_tokens} (prompt: {usage.prompt_tokens}, completion: {usage.completion_tokens})[/dim]"
                )

        except Exception as e:
            self.add_log(f"[bold red]Error:[/] {e}")
        finally:
            self.is_enriching = False

    def action_clear_output(self) -> None:
        """Clear the output panel."""
        self.query_one("#output", TextArea).clear()

    def action_copy_output(self) -> None:
        """Copy the enriched prompt to clipboard."""
        import subprocess

        output = self.query_one("#output", TextArea)
        text = output.text
        if not text:
            self.add_log("[yellow]Nothing to copy[/]")
            return
        try:
            # Use pbcopy on macOS
            process = subprocess.Popen(
                ["pbcopy"],
                stdin=subprocess.PIPE,
                text=True,
            )
            process.communicate(input=text)
            self.add_log("[bold green]✓ Copied to clipboard![/]")
        except Exception as e:
            self.add_log(f"[red]Copy failed: {e}[/]")

    def action_rescan(self) -> None:
        """Rescan the project directory."""
        self.scan_project()

    def action_toggle_realtime(self) -> None:
        """Toggle real-time enrichment mode."""
        self.realtime_mode = not self.realtime_mode
        set_realtime_mode(self.realtime_mode)
        self._update_mode_indicator()

        mode_str = "⚡ Real-time" if self.realtime_mode else "Manual (Enter)"
        self.add_log(f"[bold cyan]Mode:[/] {mode_str}")

        if self.realtime_mode:
            self.add_log(f"[dim]Debounce: {self._debounce_ms}ms[/dim]")


class MagicPromptApp(App):
    """Main Textual application for Magic Prompt."""

    TITLE = "Magic Prompt"
    SUB_TITLE = "AI-Powered Prompt Enrichment"

    CSS = """
    Screen {
        background: $background;
    }
    """

    def __init__(self):
        super().__init__()
        load_dotenv()
        self.api_key = os.getenv("GROQ_API_KEY")
        self.project_path: str | None = None

    def on_mount(self) -> None:
        self.push_screen(DirectoryScreen())

    def switch_to_main(self, project_path: str) -> None:
        """Switch to main screen after directory selection."""
        self.project_path = project_path

        if not self.api_key:
            # Need to get API key first
            self.push_screen(APIKeyScreen())
        else:
            self.push_screen(MainScreen(project_path, self.api_key))

    def set_api_key(self, key: str) -> None:
        """Set the API key and proceed to main screen."""
        self.api_key = key
        os.environ["GROQ_API_KEY"] = key
        self.pop_screen()  # Remove API key screen
        self.pop_screen()  # Remove directory screen
        self.push_screen(MainScreen(self.project_path, self.api_key))


def main() -> None:
    """Entry point for the application."""
    app = MagicPromptApp()
    app.run()


if __name__ == "__main__":
    main()
