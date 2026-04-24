# slides-builder

A GitHub Action and local dev tool for building [Reveal.js](https://revealjs.com) presentations from Markdown.

Drop `.md` files in a `slides/` folder → get a fully rendered, static presentation with syntax highlighting, speaker notes, vertical sub-slides, and optional GitHub Pages deployment.

## Quick start

```yaml
# .github/workflows/pages.yml
name: Deploy Slides
on:
  push:
    branches: [main]
    paths: ['slides/**', 'css/**', 'assets/**']

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: jenningsanderson/slides@main
        with:
          slides-dir: slides
          output-dir: dist
          title: 'My Presentation'
      - uses: actions/upload-pages-artifact@v3
        with:
          path: dist

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/deploy-pages@v4
        id: deployment
```

Then enable **Settings → Pages → Source: GitHub Actions** in your repo.

## Slide conventions

| Convention | Effect |
|---|---|
| Files named `01-intro.md`, `02-demo.md` | Sorted alphabetically → presentation order |
| `---` on its own line | New vertical sub-slide (navigate with ↓) |
| `Note:` on its own line | Everything below becomes speaker notes (`S` to open) |
| ` ```python ` fenced blocks | Syntax-highlighted via highlight.js |
| GFM pipe tables | Rendered as `<table>` |
| `<!-- .slide: class="dark" -->` | Reveal.js slide directive — applied to `<section>` |
| YAML front matter (`---\nclass: dark\n---`) | Same as above |
| `markdown="1"` on HTML elements | Enables markdown inside custom HTML blocks |

### Vertical sub-slides

```markdown
## First sub-slide

Content here.

---

## Second sub-slide

More content. Navigate down (↓) to reach this.

Note:
Speaker notes for the second sub-slide.
```

### Two-column layout

```html
<div class="two-col">
<div markdown="1">

#### Left column

Markdown works here.

</div>
<div markdown="1">

#### Right column

And here too.

</div>
</div>
```

## Local development

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/jenningsanderson/slides
cd slides
uv sync

# All commands go through the unified CLI
uv run slides --help

# Build once
uv run slides build

# Live-reload dev server (http://localhost:3000)
uv run slides serve

# Utilities
uv run slides outline          # print slide order
uv run slides lint             # check for missing notes, broken paths
uv run slides watch            # rebuild on file change

# Build flags
uv run slides build --title "My Talk"
uv run slides build --output dist/index.html
uv run slides build --validate-images
uv run slides build --export-notes notes.txt
```

## Terminal GIF tool

Record any shell command as an animated terminal GIF or interactive JSON player for your slides.

```bash
# Capture a command to JSON (interactive player, selectable text)
uv run slides capture "python3 demo.py" assets/demo.json --title "Demo"

# Render an animated GIF (no-JS fallback, works in GitHub READMEs)
uv run slides gif "python3 demo.py" assets/demo.gif --final-hold 10

# The gif subcommand needs Pillow + numpy (installed by default with uv sync)
```

See [`tools/terminal-gif/AGENTS.md`](tools/terminal-gif/AGENTS.md) for full embedding instructions and the `TerminalPlayer` API reference.

## Custom theme

Place CSS files in a `css/` directory in your repo — the action picks them up automatically.

```bash
# Copy the default theme to start from
cp css/default.css css/my-theme.css
# Edit css/my-theme.css, then rebuild
uv run slides build
```

The action uses your `css/` directory if it exists, otherwise falls back to its built-in `default.css`.

## Action inputs

| Input | Default | Description |
|---|---|---|
| `slides-dir` | `slides` | Directory containing `.md` slide files |
| `output-dir` | `dist` | Output directory (contains `index.html` + assets) |
| `title` | `Slides` | Browser tab title |
| `base-url` | _(empty)_ | Set to `/repo-name/` for GitHub Pages project sites |
| `css-dir` | _(auto)_ | Custom CSS directory; uses `css/` if present, else built-in |
| `assets-dir` | `assets` | Assets directory copied into output if present |
| `extra-build-args` | _(empty)_ | Extra flags forwarded to `slides build` |

## Action outputs

| Output | Description |
|---|---|
| `output-dir` | Absolute path to the built presentation directory |

## How it works

All markdown is converted to static HTML by Python before the browser loads anything — the [Reveal.js Markdown plugin](https://revealjs.com/markdown/) is intentionally excluded. This means:

- No flash of unrendered content
- Fenced code blocks output `class="language-xyz"` directly for highlight.js
- `Note:` sections become `<aside class="notes">` without client-side parsing
- All asset paths are **relative** — the presentation works offline and from any subdirectory
- The generated `index.html` is fully self-contained

Reveal.js 5.1.0 is vendored in this repository and copied into your output directory by the action.

## Project structure

```
slides-builder/
├── src/slides_builder/     ← Python package
│   ├── build.py            ← core build logic
│   ├── serve.py            ← live-reload dev server
│   ├── cli.py              ← unified entry point (slides …)
│   └── tools/
│       ├── terminal_capture.py
│       └── terminal_gif.py
├── tools/terminal-gif/
│   ├── terminal-player.js  ← browser-side JSON player
│   └── AGENTS.md           ← agent instructions for building demos
├── slides/                 ← example presentation source
├── css/                    ← default theme
├── assets/                 ← terminal-player.js for the demo
├── vendor/                 ← vendored Reveal.js 5.1.0
├── action.yml              ← GitHub Action definition
└── pyproject.toml
```
