## Using in Your Repo

#### 1. Add slides

```
your-repo/
├── slides/
│   ├── 01-intro.md
│   ├── 02-demo.md
│   └── 03-end.md
└── .github/
    └── workflows/
        └── pages.yml
```

#### 2. Add the workflow

```yaml
- uses: jenningsanderson/slides@main
  with:
    slides-dir: slides
    output-dir: dist
    title: 'My Presentation'
    base-url: '/your-repo/'
```

#### 3. Enable GitHub Pages

Settings → Pages → Source: **GitHub Actions**

Note:
That's it. The action copies the Reveal.js vendor files from its own repo into your dist/ directory, so you don't need to vendor anything yourself.
