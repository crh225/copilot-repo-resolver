#!/usr/bin/env python3
"""Local MCP server for resolving repository aliases."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

CONFIG_PATH = Path.home() / ".config" / "copilot-repo-resolver" / "config.json"
OWNER_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def load_config() -> dict[str, Any]:
    """Load and validate the user's local resolver configuration."""
    if not CONFIG_PATH.is_file():
        return {"repositoriesRoot": "~/development", "aliases": {}}

    with CONFIG_PATH.open(encoding="utf-8") as config_file:
        config = json.load(config_file)

    if not isinstance(config, dict):
        raise ValueError(f"{CONFIG_PATH} must contain a JSON object")
    root = config.get("repositoriesRoot", "~/development")
    aliases = config.get("aliases", {})
    if not isinstance(root, str) or not isinstance(aliases, dict) or not all(
        isinstance(alias, str) and isinstance(target, str) for alias, target in aliases.items()
    ):
        raise ValueError(f"{CONFIG_PATH} has an invalid repositoriesRoot or aliases value")
    return {"repositoriesRoot": root, "aliases": aliases}


def normalize_reference(reference: str, aliases: dict[str, str]) -> tuple[str, str | None]:
    """Resolve an alias or direct reference to an owner/repository value."""
    value = reference.strip().removeprefix("@")
    if value.endswith("/") and "/" not in value[:-1]:
        return "owner", value.removesuffix("/")
    if value in aliases:
        return "repository", aliases[value]
    if OWNER_REPOSITORY.fullmatch(value):
        return "repository", value
    raise ValueError("Reference must be an alias, owner/repository, or owner/")


def normalize_origin(origin: str) -> str:
    """Normalize common GitHub remote URL formats to owner/repository."""
    value = origin.strip().removesuffix(".git")
    if value.startswith("git@github.com:"):
        return value.removeprefix("git@github.com:")
    if value.startswith("https://github.com/"):
        return value.removeprefix("https://github.com/")
    if value.startswith("ssh://git@github.com/"):
        return value.removeprefix("ssh://git@github.com/")
    return value


def origin_for(path: Path) -> str | None:
    """Return a checkout's origin repository, if it has one."""
    result = subprocess.run(
        ["git", "-C", str(path), "remote", "get-url", "origin"],
        capture_output=True,
        check=False,
        text=True,
    )
    return normalize_origin(result.stdout) if result.returncode == 0 else None


def resolve_repository(reference: str) -> dict[str, Any]:
    """Resolve a repository reference without modifying local state."""
    config = load_config()
    kind, value = normalize_reference(reference, config["aliases"])
    if kind == "owner":
        matches = {
            alias: target for alias, target in config["aliases"].items() if target.startswith(f"{value}/")
        }
        return {"status": "ambiguous", "owner": value, "aliases": matches}

    assert value is not None
    root = Path(os.path.expanduser(config["repositoriesRoot"])).resolve()
    checkout = root / value
    if not checkout.is_dir():
        return {"status": "missing", "repository": value, "path": str(checkout)}

    origin = origin_for(checkout)
    if origin != value:
        return {
            "status": "mismatch",
            "repository": value,
            "path": str(checkout),
            "origin": origin,
        }
    return {"status": "found", "repository": value, "path": str(checkout)}


def clone_repository(repository: str, confirmed: bool) -> dict[str, Any]:
    """Clone a missing repository only after explicit user confirmation."""
    if not confirmed:
        raise ValueError("Cloning requires confirmed=true after explicit user approval")
    if not OWNER_REPOSITORY.fullmatch(repository):
        raise ValueError("repository must be an owner/repository value")

    config = load_config()
    root = Path(os.path.expanduser(config["repositoriesRoot"])).resolve()
    checkout = root / repository
    if checkout.exists():
        return {"status": "exists", "repository": repository, "path": str(checkout)}

    checkout.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["git", "clone", f"https://github.com/{repository}.git", str(checkout)],
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        return {"status": "error", "repository": repository, "message": result.stderr.strip()}

    resolved = resolve_repository(f"@{repository}")
    if resolved["status"] != "found":
        return {"status": "error", "repository": repository, "message": "Clone origin verification failed"}
    return resolved


TOOLS = [
    {
        "name": "resolve_repository",
        "description": "Resolve an alias, owner/repository, or owner/ reference without changing local state.",
        "inputSchema": {
            "type": "object",
            "properties": {"reference": {"type": "string"}},
            "required": ["reference"],
            "additionalProperties": False,
        },
    },
    {
        "name": "clone_repository",
        "description": "Clone a repository after the user explicitly approves the clone.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repository": {"type": "string"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["repository", "confirmed"],
            "additionalProperties": False,
        },
    },
]


def response(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    """Create a JSON-RPC success response."""
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def error(request_id: Any, message: str) -> dict[str, Any]:
    """Create a JSON-RPC error response."""
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32000, "message": message}}


def handle(request: dict[str, Any]) -> dict[str, Any] | None:
    """Handle one JSON-RPC request."""
    method = request.get("method")
    request_id = request.get("id")
    if method == "notifications/initialized":
        return None
    if method == "initialize":
        return response(
            request_id,
            {
                "protocolVersion": request.get("params", {}).get("protocolVersion", "2025-03-26"),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "repository-resolver", "version": "0.1.0"},
            },
        )
    if method == "tools/list":
        return response(request_id, {"tools": TOOLS})
    if method == "tools/call":
        params = request.get("params", {})
        try:
            if params.get("name") == "resolve_repository":
                result = resolve_repository(params.get("arguments", {}).get("reference", ""))
            elif params.get("name") == "clone_repository":
                arguments = params.get("arguments", {})
                result = clone_repository(arguments.get("repository", ""), arguments.get("confirmed", False))
            else:
                raise ValueError(f"Unknown tool: {params.get('name')}")
            return response(
                request_id,
                {"content": [{"type": "text", "text": json.dumps(result)}], "structuredContent": result},
            )
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            return response(
                request_id,
                {"content": [{"type": "text", "text": str(exc)}], "isError": True},
            )
    return error(request_id, f"Unsupported method: {method}")


def main() -> None:
    """Serve newline-delimited JSON-RPC requests on standard input."""
    for line in sys.stdin:
        try:
            result = handle(json.loads(line))
            if result is not None:
                print(json.dumps(result), flush=True)
        except json.JSONDecodeError as exc:
            print(json.dumps(error(None, f"Invalid JSON: {exc.msg}")), flush=True)


if __name__ == "__main__":
    main()
