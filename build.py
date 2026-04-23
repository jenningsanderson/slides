#!/usr/bin/env python3
"""
build.py — Markdown slide builder for Reveal.js.

Discovers all .md (and .html) files in slides/ sorted alphabetically,
converts markdown to fully-rendered HTML, and writes a static index.html.
Replaces the Reveal.js markdown plugin entirely — output sections are
plain <section> elements with rendered HTML inside.

Usage:
    python3 build.py                          # build → index.html
    python3 build.py --output dist/index.html # custom output
    python3 build.py --validate-images        # check asset paths, exit 1 if missing
    python3 build.py --export-notes notes.txt # write speaker notes to file
    python3 build.py --outline                # print slide title outline and exit
    python3 build.py --lint                   # check for missing notes, alt text, etc.
    python3 build.py --base-url /repo/        # set <base href> for subdirectory deploys
    python3 build.py --watch                  # rebuild on file change
    python3 build.py --slides-dir custom/     # override slides directory
    python3 build.py --no-backup              # skip index.html.bak

Markdown conventions:
    ---            Horizontal rule on its own line = new vertical sub-slide.
                   Files with multiple --- separators become vertical stacks.
    Note:          Lines after this (on its own line) become <aside class="notes">.
    <!-- .slide: class="foo" data-bg="#123" -->
                   Reveal.js slide directive — applied as attributes on <section>.
    YAML front matter (--- key: val ---) also sets <section> attributes.
                   background-* keys are automatically prefixed with data-.
    markdown="1"   Add to HTML block elements to enable markdown processing inside.
"""

import argparse
import os
import re
import signal
import sys
import time
from pathlib import Path

try:
    import markdown as md_lib
except ImportError:
    sys.exit(
        "Error: 'markdown' package required.\n"
        "Install it with:  pip install markdown\n"
        "Or:               pip install -r requirements.txt"
    )

# ---------------------------------------------------------------------------
# HTML output template
# RevealMarkdown plugin is intentionally absent — Python renders all markdown.
# ---------------------------------------------------------------------------

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
{base_href}
  <!-- Reveal.js 5.1.0 (local) -->
  <link rel="stylesheet" href="vendor/reveal.js/dist/reset.css">
  <link rel="stylesheet" href="vendor/reveal.js/dist/reveal.css">
  <link rel="stylesheet" href="vendor/reveal.js/dist/theme/white.css">
  <link rel="stylesheet" href="vendor/highlight.js/github.min.css">

  <!-- Custom Overture theme -->
  <link rel="stylesheet" href="css/overture.css">
</head>
<body>
<div class="reveal">
  <div class="slides">
{slides_html}
  </div>
</div>

<!-- Reveal.js core + plugins (local) — RevealMarkdown intentionally excluded -->
<script src="vendor/reveal.js/dist/reveal.js"></script>
<script src="vendor/reveal.js/plugin/highlight/highlight.js"></script>
<script src="vendor/reveal.js/plugin/notes/notes.js"></script>
<script src="vendor/reveal.js/plugin/zoom/zoom.js"></script>

<script>
  Reveal.initialize({{
    hash: true,
    slideNumber: 'c/t',
    transition: 'slide',
    transitionSpeed: 'fast',
    backgroundTransition: 'fade',
    controls: true,
    progress: true,
    center: false,
    width: 1280,
    height: 720,
    margin: 0.04,
    viewDistance: 20,
    plugins: [ RevealHighlight, RevealNotes, RevealZoom ]
  }});
</script>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# Markdown renderer
# Extensions:
#   tables      — GFM pipe tables
#   fenced_code — ```lang blocks → <pre><code class="language-lang">
#   md_in_html  — markdown inside HTML elements that have markdown="1"
# ---------------------------------------------------------------------------

_RENDERER: md_lib.Markdown | None = None


def _make_renderer() -> md_lib.Markdown:
    return md_lib.Markdown(
        extensions=["tables", "fenced_code", "md_in_html"],
        extension_configs={"fenced_code": {"lang_prefix": "language-"}},
    )


