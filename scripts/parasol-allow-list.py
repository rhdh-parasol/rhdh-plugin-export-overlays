#!/usr/bin/env python3
"""Expand parasol-publish-workspaces.txt for publish CI and catalog-index.

Adding a workspace: put its directory name in parasol-publish-workspaces.txt
and retarget that workspace's metadata dynamicArtifact to this fork's GHCR.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ALLOW_LIST_NAME = "parasol-publish-workspaces.txt"


def _listed_names(root: Path) -> list[str]:
    path = root / ALLOW_LIST_NAME
    if not path.is_file():
        return []
    names: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        names.append(line.removeprefix("workspaces/"))
    return names


def workspace_paths(root: Path) -> list[str]:
    return [f"workspaces/{name}" for name in _listed_names(root)]


def package_lines(root: Path) -> list[str]:
    lines: list[str] = []
    for name in _listed_names(root):
        plugins_list = root / "workspaces" / name / "plugins-list.yaml"
        if not plugins_list.is_file():
            print(
                f"warning: missing {plugins_list}, skipping",
                file=sys.stderr,
            )
            continue
        for raw in plugins_list.read_text(encoding="utf-8").splitlines():
            line = raw.split("#", 1)[0].strip()
            if not line or ":" not in line:
                continue
            plugin_path = line.split(":", 1)[0].strip().strip("'\"")
            if plugin_path:
                lines.append(f"{name}/{plugin_path}")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Overlay repo root",
    )
    parser.add_argument(
        "--workspace-path",
        default="",
        help="If set, publish only this workspace (overrides the allow-list)",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--workspaces-json",
        action="store_true",
        help="Print GitHub output workspaces=<json array of workspaces/name>",
    )
    group.add_argument(
        "--packages-file",
        type=Path,
        help="Write catalog --packages-file lines (workspace/plugins/...)",
    )
    args = parser.parse_args()
    root = args.root.resolve()

    if args.workspaces_json:
        explicit = (args.workspace_path or os.environ.get("WORKSPACE_PATH", "")).strip()
        if explicit:
            if not explicit.startswith("workspaces/"):
                explicit = f"workspaces/{explicit}"
            paths = [explicit]
        else:
            paths = workspace_paths(root)
        print(f"Workspaces to publish: {json.dumps(paths)}", file=sys.stderr)
        gh_output = os.environ.get("GITHUB_OUTPUT")
        if gh_output:
            with open(gh_output, "a", encoding="utf-8") as fh:
                fh.write("workspaces=" + json.dumps(paths) + "\n")
        else:
            print(json.dumps(paths))
        return 0

    lines = package_lines(root)
    args.packages_file.write_text(
        "\n".join(lines) + ("\n" if lines else ""),
        encoding="utf-8",
    )
    print(f"Wrote {len(lines)} package path(s) to {args.packages_file}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
