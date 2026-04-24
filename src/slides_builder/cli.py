"""
Unified CLI entry point for slides-builder.

Usage:
    slides build    [--slides-dir DIR] [--output PATH] [--title TEXT]
                    [--base-url URL] [--no-backup] [--export-notes PATH]
                    [--validate-images]
    slides serve    [--slides-dir DIR] [--output PATH] [--port PORT]
                    [--title TEXT] [--base-url URL] [--no-open]
    slides outline  [--slides-dir DIR]
    slides lint     [--slides-dir DIR]
    slides watch    [--slides-dir DIR] [--output PATH] [--title TEXT]
                    [--base-url URL] [--no-backup]
    slides capture  COMMAND output.json [--title TEXT] [--timeout SEC]
    slides gif      COMMAND output.gif  [--title TEXT] [--width PX]
                    [--height PX] [--font-size PT] [--final-hold SEC]
                    [--timeout SEC] [--max-lines N] [--dry-run]
"""

import argparse
import os
import sys


# ---------------------------------------------------------------------------
# Sub-command handlers
# ---------------------------------------------------------------------------

def _cmd_build(args: argparse.Namespace) -> None:
    from slides_builder import build as b

    project_root = os.getcwd()

    sections = b._build_sections(args.slides_dir)

    if args.validate_images:
        all_html = "\n".join(sections)
        missing = b.validate_images(all_html, project_root)
        if missing:
            print(f"Missing {len(missing)} asset(s):")
            for m in missing:
                print(f"  {m}")
            sys.exit(1)
        print(f"All assets found ({len(sections)} slides checked).")
        return

    title = args.title or "Slides"
    output_html = b.render_index_html(sections, title=title, base_url=args.base_url)

    from pathlib import Path
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not args.no_backup and output_path.exists():
        backup = output_path.with_suffix(".html.bak")
        backup.write_text(output_path.read_text(encoding="utf-8"), encoding="utf-8")

    output_path.write_text(output_html, encoding="utf-8")
    size_kb = output_path.stat().st_size // 1024
    slide_files = b.discover_slides(args.slides_dir)
    print(f"Built {len(slide_files)} slides → {output_path} ({size_kb} KB)")

    if args.export_notes:
        notes = b.collect_notes(sections)
        Path(args.export_notes).write_text(notes, encoding="utf-8")
        print(f"  Notes: {args.export_notes}")


def _cmd_serve(args: argparse.Namespace) -> None:
    from slides_builder.serve import run_server
    run_server(
        slides_dir=args.slides_dir,
        output=args.output,
        port=args.port,
        no_open=args.no_open,
        title=args.title or "Slides",
        base_url=args.base_url,
    )


def _cmd_outline(args: argparse.Namespace) -> None:
    from slides_builder import build as b
    b.print_outline(args.slides_dir)


def _cmd_lint(args: argparse.Namespace) -> None:
    from slides_builder import build as b
    project_root = os.getcwd()
    issues = b.lint_slides(args.slides_dir, project_root)
    if issues:
        print(f"Found {len(issues)} issue(s):\n")
        for issue in issues:
            print(f"  {issue}")
        print()
        sys.exit(1)
    slide_files = b.discover_slides(args.slides_dir)
    print(f"No issues found ({len(slide_files)} slides checked).")


def _cmd_watch(args: argparse.Namespace) -> None:
    from slides_builder import build as b
    project_root = os.getcwd()
    b.watch_mode(
        slides_dir=args.slides_dir,
        output=args.output,
        project_root=project_root,
        no_backup=args.no_backup,
        title=args.title or "Slides",
        base_url=args.base_url,
    )