def render_markdown(content: str) -> str:
    """Convert markdown content to HTML. Thread-unsafe but fine for single-process builds."""
    global _RENDERER
    if _RENDERER is None:
        _RENDERER = _make_renderer()
    _RENDERER.reset()
    return _RENDERER.convert(content)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

_SLIDE_DIRECTIVE_RE = re.compile(r"<!--\s*\.slide:\s*(.*?)\s*-->", re.DOTALL)
_ATTR_RE = re.compile(r'([\w-]+)=["\']([^"\']*)["\']')
# Matches a bare "Note:" on its own line (case-insensitive), preceded by a newline
_NOTE_RE = re.compile(r"\nNote:\s*\n", re.IGNORECASE)
# Matches <section ...> and </section> tags
_SECTION_TAG_RE = re.compile(r"<(/?)section(\s[^>]*)?>", re.IGNORECASE)


def extract_slide_directive(chunk: str) -> tuple[dict, str]:
    """
    Find and remove a <!-- .slide: key="val" --> comment from a chunk.
    Returns (attrs_dict, cleaned_chunk). attrs_dict is empty if none found.
    """
    match = _SLIDE_DIRECTIVE_RE.search(chunk)
    if not match:
        return {}, chunk
    attrs = dict(_ATTR_RE.findall(match.group(1)))
    cleaned = _SLIDE_DIRECTIVE_RE.sub("", chunk, count=1).strip()
    return attrs, cleaned


def extract_notes(chunk: str) -> tuple[str, str]:
    """
    Split a chunk on a bare 'Note:' line.
    Returns (main_content, notes_text). notes_text is empty string if absent.
    """
    parts = _NOTE_RE.split(chunk, maxsplit=1)
    if len(parts) == 2:
        return parts[0].rstrip(), parts[1].strip()
    return chunk.rstrip(), ""


def extract_yaml_front_matter(content: str) -> tuple[dict, str]:
    """
    Parse minimal YAML front matter (simple key: value pairs, no nesting).

    Format:
        ---
        class: dark
        background: "#123"
        ---

    Returns (meta_dict, remaining_content). Supports string values only.
    Note: distinct from <!-- .slide: ... --> — both are applied to the <section>.
    """
    lines = content.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, content

    end_idx: int | None = None
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        return {}, content

    meta: dict[str, str] = {}
    for line in lines[1:end_idx]:
        if ":" in line:
            key, _, val = line.partition(":")
            meta[key.strip()] = val.strip().strip("\"'")

    return meta, "\n".join(lines[end_idx + 1 :])


def split_on_hr(content: str) -> list[str]:
    """
    Split markdown on bare '---' lines into chunks (vertical sub-slides).

    Skips '---' lines that appear inside fenced code blocks (``` or ~~~).
    Markdown table header separator rows (|---|---| patterns) are safe because
    they contain pipe characters and will not match the bare '---' pattern.

    Returns list of non-empty stripped chunks.
    """
    lines = content.split("\n")
    chunks: list[list[str]] = []
    current: list[str] = []
    in_fence = False
    fence_char: str | None = None

    for line in lines:
        stripped = line.strip()

        # Track fenced code block entry/exit
        if stripped.startswith("```") or stripped.startswith("~~~"):
            opener = stripped[:3]
            if not in_fence:
                in_fence = True
                fence_char = opener
            elif fence_char and stripped.startswith(fence_char) and stripped.strip("`~") == "":
                in_fence = False
                fence_char = None

        if not in_fence and stripped == "---":
            chunks.append(current)
            current = []
        else:
            current.append(line)

    chunks.append(current)
    return ["\n".join(c).strip() for c in chunks if any(ln.strip() for ln in c)]


def html_file_to_sections(html_content: str) -> list[str]:
    """
    Extract top-level <section>...</section> blocks from an HTML file.
    Uses depth tracking to handle balanced tags.
    Returns list of raw HTML strings — one per section element.
    """
    sections: list[str] = []
    depth = 0
    start = 0

    for match in _SECTION_TAG_RE.finditer(html_content):
        is_closing = bool(match.group(1))
        if not is_closing:
            if depth == 0:
                start = match.start()
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                sections.append(html_content[start : match.end()])

    return sections


