# slides-builder

A GitHub Action and local dev tool for building [Reveal.js](https://revealjs.com) presentations from Markdown.

Drop `.md` files in a `slides/` folder → push → your presentation is published automatically.

**Default publish target:** GitHub Pages (`https://<owner>.github.io/<repo>/`)  
**Optional publish target:** S3 / CloudFront (`https://slides.jenningsanderson.com/<owner>/<repo>/`)

---

## GitHub Action quick start

### GitHub Pages (default)

```yaml
# .github/workflows/pages.yml
name: Deploy Slides
on:
  push:
    branches: [main]
    paths: ['slides/**', 'assets/**']

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

### Reusable workflow (Pages or S3)

Use the reusable `publish.yml` workflow to get both providers with a single line:

```yaml
# .github/workflows/slides.yml
name: Publish Slides
on:
  push:
    branches: [main]
    paths: ['slides/**', 'assets/**']

jobs:
  publish:
    uses: jenningsanderson/slides/.github/workflows/publish.yml@main
    with:
      provider: pages   # or s3
      slides-dir: slides
      output-dir: dist
      title: 'My Presentation'
    # For S3 only — supply secrets:
    # secrets:
    #   AWS_ROLE_ARN: ${{ secrets.AWS_ROLE_ARN }}
```

### S3 publishing

To publish to S3 (e.g. `slides.jenningsanderson.com/<owner>/<repo>/`):

1. Add a `deploy` section to `slides/config.yaml`:

```yaml
deploy:
  provider: s3
  s3:
    bucket: slides.jenningsanderson.com
    region: us-east-1
    # prefix: owner/repo    # optional; defaults to GITHUB_REPOSITORY
    # cloudfront_distribution_id: EXXXXXXXXXXXXX
```

2. Use the reusable workflow with `provider: s3` and one of:

   **OIDC role (recommended — no long-lived credentials):**
   ```yaml
   jobs:
     publish:
       uses: jenningsanderson/slides/.github/workflows/publish.yml@main
       with:
         provider: s3
         s3-bucket: slides.jenningsanderson.com
       secrets:
         AWS_ROLE_ARN: ${{ secrets.AWS_ROLE_ARN }}
   ```

   **Static key credentials (fallback):**
   ```yaml
   jobs:
     publish:
       uses: jenningsanderson/slides/.github/workflows/publish.yml@main
       with:
         provider: s3
         s3-bucket: slides.jenningsanderson.com
       secrets:
         AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
         AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
   ```

URL mapping: `https://slides.jenningsanderson.com/<owner>/<repo>/`

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

### Publishing locally

```bash
# GitHub Pages (validates output, actual deploy happens in CI)
uv run slides publish --provider pages --output-dir dist

# S3 (uploads immediately — requires AWS credentials in env)
uv run slides publish --provider s3 --output-dir dist \
  --bucket slides.jenningsanderson.com

# Dry-run (print what would be uploaded)
uv run slides publish --provider s3 --dry-run
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

## Config file

Project settings live in `slides/config.yaml` alongside your slides:

```yaml
title: My Presentation
# base_url: /my-repo/   # for GitHub Pages project sites
output: index.html
serve:
  port: 3000

# Deploy / publish settings (optional — defaults to GitHub Pages)
deploy:
  provider: pages          # pages | s3
  # path_prefix: ""        # optional; provider-agnostic base path
  s3:
    bucket: slides.jenningsanderson.com
    region: us-east-1
    # prefix: ""           # defaults to <owner>/<repo> from GITHUB_REPOSITORY
    # cloudfront_distribution_id: ""
    cache_control_html: "no-cache"
    cache_control_assets: "public,max-age=31536000,immutable"
```

## Custom theme

Place CSS files in `slides/css/` — right alongside your slide files. The action picks them up automatically, falling back to the built-in theme if none exist.

---

> For full technical details — architecture, CLI flags, build pipeline, action inputs, extending the tool — see [AGENTS.md](AGENTS.md).
