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
          base-url: '/${{ github.event.repository.name }}/'
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

### Custom HTML blocks

For multi-column layouts, use `markdown="1"` so the Python renderer processes the content inside:

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

## Action inputs

| Input | Default | Description |
|---|---|---|
| `slides-dir` | `slides` | Directory containing `.md` slide files |
| `output-dir` | `dist` | Output directory (contains `index.html` + assets) |
| `title` | `Slides` | Browser tab title |
| `base-url` | _(empty)_ | Set to `/repo-name/` for GitHub Pages project sites |
| `css-dir` | _(auto)_ | Custom CSS directory; uses action default if absent |
| `assets-dir` | `assets` | Assets directory copied into output if present |
| `extra-build-args` | _(empty)_ | Extra flags forwarded to `build.py` |

## Action outputs

| Output | Description |
|---|---|
| `output-dir` | Absolute path to the built presentation directory |

## Local development

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/jenningsanderson/slides
cd slides
uv sync

# Build once
uv run python build.py

# Live-reload dev server (http://localhost:3000)
uv run python server.py

# Useful flags
uv run python build.py --outline            # print slide order
uv run python build.py --lint               # check for missing notes, broken paths
uv run python build.py --validate-images    # check all asset paths exist
uv run python build.py --export-notes notes.txt
uv run python build.py --title "My Talk" --base-url /my-repo/
```

## Custom theme

Place CSS files in a `css/` directory in your repo — the action picks them up automatically. To start from the default theme:

```bash
# Copy the default theme into your repo
curl -O https://raw.githubusercontent.com/jenningsanderson/slides/main/css/default.css
mkdir -p css && mv default.css css/
```

The HTML template references `css/*.css` so any file you drop there will be loaded.

## How it works

All markdown is converted to static HTML by Python (`build.py`) before the browser loads anything — the [Reveal.js Markdown plugin](https://revealjs.com/markdown/) is intentionally excluded. This means:

- No flash of unrendered content
- Fenced code blocks output `class="language-xyz"` directly for highlight.js
- `Note:` sections become `<aside class="notes">` without client-side parsing
- The generated `index.html` is fully self-contained and works offline

Reveal.js 5.1.0 is vendored in this repository and copied into your output directory by the action.
