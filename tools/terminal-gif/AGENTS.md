# Agent Instructions — terminal-gif toolset

This document tells an LLM agent how to use the `terminal-gif` toolset to build presentations
with polished, executable code demonstrations. Read this file before writing any slides that
include command-line or code output.

---

## What this toolset does

The toolset turns any shell command into a presentation-ready animation in two formats:

| Format | File | Selectable text | Requires JS | Best for |
|--------|------|-----------------|-------------|----------|
| **Interactive HTML player** | `.json` + `terminal-player.js` | **Yes** | Yes | Reveal.js slides, web pages |
| **Animated GIF** | `.gif` | No | No | GitHub READMEs, email, Slack, PDF exports |

**Always produce both.** The JSON + player is the primary experience; the GIF is the fallback.

---

## Tool locations

The capture and gif commands are part of the `slides` CLI (package: `slides_builder`):

```
src/slides_builder/tools/
├── terminal_capture.py     ← slides capture implementation
└── terminal_gif.py         ← slides gif implementation

tools/terminal-gif/
├── terminal-player.js      ← JavaScript: play a JSON session in a <div>
├── AGENTS.md               ← this file
├── README.md
└── examples/
    ├── example.json
    ├── example.gif
    └── example.html
```

Run both tools via the unified CLI (from the repo root, after `uv sync`):

```bash
uv run slides capture "command" output.json
uv run slides gif     "command" output.gif
```

---

## Step-by-step workflow

### 1. Write and test the command first

Before recording, run the command in a real shell and confirm it produces the output you want.
Commands that require user interaction, passwords, or a specific working directory will not work
reliably in a PTY capture — script them to be fully non-interactive.

```bash
# Good — fully non-interactive
duckdb -c "SELECT count(*) FROM read_parquet('s3://...')"

# Bad — requires user input
duckdb   # opens interactive REPL
```

For multi-step workflows, write a small script and record the script:

```bash
python3 my_demo_script.py
```

### 2. Record the session

```bash
uv run slides capture \
  "python3 demos/gers_lookup.py" \
  assets/gers-lookup.json \
  --title "DuckDB — GERS registry lookup"
```

This runs the command in a Unix PTY (so programs that detect a TTY behave normally),
captures each output chunk with a real timestamp, and writes a JSON session file.

**Check the output:** open the JSON and verify `total_elapsed` is reasonable and `events`
contains the expected output lines. If the command timed out, increase `--timeout`.

### 3. Generate the GIF

```bash
uv run slides gif \
  "python3 demos/gers_lookup.py" \
  assets/gers-lookup.gif \
  --title "DuckDB — GERS registry lookup" \
  --final-hold 10
```

**GIF sizing guidelines:**

| Context | `--width` | `--height` | `--font-size` |
|---------|-----------|------------|---------------|
| Reveal.js slide (full-width) | 1100 | 660 | 17 |
| Reveal.js slide (half-width) | 720 | 480 | 14 |
| GitHub README | 900 | 540 | 15 |
| Narrow column | 640 | 400 | 13 |

Always set `--final-hold` to at least **8 seconds** so audiences can read the output.
For complex results (tables, multi-line output), use **10–12 seconds**.

### 4. Embed the player in a Reveal.js slide

Copy `terminal-player.js` to your assets directory (or reference it from `tools/terminal-gif/`).

**In an HTML slide section:**

```html
<section>
  <h2>GERS Registry Lookup</h2>
  <p>Query the registry once, then fetch the exact feature in one targeted file.</p>

  <div id="gers-demo"></div>
</section>
```

**In your Reveal initialisation script:**

```html
<script src="assets/terminal-player.js"></script>
<script>
  Reveal.on('slidechanged', ({ currentSlide }) => {
    const el = currentSlide.querySelector('[data-terminal-player]') ||
               currentSlide.querySelector('#gers-demo');
    if (!el || el._terminalPlayer) return;

    // data-attribute style (preferred for HTML slides)
    if (el.dataset.terminalPlayer) {
      TerminalPlayer.create(el, el.dataset.terminalPlayer, {
        height:    +(el.dataset.height    || 340),
        finalHold: +(el.dataset.finalHold || 9000),
        loop:      el.dataset.loop !== 'false',
      });
    }
    // Or JS API style
    else {
      TerminalPlayer.create(el, 'assets/gers-lookup.json', {
        height:    340,
        finalHold: 10000,
        loop:      true,
      });
    }
  });
</script>
```

