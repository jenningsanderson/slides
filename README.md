# slides-builder

A GitHub Action and local dev tool for building [Reveal.js](https://revealjs.com) presentations from Markdown.

Drop `.md` files in a `slides/` folder → push → GitHub Pages serves a fully static presentation.

---

## GitHub Action quick start

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

Enable **Settings → Pages → Source: GitHub Actions** in your repo.

---

## Local development

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/jenningsanderson/slides
cd slides
uv sync

uv run slides build          # build → index.html
uv run slides serve          # live-reload at http://localhost:3000
uv run slides outline        # print slide order
uv run slides lint           # check notes, alt text, broken paths
uv run slides --help         # all commands and flags
```

---

## Writing slides

| Convention | Effect |
|---|---|
| `01-intro.md`, `02-demo.md` | Alphabetical order → presentation order |
| `---` on its own line | New vertical sub-slide (↓ to navigate) |
| `Note:` on its own line | Speaker notes (press `S` to open) |
| ` ```python ` fenced blocks | Syntax-highlighted via highlight.js |
| GFM pipe tables | Rendered as `<table>` |
| `<!-- .slide: class="dark" -->` | Reveal.js `<section>` attribute |
| YAML front matter `--- class: dark ---` | Same as above |
| `markdown="1"` on an HTML element | Markdown inside custom HTML blocks |

---

## Terminal GIF tool

Record any shell command as an interactive player or animated GIF for your slides.

```bash
uv run slides capture "python3 demo.py" assets/demo.json --title "My Demo"
uv run slides gif     "python3 demo.py" assets/demo.gif  --final-hold 10
```

Embed the interactive player in a slide:

```html
<div data-terminal-player="assets/demo.json"
     data-height="340" data-final-hold="10000" data-loop="true"></div>
```

---

## Custom theme

Place any `.css` files in a `css/` directory — the action picks them up automatically, falling back to the built-in `css/default.css` if none exist.

---

> For full technical details — architecture, CLI flags, build pipeline, action inputs, extending the tool — see [AGENTS.md](AGENTS.md).
