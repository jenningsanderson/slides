## slides-builder

A GitHub Action and local dev tool for building
[Reveal.js](https://revealjs.com) presentations from Markdown.

- Drop `.md` files in a `slides/` folder
- Number them (`01-intro.md`, `02-demo.md`) to control order
- Push — GitHub Actions builds and deploys the presentation

```
uses: jenningsanderson/slides@main
with:
  slides-dir: slides
  output-dir: dist
  title: 'My Talk'
  base-url: '/my-repo/'
```

Note:
This is the title slide. Speaker notes go after a bare "Note:" line and appear when you press S.
