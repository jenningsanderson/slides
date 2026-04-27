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
---
class: "hero vaporwave"
background-gradient: "linear-gradient(135deg, #0d0015 0%, #1a003a 100%)"
---
# Vaporwave

## Neon palette for high-impact moments

Note:
Vaporwave theme — class: "hero vaporwave" with a CSS gradient background.
The h1 gets a pink-to-cyan gradient text fill via background-clip: text.
Combine with hero for a title card, or use standalone for a vivid section break.

---
---
class: vaporwave
background: "#0d0015"
---
## Vaporwave: Body Slide

<div class="two-col">
<div markdown="1">

#### Colours

- `--vp-pink`  `#ff71ce` — headings, borders
- `--vp-cyan`  `#01cdfe` — h3, links, table headers
- `--vp-green` `#05ffa1` — h4 labels
- `--vp-text`  `#e0d0ff` — body copy
- `--vp-muted` `#b090d0` — secondary text

</div>
<div markdown="1">

#### Usage

```yaml
---
class: vaporwave
background: "#0d0015"
---
## Your neon slide

# Or combine with hero
class: "hero vaporwave"
background-gradient: "linear-gradient(
  135deg, #0d0015, #1a003a)"
```

</div>
</div>

Note:
Pair vaporwave with background: "#0d0015" for the deep purple-black base.
background-gradient also works via front matter — Reveal.js renders it as a CSS gradient.

---

## Theme Reference

| Theme | Front matter | Best for |
|---|---|---|
| `hero` | `class: hero` | Title slides, section dividers |
| `dark` | `class: dark` + `background: "#1e293b"` | Code demos, terminal slides |
| `statement` | `class: statement` | Bold quotes, key takeaways |
| `vaporwave` | `class: vaporwave` + `background: "#0d0015"` | High-impact sections, title cards |

Layout utilities: `two-col` (2 columns), `cols-3` (3 columns).  
Themes compose: `class: "hero vaporwave"` stacks both.

Note:
All themes are CSS classes in slides/css/default.css.
Add your own classes there — or drop a new .css file in css/ — to extend the set.
The two-col and cols-3 layout classes work inside any theme.
background-gradient is also supported in front matter and maps to Reveal.js data-background-gradient.
