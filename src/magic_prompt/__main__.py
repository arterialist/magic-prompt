"""Entry point for running as module: python -m magic_prompt"""

from .cli import run_cli


def main() -> None:
    """Main entry point."""
    run_cli()


if __name__ == "__main__":
    main()
