#!/usr/bin/env python3
"""
terminal-gif — record a shell command and render it as an animated terminal GIF.

Usage:
    terminal-gif "command" output.gif [options]

The command is run in a real PTY so programs that detect a TTY behave normally.
Output is captured with real timestamps, then replayed as a polished animation
with a live timer pill and a long hold on the final frame.

Requirements:
    pip install pillow numpy

Example:
    terminal-gif "ls -lh" demo.gif --title "ls -lh" --final-hold 5
    terminal-gif "duckdb -c 'SELECT 42'" query.gif --width 900 --height 500
"""

import argparse
import os
import pty
import re
import select
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ── ANSI escape stripping ─────────────────────────────────────────────────────

_ANSI_RE = re.compile(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def strip_ansi(s: str) -> str:
    return _ANSI_RE.sub('', s)

# ── PTY capture ───────────────────────────────────────────────────────────────

@dataclass
class CaptureEvent:
    """A chunk of output captured at a specific elapsed time."""
    elapsed: float   # seconds since command started
    text: str        # raw text (ANSI stripped)

def run_and_capture(command: str, timeout: float = 120.0) -> Tuple[List[CaptureEvent], float]:
    """
    Run *command* in a PTY, capturing output chunks with real timestamps.
    Returns (events, total_elapsed).
    """
    events: List[CaptureEvent] = []
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
                # Decode what we can, keep incomplete sequences
                try:
                    text = buf.decode('utf-8', errors='replace')
                    buf = b""
                except Exception:
                    continue
                clean = strip_ansi(text)
                if clean:
                    events.append(CaptureEvent(elapsed=elapsed, text=clean))
            elif proc.poll() is not None:
                # Drain any remaining output
                try:
                    while True:
                        r2, _, _ = select.select([master_fd], [], [], 0.1)
                        if not r2:
                            break
                        chunk = os.read(master_fd, 4096)
                        if not chunk:
                            break
                        text = chunk.decode('utf-8', errors='replace')
                        clean = strip_ansi(text)
                        if clean:
                            elapsed2 = time.monotonic() - start
                            events.append(CaptureEvent(elapsed=elapsed2, text=clean))
                except OSError:
                    pass
                break
    finally:
        os.close(master_fd)
        proc.wait()

    total = time.monotonic() - start
    return events, total

# ── Text model ────────────────────────────────────────────────────────────────

def events_to_lines(events: List[CaptureEvent]) -> List[str]:
    """
    Merge all captured text into a list of lines (the final terminal state).
    Handles \\r\\n (treat as \\n), bare \\r (carriage-return overwrite), and \\n.
    """
    # Join all text first, then process character by character
    full_text = "".join(ev.text for ev in events)

    lines: List[str] = [""]
    i = 0
    while i < len(full_text):
        ch = full_text[i]
        if ch == '\r' and i + 1 < len(full_text) and full_text[i + 1] == '\n':
            # \r\n — treat as a normal newline
            lines.append("")
            i += 2
            continue
        if ch == '\n':
            lines.append("")
        elif ch == '\r':
            # bare \r — overwrite current line
            lines[-1] = ""
        elif ch == '\x08':  # backspace
            lines[-1] = lines[-1][:-1]
        elif ch >= ' ' or ch == '\t':
            lines[-1] += ch
        i += 1

    # Strip trailing empty lines
    while lines and not lines[-1].strip():
        lines.pop()
    return lines

def build_frames(
    command: str,
    events: List[CaptureEvent],
    total_elapsed: float,
    title: str,
    max_lines: int,
    timer_ticks: int,
    pause_before: float,
    pause_after_cmd: float,
    pause_final: float,
) -> List[Tuple[List[str], Optional[str], int]]:
    """
    Build a list of (lines_on_screen, timer_label, hold_ms) frames.

    Strategy:
      - Frame 0: empty terminal, pause_before ms
      - Frame 1: command prompt + command text, pause_after_cmd ms
      - Frames 2..N: timer ticking at ~1s intervals during execution
      - Frame N+1: full output, pause_final ms
    """
    frames: List[Tuple[List[str], Optional[str], int]] = []

    # Collect the final output lines
    all_lines = events_to_lines(events)

    # Frame 0: empty terminal
    frames.append(([], None, int(pause_before * 1000)))

    # Frame 1: show the prompt + command (before execution)
    prompt_lines = [f"❯ {command}"]
    frames.append((prompt_lines, None, int(pause_after_cmd * 1000)))

    # Timer ticking frames — evenly spaced between 0 and total_elapsed
    tick_interval = max(total_elapsed / max(timer_ticks, 1), 0.5)
    t = 0.0
    while t < total_elapsed - 0.1:
        label = f"⏱  {t:.1f} s"
        frames.append((prompt_lines, label, int(tick_interval * 1000)))
        t += tick_interval
    # Final tick at actual elapsed
    frames.append((prompt_lines, f"⏱  {total_elapsed:.1f} s", 400))

    # Final frame: prompt + command + output, long hold
    output_lines = prompt_lines + all_lines
    # Scroll: keep only the last max_lines lines
    if len(output_lines) > max_lines:
        output_lines = output_lines[-max_lines:]
    frames.append((output_lines, None, int(pause_final * 1000)))

    return frames

# ── Renderer ──────────────────────────────────────────────────────────────────

# Colour palette
BG          = (18,  18,  28)
HEADER_BG   = (28,  28,  44)
PROMPT_COL  = (80,  200, 120)
CMD_COL     = (220, 220, 220)
OUT_COL     = (180, 180, 200)
TIMER_COL   = (255, 220,  60)
COMMENT_COL = (110, 110, 155)
DIM_COL     = (80,   80, 100)

FONT_PATHS = [
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf",
]

def load_font(size: int) -> ImageFont.FreeTypeFont:
    for fp in FONT_PATHS:
        if os.path.exists(fp):
            return ImageFont.truetype(fp, size)
    return ImageFont.load_default()

def render_frame(
    lines: List[str],
    timer_str: Optional[str],
    title: str,
    W: int,
    H: int,
    font: ImageFont.FreeTypeFont,
    font_size: int,
) -> Image.Image:
    LINE_H   = int(font_size * 1.45)
    MARGIN_X = 40
    HEADER_H = 38
    TOP_Y    = HEADER_H + 10

    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Header bar
    draw.rectangle([0, 0, W, HEADER_H], fill=HEADER_BG)
    draw.text((MARGIN_X, (HEADER_H - font_size) // 2), title,
              font=font, fill=(160, 160, 200))

    # Lines
    y = TOP_Y
    for line in lines:
        if y + LINE_H > H - 10:
            break
        # Detect prompt lines (start with ❯)
        if line.startswith("❯ "):
            tw_prompt = int(font.getlength("❯ "))
            draw.text((MARGIN_X, y), "❯ ", font=font, fill=PROMPT_COL)
            draw.text((MARGIN_X + tw_prompt, y), line[2:], font=font, fill=CMD_COL)
        else:
            draw.text((MARGIN_X, y), line, font=font, fill=OUT_COL)
        y += LINE_H

    # Timer pill
    if timer_str:
        tw_t = int(font.getlength(timer_str))
        bx, by = MARGIN_X - 2, y + 2
        bw = tw_t + 16
        bh = font_size + 6
        draw.rectangle([bx, by, bx + bw, by + bh], fill=(40, 40, 12))
        draw.rectangle([bx, by, bx + bw, by + bh], outline=TIMER_COL, width=1)
        draw.text((bx + 8, by + 1), timer_str, font=font, fill=TIMER_COL)

    return img

def save_gif(
    frames: List[Tuple[List[str], Optional[str], int]],
    output_path: str,
    title: str,
    W: int,
    H: int,
    font_size: int,
    max_lines: int,
) -> None:
    font = load_font(font_size)
    LINE_H = int(font_size * 1.45)
    HEADER_H = 38
    visible = (H - HEADER_H - 20) // LINE_H

    pil_frames = []
    durations  = []

    for lines, timer_str, hold_ms in frames:
        # Scroll to last visible lines
        display = lines[-visible:] if len(lines) > visible else lines
        img = render_frame(display, timer_str, title, W, H, font, font_size)
        pil_frames.append(img)
        durations.append(hold_ms)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    print(f"Saving {len(pil_frames)} frames → {output_path}")
    pil_frames[0].save(
        output_path,
        format="GIF",
        save_all=True,
        append_images=pil_frames[1:],
        duration=durations,
        loop=0,
        optimize=False,
    )
    size_kb = os.path.getsize(output_path) / 1024
    total_s = sum(durations) / 1000
    print(f"Done!  {size_kb:.0f} KB  ·  {len(pil_frames)} frames  ·  {total_s:.1f}s total")

    # Verify
    v = Image.open(output_path)
    print(f"Verified frame durations:")
    for i in range(v.n_frames):
        v.seek(i)
        print(f"  frame {i:02d}: {v.info.get('duration', 0)} ms")

# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="terminal-gif",
        description="Run a shell command and render the output as an animated terminal GIF.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  terminal-gif "ls -lh" demo.gif
  terminal-gif "duckdb -c 'SELECT 42 AS answer'" query.gif --title "DuckDB query"
  terminal-gif "python3 script.py" out.gif --width 1200 --height 700 --final-hold 8
  terminal-gif "echo hello" test.gif --dry-run   # skip execution, use placeholder output
        """,
    )
    parser.add_argument("command",      help="Shell command to run")
    parser.add_argument("output",       help="Output GIF path")
    parser.add_argument("--title",      default=None,
                        help="Title shown in the terminal header bar (default: the command)")
    parser.add_argument("--width",      type=int, default=1100,
                        help="Canvas width in pixels (default: 1100)")
    parser.add_argument("--height",     type=int, default=660,
                        help="Canvas height in pixels (default: 660)")
    parser.add_argument("--font-size",  type=int, default=17,
                        help="Font size in points (default: 17)")
    parser.add_argument("--timer-ticks", type=int, default=8,
                        help="Number of timer tick frames during execution (default: 8)")
    parser.add_argument("--pause-before", type=float, default=1.0,
                        help="Seconds to hold on empty terminal before command (default: 1.0)")
    parser.add_argument("--pause-after-cmd", type=float, default=1.5,
                        help="Seconds to hold on command prompt before execution starts (default: 1.5)")
    parser.add_argument("--final-hold", type=float, default=10.0,
                        help="Seconds to hold on the final output frame (default: 10.0)")
    parser.add_argument("--timeout",    type=float, default=120.0,
                        help="Max seconds to wait for the command to finish (default: 120)")
    parser.add_argument("--max-lines",  type=int, default=30,
                        help="Max lines to keep on screen (scrolls older lines off, default: 30)")
    parser.add_argument("--dry-run",    action="store_true",
                        help="Skip execution; render a placeholder output frame for testing")

    args = parser.parse_args()

    title = args.title or args.command

    if args.dry_run:
        print("[dry-run] Skipping command execution")
        events = [CaptureEvent(elapsed=1.0, text="(dry-run output)\nDone.\n")]
        total_elapsed = 1.0
    else:
        print(f"Running: {args.command}")
        events, total_elapsed = run_and_capture(args.command, timeout=args.timeout)
        print(f"Captured {len(events)} chunks in {total_elapsed:.2f}s")

    frames = build_frames(
        command=args.command,
        events=events,
        total_elapsed=total_elapsed,
        title=title,
        max_lines=args.max_lines,
        timer_ticks=args.timer_ticks,
        pause_before=args.pause_before,
        pause_after_cmd=args.pause_after_cmd,
        pause_final=args.final_hold,
    )
    print(f"Built {len(frames)} frames  (total: {sum(f[2] for f in frames)/1000:.1f}s)")

    save_gif(
        frames=frames,
        output_path=args.output,
        title=title,
        W=args.width,
        H=args.height,
        font_size=args.font_size,
        max_lines=args.max_lines,
    )

if __name__ == "__main__":
    main()
