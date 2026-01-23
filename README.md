# Magic Prompt

[![PyPI version](https://badge.fury.io/py/ai-magic-prompt.svg)](https://pypi.org/project/ai-magic-prompt/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

A TUI and CLI tool that enriches short, vague prompts into detailed, structured prompts using Groq API and your project's actual file structure and codebase.

<video src="demo.mp4" controls width="100%"></video>

## Features

- 📁 **Project-Aware**: Scans your project's file structure, config files, and extracts code signatures
- 🧠 **AI-Powered**: Uses Groq's fast LLM API to intelligently expand prompts
- ⚡ **Real-Time Streaming**: Watch the enriched prompt generate in real-time
- 🖥️ **Dual Mode**: Interactive TUI or headless CLI for shell scripting
- 🗂️ **Workspace Management**: Save and switch between multiple project workspaces
- 🎯 **Dynamic Model Selection**: Automatically fetch and select from available Groq models
- 📊 **Status Bar**: Real-time display of current mode, model, and settings

## Installation

### From PyPI

```bash
pip install ai-magic-prompt
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv tool install ai-magic-prompt
```

### Raycast Extension

The easiest way to install the Raycast extension is using the built-in command:

```bash
# Print the script to your terminal
magic-prompt --install-raycast

# Or save it directly to your Raycast scripts folder
magic-prompt --install-raycast ~/path/to/raycast/scripts
```

This will generate a script that automatically uses your current `magic-prompt` installation.

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

## Configuration

Magic Prompt saves your preferences in `~/.config/magic-prompt/config.json`. You can configure these via the CLI:

### Model Selection

Set your preferred Groq model (default: `llama-3.3-70b-versatile`):

```bash
magic-prompt --model llama-3.1-8b-instant
```

### Debounce Time

Adjust the real-time enrichment delay in milliseconds (default: `800`):

```bash
magic-prompt --debounce 500
```

### Default Directory

Save your current project directory as the default:

```bash
magic-prompt --save-dir .
```

### View Current Config

```bash
magic-prompt --show-config
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

| Option            | Description                                         |
| ----------------- | --------------------------------------------------- |
| `-d, --directory` | Project directory (default: from config or cwd)     |
| `-t, --tui`       | Launch interactive TUI mode                         |
| `-q, --quiet`     | Only output result, no progress                     |
| `--retrieval`     | File retrieval mode: `tfidf`, `heuristic`, `none`   |
| `--model`         | Groq model to use (e.g., `llama-3.3-70b-versatile`) |
| `--debounce MS`   | Set debounce time for real-time mode                |
| `--save-dir DIR`  | Save default directory for future runs              |
| `--show-config`   | Show current configuration                          |

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

| Key      | Action                   |
| -------- | ------------------------ |
| `Enter`  | Submit prompt            |
| `Ctrl+T` | Toggle real-time         |
| `Ctrl+Y` | Copy to clipboard        |
| `Ctrl+U` | Clear Input              |
| `Ctrl+L` | Clear Output             |
| `Ctrl+R` | Cycle retrieval mode     |
| `F5`     | Rescan project           |
| `Ctrl+S` | Open Settings            |
| `Ctrl+M` | Cycle enrichment mode    |
| `Ctrl+W` | Manage workspaces        |
| `Ctrl+D` | Cycle through workspaces |
| `Ctrl+Q` | Quit                     |

## How It Works

1. **Scans** your project directory structure
2. **Extracts** docstrings, function signatures, and imports
3. **Retrieves** the most relevant files based on your prompt (configurable)
4. **Sends** context + your prompt to Groq's LLM
5. **Streams** an enriched version that references actual files and APIs

## Retrieval Modes

Magic Prompt uses intelligent file retrieval to select the most relevant files from your project context before sending to the LLM. This is especially important for monorepos and large projects where including all files would exceed context limits.

### Available Modes

| Mode        | Description                                 | Best For                           |
| ----------- | ------------------------------------------- | ---------------------------------- |
| `tfidf`     | Hybrid TF-IDF + heuristic scoring (default) | Large projects, balanced accuracy  |
| `heuristic` | Path and content-based structural matching  | Monorepos, explicit file targeting |
| `none`      | Include all files without filtering         | Small projects (<50 files)         |

### Setting Retrieval Mode

**CLI (one-time):**

```bash
magic-prompt --retrieval heuristic "add user auth"
```

**Config (persistent):**

```bash
# In TUI: Press Ctrl+R to cycle through modes
# Or edit ~/.config/magic-prompt/config.json:
{
  "retrieval_mode": "tfidf"
}
```

### Working Principle

**TF-IDF Mode (Hybrid):**

- Computes TF-IDF vectors for all files based on path, docstrings, functions, and classes
- Blends TF-IDF similarity (5%) with heuristic scoring (95%)
- Produces relevance percentages shown in the LLM context (e.g., `[95% relevant]`)

**Heuristic Mode:**

- Matches query keywords against file paths, function names, and class names
- Boosts exact path segment matches
- Considers file recency (recently modified files rank higher)

**None Mode:**

- Includes all scanned files up to `max_files` limit
- No filtering or ranking applied
- Use only for small projects where context fits

### Recommendations

| Scenario                         | Recommended Mode | Reason                                   |
| -------------------------------- | ---------------- | ---------------------------------------- |
| Monorepo with multiple projects  | `heuristic`      | Best at isolating the correct subproject |
| Large single project             | `tfidf`          | Balanced keyword + structural matching   |
| Small project (<50 files)        | `none`           | Full context fits, no filtering needed   |
| Targeting specific files by path | `heuristic`      | Highest weight on path segments          |
| General feature requests         | `tfidf`          | Good at keyword relevance                |

### Configuration Options

```json
{
  "retrieval_mode": "tfidf", // "tfidf" | "heuristic" | "none"
  "top_k_files": 20, // Max files to include in context
  "max_files": 5000, // Max files to scan (increase for monorepos)
  "max_depth": 8 // Directory traversal depth
}
```

## License

GNU General Public License v3.0 - see [LICENSE](LICENSE) for details.
