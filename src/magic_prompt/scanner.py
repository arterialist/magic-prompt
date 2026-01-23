"""File system scanner for extracting project context."""

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import pathspec


@dataclass
class FileSignature:
    """Represents extracted signatures from a source file."""

    path: str
    docstring: str = ""
    classes: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)


@dataclass
class ProjectContext:
    """Aggregated project context for prompt enrichment."""

    root_path: str
    file_tree: str = ""
    config_files: dict[str, str] = field(default_factory=dict)
    signatures: list[FileSignature] = field(default_factory=list)
    total_files: int = 0
    total_dirs: int = 0

    def to_prompt_context(self) -> str:
        """Format context for inclusion in LLM prompt."""
        parts = [
            f"# Project: {Path(self.root_path).name}",
            f"Path: {self.root_path}",
            f"Size: {self.total_files} files, {self.total_dirs} directories",
            "",
            "## Directory Structure",
            "```",
            self.file_tree,
            "```",
        ]

        if self.config_files:
            parts.append("\n## Configuration Files")
            for filename, content in self.config_files.items():
                parts.append(f"\n### {filename}")
                parts.append("```")
                # Truncate very long configs
                if len(content) > 1500:
                    parts.append(content[:1500] + "\n... (truncated)")
                else:
                    parts.append(content)
                parts.append("```")

        if self.signatures:
            parts.append("\n## Source Files Analysis")
            parts.append(
                "Files are listed with relevance scores based on query matching. Higher scores = more relevant:\n"
            )

            for sig in self.signatures:
                # Get relevance score if available from retrieval
                relevance = getattr(sig, "_debug_score", None)
                if relevance is not None:
                    relevance_pct = int(relevance * 100)
                    parts.append(f"### `{sig.path}` [**{relevance_pct}% relevant**]")
                else:
                    parts.append(f"### `{sig.path}`")

                if sig.docstring:
                    parts.append(f"**Purpose**: {sig.docstring}")

                if sig.imports:
                    parts.append(f"**Key imports**: {', '.join(sig.imports[:8])}")

                if sig.classes:
                    parts.append(f"**Classes**: {', '.join(sig.classes)}")

                if sig.functions:
                    parts.append(f"**Functions**: {', '.join(sig.functions)}")

                parts.append("")

        return "\n".join(parts)


# Key config files to extract content from
CONFIG_FILES = {
    "README.md",
    "README.rst",
    "README.txt",
    "package.json",
    "pyproject.toml",
    "setup.py",
    "Cargo.toml",
    "go.mod",
    "composer.json",
    "Gemfile",
    "requirements.txt",
    "Makefile",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
}

# File extensions to extract signatures from
SIGNATURE_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx"}

# Default ignore patterns
DEFAULT_IGNORES = [
    ".git",
    ".git/**",
    "node_modules",
    "node_modules/**",
    "__pycache__",
    "__pycache__/**",
    "*.pyc",
    ".venv",
    ".venv/**",
    "venv",
    "venv/**",
    ".env",
    "dist",
    "dist/**",
    "build",
    "build/**",
    ".next",
    ".next/**",
    "target",
    "target/**",
    "*.egg-info",
    "*.egg-info/**",
]


def load_gitignore(root: Path) -> pathspec.PathSpec | None:
    """Load .gitignore patterns if present."""
    gitignore_path = root / ".gitignore"
    if gitignore_path.exists():
        with open(gitignore_path, "r", encoding="utf-8", errors="ignore") as f:
            patterns = f.read().splitlines()
        return pathspec.PathSpec.from_lines("gitwildmatch", patterns)
    return None