# ---------------------------------------------------------------------------
# Section construction
# ---------------------------------------------------------------------------

# Reveal.js background attribute shorthands: background-* → data-background-*
_BG_SHORTCUTS = frozenset({
    "background", "background-color", "background-image", "background-size",
    "background-position", "background-repeat", "background-opacity",
    "background-transition", "background-video", "background-video-loop",
    "background-video-muted", "background-iframe",
})


def _build_open_tag(attrs: dict) -> str:
    if not attrs:
        return "<section>"
    parts = ["<section"]
    for k, v in attrs.items():
        if k in _BG_SHORTCUTS:
            k = "data-" + k
        parts.append(f' {k}="{v}"')
    parts.append(">")
    return "".join(parts)


def wrap_section(html_content: str, attrs: dict, notes_text: str) -> str:
    """Assemble a <section> element from rendered HTML, attributes, and optional notes."""
    open_tag = _build_open_tag(attrs)
    notes_block = (
        f'\n<aside class="notes">\n{notes_text}\n</aside>' if notes_text.strip() else ""
    )
    return f"{open_tag}\n{html_content}{notes_block}\n</section>"


def process_md_chunk(chunk: str) -> str:
    """
    Process one markdown chunk (a single slide's worth of content) into
    a rendered <section> HTML string.

    Processing order:
      1. YAML front matter  → section attributes
      2. <!-- .slide: -->   → section attributes (overrides front matter)
      3. Note: separator    → <aside class="notes">
      4. render_markdown()  → HTML body
    """
    fm_attrs, chunk = extract_yaml_front_matter(chunk)
    slide_attrs, chunk = extract_slide_directive(chunk)

    # slide directive takes precedence over front matter
    attrs = {**fm_attrs, **slide_attrs}

    content, notes = extract_notes(chunk)
    html = render_markdown(content)

    return wrap_section(html, attrs, notes)


def process_md_file(path: Path) -> str:
    """
    Process a .md file into the HTML fragment for one presentation entry.

    - Single chunk (no --- separators)  → single <section>
    - Multiple chunks                   → outer <section> wrapping sub-<section>s
                                          (vertical slide stack)
    """
    content = path.read_text(encoding="utf-8")
    chunks = split_on_hr(content)

    if len(chunks) == 1:
        return process_md_chunk(chunks[0])

    sub_sections = "\n".join(process_md_chunk(c) for c in chunks)
    return f"<section>\n{sub_sections}\n</section>"


def process_html_file(path: Path) -> str:
    """
    Process a legacy .html slide file (backward compatibility).
    Extracts <section> elements. Multiple sections become a vertical stack.
    HTML content is not processed through the markdown renderer.
    """
    content = path.read_text(encoding="utf-8")
    sections = html_file_to_sections(content)

    if not sections:
        return f"<section><p>⚠ Empty slide: {path.name}</p></section>"
    if len(sections) == 1:
        return sections[0]

    return "<section>\n" + "\n".join(sections) + "\n</section>"


# ---------------------------------------------------------------------------
# Slide discovery
# ---------------------------------------------------------------------------


def discover_slides(slides_dir: str) -> list[Path]:
    """
    Return all .md and .html files in slides_dir sorted by filename.
    Numeric prefixes (01-, 02-, ...) in filenames control presentation order.
    """
    d = Path(slides_dir)
    if not d.is_dir():
        sys.exit(f"Error: slides directory '{slides_dir}' not found.")
    return sorted(
        [p for p in d.iterdir() if p.suffix in (".md", ".html")],
        key=lambda p: p.name,
    )


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------


def render_index_html(
    slide_sections: list[str],
    title: str = "Slides",
    base_url: str = "",
) -> str:
    slides_html = "\n".join(slide_sections)
    base_href = f'  <base href="{base_url}">' if base_url else ""
    return HTML_TEMPLATE.format(title=title, base_href=base_href, slides_html=slides_html)


# ---------------------------------------------------------------------------
# Image validation
# ---------------------------------------------------------------------------


