#!/usr/bin/env python3
"""
terminal-capture — run a shell command and save the output as a JSON session file.

The JSON file can be consumed by terminal-player.js to create an animated,
selectable-text terminal div in any HTML page.

Usage:
    terminal-capture "command" output.json [options]

Example:
    terminal-capture "ls -lh" session.json --title "ls -lh"
    terminal-capture "duckdb -c 'SELECT 42'" query.json --title "DuckDB query"
"""

import argparse
import json
import os
import pty
import re
import select
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import List, Dict, Any

# ── ANSI handling ─────────────────────────────────────────────────────────────

_ANSI_RE = re.compile(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def strip_ansi(s: str) -> str:
    return _ANSI_RE.sub('', s)

# ── PTY capture ───────────────────────────────────────────────────────────────

def run_and_capture(command: str, timeout: float = 120.0) -> Dict[str, Any]:
    """
    Run *command* in a PTY, capturing output events with real timestamps.
    Returns a session dict ready to be serialised as JSON.
    """
    events: List[Dict[str, Any]] = []

    # Emit the command itself as the first "input" event at t=0
    events.append({"t": 0.0, "type": "input", "text": command})

    master_fd, slave_fd = pty.openpty()
    proc = subprocess.Popen(
        command,
        shell=True,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        close_fds=True,
    )
    os.close(slave_fd)

    start = time.monotonic()
    buf = b""

    try:
        while True:
            elapsed = time.monotonic() - start
            if elapsed > timeout:
                proc.kill()
                break
            r, _, _ = select.select([master_fd], [], [], 0.05)
            if r:
                try:
                    chunk = os.read(master_fd, 4096)
                except OSError:
                    break
                if not chunk:
                    break
                buf += chunk
                try:
                    text = buf.decode("utf-8", errors="replace")
                    buf = b""
                except Exception:
                    continue
                clean = strip_ansi(text)
                if clean:
                    t = time.monotonic() - start
                    events.append({"t": round(t, 4), "type": "output", "text": clean})
            elif proc.poll() is not None:
                # Drain remaining output
                try:
                    while True:
                        r2, _, _ = select.select([master_fd], [], [], 0.1)
                        if not r2:
                            break
                        chunk = os.read(master_fd, 4096)
                        if not chunk:
                            break
                        text = chunk.decode("utf-8", errors="replace")
                        clean = strip_ansi(text)
                        if clean:
                            t2 = time.monotonic() - start
                            events.append({"t": round(t2, 4), "type": "output", "text": clean})
                except OSError:
                    pass
                break
    finally:
        os.close(master_fd)
        proc.wait()

    total_elapsed = round(time.monotonic() - start, 4)

    return {
        "version": 1,
        "title": None,          # filled in by caller
        "command": command,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "total_elapsed": total_elapsed,
        "events": events,
    }

# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="terminal-capture",
        description="Run a shell command and save the output as a JSON session file for terminal-player.js.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  terminal-capture "ls -lh" session.json
  terminal-capture "duckdb -c 'SELECT 42'" query.json --title "DuckDB query"
  terminal-capture "python3 script.py" out.json --timeout 60
        """,
    )
    parser.add_argument("command", help="Shell command to run")
    parser.add_argument("output",  help="Output .json path")
    parser.add_argument("--title",   default=None,
                        help="Title shown in the terminal header (default: the command)")
    parser.add_argument("--timeout", type=float, default=120.0,
                        help="Max seconds to wait for the command to finish (default: 120)")

    args = parser.parse_args()

    title = args.title or args.command
    print(f"Running: {args.command}")

    session = run_and_capture(args.command, timeout=args.timeout)
    session["title"] = title

    print(f"Captured {len(session['events'])} events in {session['total_elapsed']:.2f}s")

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(session, f, indent=2, ensure_ascii=False)

    size_kb = os.path.getsize(args.output) / 1024
    print(f"Saved → {args.output}  ({size_kb:.1f} KB)")

if __name__ == "__main__":
    main()