def extract_python_signatures(file_path: Path) -> FileSignature:
    """Extract detailed signatures from Python file including docstrings."""
    sig = FileSignature(path=str(file_path))
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        tree = ast.parse(content)

        # Get module docstring
        if (
            tree.body
            and isinstance(tree.body[0], ast.Expr)
            and isinstance(tree.body[0].value, ast.Constant)
            and isinstance(tree.body[0].value.value, str)
        ):
            docstring = tree.body[0].value.value.strip()
            # Take first line or first 150 chars
            sig.docstring = docstring.split("\n")[0][:150]

        # Get imports
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    sig.imports.append(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    sig.imports.append(node.module.split(".")[0])
        sig.imports = list(dict.fromkeys(sig.imports))[:10]  # Dedupe and limit

        # Get classes and functions with docstrings
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                class_doc = ast.get_docstring(node)
                doc_hint = f" - {class_doc.split(chr(10))[0][:80]}" if class_doc else ""

                methods = [
                    n.name
                    for n in node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and not n.name.startswith("_")
                ]
                if methods:
                    sig.classes.append(
                        f"{node.name}[{', '.join(methods[:4])}]{doc_hint}"
                    )
                else:
                    sig.classes.append(f"{node.name}{doc_hint}")

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("_"):
                    func_doc = ast.get_docstring(node)
                    doc_hint = (
                        f" - {func_doc.split(chr(10))[0][:60]}" if func_doc else ""
                    )

                    args = [arg.arg for arg in node.args.args if arg.arg != "self"][:3]
                    args_str = f"({', '.join(args)})" if args else "()"
                    sig.functions.append(f"{node.name}{args_str}{doc_hint}")

    except (SyntaxError, UnicodeDecodeError, Exception):
        pass
    return sig


def extract_js_ts_signatures(file_path: Path) -> FileSignature:
    """Extract class and function signatures from JS/TS file."""
    import re

    sig = FileSignature(path=str(file_path))
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Try to get file-level JSDoc comment
        jsdoc_match = re.search(r"/\*\*\s*\n\s*\*\s*(.+?)(?:\n|\*/)", content)
        if jsdoc_match:
            sig.docstring = jsdoc_match.group(1).strip()[:150]

        # Get imports
        import_pattern = r"(?:import|require)\s*\(?['\"]([^'\"]+)['\"]"
        imports = re.findall(import_pattern, content)
        sig.imports = [i.split("/")[0].replace("@", "") for i in imports][:10]

        # Match class declarations
        class_pattern = r"(?:export\s+)?class\s+(\w+)"
        sig.classes = re.findall(class_pattern, content)[:10]

        # Match function declarations and exports
        func_patterns = [
            r"(?:export\s+)?(?:async\s+)?function\s+(\w+)",
            r"(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?\(",
        ]
        funcs = set()
        for pattern in func_patterns:
            funcs.update(re.findall(pattern, content))
        sig.functions = list(funcs)[:15]

    except (UnicodeDecodeError, OSError):
        pass
    return sig


def scan_project(
    root_path: str,
    max_depth: int = 8,
    max_files: int = 1000,
    log_callback: Callable[[str], None] | None = None,
) -> ProjectContext:
    """
    Scan a project directory and extract context for prompt enrichment.

    Args:
        root_path: Path to the project root directory
        max_depth: Maximum directory depth to scan
        max_files: Maximum number of files to process
        log_callback: Optional callback for logging progress
    """
    if log_callback:
        log_callback(f"DEBUG: scan_project called with max_files={max_files}")
    root = Path(root_path).resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Invalid directory: {root_path}")

    def log(msg: str) -> None:
        if log_callback:
            log_callback(msg)

    log(f"Scanning: {root}")

    # Load ignore patterns
    gitignore = load_gitignore(root)
    default_spec = pathspec.PathSpec.from_lines("gitwildmatch", DEFAULT_IGNORES)

    context = ProjectContext(root_path=str(root))
    tree_lines: list[str] = []
    file_count = 0
    dir_count = 0

    def should_ignore(path: Path) -> bool:
        rel_path = str(path.relative_to(root))
        if default_spec.match_file(rel_path):
            return True
        if gitignore and gitignore.match_file(rel_path):
            return True
        return False

    def scan_dir(current: Path, depth: int, prefix: str = "") -> None:
        nonlocal file_count, dir_count

        if depth > max_depth or file_count > max_files:
            return

        try:
            entries = sorted(
                current.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())
            )
        except PermissionError:
            return

        entries = [e for e in entries if not should_ignore(e)]

        for i, entry in enumerate(entries):
            is_last = i == len(entries) - 1
            connector = "└── " if is_last else "├── "
            extension = "    " if is_last else "│   "

            if entry.is_dir():
                dir_count += 1
                tree_lines.append(f"{prefix}{connector}{entry.name}/")
                scan_dir(entry, depth + 1, prefix + extension)
            else:
                file_count += 1
                tree_lines.append(f"{prefix}{connector}{entry.name}")

                # Extract config file content
                if entry.name in CONFIG_FILES:
                    log(f"Reading config: {entry.name}")
                    try:
                        with open(entry, "r", encoding="utf-8", errors="ignore") as f:
                            context.config_files[entry.name] = f.read()
                    except OSError:
                        pass

                # Extract signatures from source files
                if entry.suffix in SIGNATURE_EXTENSIONS and file_count <= max_files:
                    rel_path = str(entry.relative_to(root))
                    if entry.suffix == ".py":
                        sig = extract_python_signatures(entry)
                    elif entry.suffix in {".js", ".ts", ".jsx", ".tsx"}:
                        sig = extract_js_ts_signatures(entry)
                    else:
                        sig = FileSignature(path=rel_path)

                    sig.path = rel_path
                    if sig.classes or sig.functions or sig.docstring:
                        context.signatures.append(sig)

    log("Building file tree...")
    tree_lines.append(f"{root.name}/")
    scan_dir(root, 0)

    context.file_tree = "\n".join(tree_lines[:300])  # Increased limit
    if len(tree_lines) > 300:
        context.file_tree += f"\n... and {len(tree_lines) - 300} more entries"

    context.total_files = file_count
    context.total_dirs = dir_count

    log(
        f"Scan complete: {file_count} files, {dir_count} directories, {len(context.signatures)} analyzed"
    )
    return context
