"""Command-line interface for headless mode."""

import argparse
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from .config import get_saved_directory, save_directory
from .enricher import PromptEnricher
from .groq_client import GroqClient
from .scanner import scan_project


def get_working_directory() -> str:
    """Get working directory from config, .env, or current directory."""
    # Load .env from current directory
    load_dotenv()

    # Check for saved config first
    saved_dir = get_saved_directory()
    if saved_dir:
        return saved_dir

    # Check for MAGIC_PROMPT_DIR in env
    env_dir = os.getenv("MAGIC_PROMPT_DIR")
    if env_dir:
        expanded = os.path.expanduser(env_dir)
        if Path(expanded).is_dir():
            return expanded

    # Fall back to current directory
    return os.getcwd()


def get_prompt_from_input(args: argparse.Namespace) -> str | None:
    """Get prompt from positional arg or piped stdin."""
    # Check positional argument first
    if args.prompt:
        return " ".join(args.prompt)

    # Check if there's piped input
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()

    return None


async def run_headless(prompt: str, directory: str, quiet: bool = False) -> str:
    """Run enrichment in headless mode and return result."""
    if not quiet:
        print(f"📁 Scanning: {directory}", file=sys.stderr)

    # Scan project
    context = scan_project(
        directory,
        log_callback=None if quiet else lambda msg: print(f"   {msg}", file=sys.stderr),
    )

    if not quiet:
        print(
            f"✓ Found {context.total_files} files, {len(context.signatures)} analyzed",
            file=sys.stderr,
        )

    # Get API key
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print(
            "Error: GROQ_API_KEY not set. Set it in environment or .env file.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Initialize enricher
    client = GroqClient(api_key=api_key)
    enricher = PromptEnricher(client, context)

    if not quiet:
        print("🔮 Enriching prompt...", file=sys.stderr)

    # Stream enrichment
    result = ""
    async for chunk in enricher.enrich(prompt):
        result += chunk
        if not quiet:
            print(chunk, end="", flush=True)

    if not quiet:
        print()  # Final newline

    return result


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for CLI."""
    parser = argparse.ArgumentParser(
        prog="magic-prompt",
        description="Enrich prompts with project context using AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  magic-prompt "add user auth"              # Enrich a prompt
  echo "add logging" | magic-prompt         # Pipe prompt from stdin
  magic-prompt -d /path/to/project "refactor"  # Specify project directory
  magic-prompt --save-dir /path/to/project  # Save directory for future use
  magic-prompt --tui                        # Launch interactive TUI
        """,
    )

    parser.add_argument(
        "prompt",
        nargs="*",
        help="The prompt to enrich (can also be piped via stdin)",
    )

    parser.add_argument(
        "-d",
        "--directory",
        help="Project directory to analyze (default: from config or current dir)",
    )

    parser.add_argument(
        "--save-dir",
        metavar="DIR",
        help="Save a directory as the default for future runs",
    )

    parser.add_argument(
        "--show-config",
        action="store_true",
        help="Show current saved configuration",
    )

    parser.add_argument(
        "-t",
        "--tui",
        action="store_true",
        help="Launch interactive TUI mode instead of headless",
    )

    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress progress output, only print result (no clipboard)",
    )

    parser.add_argument(
        "--debounce",
        type=int,
        metavar="MS",
        help="Set debounce time in milliseconds for TUI real-time mode (100-5000)",
    )

    return parser


def run_cli() -> None:
    """Run the CLI application."""
    parser = create_parser()
    args = parser.parse_args()

    # Handle --show-config
    if args.show_config:
        from .config import get_config_path, load_config

        config = load_config()
        print(f"Config file: {get_config_path()}")
        if config:
            import json

            print(json.dumps(config, indent=2))
        else:
            print("No configuration saved.")
        return

    # Handle --save-dir
    if args.save_dir:
        directory = os.path.expanduser(args.save_dir)
        if not Path(directory).is_dir():
            print(f"Error: Directory not found: {directory}", file=sys.stderr)
            sys.exit(1)
        save_directory(directory)
        print(f"✓ Saved default directory: {directory}")
        return

    # Handle --debounce
    if args.debounce is not None:
        from .config import set_debounce_ms

        set_debounce_ms(args.debounce)
        print(f"✓ Debounce time set to: {args.debounce}ms")
        if not args.tui and not args.prompt:
            return  # Just setting config, exit

    # TUI mode
    if args.tui:
        from .app import main as tui_main

        tui_main()
        return

    # Get prompt
    prompt = get_prompt_from_input(args)

    if not prompt:
        # No prompt provided, launch TUI
        from .app import main as tui_main

        tui_main()
        return

    # Get directory (from arg, config, env, or cwd)
    directory = args.directory or get_working_directory()

    if not Path(directory).is_dir():
        print(f"Error: Directory not found: {directory}", file=sys.stderr)
        sys.exit(1)

    # Run headless enrichment
    load_dotenv()  # Ensure .env is loaded for API key

    try:
        if args.quiet:
            result = asyncio.run(run_headless(prompt, directory, quiet=True))
            print(result)
        else:
            result = asyncio.run(run_headless(prompt, directory, quiet=False))

        # Always copy to clipboard in headless mode
        import subprocess

        try:
            process = subprocess.Popen(
                ["pbcopy"],
                stdin=subprocess.PIPE,
                text=True,
            )
            process.communicate(input=result)
            if not args.quiet:
                print("\n✓ Copied to clipboard!", file=sys.stderr)
        except Exception as e:
            if not args.quiet:
                print(f"\nNote: Could not copy to clipboard: {e}", file=sys.stderr)

    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
