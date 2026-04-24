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

Place `terminal-player.js` in `assets/` and embed with a data attribute:

```html
<div data-terminal-player="assets/demo.json"
     data-height="340"
     data-final-hold="10000"
     data-loop="true">
</div>
```

Add to your Reveal initialisation (once per presentation):

```html
<script src="assets/terminal-player.js"></script>
<script>
  Reveal.on('slidechanged', ({ currentSlide }) => {
    const el = currentSlide.querySelector('[data-terminal-player]');
    if (!el || el._terminalPlayer) return;
    TerminalPlayer.create(el, el.dataset.terminalPlayer, {
      height: +(el.dataset.height || 340),
      finalHold: +(el.dataset.finalHold || 9000),
    });
  });
</script>
```

Note:
The player fetches the JSON at runtime via fetch(), so both the HTML and the JSON
file must be served together. Commit both assets/ files to git.