def validate_images(html: str, project_root: str) -> list[str]:
    """
    Find all local src="..." and href="..." paths in html and verify they
    exist on disk relative to project_root. Skips http(s), data:, and
    vendor/css paths.
    """
    missing: list[str] = []
    skip_prefixes = ("http://", "https://", "data:", "#", "vendor/", "css/")
    for match in re.finditer(r'(?:src|href)=["\']([^"\']+)["\']', html):
        path = match.group(1)
        if any(path.startswith(p) for p in skip_prefixes):
            continue
        if not os.path.exists(os.path.join(project_root, path)):
            missing.append(path)
    return sorted(set(missing))


# ---------------------------------------------------------------------------
# Speaker notes export
# ---------------------------------------------------------------------------


def collect_notes(slide_sections: list[str]) -> str:
    """
    Extract all <aside class="notes"> content from rendered sections.
    Returns plain text with slide-number headers.
    """
    notes_re = re.compile(r'<aside\s+class="notes">(.*?)</aside>', re.DOTALL)
    lines: list[str] = []
    slide_num = 0

    for section in slide_sections:
        for match in notes_re.finditer(section):
            slide_num += 1
            text = re.sub(r"<[^>]+>", "", match.group(1)).strip()
            if text:
                lines.append(f"--- Slide {slide_num} ---")
                lines.append(text)
                lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Outline
# ---------------------------------------------------------------------------

_H_MD_RE = re.compile(r"^#{1,4}\s+(.+?)$", re.MULTILINE)
_H_TAG_RE = re.compile(r"<h[1-4][^>]*>(.*?)</h[1-4]>", re.DOTALL)


def _first_heading(text: str, is_html: bool = False) -> str:
    """Extract the first heading from markdown or HTML content."""
    if is_html:
        m = _H_TAG_RE.search(text)
        return re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else "—"
    m = _H_MD_RE.search(text)
    return m.group(1).strip() if m else "(untitled)"


def print_outline(slides_dir: str) -> None:
    """Print a numbered presentation outline to stdout."""
    slide_files = discover_slides(slides_dir)
    print(f"\nSlide outline — {len(slide_files)} files in '{slides_dir}/'\n")
    horiz = 0
    for path in slide_files:
        content = path.read_text(encoding="utf-8")
        if path.suffix == ".html":
            sections = html_file_to_sections(content)
            horiz += 1
            title = _first_heading(sections[0] if sections else content, is_html=True)
            suffix = f"  [{len(sections)} vertical sub-slides]" if len(sections) > 1 else ""
            print(f"  {horiz:2d}. {title}{suffix}")
        else:
            chunks = split_on_hr(content)
            for i, chunk in enumerate(chunks):
                _, c = extract_yaml_front_matter(chunk)
                _, c = extract_slide_directive(c)
                c, _ = extract_notes(c)
                title = _first_heading(c)
                if i == 0:
                    horiz += 1
                    suffix = f"  [{len(chunks)} vertical sub-slides]" if len(chunks) > 1 else ""
                    print(f"  {horiz:2d}. {title}{suffix}")
    print()


# ---------------------------------------------------------------------------
# Lint
# ---------------------------------------------------------------------------

_IMG_TAG_RE = re.compile(r"<img(\s[^>]*)?>", re.IGNORECASE)
_ALT_ATTR_RE = re.compile(r'\balt=["\'][^"\']*["\']', re.IGNORECASE)
_SRC_ATTR_RE = re.compile(r'\bsrc=["\']([^"\']+)["\']', re.IGNORECASE)
_ASIDE_RE = re.compile(r'<aside\s+class="notes">', re.IGNORECASE)


