#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "tinycss2>=1.4.0,<2",
# ]
# ///

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

import tinycss2

DEFAULT_ROOT = Path("static/css")
NESTED_RULE_AT_RULES = {"media", "supports", "layer", "scope", "container"}


def iter_targets(raw_paths: list[str]) -> list[Path]:
    if raw_paths:
        targets = [Path(path) for path in raw_paths]
    else:
        targets = sorted(DEFAULT_ROOT.rglob("*.css"))

    files: list[Path] = []
    for target in targets:
        if target.is_dir():
            files.extend(sorted(target.rglob("*.css")))
            continue
        if target.suffix == ".css":
            files.append(target)

    return [path for path in files if path.exists() and not path.name.endswith(".min.css")]


def lint_nodes(nodes: Iterable[object], *, path: Path, errors: list[str]) -> None:
    for node in nodes:
        node_type = getattr(node, "type", None)

        if node_type == "error":
            errors.append(
                f"{path}:{node.source_line}:{node.source_column}: {node.message}"
            )
            continue

        if node_type == "qualified-rule":
            declarations = tinycss2.parse_declaration_list(
                node.content,
                skip_comments=True,
                skip_whitespace=True,
            )
            lint_nodes(declarations, path=path, errors=errors)
            continue

        if node_type == "at-rule" and node.content is not None:
            lower_at_keyword = getattr(node, "lower_at_keyword", "")
            if lower_at_keyword in NESTED_RULE_AT_RULES:
                nested_nodes = tinycss2.parse_rule_list(
                    node.content,
                    skip_comments=True,
                    skip_whitespace=True,
                )
            else:
                nested_nodes = tinycss2.parse_declaration_list(
                    node.content,
                    skip_comments=True,
                    skip_whitespace=True,
                )
            lint_nodes(nested_nodes, path=path, errors=errors)


def lint_file(path: Path) -> list[str]:
    css = path.read_text(encoding="utf-8")
    stylesheet = tinycss2.parse_stylesheet(
        css,
        skip_comments=True,
        skip_whitespace=True,
    )

    errors: list[str] = []
    lint_nodes(stylesheet, path=path, errors=errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lint CSS files for syntax errors using tinycss2."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="CSS files or directories to lint. Defaults to static/css.",
    )
    args = parser.parse_args()

    files = iter_targets(args.paths)
    if not files:
        print("No CSS files found to lint.", file=sys.stderr)
        return 1

    all_errors: list[str] = []
    for path in files:
        all_errors.extend(lint_file(path))

    if all_errors:
        for error in all_errors:
            print(error, file=sys.stderr)
        return 1

    print(f"CSS lint passed for {len(files)} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
