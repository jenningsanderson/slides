# terminal-gif

A suite of tools for recording shell commands and playing them back as polished animations — either as an animated GIF or as an interactive, selectable-text HTML player.

## Tools

| Tool | Input | Output | Selectable text |
|------|-------|--------|-----------------|
| `terminal-gif` | command | `.gif` | No (raster) |
| `terminal-capture` | command | `.json` | — |
| `terminal-player.js` | `.json` | HTML `<div>` | **Yes** |

The recommended workflow is:
1. Run `terminal-capture` to record the command into a JSON session file
2. Embed `terminal-player.js` in your HTML/Reveal.js slide to play it back interactively
3. Optionally run `terminal-gif` to also generate a GIF for contexts where JS isn't available

---

## terminal-gif

Runs a shell command in a real PTY and renders the output as an animated GIF with a live timer pill.

## Requirements

```bash
pip install pillow numpy
```

No other dependencies. Uses only Python stdlib for PTY capture (`pty`, `select`, `subprocess`).

## Usage

```
terminal-gif "command" output.gif [options]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `command` | Shell command to run (quoted string) |
| `output` | Output `.gif` path |

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--title TEXT` | the command | Title shown in the terminal header bar |
| `--width INT` | 1100 | Canvas width in pixels |
| `--height INT` | 660 | Canvas height in pixels |
| `--font-size INT` | 17 | Font size in points |
| `--timer-ticks INT` | 8 | Number of timer tick frames during execution |
| `--pause-before FLOAT` | 1.0 | Seconds to hold on empty terminal before command appears |
| `--pause-after-cmd FLOAT` | 1.5 | Seconds to hold on the command before execution starts |
| `--final-hold FLOAT` | 10.0 | Seconds to hold on the final output frame |
| `--timeout FLOAT` | 120.0 | Max seconds to wait for the command to complete |
| `--max-lines INT` | 30 | Max lines visible on screen (older lines scroll off) |
| `--dry-run` | — | Skip execution; render a placeholder frame for layout testing |

## Examples

```bash
# Simple directory listing
terminal-gif "ls -lh" demo.gif

# DuckDB query with custom title and longer final hold
terminal-gif "duckdb -c 'SELECT 42 AS answer'" query.gif \
  --title "DuckDB — inline query" \
  --final-hold 8

# Python script, wider canvas
terminal-gif "python3 my_script.py" result.gif \
  --width 1200 --height 700 --font-size 16

# Test layout without running the command
terminal-gif "some-slow-command" test.gif --dry-run
```

## How it works

1. **Capture** — the command is launched in a Unix PTY (`pty.openpty`) so programs that detect a TTY behave normally (coloured output, progress bars, etc.). Output chunks are recorded with `time.monotonic()` timestamps as they arrive.

2. **Frame building** — the captured output is replayed as a sequence of keyframes:
   - Frame 0: empty terminal (pause before)
   - Frame 1: command prompt with the command text (pause after command)
   - Frames 2–N: timer pill ticking at evenly-spaced intervals across the real execution duration
   - Final frame: full output with a long hold

3. **Rendering** — each frame is drawn with PIL onto an RGB canvas using a monospace font. The header bar shows the title; a yellow timer pill appears during execution.

4. **Saving** — PIL's GIF encoder is used directly (not imageio) to ensure per-frame `duration` values are correctly written into the Graphic Control Extension blocks.

## Fonts

The renderer looks for monospace fonts in this order:

1. `LiberationMono-Regular` (Linux default)
2. `DejaVuSansMono`
3. `UbuntuMono-R`
4. PIL built-in fallback

## Notes

- ANSI escape codes are stripped before rendering. Coloured terminal output is not reproduced — all output is rendered in a uniform light-grey palette.
- The PTY approach means interactive programs that require user input will hang until `--timeout` is reached. For interactive sessions, consider scripting the input with `expect` or `echo "input" | command`.
- GIF colour depth is limited to 256 colours per frame. The dark-background palette used here stays well within that limit.

---

## terminal-capture

Records a shell command into a JSON session file for playback by `terminal-player.js`.

### Usage

```bash
python3 terminal-capture "command" output.json [options]
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--title TEXT` | the command | Title shown in the terminal header |
| `--timeout FLOAT` | 120.0 | Max seconds to wait for the command |

### Examples

```bash
python3 terminal-capture "ls -lh" session.json
python3 terminal-capture "duckdb -c 'SELECT 42'" query.json --title "DuckDB query"
```

### JSON format

```json
{
  "version": 1,
  "title": "GERS Registry Lookup",
  "command": "duckdb ...",
  "recorded_at": "2026-04-22T05:00:00+00:00",
  "total_elapsed": 6.21,
  "events": [
    { "t": 0.0,  "type": "input",  "text": "duckdb -c \"...\"" },
    { "t": 1.52, "type": "output", "text": "Connecting...\n" },
    { "t": 6.21, "type": "output", "text": "1 row\n" }
  ]
}
```

---

## terminal-player.js

A zero-dependency JavaScript library that reads a JSON session file and animates it inside a styled `<div>` with fully selectable text, a live timer, and playback controls (play/pause/restart).

### Quick start

```html
<!-- 1. Add a container div -->
<div id="my-term" style="height: 300px;"></div>

<!-- 2. Load the player -->
<script src="terminal-player.js"></script>

<!-- 3. Create a player instance -->
<script>
  TerminalPlayer.create('#my-term', 'session.json');
</script>
```

### Auto-init via data attributes

```html
<div data-terminal-player="session.json"
     data-typing-speed="40"
     data-final-hold="8000"
     data-loop="true"
     style="height: 300px;">
</div>
<script src="terminal-player.js"></script>
<!-- No JS needed — auto-initialises on DOMContentLoaded -->
```

### API

```js
// Create a player in a container element
TerminalPlayer.create(selector, jsonUrl, opts)  // → Promise<player>

// Append a new div inside a parent and create a player
TerminalPlayer.embed(parentSelector, jsonUrl, opts)  // → Promise<player>

// Auto-initialise all [data-terminal-player] elements
TerminalPlayer.autoInit()
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `typingSpeed` | 35 | ms per character when typing the command |
| `pauseBeforeType` | 900 | ms pause before typing starts |
| `pauseAfterType` | 500 | ms pause after command typed, before output |
| `finalHold` | 9000 | ms to hold on the last frame before looping |
| `loop` | `true` | Whether to loop the animation |
| `autoplay` | `true` | Start playing immediately |
| `speedMultiplier` | 1.0 | Global speed factor (0.5 = half speed, 2 = double) |
| `theme` | (dark) | Object of colour/font overrides |

### Player instance methods

```js
const player = await TerminalPlayer.create('#term', 'session.json');
player.play();     // start / resume
player.pause();    // pause
player.restart();  // restart from beginning
```

### Use in Reveal.js

```html
<!-- In a slide section -->
<section>
  <h2>GERS Registry Lookup</h2>
  <div id="gers-demo" style="height: 340px; font-size: 13px;"></div>
</section>

<script>
  // Initialise when the slide becomes visible
  Reveal.on('slidechanged', ({ currentSlide }) => {
    const el = currentSlide.querySelector('#gers-demo');
    if (el && !el._terminalPlayer) {
      TerminalPlayer.create(el, 'assets/gers-session.json', {
        finalHold: 10000,
        loop: true,
      });
    }
  });
</script>
```
