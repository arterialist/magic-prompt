# Magic Prompt

A TUI and CLI tool that enriches short, vague prompts into detailed, structured prompts using Groq API and your project's actual file structure and codebase.

## Features

- 📁 **Project-Aware**: Scans your project's file structure, config files, and extracts code signatures
- 🧠 **AI-Powered**: Uses Groq's fast LLM API to intelligently expand prompts
- ⚡ **Real-Time Streaming**: Watch the enriched prompt generate in real-time
- 🖥️ **Dual Mode**: Interactive TUI or headless CLI for shell scripting

## Installation

Requires Python 3.11+ and [uv](https://github.com/astral-sh/uv):

```bash
cd magic-prompt
uv sync
```

## Setup

Get your Groq API key from [console.groq.com/keys](https://console.groq.com/keys).

```bash
cp .env.example .env
# Edit .env with your GROQ_API_KEY
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

# Copy result to clipboard
magic-prompt -c "improve error handling"
```

#### CLI Options

| Option            | Description                                   |
| ----------------- | --------------------------------------------- |
| `-d, --directory` | Project directory (default: from .env or cwd) |
| `-t, --tui`       | Launch interactive TUI mode                   |
| `-q, --quiet`     | Only output result, no progress               |
| `-c, --copy`      | Copy result to clipboard (macOS)              |

#### Environment Variables

Set in `.env` file:

- `GROQ_API_KEY` - Required API key
- `MAGIC_PROMPT_DIR` - Default project directory for headless mode

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
| `Ctrl+Y` | Copy to clipboard |
| `Ctrl+L` | Clear output      |
| `Ctrl+R` | Rescan project    |
| `q`      | Quit              |

## How It Works

1. **Scans** your project directory structure
2. **Extracts** docstrings, function signatures, and imports
3. **Sends** context + your prompt to Groq's LLM
4. **Streams** an enriched version that references actual files and APIs