def lint_slides(slides_dir: str, project_root: str) -> list[str]:
    """
    Check slides for common issues. Returns list of warning strings.

    Checks:
      - Missing speaker notes (Note: / <aside class="notes">)
      - <img> tags missing alt attribute
      - Broken local asset paths (src="assets/...")
    """
    issues: list[str] = []
    slide_files = discover_slides(slides_dir)
    skip_src = ("http://", "https://", "data:", "#", "vendor/", "css/")

    for path in slide_files:
        content = path.read_text(encoding="utf-8")

        if path.suffix == ".html":
            sections = html_file_to_sections(content) or [content]
            for i, sec in enumerate(sections):
                loc = f"{path.name}" if len(sections) == 1 else f"{path.name}:{i + 1}"
                if not _ASIDE_RE.search(sec):
                    issues.append(f"no speaker notes — {loc}")
                for img in _IMG_TAG_RE.finditer(sec):
                    tag = img.group(0)
                    if not _ALT_ATTR_RE.search(tag):
                        src = (_SRC_ATTR_RE.search(tag) or type("", (), {"group": lambda s, n: "?"})()).group(1)
                        issues.append(f"<img> missing alt text (src={src}) — {loc}")
        else:
            chunks = split_on_hr(content)
            for i, chunk in enumerate(chunks):
                loc = path.name if len(chunks) == 1 else f"{path.name}:{i + 1}"
                _, body = extract_notes(chunk)
                if not body.strip():
                    issues.append(f"no speaker notes — {loc}")
                for img in _IMG_TAG_RE.finditer(chunk):
                    tag = img.group(0)
                    if not _ALT_ATTR_RE.search(tag):
                        m = _SRC_ATTR_RE.search(tag)
                        src = m.group(1) if m else "?"
                        issues.append(f"<img> missing alt text (src={src}) — {loc}")
                for m in _SRC_ATTR_RE.finditer(chunk):
                    src = m.group(1)
                    if any(src.startswith(p) for p in skip_src):
                        continue
                    if not os.path.exists(os.path.join(project_root, src)):
                        issues.append(f"broken asset path '{src}' — {loc}")

    return issues


# ---------------------------------------------------------------------------
# Core build
# ---------------------------------------------------------------------------


def _build_sections(slides_dir: str) -> list[str]:
    """Discover slides and render each to an HTML string."""
    slide_files = discover_slides(slides_dir)
    if not slide_files:
        sys.exit(f"No slide files found in '{slides_dir}/'")

    sections: list[str] = []
    for slide_path in slide_files:
        try:
            if slide_path.suffix == ".html":
                sections.append(process_html_file(slide_path))
            else:
                sections.append(process_md_file(slide_path))
        except Exception as exc:
            print(f"  Error in {slide_path.name}: {exc}", file=sys.stderr)
            raise
    return sections


def run_build(
    slides_dir: str,
    output: str,
    project_root: str,
    no_backup: bool,
    base_url: str = "",
    verbose: bool = True,
) -> list[str]:
    """Full build pipeline: discover → render → write index.html. Returns sections list."""
    slide_files = discover_slides(slides_dir)
    if verbose:
        print(f"Building {len(slide_files)} slides from '{slides_dir}/'...")

    sections = _build_sections(slides_dir)
    output_html = render_index_html(sections, base_url=base_url)
    output_path = Path(output)

    if not no_backup and output_path.exists():
        backup = output_path.with_suffix(".html.bak")
        backup.write_text(output_path.read_text(encoding="utf-8"), encoding="utf-8")

    output_path.write_text(output_html, encoding="utf-8")

    if verbose:
        size_kb = output_path.stat().st_size // 1024
        print(f"  Written: {output_path} ({size_kb} KB, {len(sections)} slides)")

    return sections


# ---------------------------------------------------------------------------
# Watch mode
# ---------------------------------------------------------------------------


