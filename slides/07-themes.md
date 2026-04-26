---
class: hero
---
# Slide Themes

## Three named layouts, ready to use from front matter

Note:
This slide itself uses the hero theme — class: hero in YAML front matter.
Content is centred and the h2 becomes a lightweight subtitle with no underline.
Good for opening slides and section dividers.

---
---
class: dark
background: "#1e293b"
---
## Dark Theme

Code demos, terminal output, and high-contrast moments.

- Apply with `class: dark` and a dark `background` in front matter
- All heading and body colours adapt to the dark surface
- Inline code styling shifts to light-on-dark automatically

```yaml
---
class: dark
background: "#1e293b"
---
## Your dark slide
```

Note:
This sub-slide is using the dark theme. The class: dark CSS rules adjust every text colour;
the background comes from Reveal.js via the data-background attribute set by front matter.
Pair it with "#0f172a" for a deeper navy or "#1e293b" for slate.

---
---
class: statement
---
> Great slides tell a story. Not a status report.

One `index.html` — no server, no CDN, no runtime dependencies.

Note:
Statement theme — class: statement in front matter.
Put your key takeaway in a blockquote (> ...) for the large bold treatment.
The paragraph below the blockquote renders at a smaller, muted size — good for attribution or a URL.

---

## Theme Reference

| Theme | Front matter | Best for |
|---|---|---|
| `hero` | `class: hero` | Title slides, section dividers |
| `dark` | `class: dark` + `background: "#1e293b"` | Code demos, terminal slides |
| `statement` | `class: statement` | Bold quotes, key takeaways |

Layout utilities: `two-col` (2 columns), `cols-3` (3 columns).

Note:
All themes are CSS classes in slides/css/default.css.
Add your own classes there — or drop a new .css file in css/ — to extend the set.
The two-col and cols-3 layout classes work inside any theme.