def _cmd_capture(args: argparse.Namespace) -> None:
    try:
        from slides_builder.tools.terminal_capture import run_and_capture
    except ImportError as e:
        sys.exit(
            f"Import error: {e}\n"
            "The 'capture' command has no extra requirements beyond the standard library."
        )
    import json

    title = args.title or args.command
    print(f"Running: {args.command}")
    session = run_and_capture(args.command, timeout=args.timeout)
    session["title"] = title

    print(f"Captured {len(session['events'])} events in {session['total_elapsed']:.2f}s")

    import os as _os
    _os.makedirs(_os.path.dirname(_os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(session, f, indent=2, ensure_ascii=False)

    size_kb = _os.path.getsize(args.output) / 1024
    print(f"Saved → {args.output}  ({size_kb:.1f} KB)")


def _cmd_gif(args: argparse.Namespace) -> None:
    try:
        from slides_builder.tools.terminal_gif import run_and_capture, build_frames, save_gif
    except ImportError:
        sys.exit(
            "Error: 'slides gif' requires extra dependencies (Pillow, numpy).\n"
            "Install with: uv sync --extra terminal"
        )

    title = args.title or args.command

    if args.dry_run:
        from slides_builder.tools.terminal_gif import CaptureEvent
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


# ---------------------------------------------------------------------------
# Shared argument groups
# ---------------------------------------------------------------------------

def _add_slides_dir(p: argparse.ArgumentParser, default: str = "slides") -> None:
    p.add_argument(
        "--slides-dir", default=default, metavar="DIR",
        help=f"directory containing slide files (default: {default})",
    )


def _add_output(p: argparse.ArgumentParser, default: str = "index.html") -> None:
    p.add_argument(
        "--output", default=default, metavar="PATH",
        help=f"output HTML file (default: {default})",
    )


def _add_title(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--title", default="", metavar="TEXT",
        help="presentation title shown in the browser tab (default: Slides)",
    )


def _add_base_url(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--base-url", default="", metavar="URL",
        help="set <base href> for subdirectory deploys (e.g. /my-repo/)",
    )


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="slides",
        description="Build and serve Reveal.js presentations from Markdown.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
commands:
  build    Render slides to index.html
  serve    Live-reload dev server (default: http://localhost:3000)
  outline  Print a numbered slide outline
  lint     Check for missing notes, alt text, and broken paths
  watch    Rebuild automatically on file changes
  capture  Record a shell command to a JSON session file
  gif      Record a shell command and render an animated GIF

examples:
  slides build
  slides build --title "My Talk" --output dist/index.html
  slides serve --port 8080
  slides outline
  slides lint
  slides watch
  slides capture "ls -lh" assets/demo.json --title "ls demo"
  slides gif "python3 demo.py" assets/demo.gif --final-hold 10
        """,
    )

    sub = root.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    # ── build ────────────────────────────────────────────────────────────────
    bp = sub.add_parser("build", help="render slides to index.html")
    _add_slides_dir(bp)
    _add_output(bp)
    _add_title(bp)
    _add_base_url(bp)
    bp.add_argument("--no-backup", action="store_true",
                    help="do not write index.html.bak before overwriting")
    bp.add_argument("--validate-images", action="store_true",
                    help="check that all asset paths exist, exit 1 if any are missing")
    bp.add_argument("--export-notes", metavar="PATH",
                    help="write speaker notes to a plain text file")
    bp.set_defaults(func=_cmd_build)

    # ── serve ────────────────────────────────────────────────────────────────
    sp = sub.add_parser("serve", help="live-reload dev server")
    _add_slides_dir(sp)
    _add_output(sp)
    _add_title(sp)
    _add_base_url(sp)
    sp.add_argument("--port", type=int, default=3000,
                    help="port to listen on (default: 3000)")
    sp.add_argument("--no-open", action="store_true",
                    help="do not open the browser automatically")
    sp.set_defaults(func=_cmd_serve)

    # ── outline ──────────────────────────────────────────────────────────────
    op = sub.add_parser("outline", help="print a numbered slide outline")
    _add_slides_dir(op)
    op.set_defaults(func=_cmd_outline)

    # ── lint ─────────────────────────────────────────────────────────────────
    lp = sub.add_parser("lint", help="check slides for common issues")
    _add_slides_dir(lp)
    lp.set_defaults(func=_cmd_lint)

    # ── watch ────────────────────────────────────────────────────────────────
    wp = sub.add_parser("watch", help="rebuild automatically on file changes")
    _add_slides_dir(wp)
    _add_output(wp)
    _add_title(wp)
    _add_base_url(wp)
    wp.add_argument("--no-backup", action="store_true",
                    help="do not write index.html.bak before overwriting")
    wp.set_defaults(func=_cmd_watch)

    # ── capture ──────────────────────────────────────────────────────────────
    cp = sub.add_parser(
        "capture",
        help="record a shell command to a JSON session file (for terminal-player.js)",
    )
    cp.add_argument("command", help="shell command to run")
    cp.add_argument("output", help="output .json path")
    cp.add_argument("--title", default=None,
                    help="title shown in the terminal header (default: the command)")
    cp.add_argument("--timeout", type=float, default=120.0,
                    help="max seconds to wait for the command (default: 120)")
    cp.set_defaults(func=_cmd_capture)

    # ── gif ──────────────────────────────────────────────────────────────────
    gp = sub.add_parser(
        "gif",
        help="record a shell command and render an animated GIF (requires --extra terminal)",
    )
    gp.add_argument("command", help="shell command to run")
    gp.add_argument("output", help="output .gif path")
    gp.add_argument("--title", default=None,
                    help="title in the terminal header bar (default: the command)")
    gp.add_argument("--width", type=int, default=1100,
                    help="canvas width in pixels (default: 1100)")
    gp.add_argument("--height", type=int, default=660,
                    help="canvas height in pixels (default: 660)")
    gp.add_argument("--font-size", type=int, default=17,
                    help="font size in points (default: 17)")
    gp.add_argument("--timer-ticks", type=int, default=8,
                    help="number of timer tick frames during execution (default: 8)")
    gp.add_argument("--pause-before", type=float, default=1.0,
                    help="seconds to hold on empty terminal before command (default: 1.0)")
    gp.add_argument("--pause-after-cmd", type=float, default=1.5,
                    help="seconds to hold on the prompt before execution (default: 1.5)")
    gp.add_argument("--final-hold", type=float, default=10.0,
                    help="seconds to hold on the final output frame (default: 10.0)")
    gp.add_argument("--timeout", type=float, default=120.0,
                    help="max seconds to wait for the command (default: 120)")
    gp.add_argument("--max-lines", type=int, default=30,
                    help="max lines to keep on screen (default: 30)")
    gp.add_argument("--dry-run", action="store_true",
                    help="skip execution; render a placeholder frame for layout testing")
    gp.set_defaults(func=_cmd_gif)

    return root


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
