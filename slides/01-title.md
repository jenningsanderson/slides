## slides-builder

Build [Reveal.js](https://revealjs.com) presentations from Markdown files.

- Drop `.md` files into a `slides/` folder
- Number them (`01-intro.md`, `02-demo.md`) to control order
- Push — GitHub Actions builds and deploys automatically

```yaml
uses: jenningsanderson/slides@main
with:
  slides-dir: slides
  output-dir: dist
  title: 'My Talk'
```

Note:
Welcome! This is the title slide. Speaker notes appear after a bare "Note:" line.
Press S to open the speaker notes window. Use arrow keys to navigate.
