## GitHub Action

Enable in any repo with a `slides/` folder.

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

Note:
Enable Settings → Pages → Source: GitHub Actions in your repo.
The action vendors Reveal.js locally — no CDN required, works offline.

---

## Action Inputs

| Input | Default | Description |
|---|---|---|
| `slides-dir` | `slides` | Directory of `.md` source files |
| `output-dir` | `dist` | Where to write `index.html` + assets |
| `title` | `Slides` | Browser tab title |
| `base-url` | _(empty)_ | Set to `/repo-name/` for project Pages sites |
| `css-dir` | _(auto)_ | Custom CSS dir; uses `css/` if present, else built-in |
| `assets-dir` | `assets` | Assets directory copied into output |
| `extra-build-args` | _(empty)_ | Extra flags forwarded to `slides build` |

All asset paths in the generated HTML are **relative** — the presentation works
when served from any subdirectory or opened directly from the filesystem.

Note:
The base-url input is only needed for GitHub Pages project sites where the repo
is served at /repo-name/ rather than the root. It sets a <base href> element.
For user/org Pages (served at root), leave it empty.