def watch_mode(slides_dir: str, output: str, project_root: str, no_backup: bool) -> None:
    """Poll slide files and CSS for changes; rebuild on any modification."""
    stop = [False]
    signal.signal(signal.SIGINT, lambda s, f: stop.__setitem__(0, True))

    def watched_files() -> list[Path]:
        files = discover_slides(slides_dir)
        css_files = list(Path(project_root, "css").glob("*.css"))
        return files + css_files

    def snapshot(files: list[Path]) -> dict[str, float | None]:
        result: dict[str, float | None] = {}
        for f in files:
            try:
                result[str(f)] = os.stat(f).st_mtime
            except OSError:
                result[str(f)] = None
        return result

    print("Watching for changes. Press Ctrl-C to stop.\n")
    run_build(slides_dir, output, project_root, no_backup)
    mtimes = snapshot(watched_files())

    while not stop[0]:
        time.sleep(0.5)
        current = snapshot(watched_files())
        changed = [f for f in current if current[f] != mtimes.get(f)]
        if changed:
            ts = time.strftime("%H:%M:%S")
            names = ", ".join(Path(f).name for f in changed)
            print(f"[{ts}] Changed: {names}")
            run_build(slides_dir, output, project_root, no_backup, verbose=False)
            print(f"[{ts}] Rebuilt → {output}")
            mtimes = snapshot(watched_files())

    print("\nStopped.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build Reveal.js index.html from markdown slide files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  python3 build.py                           # standard build
  python3 build.py --watch                   # rebuild on file change
  python3 build.py --outline                 # print slide title outline
  python3 build.py --lint                    # check for missing notes, alt text
  python3 build.py --validate-images         # check all asset paths exist
  python3 build.py --export-notes notes.txt  # export speaker notes
  python3 build.py --base-url /overture-sandbox/  # set <base href> for subdirectory deploy
  python3 build.py --output dist/index.html  # custom output path
        """,
    )
    p.add_argument(
        "--slides-dir",
        default="slides",
        metavar="DIR",
        help="directory containing slide files (default: slides)",
    )
    p.add_argument(
        "--output",
        default="index.html",
        metavar="PATH",
        help="output HTML file (default: index.html)",
    )
    p.add_argument(
        "--outline",
        action="store_true",
        help="print a numbered slide outline and exit (no build)",
    )
    p.add_argument(
        "--lint",
        action="store_true",
        help="check slides for missing notes, alt text, and broken paths; exit 1 if issues found",
    )
    p.add_argument(
        "--validate-images",
        action="store_true",
        help="check that all asset paths exist in the built HTML, exit 1 if any are missing",
    )
    p.add_argument(
        "--export-notes",
        metavar="PATH",
        help="write speaker notes to a plain text file",
    )
    p.add_argument(
        "--base-url",
        default="",
        metavar="URL",
        help="set <base href> for subdirectory deploys (e.g. /overture-sandbox/)",
    )
    p.add_argument(
        "--watch",
        action="store_true",
        help="watch slide files for changes and rebuild automatically",
    )
    p.add_argument(
        "--title",
        default="",
        metavar="TEXT",
        help="presentation title shown in the browser tab (default: 'Slides')",
    )
    p.add_argument(
        "--no-backup",
        action="store_true",
        help="do not write index.html.bak before overwriting",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    project_root = os.getcwd()

    if args.outline:
        print_outline(args.slides_dir)
        return

    if args.lint:
        issues = lint_slides(args.slides_dir, project_root)
        if issues:
            print(f"Found {len(issues)} issue(s):\n")
            for issue in issues:
                print(f"  {issue}")
            print()
            sys.exit(1)
        slide_files = discover_slides(args.slides_dir)
        print(f"No issues found ({len(slide_files)} slides checked).")
        return

    if args.watch:
        watch_mode(args.slides_dir, args.output, project_root, args.no_backup)
        return

    sections = _build_sections(args.slides_dir)

    if args.validate_images:
        all_html = "\n".join(sections)
        missing = validate_images(all_html, project_root)
        if missing:
            print(f"Missing {len(missing)} asset(s):")
            for m in missing:
                print(f"  {m}")
            sys.exit(1)
        print(f"All assets found ({len(sections)} slides checked).")
        return

    slide_files = discover_slides(args.slides_dir)
    print(f"Building {len(slide_files)} slides from '{args.slides_dir}/'...")

    title = args.title or "Slides"
    output_html = render_index_html(sections, title=title, base_url=args.base_url)
    output_path = Path(args.output)

    if not args.no_backup and output_path.exists():
        backup = output_path.with_suffix(".html.bak")
        backup.write_text(output_path.read_text(encoding="utf-8"), encoding="utf-8")

    output_path.write_text(output_html, encoding="utf-8")
    size_kb = output_path.stat().st_size // 1024
    print(f"  Written: {output_path} ({size_kb} KB, {len(sections)} slides)")

    if args.export_notes:
        notes = collect_notes(sections)
        Path(args.export_notes).write_text(notes, encoding="utf-8")
        print(f"  Notes:   {args.export_notes}")


if __name__ == "__main__":
    main()