**Preferred: use `data-terminal-player` directly on the div** (zero extra JS per slide):

```html
<div data-terminal-player="assets/gers-lookup.json"
     data-height="340"
     data-final-hold="10000"
     data-loop="true">
</div>
```

### 5. Add a GIF fallback for the same slide

Always include the GIF as a `<noscript>` fallback or in a speaker-notes aside:

```html
<aside class="notes">
  <img src="assets/gers-lookup.gif" alt="GERS lookup demo">
</aside>
```

Or add it as a visible fallback below the player:

```html
<noscript>
  <img src="assets/gers-lookup.gif" style="width:100%">
</noscript>
```

---

## Naming conventions

Use descriptive, kebab-case names that reflect the demo content:

| Demo | JSON | GIF |
|------|------|-----|
| GERS registry lookup | `gers-registry-lookup.json` | `gers-registry-lookup.gif` |
| DuckDB GROUP BY query | `duckdb-groupby-slc.json` | `duckdb-groupby-slc.gif` |
| overturemaps CLI | `overturemaps-cli-demo.json` | `overturemaps-cli-demo.gif` |

Store all session files and GIFs in the presentation's `assets/` directory.

---

## Writing good demo scripts

For multi-step workflows, write a Python (or shell) script that:

1. **Prints step headers** as SQL comments (`-- Step 1: ...`) so the viewer knows what's happening
2. **Simulates realistic timing** — add `time.sleep()` pauses between steps to make the
   animation readable; 1–2 seconds between logical steps is ideal
3. **Produces clean, readable output** — DuckDB's box-drawing table output renders beautifully;
   aim for tables with 3–6 columns and fewer than 20 rows
4. **Ends with a clear summary line** — e.g. `1 row · 2.3 s` — so the final hold frame is
   informative

**Template for a two-step DuckDB demo:**

```python
#!/usr/bin/env python3
"""
Demo: look up a GERS ID, then fetch the exact feature.
Run with: python3 demos/gers_lookup.py
"""
import subprocess, time

GERS_ID = "379baf1c-d0ab-47e8-b6f6-d9ea16392fb7"

def run(sql, label=None):
    if label:
        print(f"-- {label}")
    result = subprocess.run(
        ["duckdb", "-c", sql],
        capture_output=False, text=True
    )
    time.sleep(0.5)

# Step 1
run(f"""
CREATE OR REPLACE TABLE result AS
  SELECT id, theme, type, path, bbox
  FROM read_parquet('s3://overturemaps-us-west-2/registry/*.parquet')
  WHERE id = '{GERS_ID}';
""", label="Step 1: query the GERS registry")

run("FROM result SELECT *;")
time.sleep(1.0)

# Step 2
run(f"""
SET VARIABLE path = (SELECT path FROM result);
SET VARIABLE bbox = (SELECT bbox FROM result);
""", label="Step 2: set variables from the table (no re-scan)")

time.sleep(0.5)

# Step 3
run(f"""
SELECT id, names.primary AS name, categories.primary AS category,
       confidence, addresses[1].freeform AS address
FROM read_parquet('s3://overturemaps-us-west-2/release/2026-04-15.0/'
                  || getvariable('path'))
WHERE id = '{GERS_ID}'
  AND bbox.xmin >= getvariable('bbox').xmin;
""", label="Step 3: fetch the exact feature using path + bbox as predicates")
```

---

## Player options reference

```js
TerminalPlayer.create('#container', 'session.json', {
  // Layout
  height:           340,    // px — fixed terminal body height (default: 340)

  // Timing (all in milliseconds)
  typingSpeed:       35,    // ms per character when typing the command
  pauseBeforeType:  900,    // ms pause on empty terminal before typing
  pauseAfterType:   500,    // ms pause after command is typed, before output
  finalHold:       9000,    // ms to hold on the last output frame

  // Playback
  loop:             true,   // loop after finalHold
  autoplay:         true,   // start immediately
  speedMultiplier:  1.0,    // 0.5 = half speed, 2.0 = double speed

  // Theme overrides (all optional)
  theme: {
    promptCol:  '#9ece6a',  // prompt ❯ colour
    cmdCol:     '#e0e0f0',  // command text colour
    accentCol:  '#7aa2f7',  // SQL keywords, table summaries
    timerText:  '#ffc832',  // timer pill text
    fontFamily: '"Fira Code", monospace',
    fontSize:   '13.5px',
  },
});
```

