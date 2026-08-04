# AGENTS.md — slides-builder technical reference

This file is the single source of truth for any agent or developer working on this
repository. Read it before modifying code, adding features, or authoring slides.

---

## What this repo is

`slides-builder` is a **GitHub Action + local CLI** that converts a folder of Markdown
files into a fully static [Reveal.js](https://revealjs.com) presentation. All Markdown
is rendered to HTML by Python before the browser loads anything — the Reveal.js Markdown
plugin is intentionally excluded. The result is a self-contained `index.html` with no
runtime dependencies on a CDN or parser.

The action is designed to be used by any repo: add a `slides/` folder, reference
`jenningsanderson/slides@main`, and GitHub Pages will host the result.

---

## Repository layout

```
slides-builder/
├── src/slides_builder/         ← installable Python package
│   ├── __init__.py
│   ├── build.py                ← core build logic (no CLI)
│   ├── serve.py                ← live-reload dev server
│   ├── cli.py                  ← unified entry point: `slides <command>`
│   ├── config.py               ← config.yaml loader and resolver
│   └── tools/
│       ├── terminal_capture.py ← `slides capture` implementation
│       └── terminal_gif.py     ← `slides gif` implementation (needs Pillow + numpy)
├── tools/terminal-gif/
│   ├── AGENTS.md               ← terminal-gif-specific agent instructions
│   └── examples/               ← example .json, .gif, .html
├── slides/                     ← example presentation (Markdown source)
│   ├── config.yaml             ← project config (title, output, css_dir, etc.)
│   ├── css/
│   │   └── default.css         ← built-in Reveal.js theme overrides
│   ├── 01-title.md
│   └── ...
├── assets/                     ← images and JSON sessions for the demo presentation
│   ├── gers-demo.json          ← captured terminal session
│   └── gers-demo.gif           ← animated GIF fallback
├── js/                         ← browser-side scripts authored in this repo
│   └── terminal-player.js      ← single canonical copy; edit only here
├── demos/                      ← scripted demo scripts for terminal capture
│   └── gers_demo.py
├── vendor/                     ← vendored third-party libraries (Reveal.js, highlight.js)
├── .github/workflows/
│   ├── ci.yml                  ← build + outline + validate on push
│   └── demo-pages.yml          ← deploys slides/ to GitHub Pages as live demo
├── action.yml                  ← GitHub Action definition
├── pyproject.toml              ← package config, entry point, optional deps
└── uv.lock
```

---

## Setup and CLI

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync          # installs slides-builder + markdown + pillow + numpy into .venv
uv run slides    # entry point
```

All commands:

```
slides build    [--slides-dir DIR] [--output PATH] [--title TEXT]
                [--base-url URL] [--no-backup]
                [--validate-images] [--export-notes PATH]

slides serve    [--slides-dir DIR] [--output PATH] [--port PORT]
                [--title TEXT] [--base-url URL] [--no-open]

slides outline  [--slides-dir DIR]
slides lint     [--slides-dir DIR]

slides watch    [--slides-dir DIR] [--output PATH] [--title TEXT]
                [--base-url URL] [--no-backup]

slides capture  COMMAND output.json [--title TEXT] [--timeout SEC]

slides gif      COMMAND output.gif  [--title TEXT] [--width PX] [--height PX]
                [--font-size PT] [--timer-ticks N] [--pause-before SEC]
                [--pause-after-cmd SEC] [--final-hold SEC]
                [--timeout SEC] [--max-lines N] [--dry-run]

slides publish  [--slides-dir DIR] [--output-dir DIR]
                [--provider pages|s3]
                [--bucket BUCKET] [--prefix PREFIX]
                [--dry-run]
```

**Defaults:**
- `--slides-dir` → `slides`
- `--output` → `index.html` (overridden by config.yaml)
- `--port` → `3000` (overridden by config.yaml `serve.port`)
- `--final-hold` → `10.0` (seconds)
- `--width` / `--height` → `1100` / `660`
- `--font-size` → `17`

CLI flags always take precedence over `config.yaml`.

---

## config.yaml

Each project's settings live in `<slides-dir>/config.yaml` (e.g. `slides/config.yaml`).
The file is optional — all keys have sensible defaults.

```yaml
# slides/config.yaml

title: My Presentation
# base_url: /my-repo/        # only needed for GitHub Pages project sites

output: index.html            # where to write the built HTML

# CSS: default is slides/css/ (alongside your slide files)
# css_dir: slides/css

# Assets: default is assets/ at the repo root
# assets_dir: assets

serve:
  port: 3000
  no_open: false

# Deploy / publish settings (optional — defaults to GitHub Pages)
deploy:
  provider: pages         # pages | s3  (default: pages)
  path_prefix: ""         # optional; provider-agnostic base path

  s3:
    bucket: slides.jenningsanderson.com
    region: us-east-1
    prefix: ""            # optional; defaults to <owner>/<repo> from GITHUB_REPOSITORY
    cloudfront_distribution_id: ""
    cache_control_html: "no-cache"
    cache_control_assets: "public,max-age=31536000,immutable"
```

**Resolution order** (highest to lowest priority):
1. CLI flag (e.g. `--title "..."`)
2. `config.yaml` value
3. Built-in default

**CSS resolution order** (both locally and in the action):
1. `<slides-dir>/css/` (new default — lives alongside slide files)
2. `css/` at the repo root (legacy fallback)
3. Built-in `slides/css/default.css` from the action itself

The `config.py` module handles loading and resolution. Key functions:
- `config.load(slides_dir)` → returns the parsed dict (empty dict if no config.yaml)
- `config.resolve(cfg, key, cli_value, default)` → applies the priority chain
- `config.get_deploy_config(cfg)` → returns resolved `deploy` sub-dict with defaults
- `config.validate_deploy_config(deploy)` → returns list of error strings (empty = valid)

---

## Python package architecture

### `src/slides_builder/build.py`

Pure build logic — no argparse, no side effects beyond writing files when `run_build()` is called.

Key public functions:

| Function | Purpose |
|---|---|
| `discover_slides(slides_dir)` | Returns sorted list of `.md` / `.html` `Path` objects |
| `render_markdown(content)` | Markdown → HTML string (thread-unsafe, single-process only) |
| `process_md_file(path)` | One `.md` file → `<section>` HTML string |
| `process_html_file(path)` | One `.html` file → `<section>` HTML string (legacy support) |
| `render_index_html(sections, title, base_url)` | Sections list → full `index.html` string |
| `run_build(slides_dir, output, project_root, ...)` | Full pipeline; writes `index.html`; returns sections list |
| `watch_mode(slides_dir, output, project_root, ...)` | Polls for changes, calls `run_build` on diff |
| `print_outline(slides_dir)` | Prints numbered slide titles to stdout |
| `lint_slides(slides_dir, project_root)` | Returns list of issue strings |
| `validate_images(html, project_root)` | Returns list of missing asset paths |
| `collect_notes(sections)` | Extracts `<aside class="notes">` text as plain string |

**Markdown extensions used:** `tables`, `fenced_code` (lang prefix `language-`), `md_in_html`.

**Processing order for each chunk:**
1. Strip YAML front matter → `<section>` attributes
2. Strip `<!-- .slide: key="val" -->` directive → `<section>` attributes (overrides front matter)
3. Split on bare `Note:` line → `<aside class="notes">`
4. `render_markdown()` on remaining content
5. Wrap in `<section>` with attributes

`background-*` keys are automatically prefixed with `data-` when building the `<section>` open tag.

### `src/slides_builder/serve.py`

Imports `slides_builder.build` directly (no subprocess). Provides `run_server(...)`.

Live-reload works by injecting a small polling script into `index.html` at serve time that
hits `/__reload__` every 800 ms and calls `location.reload()` when the version counter changes.

### `src/slides_builder/cli.py`

`argparse` with subparsers. Each subcommand dispatches to a `_cmd_*` function that imports
the relevant module lazily. The `gif` subcommand catches `ImportError` and prints a helpful
message if Pillow/numpy are missing.

### `src/slides_builder/tools/terminal_capture.py`

Runs a command in a Unix PTY (`pty.openpty`), captures output chunks with real timestamps,
and writes a JSON session file. No dependencies beyond stdlib.

JSON session format:
```json
{
  "version": 1,
  "title": "...",
  "command": "...",
  "recorded_at": "2026-04-24T...",
  "total_elapsed": 3.14,
  "events": [
    { "t": 0.0,   "type": "input",  "text": "the command" },
    { "t": 0.12,  "type": "output", "text": "first output chunk\n" }
  ]
}
```

### `src/slides_builder/tools/terminal_gif.py`

Same PTY capture as above, then renders each frame as a PIL `Image` and saves an animated
GIF. Requires `pillow` and `numpy` (`uv sync` installs them by default via
`dependency-groups.dev`).

---

## HTML template

`build.py` contains `HTML_TEMPLATE` — a Python format string. Key structure:

```
vendor/reveal.js/dist/reset.css
vendor/reveal.js/dist/reveal.css
vendor/reveal.js/dist/theme/white.css
vendor/highlight.js/github.min.css
css/default.css               ← custom theme (loaded last, highest specificity)
{slides_html}                 ← rendered <section> elements
vendor/reveal.js/dist/reveal.js
vendor/reveal.js/plugin/highlight/highlight.js
vendor/reveal.js/plugin/notes/notes.js
vendor/reveal.js/plugin/zoom/zoom.js
```

**All paths are relative.** Never use absolute paths or `<base href>` unless deploying to
a GitHub Pages project site at a subpath (use `--base-url /repo-name/` for that case).

Reveal.js is initialised with:
- `hash: true`, `slideNumber: 'c/t'`, `center: false`
- `width: 1280`, `height: 720`, `margin: 0.04`
- Plugins: `RevealHighlight`, `RevealNotes`, `RevealZoom`
- `RevealMarkdown` is **intentionally excluded**

---

## Slide authoring conventions

### File naming
Files are sorted alphabetically. Use numeric prefixes to control order:
```
slides/01-intro.md
slides/02-architecture.md
slides/03-demo.md
```

### Vertical sub-slides
A bare `---` line (not inside a fenced code block) splits a file into vertical sub-slides:
```markdown
## Slide A
Content.

---

## Slide B
Navigate down ↓ to reach this.
```
Multiple chunks → outer `<section>` wrapping inner `<section>` elements.

### Speaker notes
```markdown
## My Slide
Content here.

Note:
Everything after this line is speaker notes. Press S to open.
```
Becomes `<aside class="notes">` inside the section.

### Slide attributes

YAML front matter (first thing in the file or chunk):
```markdown
---
class: dark
background: "#1e293b"
---
## Slide title
```

Inline directive (anywhere in the chunk):
```html
<!-- .slide: class="dark" data-background="#1e293b" -->
```

Both produce attributes on the `<section>` tag. Inline directive overrides front matter.
`background-*` keys are automatically prefixed with `data-`.

### Two-column layout
```html
<div class="two-col">
<div markdown="1">

Left column markdown here.

</div>
<div markdown="1">

Right column markdown here.

</div>
</div>
```
The `two-col` class is defined in `css/default.css` as a two-column CSS grid.

### Raw HTML slides
Files with `.html` extension are supported for backward compatibility. The builder
extracts `<section>` elements from them directly without markdown processing.

---

## CSS and assets

### How CSS is resolved (both locally and in the action)

1. `<slides-dir>/css/` — **default**: lives alongside slide files (e.g. `slides/css/`)
2. `css/` at the repo root — legacy fallback
3. Built-in `slides/css/default.css` from the action itself

The chosen directory is copied to `output-dir/css/`. The HTML template loads `css/default.css`
(the filename is hardcoded in the template — name your file `default.css` or add it
alongside the existing one).

To override via `config.yaml`: set `css_dir: path/to/css`.

### Assets directory
`assets/` (configurable via `--assets-dir` / `assets-dir`) is copied to `output-dir/assets/`
if it exists. Reference assets with relative paths: `assets/image.png`, `assets/demo.json`.

### js/ directory
`js/terminal-player.js` is the **single canonical copy** of the browser-side session player.
The action copies `js/` to `output-dir/js/` automatically; the HTML template loads it from
`js/terminal-player.js`. Do not duplicate this file — edit it only in `js/`.

---

## GitHub Action (`action.yml`)

The action is a **composite** action. Steps in order:
1. Resolve absolute output path → `$GITHUB_OUTPUT`
2. Install uv via `astral-sh/setup-uv@v5`
3. `uv sync --frozen` (from the action's own directory)
4. `mkdir -p output-dir && cp -r vendor/ output-dir/vendor/ && cp -r js/ output-dir/js/`
5. Copy CSS (priority: `<slides-dir>/css/` → `css/` at repo root → action's `slides/css/`)
6. Copy `assets/` if it exists
7. `uv run slides build --slides-dir ... --output ... --no-backup [extra args]`

The tool reads `<slides-dir>/config.yaml` automatically. Action inputs act as overrides.
Most settings (title, output, serve port) belong in `config.yaml` rather than action inputs.

### Action inputs

| Input | Default | Notes |
|---|---|---|
| `slides-dir` | `slides` | Relative to `$GITHUB_WORKSPACE`; `config.yaml` is read from here |
| `output-dir` | `dist` | Relative to `$GITHUB_WORKSPACE` |
| `title` | _(empty)_ | Overrides `config.yaml` title |
| `base-url` | _(empty)_ | Only needed for project Pages sites at `/repo-name/` |
| `assets-dir` | `assets` | Copied to `output-dir/assets/` if present |
| `extra-build-args` | _(empty)_ | Appended verbatim to `slides build` |
| `provider` | `pages` | Informational: `pages` or `s3`; actual publish handled by `publish.yml` |

### Action output
`output-dir` — absolute path to the built directory (use with `upload-pages-artifact`).

---

## Terminal GIF tool — complete reference

See `tools/terminal-gif/AGENTS.md` for the full step-by-step workflow, demo script
templates, and embedding patterns. Summary:

### Capture a session
```bash
uv run slides capture "COMMAND" assets/NAME.json --title "TITLE"
```
Runs `COMMAND` in a PTY, saves timestamped JSON. No extra dependencies.

### Generate a GIF
```bash
uv run slides gif "COMMAND" assets/NAME.gif \
  --title "TITLE" \
  --width 1100 --height 660 --font-size 17 \
  --final-hold 10
```
Requires Pillow + numpy (installed by `uv sync`).

GIF sizing by context:

| Context | `--width` | `--height` | `--font-size` |
|---|---|---|---|
| Full-width slide | 1100 | 660 | 17 |
| Half-width slide | 720 | 480 | 14 |
| GitHub README | 900 | 540 | 15 |

Always use `--final-hold` ≥ 8 seconds.

### Embed the interactive player
The build system loads `js/terminal-player.js` and wires up the `slidechanged` handler
automatically. You only need the div — no extra `<script>` tags required:

```html
<!-- In each slide that uses the player -->

<!-- In each slide that uses the player -->
<div data-terminal-player="assets/NAME.json"
     data-height="340"
     data-final-hold="10000"
     data-loop="true">
</div>

<!-- GIF fallback for no-JS / PDF export -->
<noscript>
  <img src="assets/NAME.gif" style="width:100%" alt="terminal demo">
</noscript>
```

### TerminalPlayer options
```js
TerminalPlayer.create(element, 'session.json', {
  height:          340,    // px, terminal body height
  typingSpeed:      35,    // ms per character
  pauseBeforeType: 900,    // ms on empty terminal before typing
  pauseAfterType:  500,    // ms after command typed, before output
  finalHold:      9000,    // ms to hold on last frame
  loop:           true,
  autoplay:       true,
  speedMultiplier: 1.0,
  theme: {
    promptCol:  '#9ece6a',
    cmdCol:     '#e0e0f0',
    accentCol:  '#7aa2f7',
    timerText:  '#ffc832',
    fontFamily: '"Fira Code", monospace',
    fontSize:   '13.5px',
  },
});
```

---

## pyproject.toml structure

```toml
[project.scripts]
slides = "slides_builder.cli:main"

[project.optional-dependencies]
terminal = ["pillow>=10.0", "numpy>=1.24"]

[dependency-groups]
dev = ["slides-builder[terminal]"]   # installs terminal extras by default

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/slides_builder"]
```

`uv sync` installs the `dev` dependency group, which pulls in Pillow + numpy. If you
want a minimal install without the GIF dependencies: `uv sync --no-group dev`.

---

## CI workflows

**`ci.yml`** — runs on every push to `main` or `claude/**` branches:
1. `uv sync --frozen`
2. `uv run slides build --no-backup`
3. `uv run slides outline`
4. `uv run slides build --validate-images`

**`demo-pages.yml`** — runs on push to `main` when `slides/`, `css/`, `src/`, or
`action.yml` change. Self-referential: uses `jenningsanderson/slides@main` to build its
own `slides/` directory and deploy to `https://jenningsanderson.github.io/slides/`.

**`publish.yml`** — reusable workflow for consuming repositories. Supports both providers:
- `provider: pages` → `upload-pages-artifact` + `deploy-pages` (default)
- `provider: s3` → `aws s3 sync` with OIDC or static-key auth, optional CloudFront invalidation

S3 URL convention: `https://<bucket>/<owner>/<repo>/` (prefix derived from `GITHUB_REPOSITORY`
unless overridden by `deploy.s3.prefix` in config.yaml or the `s3-prefix` workflow input).

---

## Publish / deploy architecture

Build and publish concerns are separated:

| Concern | Module / file |
|---|---|
| Build static files | `build.py` → `slides build` |
| Deploy to Pages | CI workflow (`publish.yml` `deploy-pages` job) |
| Deploy to S3 | `publish.py` + CI workflow (`publish.yml` `deploy-s3` job) |

`slides publish` (local) validates config and, for S3, calls `aws s3 sync` directly.
In CI, the workflow handles the deploy steps; `slides publish --provider pages` prints
instructions and validates the output directory but does not call the Pages API.

### Using `slides publish` locally

```bash
# GitHub Pages — validates output, summarises what CI will deploy
uv run slides publish --output-dir dist

# S3 — uploads immediately (requires AWS credentials on PATH)
uv run slides publish --provider s3 --output-dir dist \
  --bucket slides.jenningsanderson.com

# Dry-run (print what would happen)
uv run slides publish --provider s3 --dry-run
```

### Config-driven publish (config.yaml)

```yaml
deploy:
  provider: s3
  s3:
    bucket: slides.jenningsanderson.com
    region: us-east-1
    prefix: myorg/myrepo          # optional; defaults to GITHUB_REPOSITORY
    cloudfront_distribution_id: EXXXXXXXXXXXXX
```

---

## Adding a new tool / extension

1. Add the implementation to `src/slides_builder/tools/new_tool.py` with a `main()` function.
2. Add a subcommand in `src/slides_builder/cli.py` — follow the `_cmd_capture` / `_cmd_gif`
   pattern: lazy import inside the handler, graceful `ImportError` message if optional deps
   are missing.
3. If new PyPI dependencies are needed:
   - Required → add to `[project.dependencies]`
   - Optional → add to `[project.optional-dependencies]` under a named extra
4. Run `uv sync` to update `uv.lock`.
5. Document the new subcommand in this file and in `README.md`.

---

## Common pitfalls

- **`---` inside fenced code blocks** is handled correctly — `split_on_hr()` tracks fence
  depth and ignores `---` between ` ``` ` pairs.
- **YAML front matter vs slide separator** — YAML front matter is only recognised at the
  very start of a chunk (before any content). A `---` elsewhere is a sub-slide separator.
- **Relative paths only** — the HTML template uses relative paths for all vendor/css/asset
  references. Do not introduce absolute URLs. Use `--base-url` only when the page is served
  from a non-root subpath.
- **`terminal-player.js` must be served** — it is fetched at runtime via `fetch()`. The
  action copies `js/terminal-player.js` to the output automatically. Do not duplicate the
  file — the canonical copy lives only in `js/`.
- **Both `.json` and `.gif` must be committed** — agents should always produce both formats
  and commit both files to the repo.
- **`--final-hold` < 8s** — do not do this; audiences need time to read terminal output.
