## Terminal GIF Tool

Turn any shell command into a polished presentation demo.

<div class="two-col">
<div markdown="1">

#### Animated GIF — no JS needed

```bash
uv run slides gif \
  "python3 demo.py" \
  assets/demo.gif \
  --title "Demo" \
  --final-hold 10
```

Best for: PDF exports, GitHub READMEs, fallbacks

</div>
<div markdown="1">

#### Interactive JSON player

```bash
uv run slides capture \
  "python3 demo.py" \
  assets/demo.json \
  --title "Demo"
```

Text is selectable. Loops in the browser.

</div>
</div>

Note:
Always produce both formats. The JSON + player is the primary experience; the GIF
is the fallback for static contexts.

---

## Embedding the Player

`terminal-player.js` is bundled automatically — just add the `data-terminal-player`
attribute to a div:

```html
<div data-terminal-player="assets/demo.json"
     data-height="340"
     data-final-hold="10000"
     data-loop="true">
</div>
```

The build system loads `js/terminal-player.js` and wires up the `slidechanged` handler
for you. No extra `<script>` tags needed.

Note:
The player fetches the JSON at runtime via fetch(), so the HTML must be served —
opening index.html directly from the filesystem won't work. Use uv run slides serve
for local development. Commit both the .json and .gif to git.
