# Magic Prompt

[![PyPI version](https://badge.fury.io/py/ai-magic-prompt.svg)](https://pypi.org/project/ai-magic-prompt/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

A TUI and CLI tool that enriches short, vague prompts into detailed, structured prompts using Groq API and your project's actual file structure and codebase.

## Features

- 📁 **Project-Aware**: Scans your project's file structure, config files, and extracts code signatures
- 🧠 **AI-Powered**: Uses Groq's fast LLM API to intelligently expand prompts
- ⚡ **Real-Time Streaming**: Watch the enriched prompt generate in real-time
- 🖥️ **Dual Mode**: Interactive TUI or headless CLI for shell scripting

## Installation

### From PyPI

```bash
pip install ai-magic-prompt
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv tool install ai-magic-prompt
```

### From Source

```bash
git clone https://github.com/arterialist/magic-prompt.git
cd magic-prompt
pip install -e .
```

## Setup

Get your Groq API key from [console.groq.com/keys](https://console.groq.com/keys).

Set it as an environment variable:

```bash
export GROQ_API_KEY=gsk_...
```

Or create a `.env` file in your project directory:

```bash
GROQ_API_KEY=your_api_key_here
```

## Usage

### Headless CLI Mode

Run from anywhere as a shell command:

```bash
# Basic usage - enrich a prompt
magic-prompt "add user authentication"

# Pipe prompt from stdin
echo "add logging" | magic-prompt

# Specify project directory
magic-prompt -d /path/to/project "refactor the API"

# Quiet mode - only output result (good for piping)
magic-prompt -q "add tests" > enriched.md
```

#### CLI Options

| Option            | Description                                     |
| ----------------- | ----------------------------------------------- |
| `-d, --directory` | Project directory (default: from config or cwd) |
| `-t, --tui`       | Launch interactive TUI mode                     |
| `-q, --quiet`     | Only output result, no progress                 |
| `--debounce MS`   | Set debounce time for real-time mode            |
| `--save-dir DIR`  | Save default directory for future runs          |
| `--show-config`   | Show current configuration                      |

### Interactive TUI Mode

```bash
magic-prompt --tui
# OR just run without arguments:
magic-prompt
```

1. Enter your project's root directory path
2. Type a short prompt (e.g., "add user authentication")
3. Watch the enriched, project-aware prompt stream in real-time
4. Press `Ctrl+Y` to copy the enriched prompt

#### TUI Keyboard Shortcuts

| Key      | Action            |
| -------- | ----------------- |
| `Enter`  | Submit prompt     |
| `Ctrl+T` | Toggle real-time  |
| `Ctrl+Y` | Copy to clipboard |
| `Ctrl+L` | Clear output      |
| `Ctrl+R` | Rescan project    |
| `Ctrl+Q` | Quit              |

## How It Works

1. **Scans** your project directory structure
2. **Extracts** docstrings, function signatures, and imports
3. **Sends** context + your prompt to Groq's LLM
4. **Streams** an enriched version that references actual files and APIs

## License

MIT License - see [LICENSE](LICENSE) for details.