**Data attribute equivalents** (all options that have a data-* form):

```html
<div data-terminal-player="session.json"
     data-height="340"
     data-typing-speed="35"
     data-pause-before-type="900"
     data-pause-after-type="500"
     data-final-hold="9000"
     data-loop="true"
     data-autoplay="true"
     data-speed-multiplier="1.0">
</div>
```

---

## Syntax colouring

The player automatically colours output based on content patterns:

| Pattern | Colour | Example |
|---------|--------|---------|
| SQL keywords at line start | Blue accent | `SELECT`, `FROM`, `WHERE`, `SET`, `CREATE` |
| Table border rows | Dim grey | `┌──────┐`, `├──────┤` |
| Numbers in table cells | Orange | `119966`, `0.9978` |
| Row summary lines | Accent | `2 rows · 69250 ms` |
| Comment lines (`-- ...`) | Dim italic | `-- Step 1: ...` |

No configuration needed — colouring is applied automatically.

---

## Reveal.js vertical slides pattern

When a slide has multiple demo steps, use Reveal.js vertical sub-slides so the main
horizontal flow is not interrupted. The parent slide introduces the concept; sub-slides
walk through each step.

```html
<!-- In your slides HTML file -->
<section>
  <!-- Parent slide: overview -->
  <section>
    <h2>GERS: Global Entity Reference System</h2>
    <p>Every Overture feature has a stable ID. Look it up anywhere.</p>
  </section>

  <!-- Sub-slide 1: registry query -->
  <section>
    <h3>Step 1 — Query the registry</h3>
    <div data-terminal-player="assets/gers-step1.json"
         data-height="320" data-final-hold="8000"></div>
  </section>

  <!-- Sub-slide 2: fetch the feature -->
  <section>
    <h3>Step 2 — Fetch the exact feature</h3>
    <div data-terminal-player="assets/gers-step2.json"
         data-height="320" data-final-hold="10000"></div>
  </section>
</section>
```

In a Markdown-driven Reveal.js deck, vertical slides are separated by `---` (horizontal)
and `--` (vertical) by default, but HTML slide files with nested `<section>` elements
give more control over player initialisation.

---

## Decision guide

Use this table to decide which format to produce for each demo:

| Situation | Recommendation |
|-----------|----------------|
| Reveal.js slide with internet access | JSON + `terminal-player.js` (primary), GIF (fallback) |
| Reveal.js slide exported to PDF | GIF only |
| GitHub README | GIF only |
| Documentation site (MkDocs, Docusaurus) | JSON + player preferred; GIF as fallback |
| Email or Slack | GIF only |
| The demo output is very wide (>120 chars) | JSON + player (horizontal scroll); GIF may clip |
| The demo takes >60 seconds to run | Pre-record with a scripted mock; do not use real command |
| The demo requires credentials or secrets | Pre-record with a scripted mock; never embed real credentials |

---

## Common mistakes to avoid

**Do not** set `--final-hold` below 8 seconds. Audiences need time to read the output,
especially in a live presentation where they cannot pause.

**Do not** record commands that produce more than ~40 lines of output without scrolling.
The GIF renderer clips at `--max-lines` (default 30); the JS player scrolls but very long
output is hard to read. Trim output with `LIMIT`, `HEAD`, or `grep` as appropriate.

**Do not** use `--dry-run` in production. It is only for testing layout.

**Do not** hardcode absolute paths in demo scripts. Use paths relative to the repo root
or environment variables so the demo works on any machine.

**Do not** forget to commit both the `.json` and `.gif` files to the repo. The player
fetches the JSON at runtime via `fetch()`, so it must be served alongside the HTML.

---

## Quick reference

```bash
# Record a session
uv run slides capture "CMD" assets/NAME.json --title "TITLE"

# Generate a GIF
uv run slides gif "CMD" assets/NAME.gif --title "TITLE" --final-hold 10

# Embed in a slide (data attribute — zero JS)
<div data-terminal-player="assets/NAME.json"
     data-height="340" data-final-hold="10000" data-loop="true"></div>

# Embed in a slide (JS API — use when you need slidechanged hook)
TerminalPlayer.create('#id', 'assets/NAME.json', { height: 340, finalHold: 10000 });

# Player script tag (once per HTML file)
<script src="assets/terminal-player.js"></script>
```
