"""Async subprocess wrapper for the Google Workspace CLI (gws)."""

import asyncio
import json
import logging
import re
import shlex
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

APPROVAL_REQUIRED_PATTERNS = [
    # Create operations
    r"calendar\s+.*events\.insert",
    r"calendar\s+.*\+insert",
    r"docs\s+.*documents\.create",
    r"docs\s+.*\+write",
    r"sheets\s+.*spreadsheets\.create",
    r"drive\s+.*files\.create",
    # Update operations
    r"calendar\s+.*events\.(update|patch)",
    r"docs\s+.*documents\.batchUpdate",
    r"sheets\s+.*values\.(update|append)",
    r"drive\s+.*files\.(update|patch)",
    # Delete operations
    r"\.delete\b",
    r"files\.emptyTrash",
]

BLOCKED_COMMANDS = ["auth", "config"]


@dataclass
class GWSResult:
    success: bool
    data: Optional[dict | list | str] = None
    error: Optional[str] = None
    command: str = ""
    requires_approval: bool = False
    dry_run: bool = False
    duration_ms: int = 0


def requires_approval(command: str) -> bool:
    for pattern in APPROVAL_REQUIRED_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return True
    return False


def _is_blocked(command: str) -> bool:
    parts = command.strip().split()
    if parts and parts[0].lower() in BLOCKED_COMMANDS:
        return True
    return False


def _smart_split(command: str) -> list[str]:
    """Split a gws command string preserving JSON blobs for --params and --json flags.

    shlex.split mangles JSON (strips quotes, splits on spaces inside braces).
    This extracts JSON values attached to those flags first, shell-splits the
    rest, then re-inserts the JSON as single arguments.
    """
    json_flags = {}
    remaining = command

    for flag in ("--params", "--json"):
        idx = remaining.find(flag)
        if idx == -1:
            continue
        after_flag = remaining[idx + len(flag):]
        # Skip whitespace to find the JSON start
        stripped = after_flag.lstrip()
        if not stripped.startswith("{") and not stripped.startswith("["):
            continue
        # Find matching closing brace/bracket
        open_char = stripped[0]
        close_char = "}" if open_char == "{" else "]"
        depth = 0
        in_string = False
        escape_next = False
        end_pos = None
        for i, ch in enumerate(stripped):
            if escape_next:
                escape_next = False
                continue
            if ch == "\\":
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == open_char:
                depth += 1
            elif ch == close_char:
                depth -= 1
                if depth == 0:
                    end_pos = i
                    break
        if end_pos is None:
            # Malformed JSON — fall back to shlex
            continue
        json_str = stripped[: end_pos + 1]
        # Calculate the full span in `remaining` to remove
        json_start_in_remaining = idx
        json_end_in_remaining = idx + len(flag) + (len(after_flag) - len(stripped)) + end_pos + 1
        json_flags[flag] = json_str
        remaining = remaining[:json_start_in_remaining] + remaining[json_end_in_remaining:]

    parts = shlex.split(remaining)

    # Re-insert JSON flags in order
    for flag, json_val in json_flags.items():
        parts.extend([flag, json_val])

    return parts


async def run_gws(command: str, dry_run: bool = False, timeout: float = 30.0, force_execute: bool = False) -> GWSResult:
    if _is_blocked(command):
        return GWSResult(success=False, error=f"Blocked command: {command.split()[0]}", command=command)

    needs_approval = requires_approval(command)
    if needs_approval and not force_execute:
        dry_run = True

    full_command = command
    if dry_run and "--dry-run" not in command:
        full_command = f"{command} --dry-run"

    args = ["gws"] + _smart_split(full_command)
    start = time.monotonic()

    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        duration_ms = int((time.monotonic() - start) * 1000)

        raw = stdout.decode().strip()
        err = stderr.decode().strip()

        if proc.returncode != 0:
            return GWSResult(
                success=False, error=err or raw or f"Exit code {proc.returncode}",
                command=full_command, requires_approval=needs_approval,
                dry_run=dry_run, duration_ms=duration_ms,
            )

        # Try parsing as JSON
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            data = raw

        return GWSResult(
            success=True, data=data, command=full_command,
            requires_approval=needs_approval, dry_run=dry_run, duration_ms=duration_ms,
        )

    except asyncio.TimeoutError:
        duration_ms = int((time.monotonic() - start) * 1000)
        return GWSResult(success=False, error=f"Timed out after {timeout}s", command=full_command, duration_ms=duration_ms)
    except FileNotFoundError:
        return GWSResult(success=False, error="gws CLI not found. Install: npm install -g @googleworkspace/cli", command=full_command)
    except Exception as e:
        duration_ms = int((time.monotonic() - start) * 1000)
        return GWSResult(success=False, error=str(e), command=full_command, duration_ms=duration_ms)
