## Slide Features

<div class="two-col">
<div markdown="1">

#### Markdown conventions

- `---` on its own line → vertical sub-slide
- `Note:` → speaker notes (`S` to open)
- ` ```python ` fenced blocks → syntax-highlighted
- GFM pipe tables supported

</div>
<div markdown="1">

#### Front matter & directives

```yaml
---
class: dark
background: "#1e293b"
---
## Dark slide
```

Or inline:

```html
<!-- .slide: class="dark" -->
```

</div>
</div>

Note:
The action ships Reveal.js 5.1.0 vendored locally — no CDN required.
All markdown is rendered to static HTML by Python before the browser loads a single byte, so there is no flash of unrendered content and no dependency on the RevealMarkdown plugin.

---

## Vertical Sub-slides

Separate sections within one file with `---`.

This slide is a sub-slide of the previous one.
Navigate **down** (↓) to reach it.

Note:
Each .md file becomes one horizontal slide. Use --- inside the file to create a vertical stack.
