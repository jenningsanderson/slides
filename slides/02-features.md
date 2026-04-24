## Markdown Features

<div class="two-col">
<div markdown="1">

#### In every slide

- `---` on its own line → vertical sub-slide ↓
- `Note:` → speaker notes (`S` to open)
- ` ```python ` fenced blocks → syntax-highlighted
- GFM pipe tables
- `markdown="1"` inside HTML blocks

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
All markdown is converted to static HTML by Python before the browser loads anything.
No flash of unrendered content. No dependency on the RevealMarkdown plugin.

---

## Vertical Sub-slides

Separate sections within one file with `---`.

Navigate **down ↓** to reach this slide from the previous one.

| File | Becomes |
|---|---|
| Single `.md`, no `---` | One horizontal slide |
| Single `.md` with `---` | Vertical stack |
| `01-intro.md`, `02-demo.md` | Two horizontal slides |

Note:
Each .md file is one horizontal entry. The --- separator creates vertical sub-slides within a file.

---

## Syntax Highlighting

All fenced code blocks are highlighted via highlight.js (GitHub theme).

```python
from slides_builder import build

sections = build.discover_slides("slides/")
html = build.render_index_html(sections, title="My Talk")
Path("index.html").write_text(html)
```

```bash
# Build once
uv run slides build

# Dev server with live reload
uv run slides serve
```

Note:
Code blocks produce class="language-xyz" directly on the pre/code elements,
which highlight.js picks up without any server-side processing.
