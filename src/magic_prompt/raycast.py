#!/usr/bin/env python3

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title Magic Prompt
# @raycast.mode fullOutput
# @raycast.packageName Magic Prompt

# Optional parameters:
# @raycast.icon 🪄
# @raycast.argument1 { "type": "text", "placeholder": "Prompt", "optional": false }
# @raycast.argument2 { "type": "text", "placeholder": "Directory (optional)", "optional": true }

# Documentation:
# @raycast.description Enrich prompts using Groq API and project context.
# @raycast.author arterialist
# @raycast.authorURL https://github.com/arterialist

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src to path if running from source
sys.path.append(str(Path(__file__).parent.parent))

from magic_prompt.cli import run_headless, get_working_directory


async def main():
    # Get arguments from Raycast
    # Raycast passes arguments as positional arguments to the script
    if len(sys.argv) < 2:
        print("Error: Prompt is required.")
        sys.exit(1)

    prompt = sys.argv[1]
    directory_arg = sys.argv[2] if len(sys.argv) > 2 else None

    # Load environment variables
    load_dotenv()

    # Get directory
    directory = directory_arg or get_working_directory()

    if not Path(directory).is_dir():
        print(f"Error: Directory not found: {directory}")
        sys.exit(1)

    try:
        # Run enrichment in quiet mode to get only the result
        result = await run_headless(prompt, directory, quiet=True)
        print(result)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
